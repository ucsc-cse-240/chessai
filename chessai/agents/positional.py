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

        self.heat_map: dict[type[chessai.core.piece.Piece], dict[chessai.core.coordinate.Coordinate, int]] = {}
        """ Positional values, optionally specialized by piece type. """

    def game_start(self,
            initial_state: chessai.core.gamestate.GameState) -> None:
        self.heat_map = self._build_heat_map(initial_state.board)

    def get_square_score(self,
            piece: chessai.core.piece.Piece,
            coordinate: chessai.core.coordinate.Coordinate,
            ) -> int:
        """ Return a piece's positional value, using its type-specific map when available. """

        piece_heat_map = self.heat_map.get(type(piece), self.heat_map[chessai.core.piece.Piece])
        return piece_heat_map[coordinate]

    @staticmethod
    def _build_heat_map(
            board: chessai.core.board.Board,
            ) -> dict[type[chessai.core.piece.Piece], dict[chessai.core.coordinate.Coordinate, int]]:
        """ Build the default map, which rewards central squares for every piece. """

        central_heat_map = {}
        maximum_distance = (board.num_files - 1) + (board.num_ranks - 1)

        for file in range(board.num_files):
            for rank in range(board.num_ranks):
                coordinate = chessai.core.coordinate.Coordinate(file, rank)
                distance_from_center = abs((2 * file) - (board.num_files - 1))
                distance_from_center += abs((2 * rank) - (board.num_ranks - 1))
                central_heat_map[coordinate] = maximum_distance - distance_from_center

        return {chessai.core.piece.Piece: central_heat_map}

def positional_state_eval(
        state: chessai.core.gamestate.GameState,
        action: chessai.core.action.Action | None = None,
        agent: typing.Any | None = None,
        **kwargs: typing.Any) -> float:
    """
    Evaluate a position from the requesting agent's perspective.

    In addition to material, pieces receive more points the closer they are to
    the center. The agent is needed to identify which color the score favors.
    This function is an alias, so any started agent can use it.
    """

    del kwargs

    player = state.turn
    positional_agent = None
    if isinstance(agent, chessai.core.agent.Agent):
        if (agent.player is not None):
            player = agent.player

        if isinstance(agent, PositionalAgent):
            if (len(agent.heat_map) > 0):
                positional_agent = agent

    default_heat_map = PositionalAgent._build_heat_map(state.board)

    if ((len(state.get_legal_move_actions()) == 0) and state.is_check(state.turn)):
        if (state.turn == player):
            return -math.inf

        return math.inf

    score = chessai.chess.gamestate.base_eval(state, action = action, agent = agent)
    if (state.turn != player):
        score *= -1

    for (coordinate, piece) in state.get_coordinate_map().items():
        square_score = default_heat_map[chessai.core.piece.Piece][coordinate]
        if (positional_agent is not None):
            square_score = positional_agent.get_square_score(piece, coordinate)

        if (piece.color == player):
            score += square_score
        else:
            score -= square_score

    return score
