import random

import chessai.tour.game
import chessai.core.gamestate
import chessai.escort.gamestate

class Game(chessai.tour.game.Game):
    """
    A special tour game where the agents must protect the king while navigating it to the designated coordinates.
    """

    def get_initial_state(self,
                          rng: random.Random,
                          fen: str | None = None) -> chessai.core.gamestate.GameState:
        if (len(self.search_targets) == 0):
            # Let the gamestate parse the FEN so we can look for search targets from a file.
            initial_state = chessai.escort.gamestate.GameState.from_fen(fen = fen)
            self.search_targets = initial_state.search_targets
        else:
            initial_state = chessai.escort.gamestate.GameState.from_fen(fen = fen, search_targets = self.search_targets)

        # The search agent is always the agent with the first move.
        self.search_agent = initial_state.turn

        return initial_state
