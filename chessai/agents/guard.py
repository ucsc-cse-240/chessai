import chessai.core.action
import chessai.core.agent
import chessai.core.gamestate

class GuardAgent(chessai.core.agent.Agent):
    """ An agent that will capture a piece if possible, otherwise it will stay still. """

    def get_action(self,
            state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        """
        Returns a stochastic aggressive action based on the game state.
        """

        # Try to capture a piece.
        legal_actions = state.get_legal_move_actions()
        for action in legal_actions:
            if (state.is_capture(action)):
                return action

        # If we couldn't find an action that is a capture, do nothing.
        return chessai.core.action.NoneAction()
