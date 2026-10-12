"""
In this file, you will implement code relating to simple single-agent searches.

For Assignment 1, you will be working on the Piece Tour problem:
given a starting square and target squares on a chessboard,
find the minimum number of moves for an arbitrary piece to travel to all of them.

You will implement four search algorithms:
  - Depth First Search (DFS)
  - Breadth First Search (BFS)
  - Uniform Cost Search (UCS)
  - A* Search

You will also implement heuristics for A* and analyze their admissibility and consistency.
"""

import random
import typing

import chessai.agents.searchproblem
import chessai.core.search
import chessai.search.common
import chessai.search.distance

class Node:
    """ A graph node with a label. """

    def __init__(self,
            label: str) -> None:
        self.label: str = label

    def __repr__(self) -> str:
        return f"Node(label = {self.label})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False

        return self.label == other.label

    def __hash__(self) -> int:
        return hash(self.label)

class StartNode(Node):
    """ A graph node for the start of a search problem. """

    def __init__(self) -> None:
        super().__init__("Start")

class GoalNode(Node):
    """ A graph node for the goal of a search problem. """

    def __init__(self) -> None:
        super().__init__("Goal")

def manual_depth_first_search() -> typing.List[Node]:
    """
    Use this function to write your solution to a manual depth first search (DFS) problem.
    This means that it will search the deepest nodes in the search tree first.
    See: https://en.wikipedia.org/wiki/Depth-first_search .
    """

    # *** Your Code Here ***
    raise NotImplementedError('manual_depth_first_search')

def depth_first_search(
        problem: chessai.core.search.SearchProblem,
        heuristic: chessai.core.search.SearchHeuristic,
        rng: random.Random,
        **kwargs: typing.Any) -> chessai.core.search.SearchSolution:
    """
    A chessai.core.search.SearchProblemSolver that implements depth first search (DFS).
    This means that it will search the deepest nodes in the search tree first.
    See: https://en.wikipedia.org/wiki/Depth-first_search .
    """

    # *** Your Code Here ***
    raise NotImplementedError('depth_first_search')

def manual_breadth_first_search() -> typing.List[Node]:
    """
    Use this function to write your solution to a manual breadth first search (BFS) problem.
    This means that it will search nodes based on what level in search tree they appear.
    See: https://en.wikipedia.org/wiki/Breadth-first_search .
    """

    # *** Your Code Here ***
    raise NotImplementedError('manual_breadth_first_search')

def breadth_first_search(
        problem: chessai.core.search.SearchProblem,
        heuristic: chessai.core.search.SearchHeuristic,
        rng: random.Random,
        **kwargs: typing.Any) -> chessai.core.search.SearchSolution:
    """
    A chessai.core.search.SearchProblemSolver that implements breadth first search (BFS).
    This means that it will search nodes based on what level in search tree they appear.
    See: https://en.wikipedia.org/wiki/Breadth-first_search .
    """

    # *** Your Code Here ***
    raise NotImplementedError('breadth_first_search')

def manual_uniform_cost_search() -> typing.List[Node]:
    """
    Use this function to write your solution to a manual uniform cost search (UCS) problem.
    This means that it will search nodes with a lower total cost first.
    See: https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm#Practical_optimizations_and_infinite_graphs .
    """

    # *** Your Code Here ***
    raise NotImplementedError('manual_uniform_cost_search')

def uniform_cost_search(
        problem: chessai.core.search.SearchProblem,
        heuristic: chessai.core.search.SearchHeuristic,
        rng: random.Random,
        **kwargs: typing.Any) -> chessai.core.search.SearchSolution:
    """
    A chessai.core.search.SearchProblemSolver that implements uniform cost search (UCS).
    This means that it will search nodes with a lower total cost first.
    See: https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm#Practical_optimizations_and_infinite_graphs .
    """

    # *** Your Code Here ***
    raise NotImplementedError('uniform_cost_search')

def manual_astar_search() -> typing.List[Node]:
    """
    Use this function to write your solution to a manual A* search (pronounced "A Star search") problem.
    This means that it will search nodes with a lower combined cost and heuristic first.
    See: https://en.wikipedia.org/wiki/A*_search_algorithm .
    """

    # *** Your Code Here ***
    raise NotImplementedError('manual_astar_search')

def astar_search(
        problem: chessai.core.search.SearchProblem,
        heuristic: chessai.core.search.SearchHeuristic,
        rng: random.Random,
        **kwargs: typing.Any) -> chessai.core.search.SearchSolution:
    """
    A chessai.core.search.SearchProblemSolver that implements A* search (pronounced "A Star search").
    This means that it will search nodes with a lower combined cost and heuristic first.
    See: https://en.wikipedia.org/wiki/A*_search_algorithm .
    """

    # *** Your Code Here ***
    raise NotImplementedError('astar_search')

def knight_distance(
        a: chessai.core.coordinate.Coordinate,
        b: chessai.core.coordinate.Coordinate,
        state: chessai.core.gamestate.GameState | None = None,
        **kwargs: typing.Any) -> float:
    """
    Compute the Knight's distance between two positions.
    """

    # *** Your Code Here ***
    raise NotImplementedError('knight_distance')

def knight_heuristic(
        node: chessai.core.search.SearchNode,
        problem: chessai.core.search.SearchProblem,
        **kwargs: typing.Any) -> float:
    """
    A distance_heuristic using Knight's distance.
    """

    return chessai.search.distance.distance_heuristic(node, problem, knight_distance, **kwargs)

class KingEscortSearchNode(chessai.core.search.SearchNode):
    """
    A search node representing a state in the King Escort problem.

    The state must encode everything the search needs to determine:
      1. Where the king currently is,
      2. where the opposing rooks are (to know where they might attack),
      3. where your knights are (to know how they can block the rooks),
      4. and whether the goal has been reached.
    """

    def __init__(self) -> None:
        """
        Construct a search node for the King Escort problem.
        You may add arguments to this constructor as needed.
        """

        # *** Your Code Here ***
        # Remember that you can also add arguments to your constructor.

class KingEscortSearchProblem(chessai.core.search.SearchProblem[KingEscortSearchNode]):
    """
    A search problem for moving an king piece from a start square to a target square
    in the minimum number of moves.
    """

    def __init__(self,
            game_state: chessai.core.gamestate.GameState,
            **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)

        # *** Your Code Here ***

    def get_starting_node(self) -> KingEscortSearchNode:
        # *** Your Code Here ***
        raise NotImplementedError('KingEscortSearchProblem.get_starting_node')

    def is_goal_node(self, node: KingEscortSearchNode) -> bool:
        # *** Your Code Here ***
        raise NotImplementedError('KingEscortSearchProblem.is_goal_node')

    def get_successor_nodes(self, node: KingEscortSearchNode) -> list[chessai.core.search.SuccessorInfo]:
        # *** Your Code Here ***
        raise NotImplementedError('KingEscortSearchProblem.get_successor_nodes')

def king_escort_heuristic(
        node: KingEscortSearchNode,
        problem: KingEscortSearchProblem,
        **kwargs: typing.Any) -> float:
    """
    A heuristic for KingEscortSearchProblem.

    This function should always return a number that is a lower bound
    on the shortest path from the state to a goal of the problem;
    i.e. it should be admissible.
    (You need not worry about consistency for this heuristic to receive full credit.)
    """

    # *** Your Code Here ***
    return chessai.search.common.null_heuristic(node, problem)

class KingEscortSearchAgent(chessai.agents.searchproblem.SearchProblemAgent):
    """
    An agent that works by solving the king escort search problem,
    and then executing the path found during the search.

    If the above king escort related classes and functions are implemented,
    you may not need to modify this agent.
    """

    def get_action(self, state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        # *** Your Code Here ***
        return super().get_action(state)
