"""
The main executable for running a Chess tournament.
"""

import argparse
import concurrent.futures
import math
import os
import random
import re
import subprocess
import sys
import typing

import edq.core.argparser
import edq.util.dirent
import edq.util.json

import chessai.core.game
import chessai.core.tournament

DELIM: str = "\t"

THIS_DIR: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
ROOT_DIR: str = os.path.join(THIS_DIR, '..', '..')

FAILURE_STATUS: str = 'failed'
SUCCESS_STATUS: str = 'success'

MS_PER_SECOND: int = 1000

SUMMARY_HEADERS: list[str] = [
    'id', 'player_one', 'player_two', 'seed', 'status', 'error', 'games_run',
    'player_one_wins', 'ties', 'player_one_losses', 'player_one_score',
    'average_moves', 'average_duration_secs', 'log_path', 'replay_path',
]

def _safe_name(value: str) -> str:
    """ Convert a supplied identifier into one safe path component. """

    safe_value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value.strip()).strip('.-')
    if len(safe_value) > 0:
        return safe_value

    # Default to a standard name.
    return 'match'

def _match_args(game: chessai.core.tournament.Game, args: argparse.Namespace,
        result_path: str, replay_path: str | None) -> list[str]:
    """ Build the compatible match CLI arguments for one scheduled match. """

    match_args = [
        sys.executable, '-m', 'chessai.match',
        '--player-one', game.player_one,
        '--player-two', game.player_two,
        '--num-games', str(args.num_games),
        '--seed', str(game.seed),
        '--max-moves', str(args.max_moves),
        '--agent-start-timeout', str(args.agent_start_timeout),
        '--agent-end-timeout', str(args.agent_end_timeout),
        '--agent-action-timeout', str(args.agent_action_timeout),
        '--isolation', args.isolation_level,
        '--ui', 'null',
        '--result-path', result_path,
    ]

    if (args.board is not None):
        match_args += ['--board', args.board]

    if (args.rotate_sides):
        match_args.append('--rotate-sides')

    for raw_agent_arg in args.raw_agent_args:
        match_args += ['--agent-arg', raw_agent_arg]

    if (replay_path is not None):
        match_args += ['--save-path', replay_path]

    return match_args

def _run_tournament_match(
        index: int,
        game: chessai.core.tournament.Game,
        args: argparse.Namespace,
        ) -> chessai.core.tournament.Game:
    """ Run one scheduled match and attach its result or failure information. """

    log_path: str | None = None
    replay_path: str | None = None
    if (args.output_dir is None):
        result_path = edq.util.dirent.get_temp_path('chessai-tournament-', '.json')
    else:
        name = f'{index + 1:04d}'
        if (game.id is not None):
            name = f'{name}-{_safe_name(game.id)}'

        match_dir = os.path.join(args.output_dir, name)
        os.makedirs(match_dir, exist_ok = True)
        result_path = os.path.join(match_dir, 'results.json')
        log_path = os.path.join(match_dir, 'match.log')
        replay_path = os.path.join(match_dir, 'game.pgn')
        game.log_path = os.path.relpath(log_path, args.output_dir)
        game.replay_path = os.path.relpath(replay_path, args.output_dir)

    try:
        if (log_path is None):
            subprocess.run(_match_args(game, args, result_path, replay_path), check = True,
                cwd = args._root_dir, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
        else:
            with open(log_path, 'w', encoding = 'utf-8') as log_file:
                subprocess.run(_match_args(game, args, result_path, replay_path), check = True,
                    cwd = args._root_dir, stdout = log_file, stderr = subprocess.STDOUT)

        raw_results = edq.util.json.load_path(result_path, strict = True)
        game.results = raw_results
        game.status = SUCCESS_STATUS
        game.error = None
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
        game.status = FAILURE_STATUS
        game.error = str(error)
    finally:
        if (args.output_dir is None) and os.path.exists(result_path):
            os.unlink(result_path)

    return game

def _run_tournament(games: list[chessai.core.tournament.Game], args: argparse.Namespace) -> None:
    """ Run scheduled matches concurrently while preserving source order. """

    with concurrent.futures.ThreadPoolExecutor(max_workers = args.workers) as executor:
        futures = [executor.submit(_run_tournament_match, index, game, args)
                   for (index, game) in enumerate(games)]
        for (index, future) in enumerate(futures):
            games[index] = future.result()

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    raw_games = edq.util.json.load_path(args.path, strict = True)
    if (not isinstance(raw_games, list)):
        raise ValueError('Tournament data must be a JSON array of match objects.')

    games = [chessai.core.tournament.Game.from_dict(raw_game) for raw_game in raw_games]
    ids = [game.id for game in games if (game.id is not None)]
    if (len(ids) != len(set(ids))):
        raise ValueError('Tournament match IDs must be unique.')

    # Set the tournament seed.
    tournament_seed = random.randint(0, 2**64)
    if (args.seed is not None):
        tournament_seed = args.seed

    # Generate seeds for each match.
    rng = random.Random(tournament_seed)
    for game in games:
        game.seed = rng.randint(0, 2**64)

    # Run the tournament.
    _run_tournament(games, args)

    summaries = [_summary(game, args.rotate_sides) for game in games]
    if (args.json):
        output = []
        for (game, summary) in zip(games, summaries):
            record = game.to_dict()
            record['summary'] = summary
            output.append(record)

        print(edq.util.json.dumps(output, indent = 4))
    else:
        print(DELIM.join(SUMMARY_HEADERS))
        for summary in summaries:
            print(DELIM.join(_table_value(summary[header]) for header in SUMMARY_HEADERS))

    if any((game.status == FAILURE_STATUS) for game in games):
        return 1

    return 0

def _summary(game: chessai.core.tournament.Game, rotate_sides: bool) -> dict[str, typing.Any]:
    """ Build one flat, player-one-oriented summary record. """

    scores: list[float] = []
    for (index, result) in enumerate(game.results):
        score = float(result['score'])
        if rotate_sides and ((index % 2) == 1):
            score = 1 - score

        scores.append(score)

    wins = sum(math.isclose(score, 1.0) for score in scores)
    ties = sum(math.isclose(score, 0.5) for score in scores)

    average_player_one_score = None
    if (len(scores) > 0):
        average_player_one_score = sum(scores) / len(scores)

    move_counts = [len(result['history']) for result in game.results]
    average_move_counts = None
    if (len(move_counts) > 0):
        average_move_counts = sum(move_counts) / len(move_counts)

    durations = []
    for result in game.results:
        if (result['end_time'] is None):
            continue

        duration_secs = (int(result['end_time']) - int(result['start_time'])) / MS_PER_SECOND
        durations.append(duration_secs)

    average_duration_secs = None
    if (len(durations) > 0):
        average_duration_secs = sum(durations) / len(durations)

    return {
        'player_one': game.player_one,
        'player_two': game.player_two,
        'id': game.id,
        'seed': game.seed,
        'status': game.status,
        'error': game.error,
        'games_run': len(game.results),
        'player_one_wins': wins,
        'ties': ties,
        'player_one_losses': len(scores) - wins - ties,
        'player_one_score': average_player_one_score,
        'average_moves': average_move_counts,
        'average_duration_secs': average_duration_secs,
        'log_path': game.log_path,
        'replay_path': game.replay_path,
    }

def _table_value(value: typing.Any) -> str:
    """
    Get a proper value to represent in a TSV table.
    """

    if (value is None):
        return ''

    return str(value).replace("\t", ' ')

def main(argv: list[str] | None = None) -> int:
    """
    Invoke a tournament.

    Will return if running the tournament was successful.
    """

    args = _get_parser().parse_args(argv)
    if (args.workers <= 0):
        raise ValueError(f'--workers must be positive, {args.workers} was specified.')

    if ((args.save_path is not None) or (args.replay_path is not None) or args.wait_for_user):
        raise ValueError('Tournament mode manages replays itself; do not use --save-path, --replay-path, or --wait-for-input.')

    args._root_dir = ROOT_DIR
    return run_cli(args)

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = typing.cast(argparse.ArgumentParser, edq.core.argparser.get_default_parser(__doc__.strip()))

    # Get the standard game options.
    parser = chessai.core.game.set_cli_args(parser, None)

    parser.add_argument('path', metavar = 'DATA_PATH',
        action = 'store', type = str,
        help = 'JSON file that holds the game information.')

    parser.add_argument('--json', dest = 'json',
        action = 'store_true', default = False,
        help = 'Output data as JSON instead of TSV.')

    parser.add_argument('--rotate-sides', dest = 'rotate_sides', action = 'store_true',
        help = 'Rotate player sides between games in every match.')

    parser.add_argument('--workers', type = int, default = os.cpu_count() or 1,
        help = 'Maximum number of matches to run concurrently (default: %(default)s).')

    parser.add_argument('--output-dir', type = str, default = None,
        help = 'Directory in which to save per-match logs and PGN replays.')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
