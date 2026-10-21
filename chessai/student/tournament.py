import chessai.core.action
import chessai.core.agent
import chessai.core.gamestate

class TournamentAgent(chessai.core.agent.Agent):
    """
    An agent that will compete in the tournament.

    You are free to use any of the techniques learned throughout the course.
    You may modify this agent however you wish,
    including which agent it inherits from.
    Remember that the tournament has strict time constraints.
    """

    def game_start(self,
            initial_state: chessai.core.gamestate.GameState) -> None:
        # *** Your Code Here ***
        super().game_start(initial_state)

    def game_complete(self,
            final_state: chessai.core.gamestate.GameState) -> None:
        # *** Your Code Here ***
        super().game_complete(final_state)

    def get_action(self, state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        # *** Your Code Here ***
        return chessai.core.action.NoneAction()
