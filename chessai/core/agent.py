import abc
import random
import typing

import chessai.core.action
import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.gamestate

class Agent(abc.ABC):
    """
    The base for all agents in the chessai system.

    Agents are called on by the game engine for three things:
    1) `game_start_full()`/`game_start()` - a notification that the game has started.
    2) `game_complete()` - a notification that the game has ended.
    3) `get_action()` - a request for the agent to provide its next action.

    For the three core agent methods: get_action(), game_start(), and game_complete(),
    this class provides "full" versions of these methods (suffixed with "_full").
    These methods may have more information and allow the agent to provide more information,
    but are a little more complex.
    By default, this class will just call the simple methods from the "full" ones,
    allowing children to just implement the simple methods.

    Agents should avoid doing any heavy work in their constructors,
    and instead do that work in game_start_full()/game_start() (where they will have access to the game state).
    """

    def __init__(self,
            name: chessai.util.reflection.Reference | str = chessai.util.alias.AGENT_RANDOM.long,
            state_eval_func: chessai.core.gamestate.AgentStateEvaluationFunction | chessai.util.reflection.Reference | str =
                    chessai.core.agentinfo.DEFAULT_STATE_EVAL,
            display_name: str = '') -> None:
        self.name: chessai.util.reflection.Reference = chessai.util.reflection.Reference(name)
        """ The name of the agent. """

        clean_state_eval_func = chessai.util.reflection.resolve_and_fetch(chessai.core.gamestate.AgentStateEvaluationFunction, state_eval_func)
        self.evaluation_function: chessai.core.gamestate.AgentStateEvaluationFunction = clean_state_eval_func
        """ The evaluation function that agent will use to assess game states. """

        if (display_name == ''):
            display_name = str(name)

        self.display_name: str = display_name
        """ The display name of the agent. """

        self.rng: random.Random = random.Random(4)
        """
        The RNG this agent should use whenever it wants randomness.
        This object will be constructed right away,
        but will be recreated with the suggested seed from the game engine during game_start_full().
        """

        self.player: chessai.core.types.Color | None = None
        """
        The color of the player this agent has been assigned for this game.
        It is initialized to None (before the game starts), but gets populated during game_start_full().
        """

        self.ply: int = -1
        """
        The number of move pairs that the agent should look ahead.
        1 ply is both max and min.
        It is initialized to -1 (before the game starts), but gets populated during game_start_full().
        """

    def get_action_full(self,
            state: chessai.core.gamestate.GameState,
            ) -> chessai.core.agentaction.AgentAction:
        """
        Get an action for this agent given the current state of the game.
        Agents may keep internal state, but the given state should be considered the source of truth.
        Calls to this method may be subject to a timeout (enforced by the isolator).

        By default, this method just calls get_action().
        Agent classes should typically just implement get_action(),
        and only implement this if they need additional functionality.
        """

        action = self.get_action(state)

        return chessai.core.agentaction.AgentAction(action)

    def get_action(self,
            state: chessai.core.gamestate.GameState,
            ) -> chessai.core.action.Action:
        """
        Get an action for this agent given the current state of the game.
        This is simplified version of get_action_full(),
        see that method for full details.
        """

        return chessai.core.action.NoneAction()

    def game_start_full(self,
            player: chessai.core.types.Color,
            suggested_seed: int,
            initial_state: chessai.core.gamestate.GameState,
            ) -> chessai.core.agentaction.AgentAction:
        """
        Notify this agent that the game is about to start.
        The state represents the initial state of the game.
        Any precomputation for this game should be done in this method.
        Calls to this method may be subject to a timeout.
        """

        self.player = player
        self.rng = random.Random(suggested_seed)

        self.game_start(initial_state)

        return chessai.core.agentaction.AgentAction(chessai.core.action.NoneAction())

    def game_start(self,
            initial_state: chessai.core.gamestate.GameState) -> None:
        """
        Notify this agent that the game is about to start.
        The state represents the initial state of the game.
        Any precomputation for this game should be done in this method.
        Calls to this method may be subject to a timeout.
        """

    def game_complete_full(self,
            final_state: chessai.core.gamestate.GameState,
            ) -> chessai.core.agentaction.AgentAction:
        """
        Notify this agent that the game has concluded.
        Agents should use this as an opportunity to make any final calculations and close any game-related resources.
        """

        self.game_complete(final_state)

        return chessai.core.agentaction.AgentAction(chessai.core.action.NoneAction())

    def game_complete(self,
            final_state: chessai.core.gamestate.GameState) -> None:
        """
        Notify this agent that the game has concluded.
        Agents should use this as an opportunity to make any final calculations and close any game-related resources.
        """

    def evaluate_state(self,
            state: chessai.core.gamestate.GameState,
            action: chessai.core.action.Action | None = None,
            **kwargs: typing.Any) -> float:
        """
        Evaluate the state to get a decide how good the current position is.
        The base implementation for this function just calls `self.evaluation_function`,
        but child classes may override this method to easily implement their own evaluations.
        """

        return self.evaluation_function(state, action = action, agent = self, **kwargs)

    def get_minimax_move(self,
            state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        """
        This function chooses the best move for the given board position, evaluation function, player, and ply.

        Parameters:
        - state: The state of the chess game, including the board and move stack.

        Returns:
        A single chessai.core.action.Action type object.
        """

        return chessai.core.action.NoneAction()


    def get_expectimax_move(self,
            state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        """
        This function chooses the best move for the given board position, evaluation function, player, and ply.

        Parameters:
        - state: The state of the chess game, including the board and move stack.

        Returns:
        A single chessai.core.action.Action type object.
        """

        return chessai.core.action.NoneAction()

def load(agent_info: chessai.core.agentinfo.AgentInfo) -> Agent:
    """
    Construct a new agent object using the given agent info.
    The name of the agent will be used as a reference to (e.g., name of) the agent's class.
    """

    agent = chessai.util.reflection.new_object(agent_info.name, **agent_info.to_flat_dict())

    if (not isinstance(agent, Agent)):
        raise ValueError(f"Loaded class is not an agent: '{agent_info.name}'.")

    return agent
