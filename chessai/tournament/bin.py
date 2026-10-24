"""
Run a round-robin tournament between staff and student agents.
The results of each match will be output as TSV.
"""

import argparse
import contextlib
import dataclasses
import enum
import logging
import math
import multiprocessing.pool
import os
import random
import re
import subprocess
import sys
import typing

import edq.core.argparser
import edq.util.dirent
import edq.util.json

import chessai.core.isolation.level
import chessai.chess.bin

THIS_DIR: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
ROOT_DIR: str = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))
SPECIAL_TEAMS_DIR: str = os.path.join(ROOT_DIR, 'special_teams')
SUBMISSIONS_DIR: str = os.path.join(ROOT_DIR, '_submissions')

AGENT_FILENAME: str = 'tournament.py'
AGENT_CLASS_NAME: str = 'TournamentAgent'

DEFAULT_AGENT_ACTION_TIMEOUT: int = 3
DEFAULT_AGENT_START_TIMEOUT: int = 15
DEFAULT_AGENT_END_TIMEOUT: int = 6
DEFAULT_MAX_MOVES: int = 100

DELIM: str = "\t"
MS_PER_SECOND: int = 1000

SUMMARY_HEADERS: list[str] = [
    'white', 'black', 'seed', 'status', 'error', 'games_run',
    'white_wins', 'ties', 'white_losses', 'white_score',
    'average_moves', 'average_duration_secs', 'log_path', 'replay_path',
]

@dataclasses.dataclass
class Team:
    """ A tournament participant discovered in an agent directory. """

    name: str
    """ The name of the team. """

    agent_path: str
    """ The absolute path to the agent for this team. """

class MatchStatus(str, enum.Enum):
    """ An enum representing the status of a match. """

    FAILURE = 'failed'
    RUNNING = 'running'
    SCHEDULED = 'scheduled'
    SUCCESS = 'success'

@dataclasses.dataclass
class Match:
    """ One scheduled match between two discovered teams. """

    white: Team
    """ The team that will play as white. """

    black: Team
    """ The team that will play as black. """

    seed: int | None = None
    """ The seed for the match. """

    results: list[dict[str, typing.Any]] = dataclasses.field(default_factory = list)
    """ The results of playing each match. """

    status: MatchStatus = MatchStatus.SCHEDULED
    """ The current status of the match. """

    error: str | None = None
    """ The matches error, which is only set if the status is a failure. """

    log_path: str | None = None
    """ The path to store the logs for the game. """

    replay_path: str | None = None
    """ The path to save the match replay. """

def _safe_name(value: str) -> str:
    """ Convert a supplied identifier into one safe path component. """

    safe_value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value.strip()).strip('.-')
    if (len(safe_value) > 0):
        return safe_value

    return 'team'

def _agent_reference(team: Team) -> str:
    """ Build the file-based reflection reference for a tournament agent. """

    return f'{team.agent_path}:{AGENT_CLASS_NAME}'

def _collect_teams(directory: str, excluded_names: set[str]) -> list[Team]:
    """ Find valid teams in one directory, in deterministic name order. """

    if (not os.path.isdir(directory)):
        raise ValueError(f"Tournament team directory does not exist: '{directory}'.")

    teams: list[Team] = []
    for entry in sorted(os.listdir(directory)):
        if (entry in excluded_names):
            continue

        team_dir = os.path.join(directory, entry)
        if (not os.path.isdir(team_dir)):
            continue

        agent_path = os.path.join(team_dir, AGENT_FILENAME)
        if (not os.path.isfile(agent_path)):
            continue

        teams.append(Team(entry, os.path.abspath(agent_path)))

    return teams

def _get_teams(args: argparse.Namespace) -> list[Team]:
    """ Discover staff and student teams and reject ambiguous team names. """

    teams = _collect_teams(args.staff_dir, set(args.ignore_team))
    teams += _collect_teams(args.submissions_dir, set(args.ignore_team))

    names = [team.name for team in teams]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if (len(duplicate_names) > 0):
        raise ValueError(f"Tournament team names must be unique: {', '.join(duplicate_names)}")

    if (len(teams) < 2):
        raise ValueError(f"At least two teams are required to run a tournament, got {len(teams)}")

    return teams

def _schedule_matches(teams: list[Team]) -> list[Match]:
    """ Schedule matches for every unique pair of teams. """

    matches: list[Match] = []
    for (index, white) in enumerate(teams):
        for black in teams[index + 1:]:
            matches.append(Match(white, black))
            matches.append(Match(black, white))

    return matches

def _match_args(match: Match, args: argparse.Namespace, replay_path: str | None, results_path: str) -> list[str]:
    """ Build the match CLI arguments for one scheduled match. """

    match_args = [
        sys.executable,  # same interpreter/venv as the parent, instead of bare 'python3'
        '-m', 'chessai.tournament.bin',
        '--white', _agent_reference(match.white),
        '--black', _agent_reference(match.black),
        '--num-games', str(args.num_games),
        '--max-moves', str(args.max_moves),
        '--agent-start-timeout', str(args.agent_start_timeout),
        '--agent-end-timeout', str(args.agent_end_timeout),
        '--agent-action-timeout', str(args.agent_action_timeout),
        '--isolation', args.isolation_level,
        '--ui', 'null',
        '--results-path', results_path,
    ]

    if (args.board is not None):
        match_args += ['--board', args.board]

    if (replay_path is not None):
        match_args += ['--save-path', replay_path]

    if (match.seed is not None):
        match_args += ['--seed', str(match.seed)]

    return match_args

def _run_tournament_match(index: int, match: Match, args: argparse.Namespace) -> Match:
    """ Run one scheduled match and attach its result or failure information. """

    with contextlib.ExitStack() as stack:
        replay_path: str | None = None
        log_path = os.devnull

        if (args.output_dir is None):
            work_dir = stack.enter_context(edq.util.dirent.get_temp_dir('chessai-'))
        else:
            name = f'{index + 1:04d}-{_safe_name(match.white.name)}-vs-{_safe_name(match.black.name)}'
            work_dir = os.path.join(args.output_dir, name)
            os.makedirs(work_dir, exist_ok = True)

            log_path = os.path.join(work_dir, 'match.log')
            replay_path = os.path.join(work_dir, 'game.pgn')
            match.log_path = os.path.relpath(log_path, args.output_dir)
            match.replay_path = os.path.relpath(replay_path, args.output_dir)

        results_path = os.path.join(work_dir, 'results.json')
        command = _match_args(match, args, replay_path, results_path)

        try:
            match.status = MatchStatus.RUNNING
            with open(log_path, 'w', encoding = 'utf-8') as log_file:
                subprocess.run(command,
                    stdin = subprocess.DEVNULL,
                    stdout = log_file,
                    stderr = subprocess.STDOUT,  # interleave both streams in order
                    shell = False,
                    check = True,
                    cwd = ROOT_DIR,
                )

            with open(results_path, 'r', encoding = 'utf-8') as file:
                match.results = edq.util.json.loads(file.read(), strict = True)

            match.status = MatchStatus.SUCCESS
            match.error = None
        except subprocess.CalledProcessError as error:
            match.status = MatchStatus.FAILURE
            match.error = f"Match exited with code {error.returncode} (see log)."
        except Exception as error:  # pylint: disable = broad-exception-caught
            match.status = MatchStatus.FAILURE
            match.error = str(error)

    return match

def _run_tournament(matches: list[Match], args: argparse.Namespace) -> None:
    """ Run scheduled matches concurrently while preserving source order. """

    with multiprocessing.pool.ThreadPool() as pool:
        work_results = []
        for (index, match) in enumerate(matches):
            work_results.append(pool.apply_async(_run_tournament_match, (index, match, args)))

        for work_result in work_results:
            work_result.wait()
            try:
                work_result.get()
            except Exception as error:  # pylint: disable = broad-exception-caught
                logging.warning("Failed to run match '%s'.", error)

def _summary(match: Match) -> dict[str, typing.Any]:
    """ Build one flat summary record. """

    scores: list[float] = []
    for result in match.results:
        scores.append(float(result['score']))

    average_score = None
    if (len(scores) > 0):
        average_score = (sum(scores) / len(scores))

    wins = sum(math.isclose(score, 1.0) for score in scores)
    ties = sum(math.isclose(score, 0.5) for score in scores)

    move_counts = [len(result['history']) for result in match.results]
    average_moves = None
    if (len(move_counts) > 0):
        average_moves = (sum(move_counts) / len(move_counts))

    durations = []
    for result in match.results:
        if (result['end_time'] is None):
            continue

        duration = (int(result['end_time']) - int(result['start_time'])) / MS_PER_SECOND
        durations.append(duration)

    average_duration = None
    if (len(durations) > 0):
        average_duration = (sum(durations) / len(durations))

    return {
        'white': match.white.name,
        'black': match.black.name,
        'seed': match.seed,
        'status': match.status,
        'error': match.error,
        'games_run': len(match.results),
        'white_wins': wins,
        'ties': ties,
        'white_losses': len(scores) - wins - ties,
        'white_score': average_score,
        'average_moves': average_moves,
        'average_duration_secs': average_duration,
        'log_path': match.log_path,
        'replay_path': match.replay_path,
    }

def _table_value(value: typing.Any) -> str:
    """ Get a proper value to represent in a TSV table. """

    if (value is None):
        return ''

    return str(value).replace("\t", ' ')

def run_cli(args: argparse.Namespace) -> int:
    """ Discover teams, run their matches, and print tournament summaries. """

    matches = _schedule_matches(_get_teams(args))

    tournament_seed = random.randint(0, 2**64)
    if (args.seed is not None):
        tournament_seed = args.seed

    rng = random.Random(tournament_seed)
    for match in matches:
        match.seed = rng.randint(0, 2**64)

    if (args.output_dir is not None):
        os.makedirs(args.output_dir, exist_ok = True)

    _run_tournament(matches, args)
    summaries = [_summary(match) for match in matches]
    if (args.json):
        print(edq.util.json.dumps(summaries, indent = 4))
    else:
        print(DELIM.join(SUMMARY_HEADERS))
        for summary in summaries:
            print(DELIM.join(_table_value(summary[header]) for header in SUMMARY_HEADERS))

    if any((match.status == MatchStatus.FAILURE) for match in matches):
        return 1

    return 0

def main(argv: list[str] | None = None) -> int:
    """ Invoke a tournament. """

    args = _get_parser().parse_args(argv)
    if (args.workers <= 0):
        raise ValueError(f'--workers must be positive, {args.workers} was specified.')

    return run_cli(args)

def _get_parser() -> argparse.ArgumentParser:
    """ Get the tournament parser. """

    parser = edq.core.argparser.get_default_parser(__doc__.strip())

    parser.add_argument('--board', type = str, default = None,
        help = 'Play every game on this board or FEN (default: %(default)s).')

    parser.add_argument('--num-games', type = int, default = 1,
        help = 'Number of games to play in every match (default: %(default)s).')

    parser.add_argument('--seed', type = int, default = None,
        help = 'Source seed for deterministic tournament match seeds.')

    parser.add_argument('--max-moves', type = int, default = DEFAULT_MAX_MOVES,
        help = 'Maximum total moves allowed in each game (-1 for unlimited).')

    parser.add_argument('--agent-start-timeout', type = float, default = DEFAULT_AGENT_START_TIMEOUT,
        help = 'Maximum seconds each agent may use to start a game (default: %(default)s).')

    parser.add_argument('--agent-end-timeout', type = float, default = DEFAULT_AGENT_END_TIMEOUT,
        help = 'Maximum seconds each agent may use to finish a game (default: %(default)s).')

    parser.add_argument('--agent-action-timeout', type = float, default = DEFAULT_AGENT_ACTION_TIMEOUT,
        help = 'Maximum seconds each agent may use per action (default: %(default)s).')

    parser.add_argument('--isolation', dest = 'isolation_level', choices = chessai.core.isolation.level.LEVELS,
        default = chessai.core.isolation.level.Level.PROCESS.value,
        help = 'Agent isolation level (default: %(default)s).')

    parser.add_argument('--staff-dir', '--special-teams-dir', dest = 'staff_dir', type = str,
        default = SPECIAL_TEAMS_DIR,
        help = 'Directory containing staff team directories (default: %(default)s).')

    parser.add_argument('--submissions-dir', dest = 'submissions_dir', type = str,
        default = SUBMISSIONS_DIR,
        help = 'Directory containing student submission directories (default: %(default)s).')

    parser.add_argument('--ignore-team', action = 'append', default = [], metavar = 'NAME',
        help = 'Ignore a team directory by name (may be used multiple times).')

    parser.add_argument('--json', action = 'store_true', default = False,
        help = 'Output match summaries as JSON instead of TSV.')

    num_cores = os.cpu_count()
    if num_cores is None:
        num_cores = 1

    num_cores = max(num_cores - 1, 1)
    parser.add_argument('--workers', type = int, default = num_cores,
        help = 'Maximum number of matches to run concurrently (default: %(default)s).')

    parser.add_argument('--output-dir', type = str, default = None,
        help = 'Directory in which to save per-match logs, results, and PGN replays.')

    return parser

if (__name__ == '__main__'):
    sys.exit(main())
