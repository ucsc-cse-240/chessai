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

import chessai.core.search
import chessai.search.common

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


class PieceTourSearchNode(chessai.core.search.SearchNode):
    """
    A search node representing a state in the Piece Tour problem.

    The state must encode everything the search needs to determine:
      1. Where the knight currently is.
      2. Whether the goal has been reached.

    For the basic Piece Tour problem (single target square),
    the position alone is sufficient. But think carefully:
    if you were to extend this to visiting multiple squares,
    what additional information would your state need to track?
    """

    def __init__(self) -> None:
        """
        Construct a search node for the Piece Tour problem.
        You may add arguments to this constructor as needed.
        """

        # *** Your Code Here ***
        # Remember that you can also add arguments to your constructor.

class PieceTourSearchProblem(chessai.core.search.SearchProblem[PieceTourSearchNode]):
    """
    A search problem for moving an arbitrary piece from a start square to target squares
    in the minimum number of moves.

    The board is a standard 8x8 chessboard.
    Squares are represented as (file, rank) tuples where file and rank are both in [0, 7].
    For example, (0, 0) is a1, (7, 7) is h8.

    Note: A knight moves in an 'L' shape: two squares in one direction and one square perpendicular.
    A knight on (file, rank) can reach up to 8 squares.
    """

    def __init__(self,
            start: tuple[int, int],
            target: tuple[int, int],
            **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)

        self._start = start
        self._target = target

        # *** Your Code Here (if needed) ***

    def get_starting_node(self) -> PieceTourSearchNode:
        # *** Your Code Here ***
        raise NotImplementedError('PieceTourSearchProblem.get_starting_node')

    def is_goal_node(self, node: PieceTourSearchNode) -> bool:
        # *** Your Code Here ***
        raise NotImplementedError('PieceTourSearchProblem.is_goal_node')

    def get_successor_nodes(self, node: PieceTourSearchNode) -> list[chessai.core.search.SuccessorInfo]:
        """
        Return a list of (successor_node, action, cost) tuples representing
        all valid moves from the current node.
        """

        # *** Your Code Here ***
        raise NotImplementedError('PieceTourSearchProblem.get_successor_nodes')

def knights_tour_heuristic(
        node: PieceTourSearchNode,
        problem: PieceTourSearchProblem,
        **kwargs: typing.Any) -> float:
    """
    A heuristic for a Piece Tour using a knight.

    Your heuristic must be ADMISSIBLE: it must never overestimate the
    true cost to reach the goal. Formally, for all nodes n:
        h(n) <= h*(n)
    where h*(n) is the true optimal cost from n to the goal.

    For full credit, your heuristic should also be CONSISTENT:
        h(n) <= cost(n, n') + h(n')
    for every successor n' of n.

    A non-trivial heuristic that is both admissible and consistent and meaningfully
    reduces the number of nodes expanded compared to UCS will receive full credit.

    Hint: Think about the minimum possible number of moves a knight could ever
    make to close a given distance, ignoring board boundaries.
    """

    # *** Your Code Here ***
    return chessai.search.common.null_heuristic(node, problem)
