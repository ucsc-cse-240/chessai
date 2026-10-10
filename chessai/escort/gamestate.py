import typing

import chessai.core.action
import chessai.core.coordinate
import chessai.core.parser
import chessai.core.types
import chessai.escort.parser
import chessai.tour.gamestate

class GameState(chessai.tour.gamestate.GameState):
    """ A game state in which one agent must escort the king to a target without getting captured. """

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
                 goal: chessai.core.coordinate.Coordinate | None = None,
                 _search_agent: chessai.core.types.Color | None = None,
                 _validate_search_targets: bool = True,
                 **kwargs: typing.Any) -> None:
        super().__init__(board, turn, castling_rights, en_passant_coordinate,
                         halfmove_clock, fullmove_number, previous_action,
                         seed, game_over, search_targets, _search_agent,
                         _validate_search_targets, **kwargs)

        # Escort games can only have a single search target, for simplicity.
        if (len(self.search_targets) > 1):
            self.search_targets = self.search_targets[:1]

        if goal is None:
            if (len(self.search_targets) == 0):
                raise ValueError("Cannot create an escort game without a goal.")

            goal = self.search_targets[0]

        if (not self.board.is_within_bounds(goal.file, goal.rank)):
            raise ValueError("Cannot create an escort game with an out of bounds target.")

        self.goal: chessai.core.coordinate.Coordinate = goal
        """ The goal of the escort game. """

    def get_legal_actions(self) -> list[chessai.core.action.Action]:
        """ Return non-capture actions, actions that capture the king, and the null action. """

        actions = super().get_legal_actions()

        escort_actions: list[chessai.core.action.Action] = []
        for action in actions:
            # Escort agents can only perform movement actions and the none action.
            if (not isinstance(action, chessai.core.action.MoveAction)):
                continue

            # Remove capture actions that are not capturing the King.
            piece = self.get(action.end_coordinate) # pylint: disable=no-member
            if ((piece is not None) and (not isinstance(piece, chessai.chess.piece.King))):
                continue

            escort_actions.append(action)

        # Escort agents are allowed to stay still, as they lose points every turn.
        escort_actions.append(chessai.core.action.NoneAction())

        return escort_actions

    def _update_targets_and_score(self, action: chessai.core.action.Action) -> None:
        """ Update the remaining targets and score based on the search agents action. """

        if isinstance(action, chessai.core.action.MoveAction):
            destination_coordinate = action.end_coordinate
            # Get points when the king reaches the goal.
            if (destination_coordinate in self.search_targets):
                # The action has not been applied, so check the piece at the starting coordinate.
                piece = self.get(action.start_coordinate) # pylint: disable=no-member
                if (isinstance(piece, chessai.chess.piece.King)):
                    # Get points for reaching a search target.
                    self.remove_search_target(destination_coordinate)
                    self.score += chessai.tour.gamestate.POSITION_POINTS

        # The agent always loses a point each turn.
        self.score -= chessai.tour.gamestate.TIME_PENALTY

    def _process_enemy_action(self, action: chessai.core.action.Action) -> None:
        """ King escort games must check if the King got captured during an opponent turn. """

        king_coordinate = self.get_king_coordinate(self.search_agent)
        if (king_coordinate is None):
            self.game_over = True

    def copy(self,
             context: typing.Union[typing.Any, None] = None,
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
            goal            = self.goal,
            _search_agent   = self.search_agent,
            _validate_search_targets = False)

        new_state.score = self.score

        return new_state

    @classmethod
    def get_gamestate_parser(cls) -> chessai.core.parser.GameStateParser:
        return chessai.escort.parser.parse_escort
