#!/usr/bin/env python3

"""
Extract a specific number of puzzles of a specified theme from a Lichess puzzle database file.
Outputs an individual puzzle file for each match found.
"""

import argparse
import csv
import os
import sys
import typing

import edq.util.dirent
import edq.util.json

THIS_DIR: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

DEFAULT_COUNT: int = -1
DEFAULT_OUTPUT_DIR: str = os.path.join(THIS_DIR, '..', 'chessai', 'resources', 'puzzles')
DEFAULT_THEME: str = 'mateIn1'

def generate_puzzle_files(
        input_csv: str,
        output_folder: str = DEFAULT_OUTPUT_DIR,
        target_theme: str = DEFAULT_THEME,
        limit: int = DEFAULT_COUNT
        ) -> bool:
    """
    Filters a Lichess CSV for a specific theme and outputs a set number of files. 
    Returns True if at least one matching puzzle was found, False otherwise.
    """

    edq.util.dirent.mkdir(output_folder)

    count = 0
    limit_reached = False
    with open(input_csv, mode = 'r', encoding = 'utf-8') as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            if ((limit >= 0) and (count >= limit)):
                limit_reached = True
                break

            themes = str(row.get('Themes', '')).split()

            if (target_theme not in themes):
                continue

            raw_puzzle_id = row.get('PuzzleId', None)
            raw_fen = row.get('FEN', None)
            raw_moves = row.get('Moves', None)

            if ((raw_puzzle_id is None) or (raw_fen is None) or (raw_moves is None)):
                continue

            puzzle_id = str(raw_puzzle_id).strip()
            fen = str(raw_fen).strip()
            moves_list: typing.List[str] = str(raw_moves).strip().split()

            if ((puzzle_id == "") or (fen == "") or (len(moves_list) == 0)):
                continue

            puzzle_data = {
                "fen": f"{fen}",
                "move_lines": [moves_list]
            }

            puzzle_path = os.path.join(output_folder, f"{puzzle_id}.json")
            edq.util.json.dump_path(puzzle_data, puzzle_path, indent = 4)

            count += 1

    if (count == 0):
        return False

    if (limit_reached):
        print(f"Reached requested limit of {limit} puzzles for theme '{target_theme}'. Stopping search.")
    elif (limit >= 0):
        print(f"Ran out of puzzles, only found {count} puzzles out of the requested {limit} for theme '{target_theme}'.")
    else:
        print(f"Successfully processed entire file. Generated {count} total puzzles for theme '{target_theme}'.")

    return True

def main(args: argparse.Namespace) -> int:
    """ Handles script execution. """

    puzzles_found = generate_puzzle_files(args.input, args.output, args.theme, args.limit)

    if (not puzzles_found):
        print(f"Error: The theme '{args.theme}' was not found in the input file.", file = sys.stderr)
        return 1

    return 0

def _load_args() -> argparse.Namespace:
    """ Handles command line argument parsing. """

    parser = argparse.ArgumentParser(description = __doc__.strip())

    parser.add_argument('input', metavar = 'INPUT_CSV', type = str,
            help = 'Path to the Lichess puzzle database file.')

    parser.add_argument('--output', dest = 'output',
            action = 'store', type = str, default = DEFAULT_OUTPUT_DIR,
            help = 'Directory to save the puzzle files (default: %(default)s).')

    parser.add_argument('--theme', dest = 'theme',
            action = 'store', type = str, default = DEFAULT_THEME,
            help = ("Puzzle theme to filter by (default: %(default)s).\n"
            "Themes list: https://github.com/lichess-org/lila/blob/0d57c7f6/translation/source/puzzleTheme.xml"))

    parser.add_argument('--limit', dest = 'limit',
            action = 'store', type = int, default = DEFAULT_COUNT,
            help = 'The maximum number of puzzles to fetch, -1 for unlimited. (default: %(default)s).')

    return parser.parse_args()

if (__name__ == "__main__"):
    sys.exit(main(_load_args()))
