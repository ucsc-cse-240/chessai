import os
import tempfile

import edq.testing.unittest
import edq.util.time

import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.game
import chessai.core.types
import chessai.tournament.bin

class TournamentRunnerTest(edq.testing.unittest.BaseTest):
    """ Test tournament discovery without running untrusted agents. """

    def test_collect_teams(self):
        """ Only immediate team directories with tournament.py participate. """

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

            teams = chessai.tournament.bin._collect_teams(temp_dir, {'excluded'})

            self.assertEqual(['alpha'], [team.name for team in teams])
            self.assertEqual(os.path.join(agent_dir, chessai.tournament.bin.AGENT_FILENAME), teams[0].agent_path)

    def test_schedule_matches(self):
        """ Every unique pairing is scheduled exactly once. """

        teams = [
            chessai.tournament.bin.Team('alpha', '/alpha.py'),
            chessai.tournament.bin.Team('beta', '/beta.py'),
            chessai.tournament.bin.Team('gamma', '/gamma.py'),
        ]

        matches = chessai.tournament.bin._schedule_matches(teams)
        actual_matches = [(match.white.name, match.black.name) for match in matches]
        expected_matches = [
            ('alpha', 'beta'), ('beta', 'alpha'),
            ('alpha', 'gamma'), ('gamma', 'alpha'),
            ('beta', 'gamma'), ('gamma', 'beta')
        ]

        self.assertEqual(actual_matches, expected_matches)

    def test_summary_rotates_scores(self):
        """ Rotated games are summarized from player one's perspective. """

        match = chessai.tournament.bin.Match(
            chessai.tournament.bin.Team('alpha', '/alpha.py'),
            chessai.tournament.bin.Team('beta', '/beta.py'),
            results = [
                chessai.core.game.GameResult(
                    1,
                    chessai.core.game.GameInfo({
                        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo('agent-dummy'),
                    }),
                    score = 1.0,
                    history = [
                        chessai.core.agentaction.AgentActionRecord(
                            chessai.core.types.Color.WHITE,
                            None,
                            edq.util.time.Duration(0),
                        ),
                    ],
                    start_time = edq.util.time.Timestamp(1000),
                    end_time = edq.util.time.Timestamp(3000),
                ),
                chessai.core.game.GameResult(
                    2,
                    chessai.core.game.GameInfo({
                        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo('agent-dummy'),
                    }),
                    score = 0.0,
                    history = [
                        chessai.core.agentaction.AgentActionRecord(
                            chessai.core.types.Color.WHITE,
                            None,
                            edq.util.time.Duration(0),
                        ),
                        chessai.core.agentaction.AgentActionRecord(
                            chessai.core.types.Color.BLACK,
                            None,
                            edq.util.time.Duration(0),
                        ),
                    ],
                    start_time = edq.util.time.Timestamp(5000),
                    end_time = edq.util.time.Timestamp(8000),
                ),
            ],
            status = chessai.tournament.bin.MatchStatus.SUCCESS,
        )

        summary = chessai.tournament.bin._summary(match)

        self.assertEqual(1, summary['white_wins'])
        self.assertEqual(1, summary['white_losses'])
        self.assertEqual(0.5, summary['white_score'])
        self.assertEqual(1.5, summary['average_moves'])
        self.assertEqual(2.5, summary['average_duration_secs'])
