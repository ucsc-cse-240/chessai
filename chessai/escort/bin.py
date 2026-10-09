import argparse
import logging
import math
import typing

import chessai.core.agentinfo
import chessai.core.game
import chessai.core.types
import chessai.escort.game
import chessai.escort.gamestate
import chessai.util.alias
import chessai.util.bin

DEFAULT_BOARD: str = 'alcove-demo'

def set_cli_args(parser: argparse.ArgumentParser, **kwargs: typing.Any) -> argparse.ArgumentParser:
    """Set Escort-specific command-line arguments."""

    parser.add_argument('--agent', dest = 'agent', action = 'store', type = str,
            default = chessai.util.alias.AGENT_SEARCH_PROBLEM.short,
            help = ('Select the Escort agent (default: %(default)s).'
                    + f' Builtin agents: {chessai.util.alias.AGENT_SHORT_NAMES}.'))

    parser.add_argument('--solver', dest = 'solver', action = 'store', type = str,
            default = chessai.util.alias.SEARCH_SOLVER_ASTAR.short,
            help = ('Select the search solver (default: %(default)s).'
                    + f' Builtin solvers: {chessai.util.alias.SEARCH_SOLVER_SHORT_NAMES}.'))

    parser.add_argument('--heuristic', dest = 'heuristic', action = 'store', type = str,
            default = chessai.util.alias.HEURISTIC_NULL.short,
            help = ('Select the search heuristic (default: %(default)s).'
                    + f' Builtin heuristics: {chessai.util.alias.HEURISTIC_SHORT_NAMES}.'))

    return parser

def init_from_args(args: argparse.Namespace) -> tuple[dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
        list[chessai.core.types.Color], dict[str, typing.Any]]:
    """Configure one cooperative white agent and remove the black agent."""

    agent_info = chessai.core.agentinfo.AgentInfo(
        name = args.agent,
        problem = chessai.util.alias.SEARCH_PROBLEM_ESCORT.short,
        solver = args.solver,
        heuristic = args.heuristic,
    )
    return {chessai.core.types.Color.WHITE: agent_info}, [chessai.core.types.Color.BLACK], {}

def log_escort_results(results: list[chessai.core.game.GameResult],
                       winning_agent_teams: set[chessai.core.types.Color],
                       prefix: str = '') -> None:
    """Log standard Escort game results."""

    scores = [result.score for result in results]
    record = ['Win' if math.isclose(score, 1.0) else 'Loss' for score in scores]
    logging.info('%sAverage Score: %0.2f', prefix, sum(scores) / len(scores))
    logging.info('%sRecord:        %s', prefix, ', '.join(record))
    logging.info('%sAverage Moves: %s', prefix, sum(len(result.history) for result in results) / len(results))

def main(argv: list[str] | None = None,
         ) -> list[chessai.core.game.GameResult]:
    """Invoke a game of Escort."""

    return chessai.util.bin.run_main(
        description = 'Play a cooperative Escort game.',
        default_board = DEFAULT_BOARD,
        game_class = chessai.escort.game.Game,
        state_class = chessai.escort.gamestate.GameState,
        custom_set_cli_args = set_cli_args,
        custom_init_from_args = init_from_args,
        log_results = log_escort_results,
        argv = argv,
    )

if (__name__ == '__main__'):
    main()
