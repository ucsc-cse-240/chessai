import math

import chessai.chess.piece
import chessai.core.action
import chessai.core.agent
import chessai.core.board
import chessai.core.gamestate
import chessai.core.piece
import chessai.core.types

class SparringAgent(chessai.core.agent.Agent):
    """
    A weak but competent chess opponent intended for local practice.

    The agent does not search an opponent's replies or evaluate complete board positions.
    It makes a single move at a time using a few chess habits:
     - prefer a capture,
     - avoid leaving the moved piece attacked when possible, and
     - develop pieces toward the center of the board.

    The agent is a solid baseline for a tournament agent.
    """

    def __init__(self,
            name: chessai.util.reflection.Reference | str = chessai.util.alias.AGENT_RANDOM.long,
            state_eval_func: chessai.core.gamestate.AgentStateEvaluationFunction | chessai.util.reflection.Reference | str =
                    chessai.core.agentinfo.DEFAULT_STATE_EVAL) -> None:
        super().__init__(name, state_eval_func)

        self._good_files: list[int] = []
        self._good_ranks: list[int] = []
        self._home_rank: int = 0

    def game_start(self,
            initial_state: chessai.core.gamestate.GameState) -> None:
        self._good_ranks = self._mid_ranks(initial_state.board)
        self._good_files = self._mid_files(initial_state.board)

        if (self.player != chessai.core.types.Color.WHITE):
            self._home_rank = initial_state.board.num_ranks - 1

    def get_action(self,
            state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        legal_moves = state.get_legal_move_actions()
        if (len(legal_moves) == 0):
            return chessai.core.action.NoneAction()

        best_score = -math.inf
        best_moves: list[chessai.core.action.Action] = []
        for action in legal_moves:
            score = self._move_score(state, action)
            if (score > best_score):
                best_score = score
                best_moves = [action]
            elif (score == best_score):
                best_moves.append(action)

        return self.rng.choice(best_moves)

    def _move_score(self,
            state: chessai.core.gamestate.GameState,
            action: chessai.core.action.Action,
            ) -> int:
        if (not isinstance(action, chessai.core.action.MoveAction)):
            return -1

        piece = state.get(action.start_coordinate)
        if (piece is None):
            return -1

        score = self._capture_bonus(state, action)
        score += self._development_bonus(piece, action)

        successor = state.generate_successor(action, self.rng)
        opponent_attacks = successor.get_attacked_coordinates(successor.turn)
        if (action.end_coordinate in opponent_attacks):
            score -= 8

        return score

    def _capture_bonus(self,
            state: chessai.core.gamestate.GameState,
            action: chessai.core.action.MoveAction,
            ) -> int:
        if isinstance(action, chessai.core.action.PromotionAction):
            return 12

        if (state.is_capture(action)):
            return 10

        return 0

    def _development_bonus(self,
            piece: chessai.core.piece.Piece,
            action: chessai.core.action.MoveAction,
            ) -> int:
        score = 0
        if isinstance(piece, (chessai.chess.piece.Knight, chessai.chess.piece.Bishop)):
            if (action.start_coordinate.rank == self._home_rank):
                score += 3

        if isinstance(piece, chessai.chess.piece.Pawn):
            if (action.end_coordinate.file in self._good_files):
                score += 2

        if ((action.end_coordinate.file in self._good_files) and (action.end_coordinate.rank in self._good_ranks)):
            score += 1

        return score

    def _mid_ranks(self, board: chessai.core.board.Board) -> list[int]:
        return self._mid_points(board.num_ranks)

    def _mid_files(self, board: chessai.core.board.Board) -> list[int]:
        return self._mid_points(board.num_files)

    def _mid_points(self, size: int) -> list[int]:
        mid_point = size // 2

        mid_points = [mid_point]
        if mid_point != 0:
            mid_points.append(mid_point - 1)

        return mid_points
