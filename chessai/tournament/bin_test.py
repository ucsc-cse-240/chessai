import os
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
