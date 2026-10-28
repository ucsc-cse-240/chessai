# TODO: When writing docstrings, add a space in between the text and the quotes.
"""Run reproducible local scale tests for the chessai tournament runner."""

import argparse
import json
import os
# TODO: Never use pathlib, use os.path for all path operations.
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import typing

DEFAULT_SEED: int = 240
DEFAULT_MAX_MOVES: int = 4
DEFAULT_LATENCY_SECS: float = 0.05
POLL_INTERVAL_SECS: float = 0.05

# TODO: Write the scenarios as an enum.
# Provide a method on the enum to get the teams.
# Either have a defined return type (not a dict[str, typing.Any]) or have it return the teams to play.
SCENARIOS: dict[str, dict[str, typing.Any]] = {
    'smoke': {'teams': 6, 'behaviors': ['instant'], 'repeat': True},
    'fault': {'teams': 8, 'behaviors': ['instant', 'crash', 'hang', 'noisy'], 'repeat': False},
    'sweep': {'team_counts': [4, 8, 16, 32], 'behaviors': ['instant'], 'repeat': False},
    'latency': {'teams': 16, 'behaviors': ['latency'], 'worker_counts': [1, 2, 4], 'repeat': False},
    'nightly': {'teams': 32, 'behaviors': ['instant', 'latency'], 'repeat': False},
    'full': {'teams': 155, 'behaviors': ['instant'], 'repeat': False},
}

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
    """A generated agent used only by the tournament scale harness."""

    def get_action(self, state: chessai.core.gamestate.GameState) -> chessai.core.action.Action:
        if BEHAVIOR == 'crash':
            raise RuntimeError('synthetic crash')
        # TODO: Add a newline after an if statement so it doesn't look like an if-else block.
        if BEHAVIOR == 'hang':
            time.sleep(60)
        if BEHAVIOR == 'latency':
            time.sleep(LATENCY_SECS)
        if BEHAVIOR == 'noisy':
            print('synthetic diagnostic ' * 64, file=sys.stderr)
        return state.get_legal_actions()[0]
'''

def _make_fleet(root: pathlib.Path, team_count: int, behaviors: list[str], latency_secs: float) -> None:
    """Create deterministic team directories for a synthetic fleet."""

    # TODO: Even though this won't run on windows, always use os.path.join for path creation.
    fleet_dir = root / 'staff'
    fleet_dir.mkdir()
    for index in range(team_count):
        team_dir = fleet_dir / f'team-{index:03d}'
        team_dir.mkdir()
        behavior = behaviors[index % len(behaviors)]
        (team_dir / 'tournament.py').write_text(_agent_source(behavior, latency_secs), encoding = 'utf-8')
    (root / 'submissions').mkdir()

# TODO: This is too complicated for a first version. Remove all instances of tracing and performance tracking.
# I just want the script to run a tournament according to the number of agents and behavior.
def _descendant_pids(pid: int) -> set[int]:
    """Return descendants visible through Linux procfs, or an empty set elsewhere."""

    descendants: set[int] = set()
    pending = [pid]
    while pending:
        parent = pending.pop()
        try:
            children = [int(value) for value in pathlib.Path(
                f'/proc/{parent}/task/{parent}/children').read_text(encoding = 'utf-8').split()]
        except OSError:
            continue
        for child in children:
            if child not in descendants:
                descendants.add(child)
                pending.append(child)
    return descendants

# TODO: This is too complicated for a first version. Remove all instances of tracing and performance tracking.
def _process_sample(pid: int) -> dict[str, int | None]:
    """Collect Linux process measurements without adding a dependency."""

    try:
        status = pathlib.Path(f'/proc/{pid}/status').read_text(encoding = 'utf-8')
    except OSError:
        return {'rss_kib': None, 'fd_count': None, 'child_count': None}
    rss_kib = None
    for line in status.splitlines():
        if line.startswith('VmRSS:'):
            rss_kib = int(line.split()[1])
            break
    try:
        fd_count = len(list(pathlib.Path(f'/proc/{pid}/fd').iterdir()))
    except OSError:
        fd_count = None
    return {'rss_kib': rss_kib, 'fd_count': fd_count, 'child_count': len(_descendant_pids(pid))}

def _load_raw_results(output_dir: pathlib.Path) -> list[dict[str, typing.Any]]:
    """Read raw game results written by completed tournament matches."""

    results: list[dict[str, typing.Any]] = []
    # TODO: We should limit the usage of globs if possible. Can we not track or determine the location of the results?
    for path in sorted(output_dir.glob('*/results.json')):
        results.extend(json.loads(path.read_text(encoding = 'utf-8')))
    return results

# TODO: unclear input types, why so many dict[str, typing.Any]?
# TODO: I would rather import a stdlib solution to track process leaks than craft it myself.
def _check_invariants(team_count: int, num_games: int, summaries: list[dict[str, typing.Any]],
        raw_results: list[dict[str, typing.Any]], return_code: int, parse_error: str | None,
        temporary_entries: list[pathlib.Path], leaked_processes: int, fault_test: bool) -> list[str]:
    """Return deterministic correctness violations for one harness run."""

    expected_matches = team_count * (team_count - 1)
    required_headers = {
        'white', 'black', 'seed', 'status', 'error', 'games_run', 'white_wins', 'ties',
        'white_losses', 'white_score', 'average_moves', 'average_duration_secs', 'log_path', 'replay_path',
    }
    violations = []
    if parse_error is not None:
        violations.append(f'Tournament JSON did not parse: {parse_error}')
    if len(summaries) != expected_matches:
        violations.append(f'Expected {expected_matches} summaries, found {len(summaries)}.')
    # TODO: We typically avoid the use of any when possible. I would rather iterate over each summary and check multiple failure conditions.
    if any(set(summary) != required_headers for summary in summaries):
        violations.append('One or more summaries did not contain exactly the documented fields.')
    if any(not isinstance(summary.get('average_duration_secs'), (float, int)) for summary in summaries):
        violations.append('One or more summary durations were not numeric.')
    if any(summary.get('status') != 'success' for summary in summaries):
        violations.append('One or more match subprocesses failed.')
    if return_code != 0:
        violations.append(f'Expected successful tournament exit code, found {return_code}.')
    expected_results = expected_matches * num_games
    if len(raw_results) != expected_results:
        violations.append(f'Expected {expected_results} raw game results, found {len(raw_results)}.')
    if temporary_entries:
        violations.append(f'Found {len(temporary_entries)} leftover tournament temp directories.')
    if leaked_processes:
        violations.append(f'Found {leaked_processes} child processes alive after tournament exit.')
    if fault_test:
        reasons = {result.get('termination_reason') for result in raw_results}
        if 'Agent Crashed' not in reasons:
            violations.append('Fault fleet did not produce an Agent Crashed result.')
        if 'Agent Timeout' not in reasons:
            violations.append('Fault fleet did not produce an Agent Timeout result.')
    return violations

# TODO: Bad name, we should only ever run one tournament in the script.
# We may have many teams or ask for many games per match, but never run multiple tournaments in one invocation.
def _run_once(args: argparse.Namespace, team_count: int, behaviors: list[str], workers: int,
        run_name: str) -> dict[str, typing.Any]:
    """Generate a fleet, run one tournament child process, and collect measurements."""

    run_root = pathlib.Path(tempfile.mkdtemp(prefix = f'chessai-scale-{run_name}-'))
    temp_root = run_root / 'temporary'
    temp_root.mkdir()
    output_dir = run_root / 'output'
    _make_fleet(run_root, team_count, behaviors, args.latency_secs)
    command = [sys.executable, '-m', 'chessai.tournament.bin', '--staff-dir', str(run_root / 'staff'),
        '--submissions-dir', str(run_root / 'submissions'), '--workers', str(workers),
        '--num-games', str(args.num_games), '--max-moves', str(args.max_moves), '--seed', str(args.seed),
        '--agent-action-timeout', str(args.agent_action_timeout),
        '--agent-start-timeout', str(args.agent_start_timeout), '--agent-end-timeout', str(args.agent_end_timeout),
        '--isolation', args.isolation, '--ui', 'null', '--json', '--output-dir', str(output_dir)]
    if args.match_timeout is not None:
        command += ['--match-timeout', str(args.match_timeout)]
    environment = os.environ.copy()
    environment.update({'TMPDIR': str(temp_root), 'TEMP': str(temp_root), 'TMP': str(temp_root)})
    start = time.monotonic()
    process = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.PIPE,
        text = True, env = environment)
    peak_rss_kib = None
    peak_children = 0
    initial_fds = None
    final_fds = None
    observed_children: set[int] = set()
    while process.poll() is None:
        sample = _process_sample(process.pid)
        if sample['rss_kib'] is not None:
            peak_rss_kib = max(peak_rss_kib or 0, sample['rss_kib'])
        if sample['child_count'] is not None:
            peak_children = max(peak_children, sample['child_count'])
        if initial_fds is None:
            initial_fds = sample['fd_count']
        final_fds = sample['fd_count']
        observed_children.update(_descendant_pids(process.pid))
        time.sleep(POLL_INTERVAL_SECS)
    stdout, stderr = process.communicate()
    wall_time = time.monotonic() - start
    summaries: list[dict[str, typing.Any]] = []
    parse_error = None
    try:
        summaries = json.loads(stdout)
    except json.JSONDecodeError as error:
        parse_error = str(error)
    raw_results = _load_raw_results(output_dir)
    temporary_entries = list(temp_root.iterdir())
    leaked_processes = sum(pathlib.Path(f'/proc/{pid}').exists() for pid in observed_children)
    expected_matches = team_count * (team_count - 1)
    result: dict[str, typing.Any] = {
        'name': run_name, 'teams': team_count, 'workers': workers, 'behaviors': behaviors,
        'return_code': process.returncode, 'wall_time_secs': wall_time, 'matches_total': len(summaries),
        'matches_failed': sum(summary.get('status') == 'failed' for summary in summaries),
        'matches_per_second': expected_matches / wall_time if wall_time > 0 else None,
        'overhead_per_match_secs': (wall_time * workers) / expected_matches if expected_matches > 0 else None,
        'parent_peak_rss_mb': peak_rss_kib / 1024 if peak_rss_kib is not None else None,
        'children_peak_count': peak_children,
        'fd_growth': final_fds - initial_fds if final_fds is not None and initial_fds is not None else None,
        'leaked_processes': leaked_processes,
        'leftover_temp_dirs': len(temporary_entries),
        'output_bytes': sum(path.stat().st_size for path in output_dir.rglob('*') if path.is_file()),
        'stderr': stderr, 'summaries': summaries, 'raw_results': raw_results, 'run_root': str(run_root),
    }
    result['violations'] = _check_invariants(team_count, args.num_games, summaries, raw_results, process.returncode,
        parse_error, temporary_entries, leaked_processes, any(behavior in ('crash', 'hang') for behavior in behaviors))
    if not args.keep_output:
        shutil.rmtree(run_root)
        result['run_root'] = None
    return result

def _signature(result: dict[str, typing.Any]) -> list[tuple[typing.Any, ...]]:
    """Return summary values expected to be deterministic with a fixed seed."""

    return [(summary['white'], summary['black'], summary['seed'], summary['white_score'],
        summary['average_moves']) for summary in result['summaries']]

def _linear_fit(runs: list[dict[str, typing.Any]]) -> dict[str, float | None]:
    """Fit wall time against match count for a sweep."""

    points = [(run['teams'] * (run['teams'] - 1), run['wall_time_secs']) for run in runs]
    if len(points) < 2:
        return {'slope_secs_per_match': None, 'intercept_secs': None, 'r_squared': None}
    x_mean = sum(x for x, _ in points) / len(points)
    y_mean = sum(y for _, y in points) / len(points)
    denominator = sum((x - x_mean) ** 2 for x, _ in points)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    intercept = y_mean - slope * x_mean
    total = sum((y - y_mean) ** 2 for _, y in points)
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    return {'slope_secs_per_match': slope, 'intercept_secs': intercept,
        'r_squared': 1.0 if total == 0 else 1.0 - residual / total}

def main(argv: list[str] | None = None) -> int:
    """Run one scale scenario and write machine-readable measurements."""

    # TODO: Look at other argument parsers in the project to get a better sense of how we write arguments.
    # For example, you must include help messages.
    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument('--scenario', choices = sorted(SCENARIOS), default = 'smoke')
    parser.add_argument('--teams', type = int, default = None)
    parser.add_argument('--workers', type = int, default = 2)
    parser.add_argument('--num-games', type = int, default = 1)
    parser.add_argument('--max-moves', type = int, default = DEFAULT_MAX_MOVES)
    parser.add_argument('--seed', type = int, default = DEFAULT_SEED)
    parser.add_argument('--latency-secs', type = float, default = DEFAULT_LATENCY_SECS)
    parser.add_argument('--agent-action-timeout', type = float, default = 0.2)
    parser.add_argument('--agent-start-timeout', type = float, default = 1.0)
    parser.add_argument('--agent-end-timeout', type = float, default = 1.0)
    parser.add_argument('--match-timeout', type = float, default = None)
    parser.add_argument('--isolation', choices = ['none', 'process', 'tcp'], default = 'process')
    parser.add_argument('--out', type = pathlib.Path, default = pathlib.Path('scale-metrics.json'))
    parser.add_argument('--keep-output', action = 'store_true')
    # TODO: Add more vertical white space in general, things are too crammed and do not help readers determine the 'chunks' of what is happening.
    args = parser.parse_args(argv)
    if args.teams is not None and args.teams < 2:
        parser.error('--teams must be at least 2.')
    if args.workers <= 0:
        parser.error('--workers must be positive.')
    scenario = SCENARIOS[args.scenario]
    team_counts = scenario.get('team_counts', [args.teams or scenario['teams']])
    if args.teams is not None:
        team_counts = [args.teams]
    worker_counts = scenario.get('worker_counts', [args.workers]) if args.scenario == 'latency' else [args.workers]
    # TODO: List comprehension should only be used for very simple work, this is too complicated for a comprehension.
    runs = [_run_once(args, team_count, scenario['behaviors'], workers,
        f'{args.scenario}-{team_count}-teams-{workers}-workers')
        for team_count in team_counts for workers in worker_counts]
    if scenario.get('repeat'):
        repeated = _run_once(args, team_counts[0], scenario['behaviors'], worker_counts[0],
            f'{args.scenario}-repeat')
        if _signature(runs[0]) != _signature(repeated):
            runs[0]['violations'].append('Repeated seeded run did not produce identical summaries.')
        runs.append(repeated)
    metrics = {'schema_version': 1, 'scenario': args.scenario,
        'environment': {'python': sys.version, 'cpu_count': os.cpu_count(), 'platform': sys.platform},
        'runs': runs, 'fit': _linear_fit(runs) if args.scenario == 'sweep' else None}
    args.out.write_text(json.dumps(metrics, indent = 2), encoding = 'utf-8')
    violations = [violation for run in runs for violation in run['violations']]
    print(f"{args.scenario}: {len(runs)} run(s), {len(violations)} invariant violation(s)")
    for run in runs:
        print(f"  {run['name']}: {run['matches_total']} matches in {run['wall_time_secs']:.2f}s")
    # TODO: Try to avoid this syntax. I would rather have clear conditionals for failures on multiple lines.
    return 1 if violations else 0

if (__name__ == '__main__'):
    sys.exit(main())
