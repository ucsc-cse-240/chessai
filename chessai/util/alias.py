"""
This file provides useful aliases/shortcuts or short names for different objects in chessai.
For example, the `agent-random` alias can be used to reference `chessai.agents.random.RandomAgent`.
"""

class Alias:
    """ An alias for some object name. """

    _alias_map: dict[str, str] = {}
    """ Keep track of all aliases for testing purposes. """

    _all_aliases: list['Alias'] = []
    """ Keep track of all aliases mappings for lookup. """

    def __init__(self,
            short: str, long: str,
            is_qualified_name: bool = True, skip_windows_test: bool = False,
            ) -> None:
        self.short: str = short
        """ The short name for this alias. """

        self.long: str = long
        """ The long name for this alias. """

        self.is_qualified_name: bool = is_qualified_name
        """
        Whether this alias represents a qualified name.
        Alias that are qualified names will be tested with reflection.
        """

        self.skip_windows_test: bool = skip_windows_test
        """ If this alias' reflection test should be skipped on Windows. """

        if ('.' in short):
            raise ValueError(f"Dots ('.') are not allowed in aliases. Found '{short}'.")

        if (short in Alias._alias_map):
            raise ValueError(f"Found duplicate alias: '{short}' -> '{long}'.")

        Alias._alias_map[short] = long
        Alias._all_aliases.append(self)

    def __repr__(self) -> str:
        return f"('{self.short}' -> '{self.long}')"

def lookup(short: str, default: str | None = None) -> str:
    """
    Lookup the long name for an alias.
    Return the alias long name if the alias is found,
    and the default value if the alias is not found.
    If the alias is not found and no default is specified,
    then raise an error.
    """

    if (short in Alias._alias_map):
        return Alias._alias_map[short]

    if (default is not None):
        return default

    raise ValueError(f"Could not find alias: '{short}'.")

AGENT_AGGRESSIVE: Alias = Alias('agent-aggressive', 'chessai.agents.aggressive.AggressiveAgent')
AGENT_DUMMY: Alias = Alias('agent-dummy', 'chessai.agents.dummy.DummyAgent')
AGENT_GAURD: Alias = Alias('agent-guard', 'chessai.agents.guard.GuardAgent')
AGENT_GREEDY: Alias = Alias('agent-greedy', 'chessai.agents.greedy.GreedyAgent')
AGENT_MINIMAX: Alias = Alias('agent-minimax', 'chessai.student.multiagents.MyMinimaxLikeAgent')
AGENT_MULTI_SCRIPTED: Alias = Alias('agent-multi-scripted', 'chessai.agents.multiscripted.MultiScriptedAgent')
AGENT_PICK_FIRST: Alias = Alias('agent-pick-first', 'chessai.agents.pickfirst.PickFirstAgent')
AGENT_RANDOM: Alias = Alias('agent-random', 'chessai.agents.random.RandomAgent')
AGENT_REFLEX: Alias = Alias('agent-reflex', 'chessai.student.multiagents.ReflexAgent')
AGENT_SCRIPTED: Alias = Alias('agent-scripted', 'chessai.agents.scripted.ScriptedAgent')
AGENT_SEARCH_PROBLEM: Alias = Alias('agent-search-problem', 'chessai.agents.searchproblem.SearchProblemAgent')
AGENT_TIMEOUT: Alias = Alias('agent-timeout', 'chessai.agents.testing.TimeoutAgent')
AGENT_USER_INPUT: Alias = Alias('agent-user-input', 'chessai.agents.userinput.UserInputAgent')

AGENT_SHORT_NAMES: list[str] = [
    AGENT_AGGRESSIVE.short,
    AGENT_DUMMY.short,
    AGENT_MINIMAX.short,
    AGENT_MULTI_SCRIPTED.short,
    AGENT_GAURD.short,
    AGENT_GREEDY.short,
    AGENT_RANDOM.short,
    AGENT_SCRIPTED.short,
    AGENT_SEARCH_PROBLEM.short,
    AGENT_TIMEOUT.short,
    AGENT_USER_INPUT.short,
]

DISTANCE_EUCLIDEAN: Alias = Alias('distance-euclidean', 'chessai.search.distance.euclidean_distance')
DISTANCE_MANHATTAN: Alias = Alias('distance-manhattan', 'chessai.search.distance.manhattan_distance')
DISTANCE_KNIGHT: Alias = Alias('distance-knight', 'chessai.search.distance.knight_distance')

DISTANCE_SHORT_NAMES: list[str] = [
    DISTANCE_EUCLIDEAN.short,
    DISTANCE_MANHATTAN.short,
    DISTANCE_KNIGHT.short,
]

COST_FUNC_LONGITUDINAL: Alias = Alias('cost-longitudinal', 'chessai.search.common.longitudinal_cost_function')
COST_FUNC_STAY_EAST: Alias = Alias('cost-stay-east', 'chessai.search.common.stay_east_cost_function')
COST_FUNC_STAY_WEST: Alias = Alias('cost-stay-west', 'chessai.search.common.stay_west_cost_function')
COST_FUNC_UNIT: Alias = Alias('cost-unit', 'chessai.search.common.unit_cost_function')

COST_FUNC_SHORT_NAMES: list[str] = [
    COST_FUNC_LONGITUDINAL.short,
    COST_FUNC_STAY_EAST.short,
    COST_FUNC_STAY_WEST.short,
    COST_FUNC_UNIT.short,
]

HEURISTIC_EUCLIDEAN: Alias = Alias('heuristic-euclidean', 'chessai.search.distance.euclidean_heuristic')
HEURISTIC_KNIGHT: Alias = Alias('heuristic-knight', 'chessai.student.singlesearch.knights_tour_heuristic')
HEURISTIC_MANHATTAN: Alias = Alias('heuristic-manhattan', 'chessai.search.distance.manhattan_heuristic')
HEURISTIC_NULL: Alias = Alias('heuristic-null', 'chessai.search.common.null_heuristic')

HEURISTIC_SHORT_NAMES: list[str] = [
    HEURISTIC_EUCLIDEAN.short,
    HEURISTIC_KNIGHT.short,
    HEURISTIC_MANHATTAN.short,
    HEURISTIC_NULL.short,
]

SEARCH_PROBLEM_POSITION: Alias = Alias('search-problem-position', 'chessai.search.position.PositionSearchProblem')

SEARCH_PROBLEM_SHORT_NAMES: list[str] = [
    SEARCH_PROBLEM_POSITION.short,
]

SEARCH_SOLVER_ASTAR: Alias = Alias('search-solver-astar', 'chessai.student.singlesearch.astar_search')
SEARCH_SOLVER_BFS: Alias = Alias('search-solver-bfs', 'chessai.student.singlesearch.breadth_first_search')
SEARCH_SOLVER_DFS: Alias = Alias('search-solver-dfs', 'chessai.student.singlesearch.depth_first_search')
SEARCH_SOLVER_TOUR_BASE: Alias = Alias('search-solver-tour-base', 'chessai.search.tourbase.tour_base_search')
SEARCH_SOLVER_RANDOM: Alias = Alias('search-solver-random', 'chessai.search.random.random_search')
SEARCH_SOLVER_UCS: Alias = Alias('search-solver-ucs', 'chessai.student.singlesearch.uniform_cost_search')

SEARCH_SOLVER_SHORT_NAMES: list[str] = [
    SEARCH_SOLVER_ASTAR.short,
    SEARCH_SOLVER_BFS.short,
    SEARCH_SOLVER_DFS.short,
    SEARCH_SOLVER_TOUR_BASE.short,
    SEARCH_SOLVER_RANDOM.short,
    SEARCH_SOLVER_UCS.short,
]

STATE_EVAL_BASE: Alias = Alias('state-eval-base', 'chessai.chess.gamestate.base_eval')
STATE_EVAL_MINIMAX_BETTER: Alias = Alias('state-eval-minimax-better', 'chessai.student.multiagents.better_state_eval')

STATE_EVAL_SHORT_NAMES: list[str] = [
    STATE_EVAL_BASE.short,
    STATE_EVAL_MINIMAX_BETTER.short,
]

UI_NULL: Alias = Alias('null', 'chessai.ui.null.NullUI')
UI_STDIO: Alias = Alias('text', 'chessai.ui.text.StdioUI', skip_windows_test = True)
# UI_STDIO_PACMAN: Alias = Alias('text-pacman', 'chessai.pacman.textui.StdioUI', skip_windows_test = True)
UI_RAW_TEXT: Alias = Alias('raw-text', 'chessai.ui.text.TextUI', skip_windows_test = True)
# UI_TK: Alias = Alias('tk', 'chessai.ui.tk.TkUI')
# UI_WEB: Alias = Alias('web', 'chessai.ui.web.WebUI')

UI_SHORT_NAMES: list[str] = [
    UI_NULL.short,
    UI_STDIO.short,
    # UI_TK.short,
    # UI_WEB.short,
]
