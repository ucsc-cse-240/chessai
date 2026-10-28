#!/usr/bin/env python3

""" Run reproducible local scale tests for the chessai tournament runner. """

import argparse
import enum
import os
import shutil
import subprocess
import sys
import tempfile

DEFAULT_SEED: int = 240
DEFAULT_MAX_MOVES: int = 4
DEFAULT_LATENCY_SECS: float = 0.05

class Scenario(enum.Enum):
    """ A potential configuration for running a tournament. """

    SMOKE = (6, ('instant',))
    FAULT = (8, ('instant', 'crash', 'hang', 'noisy'))
    LATENCY = (16, ('latency',))
    NIGHTLY = (32, ('instant', 'latency'))
    FULL = (155, ('instant',))

    def __init__(self, team_count: int, behaviors: tuple[str, ...]) -> None:
        self.team_count: int = team_count
        self.behaviors: tuple[str, ...] = behaviors

    def get_teams(self, team_count: int | None = None) -> list[str]:
        """ Return one agent behavior for each generated team. """

        if (team_count is None):
            team_count = self.team_count

        teams: list[str] = []
        for index in range(team_count):
            teams.append(self.behaviors[index % len(self.behaviors)])

        return teams

def _agent_source(behavior: str, latency_secs: float) -> str:
    """Build one private synthetic tournament agent module."""

    return f'''import sys
import time

import chessai.core.action
import chessai.core.agent
import chessai.core.gamestate

BEHAVIOR = {behavior!r}
LATENCY_SECS = {latency_secs!r}

class TournamentAgent(chessai.core.agent.Agent):
    """ A generated agent used only by the tournament scale harness. """

    def get_action(self, state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        if BEHAVIOR == 'crash':
            raise RuntimeError('synthetic crash')

        if BEHAVIOR == 'hang':
            time.sleep(60)

        if BEHAVIOR == 'latency':
            time.sleep(LATENCY_SECS)

        if BEHAVIOR == 'noisy':
            print('synthetic diagnostic ' * 64, file=sys.stderr)

        return state.get_legal_actions()[0]
'''

def _make_fleet(root: str, teams: list[str], latency_secs: float) -> tuple[str, str]:
    """ Create deterministic team directories for a synthetic fleet. """

    staff_dir = os.path.join(root, 'staff')
    os.mkdir(staff_dir)
    for index, behavior in enumerate(teams):
        team_dir = os.path.join(staff_dir, f'team-{index:03d}')
        os.mkdir(team_dir)
        agent_path = os.path.join(team_dir, 'tournament.py')
        with open(agent_path, 'w', encoding = 'utf-8') as agent_file:
            agent_file.write(_agent_source(behavior, latency_secs))

    submissions_dir = os.path.join(root, 'submissions')
    os.mkdir(submissions_dir)

    return staff_dir, submissions_dir

def _run_tournament(args: argparse.Namespace, scenario: Scenario) -> int:
    """ Generate one fleet and run one tournament child process. """

    team_count = scenario.team_count
    if (args.teams is not None):
        team_count = args.teams

    root = tempfile.mkdtemp(prefix = f'chessai-scale-{scenario.name.lower()}-')
    temporary_dir = os.path.join(root, 'temporary')
    os.mkdir(temporary_dir)
    staff_dir, submissions_dir = _make_fleet(root, scenario.get_teams(team_count), args.latency_secs)
    command = [
        sys.executable, '-m', 'chessai.tournament.bin',
        '--staff-dir', staff_dir,
        '--submissions-dir', submissions_dir,
        '--workers', str(args.workers),
        '--num-games', str(args.num_games),
        '--max-moves', str(args.max_moves),
        '--seed', str(args.seed),
        '--agent-action-timeout', str(args.agent_action_timeout),
        '--agent-start-timeout', str(args.agent_start_timeout),
        '--agent-end-timeout', str(args.agent_end_timeout),
        '--isolation', args.isolation,
        '--ui', 'null',
    ]
    if (args.match_timeout is not None):
        command += ['--match-timeout', str(args.match_timeout)]

    environment = os.environ.copy()
    environment.update({'TMPDIR': temporary_dir, 'TEMP': temporary_dir, 'TMP': temporary_dir})
    try:
        return subprocess.run(command, check = False, env = environment).returncode
    finally:
        if (args.keep_output):
            print(f'Generated fleet kept at: {root}')
        else:
            shutil.rmtree(root)

def main(argv: list[str] | None = None) -> int:
    """ Run one selected tournament scenario. """

    parser = argparse.ArgumentParser(description = __doc__.strip())

    parser.add_argument('--scenario', choices = [scenario.name.lower() for scenario in Scenario], default = 'smoke',
        help = 'Synthetic fleet to run (default: %(default)s).')

    parser.add_argument('--teams', type = int, default = None,
        help = 'Override the number of generated teams for the selected scenario.')

    parser.add_argument('--workers', type = int, default = 2,
        help = 'Maximum number of matches to run concurrently (default: %(default)s).')

    parser.add_argument('--num-games', type = int, default = 1,
        help = 'Number of games to play in every match (default: %(default)s).')

    parser.add_argument('--max-moves', type = int, default = DEFAULT_MAX_MOVES,
        help = 'Maximum total moves allowed in each game (default: %(default)s).')

    parser.add_argument('--seed', type = int, default = DEFAULT_SEED,
        help = 'Source seed for deterministic tournament match seeds (default: %(default)s).')

    parser.add_argument('--latency-secs', type = float, default = DEFAULT_LATENCY_SECS,
        help = 'Delay used by each latency agent action (default: %(default)s).')

    parser.add_argument('--agent-action-timeout', type = float, default = 0.2,
        help = 'Maximum seconds each agent may use per action (default: %(default)s).')

    parser.add_argument('--agent-start-timeout', type = float, default = 1.0,
        help = 'Maximum seconds each agent may use to start a game (default: %(default)s).')

    parser.add_argument('--agent-end-timeout', type = float, default = 1.0,
        help = 'Maximum seconds each agent may use to finish a game (default: %(default)s).')

    parser.add_argument('--match-timeout', type = float, default = None, metavar = 'SECONDS',
        help = 'Overall timeout for one match subprocess (default: derive one from game limits).')

    parser.add_argument('--isolation', choices = ['none', 'process', 'tcp'], default = 'process',
        help = 'Agent isolation level (default: %(default)s).')

    parser.add_argument('--keep-output', action = 'store_true',
        help = 'Keep the generated agent fleet after the tournament finishes.')

    args = parser.parse_args(argv)
    if (args.teams is not None and args.teams < 2):
        parser.error('--teams must be at least 2.')

    if (args.workers <= 0):
        parser.error('--workers must be positive.')

    scenario = Scenario[args.scenario.upper()]

    return _run_tournament(args, scenario)

if (__name__ == '__main__'):
    sys.exit(main())
