import enum
import gzip
import logging
import os
import random
import re
import typing

import edq.util.serial

import chessai.core.action
import chessai.core.board
import chessai.core.castling
import chessai.core.coordinate
import chessai.core.gamestate
import chessai.core.piece
import chessai.core.types

THIS_DIR: str = os.path.join(os.path.dirname(os.path.realpath(__file__)))
GAMES_DIR: str = os.path.join(THIS_DIR, '..', 'resources', 'games')

PGN_FILE_EXTENSION: str = '.pgn'
GZIP_FILE_EXTENSION: str = '.gz'

DEFAULT_ENCODING: str = 'utf-8'

# File parsing patterns.
SEPARATOR_PATTERN: re.Pattern = re.compile(r'^\s*-{3,}\s*$')

# PGN parsing patterns.
TAG_PATTERN: re.Pattern= re.compile(r"^\[([A-Za-z0-9][A-Za-z0-9_+#=:-]*)\s+\"([^\r]*)\"\]\s*$")
TAG_NAME_PATTERN: re.Pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_+#=:-]*\Z")
MOVETEXT_PATTERN: re.Pattern = re.compile(r"""
    (
        [NBKRQ]?[a-h]?[1-8]?[\-x]?[a-h][1-8](?:=?[nbrqkNBRQK])?
        |[PNBRQK]?@[a-h][1-8]
        |--
        |Z0
        |0000
        |@@@@
        |O-O(?:-O)?
        |0-0(?:-0)?
    )
    |(\{.*?})
    |(\{.*)
    |(;.*)
    |(\$[0-9]+)
    |(\()
    |(\))
    |(\*|1-0|0-1|1/2-1/2)
    |([\?!]{1,2})
    """, re.DOTALL | re.VERBOSE)

SKIP_MOVETEXT_PATTERN: re.Pattern = re.compile(r""";|\{|\}""")

FEN_HEADER_KEY: str = 'FEN'
SET_UP_HEADER_KEY: str = 'SetUp'

MAX_PGN_LINE_LENGTH: int = 80

PGN_HEADERS: list[str] = [
    "event",
    "site",
    "date",
    "round",
    "white",
    "black",
    "result",
]

class StandardHeaders(edq.util.serial.DictConverter):
    """
    These seven standard tags will always be present in the headers:
     - Event: the name of the tournament or match event
     - Site: the location of the event
     - Date: the starting date of the game
     - Round: the playing round ordinal of the game
     - White: the player of the white pieces
     - Black: the player of the black pieces
     - Result: the result of the game

    To see the full description of the possible headers and their format,
    see https://www.saremba.de/chessgml/standards/pgn/pgn-complete.htm#c8.1 .
    """

    def __init__(self,
            event: str = "?",
            site: str = "?",
            date: str = "????.??.??",
            game_round: str = "?",
            white: str = "?",
            black: str = "?",
            result: str = "*",
            ) -> None:
        self.event: str = event
        """ The name of the tournament or match event. """

        self.site: str = site
        """ The location of the event. """

        self.date: str = date
        """ The starting date of the game. """

        self.round: str = game_round
        """ The playing round ordinal of the game. """

        self.white: str = white
        """ The player of the white pieces. """

        self.black: str = black
        """ The player of the black pieces. """

        self.result: str = result
        """ The result of the game. """

    def _set(self, attribute: str, value: str) -> None:
        """ Update the header attribute to the given value. """

        match attribute.lower():
            case "event":
                self.event = value
            case "site":
                self.site = value
            case "date":
                self.date = value
            case "round":
                self.round = value
            case "white":
                self.white = value
            case "black":
                self.black = value
            case "result":
                self.result = value
            case _:
                return

    def to_pgn(self) -> list[str]:
        """ Convert the headers to a list of PGN tags. """

        tags: list[str] = []

        tags.append(_to_tag("Event", self.event))
        tags.append(_to_tag("Site", self.site))
        tags.append(_to_tag("Date", self.date))
        tags.append(_to_tag("Round", self.round))
        tags.append(_to_tag("White", self.white))
        tags.append(_to_tag("Black", self.black))
        tags.append(_to_tag("Result", self.result))

        return tags

    def __eq__(self, other: object) -> bool:
        if (not isinstance(other, StandardHeaders)):
            return False

        return (self.event == other.event
            and self.site == other.site
            and self.date == other.date
            and self.round == other.round
            and self.white == other.white
            and self.black == other.black
            and self.result == other.result)

class PGNResult(str, enum.Enum):
    """ The possible game endings denoted in a PGN. """

    WHITE_WIN = '1-0'
    """ White won the game. """

    BLACK_WIN = '0-1'
    """ Black won the game. """

    TIE = '1/2-1/2'
    """ The game was a tie. """

    IN_PROGRESS = '*'
    """ The game is still in progress. """

    UNKNOWN = 'Unknown'
    """ The ending of the game is unknown. """

class ParsedPGN(edq.util.serial.DictConverter):
    """
    The parsed result of a single PGN game.
    """

    def __init__(self,
                 headers: StandardHeaders | None = None,
                 optional_headers: dict[str, typing.Any] | None = None,
                 starting_fen: str | None = None,
                 initial_actions: list[chessai.core.action.Action] | None = None,
                 comments: list[str] | None = None,
                 result: PGNResult = PGNResult.UNKNOWN) -> None:

        if (headers is None):
            headers = StandardHeaders()

        self.headers: StandardHeaders = headers
        """ The standard headers from a single PGN game. """

        if (optional_headers is None):
            optional_headers = {}

        self.optional_headers: dict[str, typing.Any] = optional_headers
        """ Any additional headers parsed from the PGN. """

        self.starting_fen: str | None = starting_fen
        """ The starting FEN for the game, which is often omitted to denote the default FEN. """

        if (initial_actions is None):
            initial_actions = []

        self.initial_actions: list[chessai.core.action.Action] = initial_actions
        """ The mainline moves in the game. """

        if (comments is None):
            comments = []

        self.comments: list[str] = comments
        """ The comments found in the game. """

        self.result: PGNResult = result
        """ The result of the PGN or if the game is still in progress. """

    def get_starting_fen(self) -> str | None:
        """ Get the optional FEN header from the PGN. """

        return self.optional_headers.get(FEN_HEADER_KEY, None)

def parse_pgn(pgn: str, state_class: typing.Type[chessai.core.gamestate.GameState]) -> ParsedPGN | None:
    """
    Parse a single PGN string into a ParsedPGN.

    Raises ValueError if the PGN is malformed.
    See https://en.wikipedia.org/wiki/Portable_Game_Notation .
    """

    lines = pgn.splitlines()

    # If it is only one line, try loading it from a file.
    if (len(lines) == 1):
        pgn = load_pgn_from_file(pgn)
        lines = pgn.splitlines()

    index = 0

    headers: StandardHeaders = StandardHeaders()

    optional_headers: dict[str, typing.Any] = {}

    # Parse the header fields.
    for i, line in enumerate(lines):
        # Track where we are in the lines.
        index = i

        clean_line = line.strip()

        # Skip empty lines.
        if (len(line) == 0):
            continue

        # Skip comments.
        if (_is_pgn_comment_line(clean_line)):
            continue

        # Headers must begin with an open bracket.
        if (not clean_line.startswith("[")):
            break

        tag_match = TAG_PATTERN.match(clean_line)

        # Ignore malformed tags.
        if (not tag_match):
            continue

        tag_header_key = tag_match.group(1)
        tag_header_value = tag_match.group(2)

        # Determine if this is a standard header key or not.
        if (tag_header_key.lower() in PGN_HEADERS):
            headers._set(tag_header_key, tag_header_value)
        else:
            optional_headers[tag_header_key] = tag_header_value

    # No game found.
    if (headers == StandardHeaders()):
        return None

    # Start scanning for moves from the end of the headers.
    lines = lines[index:]

    # Set up a gamestate to follow along and parse SANs.
    fen = optional_headers.get(FEN_HEADER_KEY, None)
    state = state_class.from_fen(fen = fen)
    rng = random.Random(1)

    initial_actions: list[chessai.core.action.Action] = []
    comments: list[str] = []
    result: PGNResult = PGNResult.UNKNOWN

    in_comment = False
    comment_buffer: list[str] = []

    skip_variation_depth = 0

    for line in lines:
        line = line.strip()

        if (not line):
            break

        # Skip whole-line comments.
        if _is_pgn_comment_line(line):
            continue

        i = 0
        while (i < len(line)):
            if in_comment:
                end_index = line.find("}", i)

                # The rest of the line is part of the comment.
                if (end_index == -1):
                    comment_buffer.append(line[i:])
                    break

                # Add the remainder of the comment and continue processing the current line.
                comment_buffer.append(line[i:end_index])
                comments.append("\n".join(comment_buffer).strip())

                comment_buffer = []
                in_comment = False

                i = end_index + 1

                continue

            match = MOVETEXT_PATTERN.match(line, i)

            if (not match):
                i += 1
                continue

            token = match.group(0)
            i = match.end()

            # Handle block comments {...}.
            if token.startswith("{"):
                content = token[1:]

                end_index = content.find("}")

                if (end_index == -1):
                    # Track part of a multi-line comment.
                    in_comment = True
                    comment_buffer.append(content)
                else:
                    # Add the in-line comment and continue processing this line.
                    comments.append(content[:end_index].strip())

                continue

            # Skip variations (...) entirely.
            if (token == "("):
                skip_variation_depth += 1
                continue

            if (token == ")"):
                if (skip_variation_depth > 0):
                    skip_variation_depth -= 1

                continue

            if (skip_variation_depth > 0):
                continue

            # Skip line comments.
            if token.startswith(";"):
                break

            # Skip move numbers like "1." or "23.".
            if token.endswith("."):
                continue

            # Skip results.
            if (token in ["1-0", "0-1", "1/2-1/2", "*"]):
                result = PGNResult(token)
                break

            # Skip NAGs / annotations.
            if (token.startswith("$") or (token in ["!", "?", "!!", "??", "!?", "?!"])):
                continue

            # Otherwise, this must be a SAN move.
            action = state.get_action_from_san(token)
            if (action == chessai.core.action.NoneAction()):
                raise ValueError(f"Unable to find a legal action for the SAN: '{token}'.")

            state.process_turn_full(action, rng)
            initial_actions.append(action)

    # Check if the gamestate agrees with the expected result.
    if ((result in [PGNResult.WHITE_WIN, PGNResult.BLACK_WIN]) and (not state.is_game_over())):
        # The game is not over when the PGN believes it should be, so add a forfeit action.
        initial_actions.append(chessai.core.action.ForfeitAction())

    if ((result == PGNResult.TIE) and (not state.is_game_over())):
        # The game must be a proposed draw, so add the draw handshake.
        initial_actions.append(chessai.core.action.ProposeDrawAction())
        initial_actions.append(chessai.core.action.AcceptDrawAction())

    return ParsedPGN(
        headers          = headers,
        optional_headers = optional_headers,
        initial_actions  = initial_actions,
        comments         = comments,
        result           = result,
    )

def load_pgn_from_file(path: str) -> str:
    """
    Load the PGN string from a file.

    If the given path does not exist,
    try to prefix the path with the standard game directory and suffix with the standard extension.
    """

    raw_path = path

    # If the path does not exist, try the boards directory.
    if (not os.path.exists(path)):
        path = os.path.join(GAMES_DIR, path)

        # If this path does not have a good extension, add one.
        if ((os.path.splitext(path)[-1] != PGN_FILE_EXTENSION) and (os.path.splitext(path)[-1] != GZIP_FILE_EXTENSION)):
            path = path + PGN_FILE_EXTENSION

    # If the path still does not exist, try adding the GZip extension.
    if (not os.path.exists(path)):
        if (os.path.splitext(path)[-1] != GZIP_FILE_EXTENSION):
            path = path + GZIP_FILE_EXTENSION

    if (not os.path.exists(path)):
        raise ValueError(f"Could not find PGN file, path does not exist: '{raw_path}'.")

    if (os.path.splitext(path)[-1] == GZIP_FILE_EXTENSION):
        return load_pgn_from_gzip(path)

    contents = edq.util.dirent.read_file(path, strip = False)
    return contents

def load_pgn_from_gzip(path: str) -> str:
    """
    Load the PGN string from a file.

    If the given path does not exist,
    try to prefix the path with the standard game directory and suffix with the standard extension.
    """

    raw_path = path

    # If the path does not exist, try the boards directory.
    if (not os.path.exists(path)):
        path = os.path.join(GAMES_DIR, path)

        # If this path does not have a good extension, add one.
        if (os.path.splitext(path)[-1] != GZIP_FILE_EXTENSION):
            path = path + GZIP_FILE_EXTENSION

    if (not os.path.exists(path)):
        raise ValueError(f"Could not find PGN file, path does not exist: '{raw_path}'.")

    with gzip.open(path, 'rb') as file:
        uncompressed_contents = file.read()
        decompressed_contents = uncompressed_contents.decode(DEFAULT_ENCODING)

    return decompressed_contents

def to_pgn(headers: StandardHeaders, optional_headers: dict[str, typing.Any],
           state_class: typing.Type[chessai.core.gamestate.GameState], start_fen: str,
           actions: list[chessai.core.action.Action]) -> str:
    """
    Convert a game into a PGN.

    Raises an error if any of the seven required headers are missing.
    If a move cannot be generated from an action and gamestate pair, an error is raised.
    """

    lines: list[str] = headers.to_pgn()

    # Non-default starting FENs require additional PGN information.
    if (start_fen != chessai.core.gamestate.DEFAULT_FEN):
        lines.append(_to_tag(SET_UP_HEADER_KEY, '1'))
        lines.append(_to_tag(FEN_HEADER_KEY, start_fen))

    # Add optional headers.
    for (key, value) in optional_headers.items():
        try:
            str_value = str(value)
        except Exception:
            logging.warning("Could not convert optional header value for key '%s' to a string.", key)
            continue

        lines.append(_to_tag(str(key), str_value))

    # Add an extra blank line after the header section.
    lines.append('')

    # Build the move SAN tokens while replaying the game.
    state = state_class.from_fen(fen = start_fen)
    pgn_tokens: list[str] = []
    current_fullmove_number = 0

    for action in actions:
        # Ignore meta actions as they do not have a valid SAN representation.
        if (not isinstance(action, chessai.core.action.MoveAction)):
            continue

        if (state.fullmove_number != current_fullmove_number):
            pgn_tokens.append(f"{state.fullmove_number}.")
            current_fullmove_number = state.fullmove_number

        san = _action_to_san(action, state)
        pgn_tokens.append(san)

        state.push(action)

    # Add the result token.
    pgn_tokens.append(headers.result)

    movetext_lines: list[str] = []
    current_line = ''

    for token in pgn_tokens:
        if (len(current_line) == 0):
            candidate_line = token
        else:
            candidate_line = f"{current_line} {token}"

        # Keep building a line until it surpasses the max line length.
        if (len(candidate_line) <= MAX_PGN_LINE_LENGTH):
            current_line = candidate_line
        else:
            movetext_lines.append(current_line)
            current_line = token

    if (len(current_line) > 0):
        movetext_lines.append(current_line)

    lines.extend(movetext_lines)

    # Add a trailing newline after the movetext.
    lines.append('')

    return '\n'.join(lines)

def _escape_tag_value(value: str) -> str:
    """ Escape the tag value to avoid parsing errors. """

    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return escaped

def _to_tag(header: str, value: str) -> str:
    """ Write a header and its value to a PGN tag. """

    escaped_value = _escape_tag_value(value)
    return f'[{header} "{escaped_value}"]'

def _action_to_san(action: chessai.core.action.MoveAction, state: chessai.core.gamestate.GameState) -> str:
    """
    Convert an action to a SAN using the state before the action is applied evaluate SAN move ambiguity.

    This method does not understand meta actions (i.e., forfeits or draw actions).
    """

    piece = state.get(action.start_coordinate)
    if (piece is None):
        raise ValueError(f"The start coordinate for action '{action.uci()}' does not have a piece.")

    piece_symbol_upper = piece.symbol().upper()

    move_san: str | None = None

    # Detect castling by checking for a king moving two squares horizontally.
    if (piece_symbol_upper == 'K'):
        file_delta = action.end_coordinate.file - action.start_coordinate.file

        if (file_delta == 2):
            # Kingside castle.
            move_san = 'O-O'
        elif (file_delta == -2):
            # Queenside castle.
            move_san = 'O-O-O'

    is_pawn = (piece_symbol_upper == 'P')

    if (move_san is None):
        is_capture = state.is_capture(action)

        # Detect en-passant captures.
        if (is_pawn and (action.end_coordinate == state.en_passant_coordinate)):
            is_capture = True

        # Check if the move is ambiguous.
        ambiguous_actions: list[chessai.core.action.MoveAction] = []
        for alternate_action in state.get_legal_actions():
            if (not isinstance(alternate_action, chessai.core.action.MoveAction)):
                continue

            # An ambiguous move must have the same action type.
            if (type(alternate_action) != type(action)):
                continue

            # An ambiguous move must end at the same coordinate.
            if (alternate_action.end_coordinate != action.end_coordinate):
                continue

            # An ambiguous move cannot start at the same coordinate because that would be the same piece moving.
            if (alternate_action.start_coordinate == action.start_coordinate):
                continue

            # An ambiguous action must have the same promotion.
            if (isinstance(action, chessai.core.action.PromotionAction)
                    and isinstance(alternate_action, chessai.core.action.PromotionAction)
                    and (alternate_action.promotion != action.promotion)):
                continue

            # An ambiguous action must have a different piece type.
            alternate_action_piece = state.get(alternate_action.start_coordinate)
            if (alternate_action_piece is None):
                continue

            if (alternate_action_piece.symbol().upper() != piece_symbol_upper):
                continue

            ambiguous_actions.append(alternate_action)

        disambiguation_str = ''

        # Pawn actions cannot be ambiguous.
        if ((len(ambiguous_actions) > 0) and (not is_pawn)):
            # Check if there is an ambiguous action on the same file.
            same_file = False
            for ambiguous_action in ambiguous_actions:
                if (ambiguous_action.start_coordinate.file != action.start_coordinate.file):
                    continue

                same_file = True

            # Check if there is an ambiguous action on the same rank.
            same_rank = False
            for ambiguous_action in ambiguous_actions:
                if (ambiguous_action.start_coordinate.rank != action.start_coordinate.rank):
                    continue

                same_rank = True

            if (not same_file):
                disambiguation_str = action.start_coordinate.uci(only_file = True)
            elif (not same_rank):
                disambiguation_str = action.start_coordinate.uci(only_rank = True)
            else:
                # Fallback to the entire coordinate.
                disambiguation_str = action.start_coordinate.uci()

        # Build the final SAN with the above information.
        destination_str = action.end_coordinate.uci()

        if (is_pawn):
            if is_capture:
                # Pawn captures require the starting file to disambiguate.
                start_file = action.start_coordinate.uci(only_file = True)
                move_san = f"{start_file}x{destination_str}"
            else:
                move_san = destination_str
        else:
            if is_capture:
                capture_str = 'x'
            else:
                capture_str = ''

            move_san = f"{piece_symbol_upper}{disambiguation_str}{capture_str}{destination_str}"

        # Add the piece promotion suffix.
        if isinstance(action, chessai.core.action.PromotionAction):
            move_san += f"={action.promotion.symbol().upper()}"

    # Apply the action and check for check and checkmate.
    successor = state.generate_successor(action)

    if (successor.is_checkmate()):
        move_san += '#'
    elif (successor.is_check(successor.turn)):
        move_san += '+'

    return move_san

def _is_pgn_comment_line(line: str) -> bool:
    """
    Returns if the line is a comment.

    A line is a comment in a PGN if it  starts with a '%' or ';'.
    """

    line = line.strip()
    if (len(line) == 0):
        return True

    if (line[0] == '%'):
        return True

    if (line[0] == ';'):
        return True

    return False
