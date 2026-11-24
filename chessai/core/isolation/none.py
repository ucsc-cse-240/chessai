import logging
import random
import typing

import edq.util.time

import chessai.core.agent
import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.gamestate
import chessai.core.isolation.isolator

class NoneIsolator(chessai.core.isolation.isolator.AgentIsolator):
    """
    An isolator that does not do any isolation between the engine and agents.
    All agents will be run in the same thread (and therefore processes space).
    This is the simplest and fastest of all isolators, but offers the least control and protection.
    Agents cannot be timed out (since they run on the same thread).
    Agents can also access any memory, disk, or permissions that the core engine has access to.
    """

    def __init__(self) -> None:
        self._agents: dict[chessai.core.types.Color, chessai.core.agent.Agent] = {}
        """
        The agents that this isolator manages.
        These agents are held and ran in this thread's memory space.
        """

    def init_agents(self, agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo]) -> None:
        self._agents = {}
        for (team, agent_info) in agent_infos.items():
            self._agents[team] = chessai.core.agent.load(agent_info)

    def game_start(self,
            rng: random.Random,
            initial_state: chessai.core.gamestate.GameState,
            timeout: float,
            ) -> dict[chessai.core.types.Color, chessai.core.agentaction.AgentActionRecord]:
        results = {}
        for (team, agent) in self._agents.items():
            data = {
                'player': team,
                'suggested_seed': rng.randint(0, 2**64),
                'initial_state': initial_state,
            }

            results[team] = _call_agent_method(team, agent.game_start_full, data)

        return results

    def game_complete(self,
            final_state: chessai.core.gamestate.GameState,
            timeout: float,
            ) -> dict[chessai.core.types.Color, chessai.core.agentaction.AgentActionRecord]:
        results = {}
        for (team, agent) in self._agents.items():
            data = {
                'final_state': final_state,
            }

            results[team] = _call_agent_method(final_state.turn, agent.game_complete_full, data)

        return results

    def get_action(self,
            state: chessai.core.gamestate.GameState,
            timeout: float,
            ) -> chessai.core.agentaction.AgentActionRecord:
        agent = self._agents[state.turn]
        data = {
            'state': state,
        }

        return _call_agent_method(state.turn, agent.get_action_full, data)

    def close(self) -> None:
        self._agents.clear()

def _call_agent_method(
        player: chessai.core.types.Color,
        agent_method: typing.Callable[..., chessai.core.agentaction.AgentAction],
        agent_method_kwargs: dict[str, typing.Any],
        ) -> chessai.core.agentaction.AgentActionRecord:
    """ Call a method on the agent and do all the proper bookkeeping. """

    crashed = False
    agent_action: chessai.core.agentaction.AgentAction | None = None

    start_time = edq.util.time.Timestamp.now()

    try:
        agent_action = agent_method(**agent_method_kwargs)
    except Exception as ex:
        crashed = True
        logging.warning("Player %s crashed.", player, exc_info = ex)

    end_time = edq.util.time.Timestamp.now()

    return chessai.core.agentaction.AgentActionRecord(
            player = player,
            agent_action = agent_action,
            duration = end_time.sub(start_time),
            crashed = crashed)
