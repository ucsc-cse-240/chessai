import logging
import random
import typing

import edq.util.serial

import chessai.core.action
import chessai.core.agentaction
import chessai.core.board
import chessai.core.castling
import chessai.core.parser
import chessai.core.piece
import chessai.core.coordinate
import chessai.core.types

DEFAULT_FEN: str = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

_KNOWN_LEGAL_ACTIONS: dict[str, list[chessai.core.action.Action]] = {}

GameStateT = typing.TypeVar("GameStateT", bound="GameState")

class GameState(edq.util.serial.DictConverter):
    """
    The base for all game states in chessai.
    A game state should contain all the information about the current state of the game.
    The board is not responsible for any mutable state.

    Game states should only be interacted with via their methods and not their member variables.
    """

    def __init__(self,
                 board: chessai.core.board.Board,
                 turn: chessai.core.types.Color,
                 castling_rights: chessai.core.castling.CastlingRights,
                 en_passant_coordinate: chessai.core.coordinate.Coordinate | None = None,
                 halfmove_clock: int = 0,
                 fullmove_number: int = 1,
                 previous_action: chessai.core.action.Action | None = None,
                 seed: int = -1,
                 game_over: bool = False,
                 **kwargs: typing.Any) -> None:
        self.board: chessai.core.board.Board = board
        """ The board responsible for holding the position of pieces. """

        self.turn: chessai.core.types.Color = turn
        """ The color of the current player. """

        self.castling_rights: chessai.core.castling.CastlingRights = castling_rights
        """ The available castling moves. """

        self.en_passant_coordinate: chessai.core.coordinate.Coordinate | None = en_passant_coordinate
        """ The en-passant target coordinate, or None. """

        self.halfmove_clock: int = halfmove_clock
        """ The number of plies since the last pawn move or capture (50-move rule). """

        self.fullmove_number: int = fullmove_number
        """ Increments after every black move, starting at 1. """

        self.previous_action: chessai.core.action.Action | None = previous_action
        """ The ordered history of all actions taken, starting with the oldest action. """

        self.seed: int = seed
        """ A utility seed that components using the game state may use to seed their own RNGs. """

        self.game_over: bool = game_over
        """ Indicates that this state represents a complete game. """

    def get_fen(self, partial: bool = False) -> str:
        """
        Serialize the current gamestate to a FEN string.

        Note that this operation looses the move history.
        """

        return chessai.core.parser.serialize_fen(
            board             = self.board,
            turn              = self.turn,
            castling_rights   = self.castling_rights,
            en_passant_coordinate = self.en_passant_coordinate,
            halfmove_clock    = self.halfmove_clock,
            fullmove_number   = self.fullmove_number,
            partial           = partial,
        )

    # -----------------------------------------------
    # Useful methods for students.
    # -----------------------------------------------

    def get(self, coordinate: chessai.core.coordinate.Coordinate) -> chessai.core.piece.Piece | None:
        """ Get the piece at the given coordinate, if it is present. """

        return self.board.get(coordinate.file, coordinate.rank)

    def get_coordinate_map(self, color: chessai.core.types.Color | None = None,
                           ) -> dict[chessai.core.coordinate.Coordinate, chessai.core.piece.Piece]:
        """
        Get the locations and pieces that are on the board.
        Providing a color will filter the results to only include pieces of that color.
        """

        pieces = self.board.get_coordinate_map()
        if (color is None):
            return pieces

        filtered_pieces = {}
        for (coordinate, piece) in pieces.items():
            if (piece.color != color):
                continue

            filtered_pieces[coordinate] = piece

        return filtered_pieces

    def get_previous_action(self) -> chessai.core.action.Action | None:
        """ Returns the most recent action taken. """

        return self.previous_action

    def get_legal_actions(self) -> list[chessai.core.action.Action]:
        """ Return the list of legal actions for the current player. """

        # If the most recent move was a draw proposal, the opponent must respond.
        if (isinstance(self.get_previous_action(), chessai.core.action.ProposeDrawAction)):
            return [
                chessai.core.action.AcceptDrawAction(),
                chessai.core.action.RejectDrawAction(),
            ]

        # Check if we have previously calculated the legal actions for this gamestate.
        partial_fen = self.get_fen(partial = True)
        precomputed_legal_actions = _KNOWN_LEGAL_ACTIONS.get(partial_fen, None)
        if (precomputed_legal_actions is not None):
            return precomputed_legal_actions.copy()

        # Players can always propose a draw or forfeit.
        legal_actions: list[chessai.core.action.Action] = [
            chessai.core.action.ProposeDrawAction(),
            chessai.core.action.ForfeitAction(),
        ]

        # Check if the player is currently in check, so we cannot short-circuit work in is_check().
        started_in_check = self.is_check(self.turn)

        pseudo_legal_moves = self._get_pseudo_legal_moves()
        for action in pseudo_legal_moves:
            # Get the piece before pushing (needed for special move processing).
            piece = self.get(action.start_coordinate)
            if piece is None:
                logging.warning("Found a pseduo legal action without a piece at its start coordinate: %s", action)
                continue

            # Generate a successor state to test if this move is legal.
            successor: 'GameState' = self.copy()

            # Apply the move to the test state.
            _, successor.en_passant_coordinate = successor._process_special_move(action, piece)
            successor.board.push(action)

            # Advance the turn for checking for check.
            successor.turn = self.turn.opposite()

            # Record the action to be able to short-circuit if it is in check.
            successor.previous_action = action

            # Check if this move leaves our king in check (making it illegal).
            if (not successor.is_check(self.turn, started_in_check = started_in_check)):
                legal_actions.append(action)

        # Sort the legal actions for consistency.
        legal_actions.sort()

        # Cache the legal actions.
        _KNOWN_LEGAL_ACTIONS[partial_fen] = legal_actions

        return legal_actions.copy()

    def get_legal_move_actions(self) -> list[chessai.core.action.Action]:
        """ Get the list of legal actions, without any meta actions. """

        legal_actions = self.get_legal_actions()
        return [legal_action for legal_action in legal_actions if isinstance(legal_action, chessai.core.action.MoveAction)]

    def is_capture(self, action: chessai.core.action.Action) -> bool:
        """ Return whether the given action captures a piece. """

        if (not isinstance(action, chessai.core.action.MoveAction)):
            return False

        return self.board.is_capture(action)

    def get_attacked_coordinates(self,
                                 color: chessai.core.types.Color,
                                 ) -> dict[chessai.core.coordinate.Coordinate, int]:
        """
        Returns the coordinates that the given color can attack,
        ignoring if that player is in check or would leave them in check.
        """

        attacked_coordinates = {}
        for (file, rank_dict) in self.board.pieces.items():
            for (rank, piece) in rank_dict.items():
                if (piece.color != color):
                    continue

                for movement_vector in piece.move_vectors():
                    # Push movement types cannot attack a coordinate.
                    if (movement_vector.kind == chessai.core.piece.MoveKind.PUSH):
                        break

                    current_rank = rank
                    current_file = file

                    num_repetitions = movement_vector.num_repetitions
                    while (num_repetitions != 0):
                        current_file += movement_vector.file_delta
                        current_rank += movement_vector.rank_delta
                        if (not self.board.is_within_bounds(current_file, current_rank)):
                            break

                        current_coordinate = chessai.core.coordinate.Coordinate(current_file, current_rank)
                        if (current_coordinate not in attacked_coordinates):
                            attacked_coordinates[current_coordinate] = 1
                        else:
                            attacked_coordinates[current_coordinate] += 1

                        occupant = self.board.get(current_file, current_rank)
                        if (occupant is not None):
                            break

                        num_repetitions -= 1

        return attacked_coordinates

    def get_neighbors(self,
            start_coordinate: chessai.core.coordinate.Coordinate
            ) -> list[tuple[chessai.core.action.Action, chessai.core.coordinate.Coordinate]]:
        """ Get coordinates that the piece at the given coordinate can reach legally, and the action it would take to get there. """

        neighbors: list[tuple[chessai.core.action.Action, chessai.core.coordinate.Coordinate]] = []

        for action in self.get_legal_actions():
            if (not isinstance(action, chessai.core.action.MoveAction)):
                continue

            # Skip the legal moves that are not from the starting coordinate.
            if (action.start_coordinate != start_coordinate): # pylint: disable=no-member
                continue

            neighbors.append((action, action.end_coordinate)) # pylint: disable=no-member

        return neighbors

    def is_check(self, color: chessai.core.types.Color, started_in_check: bool = True) -> bool:
        """ Determines if the given color, not the state's color, is in check. """

        return False

    def is_checkmate(self) -> bool:
        """ Determines if the current player is in checkmate. """

        # A draw proposal can never cause a checkmate.
        if (isinstance(self.get_previous_action(), chessai.core.action.ProposeDrawAction)):
            return False

        legal_actions = self.get_legal_actions()

        # Only count move actions when checking checkmate.
        checkmate_escape_actions = [action for action in legal_actions if isinstance(action, chessai.core.action.MoveAction)]

        return ((len(checkmate_escape_actions) == 0) and self.is_check(self.turn))

    def is_stalemate(self) -> bool:
        """ Determines if the current player is in stalemate. """

        # A draw proposal can never cause a stalemate.
        if (isinstance(self.get_previous_action(), chessai.core.action.ProposeDrawAction)):
            return False

        legal_actions = self.get_legal_actions()

        # Only count move actions when checking stalemate.
        checkmate_escape_actions = [action for action in legal_actions if isinstance(action, chessai.core.action.MoveAction)]

        return ((len(checkmate_escape_actions) == 0) and (not self.is_check(self.turn)))

    def is_insufficient_material(self) -> bool:
        """ Processes if there is insufficient material to get a checkmate for all colors. """

        return False

    def is_variant_win(self) -> bool:
        """ Determines if the game is a win due to a variant rule. """

        return False

    def is_variant_loss(self) -> bool:
        """ Determines if the game is a loss due to a variant rule. """

        return False

    def is_game_over(self) -> bool:
        """ Returns whether the game is over according to the board rules. """

        if (self.game_over):
            return True

        if (self.is_checkmate()):
            return True

        if (self.is_stalemate()):
            return True

        if (self.is_insufficient_material()):
            return True

        if (self.is_variant_win()):
            return True

        if (self.is_variant_loss()):
            return True

        return False

    def get_winners(self) -> list[chessai.core.types.Color]:
        """
        Gets the list of winners from the game.
        An empty list signifies the game is in progress or it is a tie.
        """

        # If the previous agent forfeited the game, the current agent won.
        if (isinstance(self.get_previous_action(), chessai.core.action.ForfeitAction)):
            return [self.turn]

        # If the agent is in checkmate, the opponent won.
        if (self.is_checkmate()):
            return [self.turn.opposite()]

        return []

    def get_termination_reason(self) -> chessai.core.types.TerminationReason:
        """ Return the reason the game ended. """

        if (self.is_checkmate()):
            return chessai.core.types.TerminationReason.CHECKMATE

        if (self.is_stalemate()):
            return chessai.core.types.TerminationReason.STALEMATE

        if (self.is_insufficient_material()):
            return chessai.core.types.TerminationReason.INSUFFICIENT_MATERIAL

        if (isinstance(self.get_previous_action(), chessai.core.action.ForfeitAction)):
            return chessai.core.types.TerminationReason.FORFEIT

        if (isinstance(self.get_previous_action(), chessai.core.action.AcceptDrawAction)):
            return chessai.core.types.TerminationReason.ACCEPTED_DRAW_PROPOSAL

        if (self.is_variant_win()):
            return chessai.core.types.TerminationReason.VARIANT_WIN

        if (self.is_variant_loss()):
            return chessai.core.types.TerminationReason.VARIANT_LOSS

        if (not self.is_game_over()):
            return chessai.core.types.TerminationReason.IN_PROGRESS

        return chessai.core.types.TerminationReason.UNKNOWN

    def get_action_from_san(self, san: str) -> chessai.core.action.Action:
        """
        Get the action from the given SAN.

        See https://en.wikipedia.org/wiki/Algebraic_notation_(chess) .

        SANs should only be used when interacting with PGNs.
        So, this is not a useful method for students.
        """

        # Remove check (+) and checkmate (#) indicators and captures (x).
        san_clean = san.replace('+', '').replace('#', '').replace('x', '')

        # Handle castling.
        if (san_clean in ['O-O', '0-0', 'O-O-O', '0-0-0']):
            if (self.turn == chessai.core.types.Color.WHITE):
                rank = 0
            else:
                rank = self.board.num_ranks - 1

            # Find the king.
            king_coord: chessai.core.coordinate.Coordinate | None = None
            for (current_file, rank_dict) in self.board.pieces.items():
                for (current_rank, piece) in rank_dict.items():
                    if (piece.symbol() not in ['k', 'K']):
                        continue

                    if (piece.color != self.turn):
                        continue

                    king_coord = chessai.core.coordinate.Coordinate(current_file, current_rank)
                    break

            # Could not find a king for the proper color.
            if ((king_coord is None) or (king_coord.rank != rank)):
                logging.warning("Unable to find a king on the board when parsing a SAN castling move: '%s'.", san)

                return chessai.core.action.NoneAction()

            start_file = king_coord.file

            if (san_clean in ['O-O', '0-0']):
                # Kingside castling.
                end_file = self.board.num_files - 2
            else:
                # Queenside castling.
                end_file = 2

            return chessai.core.action.MoveAction(
                chessai.core.coordinate.Coordinate(start_file, rank),
                chessai.core.coordinate.Coordinate(end_file, rank)
            )

        # Parse optional promotion piece.
        promotion_piece = None
        if ('=' in san_clean):
            parts = san_clean.split('=')
            san_clean = parts[0]

            if (self.turn == chessai.core.types.Color.WHITE):
                promotion_symbol = parts[1].upper()
            else:
                promotion_symbol = parts[1].lower()

            promotion_piece = chessai.core.piece.get_registered_piece(promotion_symbol)

        # Extract the destination coordinate, which is always the last 2 characters for standard moves.
        dest_coord = chessai.core.coordinate.Coordinate.from_uci(san_clean[-2:])

        # Determine the piece type from the first character and default to Pawn if first character is lowercase,
        # which denotes the file.
        piece_symbol = None
        disambig_file = None
        disambig_rank = None

        if san_clean[0].isupper():
            # Piece move (e.g., Nf3, Qd4, Raxe1).
            if (self.turn == chessai.core.types.Color.WHITE):
                piece_symbol = san_clean[0].upper()
            else:
                piece_symbol = san_clean[0].lower()

            # Check for disambiguation.
            middle = san_clean[1:-2]
            if middle:
                if middle[0].isalpha():
                    disambig_file = ord(middle[0]) - ord('a')

                if middle[-1].isdigit():
                    disambig_rank = int(middle[-1]) - 1
        else:
            # Pawn move (e.g., e4, exd5, e8=Q).
            if (self.turn == chessai.core.types.Color.WHITE):
                piece_symbol = 'P'
            else:
                piece_symbol = 'p'

            # Check for pawn capture disambiguation (file)
            if (len(san_clean) > 2 and san_clean[0].isalpha()):
                disambig_file = ord(san_clean[0]) - ord('a')

        # Get the piece class for comparison.
        piece = chessai.core.piece.get_registered_piece(piece_symbol)

        candidates = []

        # Find matching legal action.
        for legal_action in self.get_legal_actions():
            # Skip actions that are not moves.
            if (not isinstance(legal_action, chessai.core.action.MoveAction)):
                continue

            if (legal_action.end_coordinate != dest_coord): # pylint: disable=no-member
                continue

            # If there is a promotion, the action must be a promotion action with the matching piece type.
            if (promotion_piece is not None):
                if (not isinstance(legal_action, chessai.core.action.PromotionAction)):
                    continue

                if (type(legal_action.promotion) != type(promotion_piece)): # pylint: disable=no-member
                    continue
            else:
                if isinstance(legal_action, chessai.core.action.PromotionAction):
                    continue

            piece_at_start = self.get(legal_action.start_coordinate) # pylint: disable=no-member
            if (piece_at_start is None):
                continue

            if (piece_at_start != piece):
                continue

            if ((disambig_file is not None) and (legal_action.start_coordinate.file != disambig_file)): # pylint: disable=no-member
                continue

            if ((disambig_rank is not None) and (legal_action.start_coordinate.rank != disambig_rank)): # pylint: disable=no-member
                continue

            candidates.append(legal_action)

        # Return the unambiguous match.
        if (len(candidates) == 1):
            return candidates[0]

        return chessai.core.action.NoneAction()

    # -----------------------------------------------
    # State mutation
    # -----------------------------------------------

    def push(self, action: chessai.core.action.Action) -> None:
        """ Apply action to the game state and update all metadata. """

        # If the agent forfeits the game or accepts a draw, end the game.
        if (isinstance(action, (chessai.core.action.ForfeitAction, chessai.core.action.AcceptDrawAction))):
            self._progress_state(action, False)
            self.game_over = True
            return

        # If the agent proposes a draw offer or rejects a draw offer, progress the state to the opponent.
        if (isinstance(action, (chessai.core.action.ProposeDrawAction, chessai.core.action.RejectDrawAction))):
            self._progress_state(action, False)
            return

        if (not isinstance(action, chessai.core.action.MoveAction)):
            self._progress_state(action, False)
            return

        piece = self.get(action.start_coordinate)
        if (piece is None):
            raise ValueError(f"Cannot push an action from an empty coordinate: '{action.uci()}'.")

        # Allow games to process any special moves.
        is_special_capture, self.en_passant_coordinate = self._process_special_move(action, piece)

        # Apply the action to the board and receive the updates.
        is_capture = self.board.push(action)

        # Allow for subclasses to reset clocks on special actions.
        reset_clock = self._should_reset_halfmove_clock(action, piece)

        # Update the clocks.
        self._progress_state(action, (reset_clock or is_capture or is_special_capture))

    def _progress_state(self, action: chessai.core.action.Action, reset_clock: bool) -> None:
        """ A helper function to update the basic state of the game. """

        if (reset_clock):
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if (self.turn == chessai.core.types.Color.BLACK):
            self.fullmove_number += 1

        # Advance the turn.
        self.turn = self.turn.opposite()

        self.previous_action = action

    def _get_pseudo_legal_moves(self) -> list[chessai.core.action.MoveAction]:
        """ Get all of the actions that can be taken on this gamestate, regardless if it violates pins or checks. """

        return self._get_base_move_actions()

    def _get_base_move_actions(self) -> list[chessai.core.action.MoveAction]:
        """
        Expands all movement vectors from the pieces on the board.
        Pieces will move until they can capture or reach the end of the board.
        There are no other special rules applied.
        """

        actions: list[chessai.core.action.MoveAction] = []

        for (file, rank_dict) in self.board.pieces.items():
            for (rank, piece) in rank_dict.items():
                if (piece.color != self.turn):
                    continue

                for movement_vector in piece.move_vectors():
                    current_rank = rank
                    current_file = file

                    coordinate = chessai.core.coordinate.Coordinate(file, rank)

                    num_repetitions = movement_vector.num_repetitions
                    while (num_repetitions != 0):
                        current_file += movement_vector.file_delta
                        current_rank += movement_vector.rank_delta
                        if (not self.board.is_within_bounds(current_file, current_rank)):
                            break

                        occupant = self.board.get(current_file, current_rank)

                        is_occupied = occupant is not None
                        is_enemy    = (occupant is not None) and (occupant.color != piece.color)
                        is_ally     = (occupant is not None) and (occupant.color == piece.color)

                        # No movement type can move on top of an ally.
                        if (is_ally):
                            break

                        # Push movement types cannot capture.
                        if ((movement_vector.kind == chessai.core.piece.MoveKind.PUSH) and is_occupied):
                            break

                        # Capture movement types must target an enemy.
                        if ((movement_vector.kind == chessai.core.piece.MoveKind.CAPTURE) and (not is_enemy)):
                            break

                        current_coordinate = chessai.core.coordinate.Coordinate(current_file, current_rank)

                        actions.append(chessai.core.action.MoveAction(coordinate, current_coordinate))

                        if (is_occupied):
                            break

                        num_repetitions -= 1

        return actions

    def _should_reset_halfmove_clock(self, action: chessai.core.action.Action, piece: chessai.core.piece.Piece) -> bool:
        """ A helper function that allows gamestates to signal if the halfmove clock should be reset after an action. """

        return False

    def _process_special_move(self,
            action: chessai.core.action.Action,
            piece: chessai.core.piece.Piece,
            ) -> tuple[bool, chessai.core.coordinate.Coordinate | None]:
        """ A helper function that allows gamestates to do any additional processing for special moves. """

        return False, None

    def copy(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> 'GameState':
        """
        Get a deep copy of this state.

        Child classes are responsible for making any deep copies they need to.
        """

        new_state = type(self)(
            board           = self.board.copy(),
            turn            = self.turn,
            castling_rights = self.castling_rights,
            en_passant_coordinate = self.en_passant_coordinate,
            halfmove_clock  = self.halfmove_clock,
            fullmove_number = self.fullmove_number,
            previous_action = self.previous_action,
            seed            = self.seed,
            game_over       = self.game_over)

        return new_state

    def generate_successor(self,
            action: chessai.core.action.Action,
            rng: random.Random | None = None,
            **kwargs: typing.Any,
            ) -> 'GameState':
        """
        Create a new deep copy of this state that represents the current agent taking the given action.
        To just apply an action to the current state, use process_turn().
        """

        successor = self.copy()
        successor.process_turn_full(action, rng, **kwargs)

        return successor

    # -----------------------------------------------
    # Functions used for agents to follow the flow of the game.
    # -----------------------------------------------

    def game_start(self) -> None:
        """
        Indicate that the game is starting.
        This will initialize some state.
        """

    def agents_game_start(self,
            agent_responses: dict[chessai.core.types.Color, chessai.core.agentaction.AgentActionRecord],
            ) -> None:
        """ Indicate that agents have been started. """

    def game_complete(self) -> tuple[list[chessai.core.types.Color], float]:
        """
        Indicate that the game has ended.
        The state should take any final actions and return the player colors of the winning agents (if any) and the score of the game.
        """

        return ([], 0)

    def process_agent_timeout(self, player: chessai.core.types.Color) -> None:
        """
        Notify the state that the given agent has timed out.
        The state should make any updates and set the end of game information.
        """

        self.game_over = True

    def process_agent_crash(self, player: chessai.core.types.Color) -> None:
        """
        Notify the state that the given agent has crashed.
        The state should make any updates and set the end of game information.
        """

        self.game_over = True

    def process_game_timeout(self) -> None:
        """
        Notify the state that the game has reached the maximum number of turns without ending.
        The state should make any updates and set the end of game information.
        """

        self.game_over = True

    def process_turn(self,
            action: chessai.core.action.Action,
            rng: random.Random | None = None,
            **kwargs: typing.Any) -> None:
        """
        Process the current agent's turn with the given action.
        This may modify the current state.
        To get a copy of a potential successor state, use generate_successor().
        """

        self.push(action)

    def process_turn_full(self,
            action: chessai.core.action.Action,
            rng: random.Random | None = None,
            **kwargs: typing.Any) -> None:
        """
        Process the current agent's turn with the given action.
        This will modify the current state.
        First process_turn() will be called,
        then any bookkeeping will be performed.
        Child classes should prefer overriding the simpler process_turn().

        To get a copy of a potential successor state, use generate_successor().
        """

        # If the game is over, don't do anything.
        # This case can come up when planning agent actions and generating successors.
        if (self.is_game_over()):
            return

        self.process_turn(action, rng, **kwargs)
        return

    @classmethod
    def get_gamestate_parser(cls) -> chessai.core.parser.GameStateParser:
        """ Get the parser that can convert user inputs into a gamestate. """

        return chessai.core.parser.parse_fen

    @classmethod
    def from_fen(cls: type[GameStateT],
                 fen: str | None = None,
                 previous_action: chessai.core.action.Action | None = None,
                 seed: int = -1,
                 game_over: bool = False,
                 fen_parser: chessai.core.parser.GameStateParser | None = None,
                 **kwargs: typing.Any) -> GameStateT:
        """ Create a gamestate from a starting FEN. """

        if (fen is None):
            fen = DEFAULT_FEN

        if (fen_parser is None):
            fen_parser = cls.get_gamestate_parser()

        parsed_fen = fen_parser(data = fen, **kwargs)

        board = chessai.core.board.Board(pieces = parsed_fen.pieces,
                                         num_files = parsed_fen.num_files,
                                         num_ranks = parsed_fen.num_ranks)

        if (kwargs is not None):
            parsed_fen.options.update(kwargs)

        return cls(board          = board,
            turn                  = parsed_fen.turn,
            castling_rights       = parsed_fen.castling_rights,
            en_passant_coordinate = parsed_fen.en_passant_coordinate,
            halfmove_clock        = parsed_fen.halfmove_clock,
            fullmove_number       = parsed_fen.fullmove_number,
            previous_action       = previous_action,
            seed                  = seed,
            game_over             = game_over,
            **parsed_fen.options,
        )

@typing.runtime_checkable
class AgentStateEvaluationFunction(typing.Protocol):
    """
    A function that can be used to score a game state.
    """

    def __call__(self,
            state: GameState,
            action: chessai.core.action.Action | None = None,
            agent: typing.Any | None = None,
            **kwargs: typing.Any) -> float:
        """
        Compute a score for a state that the provided agent can use to decide actions.
        The current state is the only required argument, the others are optional.
        Passing the agent asking for this evaluation is a simple way to pass persistent state
        (like pre-computed heuristics) from the agent to this function.
        """
