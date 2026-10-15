"""
The main executable for running a Chess tournament.
"""

import argparse
import logging
import multiprocessing.pool
import os
import subprocess
import sys
import typing

import edq.core.argparser
import edq.util.dirent
import edq.util.json

import chessai.core.tournament
import chessai.util

_logger = logging.getLogger(__name__)

THIS_DIR: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
ROOT_DIR: str = os.path.join(THIS_DIR, '..', '..')

DELIM: str = "\t"

# TODO: Fix the headers to be useful.
INITIAL_HEADERS: typing.List[str] = ['id', 'name', 'owner', 'price', 'url']

def _table_value(value: typing.Any) -> str:
    """
    Get a proper value to represent in a TSV table.
    """

    if (value is None):
        return ''

    return str(value).replace("\t", ' ')

def _run_tournament_match(
        # TODO: May need to define a new tournament game model.
        game: chessai.core.tournament.Game,
        rotate_sides: bool,
        num_games: int,
        seed: typing.Union[int, None],
        ) -> None:
    """ Run a single tournament match between two players. """

    _logger.info("Computing stats for game `%s`.", game.long_name())

    temp_path = edq.util.dirent.get_temp_path('chessai-', '.json')
    edq.util.json.dump_path(game, temp_path)

    # How should we pass the standard game options collected from set_cli_args?
    args = [
        'python3',
        '-m', 'chessai.match.bin',
        '--player-one', game.TODO,
        '--player-two', game.TODO,
    ]

    if (rotate_sides):
        args += ['--rotate-sides']

    if (seed is not None):
        args += ['--seed', str(seed)]

    result = subprocess.run(args, capture_output = True, shell = False, cwd = ROOT_DIR, check = True, text = True)

    new_game = chessai.core.tournament.Game.from_dict(edq.util.json.loads(result.stdout, strict = True))
    game.stats = new_game.stats

    _logger.info("Done computing stats for game `%s`.", game.long_name())

def _run_tournament(games: typing.List[chessai.core.tournament], args: argparse.Namespace):
    """ Run a match in the tournament. """

    with multiprocessing.pool.ThreadPool() as pool:
        work_results = []
        for game in games:
            work_results.append(pool.apply_async(_run_tournament_match, (game, args.simulation, args.num_simulation_runs, args.seed)))

        for work_result in work_results:
            work_result.wait()
            work_result.get()

def run_cli(args: argparse.Namespace) -> int:
    """ Run the CLI. """

    games = []
    for raw_game in edq.util.json.load_path(args.path, strict = True):
        games.append(chessai.core.tournament.Game.from_dict(raw_game))

    # Run tournament
    _run_tournament(games, args)

    if (args.json):
        print(edq.util.json.dumps(games, indent = 4))
        return 0

    # Convert the info to a dict, so it can be flattented for the output table.
    flat_games = [chessai.util.flatten_dict(game.to_dict()) for game in games]

    # Collect all the possible fields/headers
    all_headers = set()
    for flat_game in flat_games:
        all_headers |= set(flat_game.keys())

    # Remove headers that will be at the front.
    all_headers -= set(INITIAL_HEADERS)

    # Sort keys by the nested level (from flatening) and then lexicographically.
    headers = INITIAL_HEADERS + sorted(all_headers, key = lambda header: (header.count(chessai.util.DEFAULT_KEY_DELIM), header))

    rows = []
    for flat_game in flat_games:
        rows.append([_table_value(flat_game.get(header, None)) for header in headers])

    print(DELIM.join(headers))
    for row in rows:
        print(DELIM.join(row))

    return 0

def main() -> int:
    """
    Invoke a tournament.

    Will return if running the tournament was successful.
    """

    return run_cli(_get_parser().parse_args())

def _get_parser() -> argparse.ArgumentParser:
    """ Get the parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    # Get the standard game options.
    parser = chessai.core.game.set_cli_args(parser, None)

    parser.add_argument('path', metavar = 'DATA_PATH',
        action = 'store', type = str,
        help = 'JSON file that holds the game information.')

    parser.add_argument('--json', dest = 'json',
        action = 'store_true', default = False,
        help = 'Output data as JSON instead of TSV.')

    parser.add_argument('--rotate-sides', dest = 'rotate_sides',
        action = 'store_false', default = True,
        help = 'Rotate sides between each game in the match (default: %(default)s).')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
