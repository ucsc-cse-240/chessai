import os
import typing

import chessai.chess.piece
import chessai.core.parser
import chessai.tour.parser

THIS_DIR: str = os.path.join(os.path.dirname(os.path.realpath(__file__)))
ESCORT_DIR: str = os.path.join(THIS_DIR, '..', 'resources', 'escort')

ESCORT_FILE_EXTENSION: str = '.json'

def parse_escort(data: str,
               default_dir: str = ESCORT_DIR,
               default_extension: str = ESCORT_FILE_EXTENSION,
               string_parser: chessai.core.parser.GameStateStringParser = chessai.tour.parser.parse_tour_from_string,
               accepts_raw_string: bool = False,
               options: dict[str, typing.Any] | None = None,
               **kwargs: typing.Any) -> chessai.core.parser.ParsedGameState:
    """
    Parse an Escort GameState from a file path.

    If the filepath does not exist, the default directory and file extension are added.
    """

    parsed_state = chessai.core.parser.parse_fen(data,
            default_dir = default_dir,
            default_extension = default_extension,
            string_parser = string_parser,
            accepts_raw_string = accepts_raw_string,
            **kwargs)

    # Escort games must at least one king on the agent's turn, which is always the starting turn.
    for _, piece in parsed_state.pieces.items():
        if not isinstance(piece, chessai.chess.piece.King):
            continue

        # Check that the king is on the agent's team.
        if (piece.color != parsed_state.turn):
            continue

        return parsed_state

    raise ValueError('Escort games must have at least one king for the agent')
