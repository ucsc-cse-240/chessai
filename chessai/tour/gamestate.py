import random
import typing

import edq.util.serial

import chessai.chess.gamestate
import chessai.core.action
import chessai.core.board
import chessai.core.parser
import chessai.tour.parser
import chessai.tour.piece

TIME_PENALTY: int = 1
""" Number of points lost each round. """

POSITION_POINTS: int = 10
""" Points for reaching a search position. """

BOARD_CLEAR_POINTS: int = 500
""" Points for reaching all search positions on the board. """

LOSE_POINTS: int = -500
""" Points for not finding a solution. """

CRASH_POINTS: int = -1000000
""" Points for crashing the game. """

class GameState(chessai.chess.gamestate.GameState):
    """ A game state specific to a Tour game. """

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
                 search_targets: list[chessai.core.coordinate.Coordinate] | dict[str, typing.Any] | None = None,
                 _search_agent: chessai.core.types.Color | None = None,
                 _validate_search_targets: bool = True,
                 **kwargs: typing.Any) -> None:
        super().__init__(board, turn, castling_rights, en_passant_coordinate,
                         halfmove_clock, fullmove_number, previous_action,
                         seed, game_over, **kwargs)

        self.score: int = 0
        """ The score for the Tour. """

        if (search_targets is None):
            search_targets = []

        # Convert the string case into the dict case.
        if (isinstance(search_targets, str)):
            search_targets = {
                chessai.core.coordinate.COORDINATES_KEY: search_targets
            }

        if (isinstance(search_targets, dict)):
            search_targets = chessai.core.coordinate.coordinates_from_dict(search_targets)

        self.search_targets: list[chessai.core.coordinate.Coordinate] = search_targets
        """ The targets of the piece tour search. """

        search_agent = self.turn
        if (_search_agent is not None):
            search_agent = _search_agent

        self.search_agent = search_agent
        """ The agent solving the tour search. """

        # A Tour problem must have at least one search target.
        if (_validate_search_targets and (len(self.search_targets) == 0)):
            raise ValueError("Cannot create a Tour game state without at least one search target.")

    def is_game_over(self) -> bool:
        if (self.game_over):
            return True

        # Check if the search agent has any remaining moves, besides the none action.
        if (self.turn == self.search_agent):
            legal_actions = self.get_legal_actions()
            if ((len(legal_actions) == 1) and
                    (isinstance(legal_actions[0], chessai.core.action.NoneAction))):
                return True

        return (len(self.search_targets) == 0)

    def is_checkmate(self) -> bool:
        return False

    def is_stalemate(self) -> bool:
        return False

    def is_insufficient_material(self) -> bool:
        return False

    def is_variant_win(self) -> bool:
        if (self.is_game_over() and (self.score > 0)):
            return True

        return False

    def is_variant_loss(self) -> bool:
        if (self.is_game_over() and (self.score <= 0)):
            return True

        return False

    def get_legal_actions(self) -> list[chessai.core.action.Action]:
        tour_actions: list[chessai.core.action.Action] = []

        legal_actions = super().get_legal_actions()
        for action in legal_actions:
            # Tour agents can only perform movement actions and the none action.
            if (not isinstance(action, chessai.core.action.MoveAction)):
                continue

            # Remove any actions that are capturing a Rock.
            piece = self.get(action.end_coordinate) # pylint: disable=no-member
            if (isinstance(piece, chessai.tour.piece.Rock)):
                continue

            tour_actions.append(action)

        # Tour agents are allowed to stay still, as they lose points every turn.
        tour_actions.append(chessai.core.action.NoneAction())

        return tour_actions

    def remove_search_target(self, coordinate: chessai.core.coordinate.Coordinate) -> None:
        """
        Remove a search target from the gamestate.
        If the coordinate is not a search target, the state is unchanged.
        """

        if (coordinate not in self.search_targets):
            return

        self.search_targets.remove(coordinate)

    def process_turn(self,
            action: chessai.core.action.Action,
            rng: random.Random | None = None,
            **kwargs: typing.Any) -> None:
        # Only update the score when it is the search agents turn.
        if (self.turn == self.search_agent):
            self._update_targets_and_score(action)
        else:
            self._process_enemy_action(action)

        self.push(action)

    def _update_targets_and_score(self, action: chessai.core.action.Action) -> None:
        """ Update the remaining targets and score based on the search agents action. """

        if isinstance(action, chessai.core.action.MoveAction):
            destination_coordinate = action.end_coordinate
            if (destination_coordinate in self.search_targets):
                # Get points for reaching a search target.
                self.remove_search_target(destination_coordinate)
                self.score += POSITION_POINTS

        # The agent always loses a point each turn.
        self.score -= TIME_PENALTY

    def _process_enemy_action(self, action: chessai.core.action.Action) -> None:
        """
        Process the action of the non-player agent.
        This can be used to make any necessary updates for subclasses.
        """

    def process_agent_timeout(self, player: chessai.core.types.Color) -> None:
        # Treat timeouts like crashes.
        self.process_agent_crash(player)

    def process_agent_crash(self, player: chessai.core.types.Color) -> None:
        super().process_agent_crash(player)

        if (player == chessai.core.types.Color.WHITE):
            self.score += CRASH_POINTS

    def game_complete(self) -> tuple[list[chessai.core.types.Color], float]:
        """
        Determine the outcome of the tour.

        The tour agent wins if they reach all search targets.
        Otherwise the agent loses.
        """

        if (len(self.search_targets) == 0):
            self.score += BOARD_CLEAR_POINTS

            return ([self.search_agent], self.score)

        self.score += LOSE_POINTS

        return ([self.search_agent.opposite()], self.score)

    def copy(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> 'GameState':
        new_state = type(self)(
            board           = self.board.copy(),
            turn            = self.turn,
            castling_rights = self.castling_rights,
            en_passant_coordinate = self.en_passant_coordinate,
            halfmove_clock  = self.halfmove_clock,
            fullmove_number = self.fullmove_number,
            previous_action = self.previous_action,
            seed            = self.seed,
            game_over       = self.game_over,
            search_targets  = self.search_targets.copy(),
            _search_agent   = self.search_agent,
            _validate_search_targets = False)

        new_state.score = self.score

        return new_state

    @classmethod
    def get_gamestate_parser(cls) -> chessai.core.parser.GameStateParser:
        return chessai.tour.parser.parse_tour
