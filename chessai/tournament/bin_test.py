import os
import unittest
import sys
import tempfile

import edq.testing.unittest
import edq.util.time

import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.game
import chessai.core.types
import chessai.tournament.bin

def _agent(name: str) -> chessai.core.agentinfo.AgentInfo:
    return chessai.core.agentinfo.AgentInfo(name = name)

class TournamentRunnerTest(edq.testing.unittest.BaseTest):
    """ Test tournament discovery without running untrusted agents. """

    def test_collect_teams(self):
        """ Only non-excluded immediate directories with tournament.py participate. """

        with tempfile.TemporaryDirectory() as temp_dir:
            agent_dir = os.path.join(temp_dir, 'alpha')
            os.makedirs(agent_dir)
            with open(os.path.join(agent_dir, chessai.tournament.bin.AGENT_FILENAME), 'w', encoding = 'utf-8'):
                pass

            os.makedirs(os.path.join(temp_dir, 'missing-agent'))
            excluded_dir = os.path.join(temp_dir, 'excluded')
            os.makedirs(excluded_dir)
            with open(os.path.join(excluded_dir, chessai.tournament.bin.AGENT_FILENAME), 'w', encoding = 'utf-8'):
                pass

            # [(excluded names, expected names), ...]
            test_cases = [
                (set(), ['alpha', 'excluded']),
                ({'excluded'}, ['alpha']),
            ]

            for (i, test_case) in enumerate(test_cases):
                (excluded_names, expected_names) = test_case
                expected_references = []
                for name in expected_names:
                    reference = chessai.tournament.bin._agent_reference(
                        os.path.join(temp_dir, name, chessai.tournament.bin.AGENT_FILENAME))
                    expected_references.append(reference)

                with self.subTest(msg = f"Case {i}:"):
                    teams = chessai.tournament.bin._collect_teams(temp_dir, excluded_names)
                    actual_names = []
                    for team in teams:
                        actual_names.append(str(team.name))

                    self.assertEqual(expected_references, actual_names)

    def test_schedule_matches(self):
        """ Every unique pairing is scheduled exactly once. """

        test_cases = [
            (
                ['agent-random', 'agent-pick-first'],
                [
                    ('agent-random', 'agent-pick-first'), ('agent-pick-first', 'agent-random'),
                ]
            ),
            (
                ['agent-random', 'agent-pick-first', 'agent-greedy'],
                [
                    ('agent-random', 'agent-pick-first'), ('agent-pick-first', 'agent-random'),
                    ('agent-random', 'agent-greedy'), ('agent-greedy', 'agent-random'),
                    ('agent-pick-first', 'agent-greedy'), ('agent-greedy', 'agent-pick-first'),
                ]
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            (agent_names, expected_matches) = test_case
            agents = []
            for agent_name in agent_names:
                agents.append(agent_name)

            with self.subTest(msg = f"Case {i}:"):
                matches = chessai.tournament.bin._schedule_matches(agents)
                actual_matches = []
                for match in matches:
                    actual_matches.append((match.white, match.black))

                self.assertEqual(expected_matches, actual_matches)

    @unittest.skipIf(sys.platform.startswith("win"), "tournaments require POSIX")
    def test_run_tournament(self):
        """ Run tournament matches and observe the results. """

        default_argv = [
                '--seed', '4',
                ]

        # [([(white name, black name), ...], [argv, ...], [[(score, num moves, reason), ...], ...])]
        test_cases: list[tuple[
                list[tuple[str, str]],
                list[str],
                list[list[tuple[float, int, chessai.core.types.TerminationReason]]]
            ]] = [
                # Simple random setup.
                (
                    [
                        ('agent-random', 'agent-random'),
                    ],
                    [],
                    [
                        [(0.5, 100, chessai.core.types.TerminationReason.GAME_TIMEOUT)],
                    ],
                ),

                # Limit the number of moves.
                (
                    [
                        ('agent-random', 'agent-random'),
                    ],
                    [
                        '--max-moves', '10',
                    ],
                    [
                        [(0.5, 10, chessai.core.types.TerminationReason.GAME_TIMEOUT)],
                    ],
                ),

                # Multiple matches.
                (
                    [
                        ('agent-random', 'agent-random'),
                        ('agent-random', 'agent-random'),
                    ],
                    [
                        '--max-moves', '10',
                    ],
                    [
                        [(0.5, 10, chessai.core.types.TerminationReason.GAME_TIMEOUT)],
                        [(0.5, 10, chessai.core.types.TerminationReason.GAME_TIMEOUT)],
                    ],
                ),

                # Dummy agent loses.
                (
                    [
                        ('agent-dummy', 'agent-random'),
                    ],
                    [
                        '--max-moves', '10',
                    ],
                    [
                        [(0, 1, chessai.core.types.TerminationReason.AGENT_CRASHED)],
                    ],
                ),

                # Random agent beats dummy agent.
                (
                    [
                        ('agent-random', 'agent-dummy'),
                    ],
                    [
                        '--max-moves', '10',
                    ],
                    [
                        [(1, 2, chessai.core.types.TerminationReason.AGENT_CRASHED)],
                    ],
                ),

                # Multiple games for each match.
                (
                    [
                        ('agent-random', 'agent-random'),
                    ],
                    [
                        '--max-moves', '10',
                        '--num-games', '2',
                    ],
                    [
                        [
                            (0.5, 10, chessai.core.types.TerminationReason.GAME_TIMEOUT),
                            (0.5, 10, chessai.core.types.TerminationReason.GAME_TIMEOUT),
                        ],
                    ],
                ),
            ]

        for (i, test_case) in enumerate(test_cases):
            (all_team_names, extra_argvs, all_expected_results) = test_case

            with self.subTest(msg = f"Case {i}:"):
                # Construct the matches
                matches = []
                for team_names in all_team_names:
                    (white_team, black_team) = team_names
                    white_info = chessai.core.agentinfo.AgentInfo(name = white_team)
                    black_info = chessai.core.agentinfo.AgentInfo(name = black_team)

                    match = chessai.tournament.bin.Match(white = white_info, black = black_info)
                    matches.append(match)

                # Construct and parse the match args
                argv = default_argv + extra_argvs

                parser = chessai.tournament.bin._get_parser()
                args = parser.parse_args(argv)

                # Running the tournament stores results within the match objects
                chessai.tournament.bin._run_tournament(matches, args)

                # Collect the results from the matches
                all_actual_results = []
                for match in matches:
                    all_actual_results.append(match.results)

                self.assertEqual(len(all_expected_results), len(all_actual_results))

                for (expected_results, actual_results) in zip(all_expected_results, all_actual_results):
                    self.assertEqual(len(expected_results), len(actual_results))

                    for (expected_result, actual_result) in zip(expected_results, actual_results):
                        (expected_score, expected_num_moves, expected_reason) = expected_result
                        self.assertAlmostEqual(expected_score, actual_result.score)
                        self.assertEqual(expected_num_moves, len(actual_result.history))
                        self.assertEqual(expected_reason, actual_result.termination_reason)
