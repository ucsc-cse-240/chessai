"""
The main executable for running a Chess match, or a series of Chess games.
"""

import argparse
import logging
import math
import typing

import edq.util.json

import chessai.chess.game
import chessai.core.agentinfo
import chessai.core.types
import chessai.util.alias
import chessai.util.bin

def set_cli_args(parser: argparse.ArgumentParser, **kwargs: typing.Any) -> argparse.ArgumentParser:
    """
    Set match-specific CLI arguments.
    This is a sibling to init_from_args(), as the arguments set here can be interpreted there.
    """

    parser.add_argument('--player-one', dest = 'player_one',
            action = 'store', type = str, default = chessai.util.alias.AGENT_RANDOM.short,
            help = ('Select the chess team that will start by playing on the white team (default: %(default)s).'
                    + f' Builtin teams: {chessai.util.alias.AGENT_SHORT_NAMES}.'))

    parser.add_argument('--player-two', dest = 'player_two',
            action = 'store', type = str, default = chessai.util.alias.AGENT_RANDOM.short,
            help = ('Select the chess team that will start by playing on the black team (default: %(default)s).'
                    + f' Builtin teams: {chessai.util.alias.AGENT_SHORT_NAMES}.'))

    parser.add_argument('--rotate-sides', dest = 'rotate_sides',
            action = 'store_true',
            help = ('Rotate the sides player one and player two play on between each game.'))

    parser.add_argument('--result-path', dest = 'result_path',
            action = 'store', type = str, default = None,
            help = 'If specified, write the structured game results as JSON to this path.')

    return parser

def init_from_args(args: argparse.Namespace) -> tuple[dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
        list[chessai.core.types.Color], dict[str, typing.Any]]:
    """
    Setup agents based on Chess rules.

    Agent infos are supplied via the `--player-one` and `--player-two` arguments.
    Missing agents will be filled in with random agents.
    """

    base_agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo] = {
        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo(name = args.player_one),
        chessai.core.types.Color.BLACK: chessai.core.agentinfo.AgentInfo(name = args.player_two),
    }

    return base_agent_infos, [], {}

def log_match_results(results: list[chessai.core.game.GameResult], winning_agent_teams: set[chessai.core.types.Color], prefix: str = '') -> None:
    """
    Log the result of running several match games.
    """

    move_counts: list[int] = [len(result.history) for result in results]
    scores: list[float] = [result.score for result in results]

    # Determine if we rotated sides during the match.
    if (len(results) > 1):
        game_one_white_name = str(results[0].game_info.agent_infos[chessai.core.types.Color.WHITE].name)
        game_two_white_name = str(results[1].game_info.agent_infos[chessai.core.types.Color.WHITE].name)

        # Player one is not the same for match one and two, so we must have rotated sides.
        if game_one_white_name != game_two_white_name:
            for i, score in enumerate(scores):
                if (i % 2 == 0):
                    continue

                # Flip the score so all scores are in the perspective of player one.
                scores[i] = abs(1 - score)

    record: list[str] = []
    for score in scores:
        if (math.isclose(score, 0.5)):
            record.append('Tie')
        elif (math.isclose(score, 1.0)):
            record.append('Win')
        else:
            record.append('Loss')

    average_score: float = (sum(scores)) / len(scores)
    logging.info('Average Score: %0.2f', average_score)

    # Avoid logging long lists (which can be a bit slow in Python's logging module).
    log_lists_to_info: bool = (len(results) < chessai.util.bin.SCORE_LIST_MAX_INFO_LENGTH)
    log_lists_to_debug: bool = (logging.getLogger().getEffectiveLevel() <= logging.DEBUG)

    joined_scores: str = ''
    joined_record: str = ''
    joined_move_counts: str = ''

    if (log_lists_to_info or log_lists_to_debug):
        joined_scores = ', '.join([str(score) for score in scores])
        joined_record = ', '.join(record)
        joined_move_counts = ', '.join([str(move_count) for move_count in move_counts])

    if (log_lists_to_info):
        logging.info('%sScores:        %s', prefix, joined_scores)
    elif (log_lists_to_debug):
        logging.debug('%sScores:        %s', prefix, joined_scores)

    if (log_lists_to_info):
        logging.info('%sRecord:        %s', prefix, joined_record)
    elif (log_lists_to_debug):
        logging.debug('%sRecord:        %s', prefix, joined_record)

    logging.info('%sAverage Moves: %s', prefix, sum(move_counts) / float(len(results)))

    if (log_lists_to_info):
        logging.info('%sMove Counts:   %s', prefix, joined_move_counts)
    elif (log_lists_to_debug):
        logging.debug('%sMove Counts:   %s', prefix, joined_move_counts)

def main(argv: list[str] | None = None) -> list[chessai.core.game.GameResult]:
    """
    Invoke a match of chess.

    Will return the results of the games.
    """

    parser = chessai.util.bin.get_parser(
        description = "Play a match of chess.",
        default_board = None,
        custom_set_cli_args = set_cli_args,
    )

    args = chessai.util.bin.parse_args(
        parser,
        chessai.chess.game.Game,
        chessai.chess.gamestate.GameState,
        custom_init_from_args = init_from_args,
        argv = argv,
    )

    results = chessai.util.bin.run_games(args, log_results = log_match_results)

    # Write results to a file so they can be collected.
    if (args.result_path is not None):
        edq.util.json.dump_path(results, args.result_path)

    return results

if (__name__ == '__main__'):
    main()
