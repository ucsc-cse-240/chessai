import logging
import typing

import edq.util.time

import chessai.core.action
import chessai.core.agent
import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.board
import chessai.core.gamestate
import chessai.core.search
import chessai.core.coordinate
import chessai.search.common
import chessai.search.random
import chessai.search.position
import chessai.util.alias
import chessai.util.reflection

DEFAULT_PROBLEM: str = chessai.util.alias.SEARCH_PROBLEM_POSITION.long
DEFAULT_PROBLEM_COST: str = chessai.util.alias.COST_FUNC_UNIT.long
DEFAULT_SOLVER: str = chessai.util.alias.SEARCH_SOLVER_RANDOM.long
DEFAULT_HEURISTIC: str = chessai.util.alias.HEURISTIC_NULL.long

class SearchProblemAgent(chessai.core.agent.Agent):
    """
    An agent that works by first solving a search problem (chessai.core.search.Problem),
    and then executing the path found during the search.
    """

    def __init__(self,
            problem: type[chessai.core.search.SearchProblem] | chessai.util.reflection.Reference | str = DEFAULT_PROBLEM,
            problem_cost: chessai.core.search.CostFunction | chessai.util.reflection.Reference | str = DEFAULT_PROBLEM_COST,
            solver: chessai.core.search.SearchProblemSolver | chessai.util.reflection.Reference | str = DEFAULT_SOLVER,
            heuristic: chessai.core.search.SearchHeuristic | chessai.util.reflection.Reference | str = DEFAULT_HEURISTIC,
            **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)

        claen_problem_class = chessai.util.reflection.resolve_and_fetch(type, problem)
        self._problem_class: type[chessai.core.search.SearchProblem] = claen_problem_class
        """ The search problem class this agent will use. """

        claen_problem_cost_function = chessai.util.reflection.resolve_and_fetch(chessai.core.search.CostFunction, problem_cost)
        self._problem_cost_function: chessai.core.search.CostFunction = claen_problem_cost_function
        """ The cost function for this agent's search problem. """

        claen_solver_function = chessai.util.reflection.resolve_and_fetch(chessai.core.search.SearchProblemSolver, solver)
        self._solver_function: chessai.core.search.SearchProblemSolver = claen_solver_function
        """ The search solver function this agent will use. """

        claen_heuristic_function = chessai.util.reflection.resolve_and_fetch(chessai.core.search.SearchHeuristic, heuristic)
        self._heuristic_function: chessai.core.search.SearchHeuristic = claen_heuristic_function
        """ The search heuristic function this agent will use. """

        self._actions: list[chessai.core.action.Action] = []
        """ The actions that the search solver came up with. """

        logging.debug("Created a SearchProblemAgent using problem '%s', cost function '%s', solver '%s', and heuristic '%s'.",
                chessai.util.reflection.get_qualified_name(problem),
                chessai.util.reflection.get_qualified_name(problem_cost),
                chessai.util.reflection.get_qualified_name(solver),
                chessai.util.reflection.get_qualified_name(heuristic))

    def get_action(self, state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        if (len(self._actions) == 0):
            return chessai.core.action.NoneAction()

        return self._actions.pop(0)

    def game_start_full(self,
            player: chessai.core.types.Color,
            suggested_seed: int,
            initial_state: chessai.core.gamestate.GameState,
            ) -> chessai.core.agentaction.AgentAction:
        # Do the standard game initialization steps.
        super().game_start_full(player, suggested_seed, initial_state)

        # This is the agent's first time seeing the game's state (which includes the board).
        # Create a search problem using the game's state, and solve the problem.

        start_time = edq.util.time.Timestamp.now()
        (solution, position_history, expanded_node_count) = self._do_search(initial_state)
        end_time = edq.util.time.Timestamp.now()

        self._actions = solution.actions

        logging.info("Path found with %d steps and a total cost of %0.2f in %0.2f seconds. %d search nodes expanded.",
                len(solution.actions), solution.cost, (end_time.sub(start_time).to_secs()), expanded_node_count)
        logging.trace(f"Position history: '{position_history}'.") # type: ignore[attr-defined]  # pylint: disable=no-member

        return chessai.core.agentaction.AgentAction()

    def _do_search(self,
            state: chessai.core.gamestate.GameState,
            ) -> tuple[chessai.core.search.SearchSolution, list[chessai.core.coordinate.Coordinate], int]:
        """
        Perform the actual search operation.
        Children may override this to change searching behavior.
        Return: (solution, position history, expanded node count).
        """

        search_problem = self._problem_class(game_state = state, cost_function = self._problem_cost_function)
        solution = self._solver_function(search_problem, self._heuristic_function, self.rng)

        if (solution.goal_node is not None):
            search_problem.complete(solution.goal_node)

        return (solution, search_problem.position_history, search_problem.expanded_node_count)

class GreedySubproblemSearchAgent(SearchProblemAgent):
    """
    An agent that greedily solves several search problems (instead of just one main one).
    This agent will repeatedly create and solve search problems until the game state signals the game is over
    (chessai.core.gamestate.GameState.game_over == True).
    Once the goal is reached, the actions from all subproblem solutions will be concatenated to form the final list of actions.
    """

    def _do_search(self,
            state: chessai.core.gamestate.GameState,
            ) -> tuple[chessai.core.search.SearchSolution, list[chessai.core.coordinate.Coordinate], int]:
        actions = []
        total_cost = 0.0
        goal_node = None
        total_position_history = []
        total_expanded_node_count = 0

        while (not state.game_over):
            # Solve the subproblem.
            (solution, position_history, expanded_node_count) = super()._do_search(state)

            if (solution.goal_node is None):
                raise ValueError("Failed to solve subproblem.")

            # Add all the components of the sub-solution to the total solution.
            actions += solution.actions
            total_cost += solution.cost
            goal_node = solution.goal_node
            total_position_history += position_history
            total_expanded_node_count += expanded_node_count

            # Move to the next state by applying all the actions.
            for action in solution.actions:
                state = state.generate_successor(action, self.rng)

        solution = chessai.core.search.SearchSolution(actions, total_cost, goal_node)
        return (solution, total_position_history, total_expanded_node_count)
