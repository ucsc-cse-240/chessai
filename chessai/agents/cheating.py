import chessai.chess.piece
import chessai.core.action
import chessai.core.agent
import chessai.core.coordinate
import chessai.core.gamestate

class CheatingAgent(chessai.core.agent.Agent):
    """
    This agent cheats!
    On its turn, this agent will try to modify the game state to declare itself the winner.
    Agent isolation should prevent this agent from cheating.
    """

    def get_action(self, state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        enemy_king_coordinate = None

        # Remove all opposing pieces, except the king.
        for piece_position in state.get_coordinate_map(state.turn.opposite()):
            piece = state.get(piece_position)
            if isinstance(piece, chessai.chess.piece.King):
                enemy_king_coordinate = piece_position
                continue

            state.board.remove(piece_position)

        # Place queens all around the enemy king.
        if (enemy_king_coordinate is not None):
            for file_delta in range(-1, 2):
                for rank_delta in range(-1, 2):
                    # Don't replace the enemy king.
                    if (file_delta == 0) and (rank_delta == 0):
                        continue

                    file = enemy_king_coordinate.file - file_delta
                    rank = enemy_king_coordinate.rank - rank_delta
                    if not state.board.is_within_bounds(file, rank):
                        continue

                    state.board.set(chessai.chess.piece.Queen(state.turn),
                                    chessai.core.coordinate.Coordinate(file, rank))

        # Prioritize movement actions.
        legal_actions = state.get_legal_move_actions()

        # Fall back to all legal actions if there are no legal movement actions.
        if (len(legal_actions) == 0):
            legal_actions = state.get_legal_actions()

        # Try to move one of the queens without capturing the king.
        if (enemy_king_coordinate is not None):
            for action in legal_actions:
                if not isinstance(action, chessai.core.action.MoveAction):
                    continue

                if (action.end_coordinate == enemy_king_coordinate):
                    continue

                # All of our queens must be near the enemy king.
                file_delta = abs(action.start_coordinate.file - enemy_king_coordinate.file)
                if file_delta > 1:
                    continue

                rank_delta = abs(action.start_coordinate.rank - enemy_king_coordinate.rank)
                if rank_delta > 1:
                    continue

                return action

        # Take any remaining random action.
        return self.rng.choice(legal_actions)
