import collections
import math
import typing

import chessai.agents.greedy
import chessai.chess.gamestate
import chessai.core.action
import chessai.core.agent
import chessai.core.agentinfo
import chessai.core.board
import chessai.core.coordinate
import chessai.core.gamestate
import chessai.core.piece
import chessai.util.alias
import chessai.util.reflection

POSITIONAL_STATE_EVAL: str = chessai.util.alias.STATE_EVAL_POSITIONAL.long

class PositionalAgent(chessai.agents.greedy.GreedyAgent):
    """
    A greedy chess opponent that values material and central squares.

    This class inherits its move-selection behavior from GreedyAgent.
    Its only change is using positional_state_eval() as the default evaluator.
    """

    def __init__(self,
            name: chessai.util.reflection.Reference | str = chessai.util.alias.AGENT_POSITIONAL.long,
            state_eval_func: chessai.core.gamestate.AgentStateEvaluationFunction | chessai.util.reflection.Reference | str =
                    POSITIONAL_STATE_EVAL,
            display_name: str = '') -> None:
        # AgentInfo supplies the shared default when no evaluator was requested.
        if (state_eval_func == chessai.core.agentinfo.DEFAULT_STATE_EVAL):
            state_eval_func = POSITIONAL_STATE_EVAL

        super().__init__(name, state_eval_func, display_name)

        self.heat_map: dict[type[chessai.core.piece.Piece], dict[chessai.core.coordinate.Coordinate, float]] = {}
        """ Positional values, optionally specialized by piece type. """

    def game_start(self,
            initial_state: chessai.core.gamestate.GameState) -> None:
        player = self.player
        if (player is None):
            player = initial_state.turn

        # Build a heat map given for the player the agent is playing as.
        self.heat_map = self._build_heat_map(initial_state.board, player)

    def get_square_score(self,
            piece: chessai.core.piece.Piece,
            coordinate: chessai.core.coordinate.Coordinate,
            ) -> float:
        """ Return a piece's positional value, using its type-specific map when available. """

        return self._get_heat_map_score(self.heat_map, piece, coordinate) + self.rng.uniform(-0.1, 0.1)

    @staticmethod
    def _get_heat_map_score(
            heat_map: dict[type[chessai.core.piece.Piece], dict[chessai.core.coordinate.Coordinate, float]],
            piece: chessai.core.piece.Piece,
            coordinate: chessai.core.coordinate.Coordinate,
            ) -> float:
        """ Return a piece's positional value from a supplied heat map. """

        for piece_type in type(piece).mro():
            if piece_type in heat_map:
                return heat_map[piece_type][coordinate]

        return heat_map[chessai.core.piece.Piece][coordinate]

    @staticmethod
    def _build_heat_map(
            board: chessai.core.board.Board,
            player: chessai.core.types.Color,
            ) -> dict[type[chessai.core.piece.Piece], dict[chessai.core.coordinate.Coordinate, float]]:
        """
        Build the default heat map.

        Kings prefer to move to the edge of the board.
        Pawns prefer to move to the opposite side of the board to promote.
        Other pieces prefer moving to the center of the board.
        """

        central_heat_map = {}
        edge_heat_map = {}
        opposite_heat_map = {}

        final_rank = board.num_ranks - 1
        if (player == chessai.core.types.Color.BLACK):
            final_rank = 0

        maximum_distance = (board.num_files - 1) + (board.num_ranks - 1)

        for file in range(board.num_files):
            for rank in range(board.num_ranks):
                coordinate = chessai.core.coordinate.Coordinate(file, rank)
                distance_from_center = abs((2 * file) - (board.num_files - 1))
                distance_from_center += abs((2 * rank) - (board.num_ranks - 1))
                central_heat_map[coordinate] = float(maximum_distance - distance_from_center)
                edge_heat_map[coordinate] = float(distance_from_center - maximum_distance)
                opposite_heat_map[coordinate] = 2.5 * ((board.num_ranks - 1) - abs(final_rank - rank))

        return {
            # Default to always scoring the piece as 0.
            chessai.core.piece.Piece: collections.defaultdict(float),

            # Prefer to move the king to the edge of the map.
            chessai.chess.piece.King: edge_heat_map,

            # Prefer to move attacking pieces to the center.
            chessai.chess.piece.Queen: central_heat_map,
            chessai.chess.piece.Rook: central_heat_map,
            chessai.chess.piece.Bishop: central_heat_map,
            chessai.chess.piece.Knight: central_heat_map,

            # Prefer to move the pawns to the other side of the board to promote.
            chessai.chess.piece.Pawn: opposite_heat_map,
        }

def positional_state_eval(
        state: chessai.core.gamestate.GameState,
        action: chessai.core.action.Action | None = None,
        agent: typing.Any | None = None,
        **kwargs: typing.Any) -> float:
    """
    Evaluate a position from the requesting agent's perspective.

    In addition to material, pieces receive a reward based on their position.
    By default, the positional scoring is based on PositionalAgent._build_heat_map().
    """

    player = state.turn
    positional_agent = None
    if isinstance(agent, chessai.core.agent.Agent):
        if (agent.player is not None):
            player = agent.player

        if isinstance(agent, PositionalAgent):
            positional_agent = agent

    heat_maps = {
        color: PositionalAgent._build_heat_map(state.board, color)
        for color in chessai.core.types.Color
    }

    if ((len(state.get_legal_move_actions()) == 0) and state.is_check(state.turn)):
        if (state.turn == player):
            return -math.inf

        return math.inf

    score = chessai.chess.gamestate.base_eval(state, action = action, agent = agent)

    for (coordinate, piece) in state.get_coordinate_map().items():
        piece_heat_map = heat_maps[piece.color]
        square_score = PositionalAgent._get_heat_map_score(piece_heat_map, piece, coordinate)
        if ((positional_agent is not None) and (piece.color == player)):
            square_score = positional_agent.get_square_score(piece, coordinate)

        if (piece.color == player):
            score += 0.15 * square_score
        else:
            score -= 0.15 * square_score

    return score
