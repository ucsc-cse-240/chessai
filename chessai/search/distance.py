"""
This files contains functions and tools to computing and keeping track of distances between two positions on a board.
"""

import logging
import random
import typing

import chessai.core.board
import chessai.core.gamestate
import chessai.core.search
import chessai.core.coordinate
import chessai.core.types
import chessai.search.common
import chessai.search.position
import chessai.search.random
import chessai.util.alias
import chessai.util.reflection

@typing.runtime_checkable
class DistanceFunction(typing.Protocol):
    """
    A function that computes the distance between two points.
    The game state is optional and will not apply to all distance functions.
    """

    def __call__(self,
            a: chessai.core.coordinate.Coordinate,
            b: chessai.core.coordinate.Coordinate,
            state: chessai.core.gamestate.GameState | None = None,
            **kwargs: typing.Any) -> float:
        ...

def manhattan_distance(
        a: chessai.core.coordinate.Coordinate,
        b: chessai.core.coordinate.Coordinate,
        state: chessai.core.gamestate.GameState | None = None,
        **kwargs: typing.Any) -> float:
    """
    Compute the Manhattan distance between two positions.
    See: https://en.wikipedia.org/wiki/Taxicab_geometry .
    """

    return abs(a.rank - b.rank) + abs(a.file - b.file)

def euclidean_distance(
        a: chessai.core.coordinate.Coordinate,
        b: chessai.core.coordinate.Coordinate,
        state: chessai.core.gamestate.GameState | None = None,
        **kwargs: typing.Any) -> float:
    """
    Compute the Euclidean distance between two positions.
    See: https://en.wikipedia.org/wiki/Euclidean_distance .
    """

    return float(((a.rank - b.rank) ** 2 + (a.file - b.file) ** 2) ** 0.5)

def knight_distance(
        a: chessai.core.coordinate.Coordinate,
        b: chessai.core.coordinate.Coordinate,
        state: chessai.core.gamestate.GameState | None = None,
        solver: chessai.core.search.SearchProblemSolver | str = chessai.util.alias.SEARCH_SOLVER_BFS.long,
        **kwargs: typing.Any) -> float:
    """
    Compute the "knight distance" between any two positions.
    This distance is the solution to a chessai.search.position.PositionSearchProblem between a and b.
    By default, BFS will be used to solve the search problem.
    If BFS is not implemented, then random search will be used.
    Note that random search can take a REALLY long time,
    so it is strongly recommended that you have BFS implemented before using this.
    """

    if (state is None):
        raise ValueError("Cannot compute maze distance without a game state.")

    # Fetch our solver.
    if (isinstance(solver, str)):
        solver = chessai.util.reflection.fetch(solver)

    solver = typing.cast(chessai.core.search.SearchProblemSolver, solver)
    problem = chessai.search.position.PositionSearchProblem(state, goal_position = b, start_position = a)
    rng = random.Random(state.seed)

    try:
        solution = solver(problem, chessai.search.common.null_heuristic, rng)
        return len(solution.actions)
    except NotImplementedError:
        # If this solver is not implemented, fall back to random search.
        solution = chessai.search.random.random_search(problem, chessai.search.common.null_heuristic, rng)
        return len(solution.actions)

def distance_heuristic(
        node: chessai.core.search.SearchNode,
        problem: chessai.core.search.SearchProblem,
        distance_function: DistanceFunction = manhattan_distance,
        **kwargs: typing.Any) -> float:
    """
    A heuristic that looks for positional information in this search information,
    and returns the result of the given distance function if that information is found.
    Otherwise, the result of the null heuristic will be returned.

    In the search node, a "position" attribute of type chessai.core.coordinate.Coordinate will be checked,
    and in the search problem, a "goal_positions" attribute of type list[chessai.core.coordinate.Coordinate] will be checked.
    """

    if ((not hasattr(node, 'position')) or (not isinstance(getattr(node, 'position'), chessai.core.coordinate.Coordinate))):
        return chessai.search.common.null_heuristic(node, problem, **kwargs)

    if ((not hasattr(problem, 'goal_positions')) or (not isinstance(getattr(problem, 'goal_positions'), list))):
        return chessai.search.common.null_heuristic(node, problem, **kwargs)

    a = getattr(node, 'position')
    list_b = getattr(problem, 'goal_positions')

    if (len(list_b) == 0):
        return chessai.search.common.null_heuristic(node, problem, **kwargs)

    for b in list_b:
        if (not isinstance(b, chessai.core.coordinate.Coordinate)):
            return chessai.search.common.null_heuristic(node, problem, **kwargs)

    return min(distance_function(a, b) for b in list_b)

def manhattan_heuristic(
        node: chessai.core.search.SearchNode,
        problem: chessai.core.search.SearchProblem,
        **kwargs: typing.Any) -> float:
    """
    A distance_heuristic using Manhattan distance.
    """

    return distance_heuristic(node, problem, manhattan_distance, **kwargs)

def euclidean_heuristic(
        node: chessai.core.search.SearchNode,
        problem: chessai.core.search.SearchProblem,
        **kwargs: typing.Any) -> float:
    """
    A distance_heuristic using Euclidean distance.
    """

    return distance_heuristic(node, problem, euclidean_distance, **kwargs)

class DistancePreComputer:
    """
    An object that pre-computes and caches the maze_distance between EVERY pair of non-wall points in a board.
    The initial cost is high, but this can be continually reused for the same board.
    """

    def __init__(self) -> None:
        self._distances: dict[chessai.core.coordinate.Coordinate, dict[chessai.core.coordinate.Coordinate, int]] = {}
        """
        The distances for the computed layout.
        The lower (according to `<`) position is always indexed first.
        Internally, we use int distances since we are computing maze distances (respecting walls).
        """

    def get_distance(self,
            a: chessai.core.coordinate.Coordinate,
            b: chessai.core.coordinate.Coordinate,
            ) -> float | None:
        """
        Get the distance between two points in the computed board.
        If no distance exists, then None will be returned.
        No distance can mean several things:
         - one or more positions are outside the board,
         - one or more positions are a wall,
         - or there is no path between the two positions.

        compute() must be called before calling this method,
        """

        lower, upper = sorted((a, b))

        return self._distances.get(lower, {}).get(upper, None)

    def get_distance_default(self,
            a: chessai.core.coordinate.Coordinate,
            b: chessai.core.coordinate.Coordinate,
            default: float
            ) -> float:
        """ Get the distance, but return the default if there is no path. """

        distance = self.get_distance(a, b)
        if (distance is not None):
            return distance

        return default

    def compute(self, state: chessai.core.gamestate.GameState) -> None:
        """
        Compute ALL non-wall distances in this gamestate.
        This must be called before get_distance().
        """

        logging.debug("Computing distances on gamestate '%s'.", state.get_fen())

        if (len(self._distances) > 0):
            raise ValueError("Cannot compute distances more than once.")

        # First, load in all the neighbors.
        self._load_identities_and_adjacencies(state)

        # Now continually go through all current distances and see if one more node can be added to the path.
        # Stop when no distances get added.
        target_length = 0
        added_distance = True
        while (added_distance):  # pylint: disable=too-many-nested-blocks
            target_length += 1
            added_distance = False

            # Note that we make copies of the collections we are iterating over because they may be changed during iteration.
            for a in list(self._distances.keys()):
                for (b, distance) in list(self._distances[a].items()):
                    # Only look at the current greatest length paths.
                    if (distance != target_length):
                        continue

                    # Take turns trying to add to each end of the path.
                    for (start, end) in ((a, b), (b, a)):
                        for (_, neighbor) in state.get_neighbors(end):
                            old_distance = self.get_distance(start, neighbor)

                            # Skip shorter distances.
                            if ((old_distance is not None) and (old_distance <= target_length)):
                                continue

                            self._put_distance(start, neighbor, target_length + 1)
                            added_distance = True

        logging.debug("Finished computing distances on gamestate '%s'.", state.get_fen())

    def _load_identities_and_adjacencies(self, state: chessai.core.gamestate.GameState) -> None:
        """ Load identity (0) and adjacency (1) distances. """

        for rank in range(state.board.num_ranks):
            for file in range(state.board.num_files):
                position = chessai.core.coordinate.Coordinate(file, rank)

                # if (board.is_wall(position)):
                    # continue

                self._put_distance(position, position, 0)

                for (_, neighbor) in state.get_neighbors(position):
                    self._put_distance(position, neighbor, 1)

    def _put_distance(self, a: chessai.core.coordinate.Coordinate, b: chessai.core.coordinate.Coordinate, distance: int) -> None:
        lower, upper = sorted((a, b))

        if (lower not in self._distances):
            self._distances[lower] = {}

        self._distances[lower][upper] = distance
