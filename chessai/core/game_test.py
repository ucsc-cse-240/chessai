import edq.testing.unittest
import edq.util.time
import edq.util.serial

import chessai.core.action
import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.game
import chessai.core.isolation.level
import chessai.core.types

def _get_two_dummy_agents() -> dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo]:
    """ Get a fresh set of dummy agent infos for both colors. """

    return {
        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo('agent-dummy'),
        chessai.core.types.Color.BLACK: chessai.core.agentinfo.AgentInfo('agent-dummy'),
    }

class GameResultTest(edq.testing.unittest.BaseTest):
    """ Test chessai.core.game.GameResult functionality. """

    def test_serialization(self):
        """ Test serialization round trips. """

        # [GameResult, ...]
        test_cases: list[chessai.core.game.GameResult] = [
            # Minimal: one agent, all defaults.
            chessai.core.game.GameResult(
                1,
                chessai.core.game.GameInfo(
                    agent_infos = {
                        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo('agent-dummy'),
                    },
                ),
            ),

            # Both agents, default game info.
            chessai.core.game.GameResult(
                2,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                ),
            ),

            # Fully customized game info.
            chessai.core.game.GameResult(
                3,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    start_fen = '8/8/8/4k3/8/8/4K3/4R3 w - - 0 1',
                    isolation_level = chessai.core.isolation.level.Level.PROCESS,
                    max_moves = 100,
                    agent_start_timeout = 1.5,
                    agent_end_timeout = 2.5,
                    agent_action_timeout = 3.5,
                    seed = 12345,
                    event = 'Test Event',
                    site = 'Test Site',
                    date = '2025.01.02',
                    game_round = '7',
                    white_player = 'Alice',
                    black_player = 'Bob',
                    extra_info = {'Opening': 'Sicilian', 'Rating': 1500},
                    wait_for_user = True,
                ),
            ),

            # Finished game: checkmate with a white win.
            chessai.core.game.GameResult(
                4,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 4,
                ),
                termination_reason = chessai.core.types.TerminationReason.CHECKMATE,
                score = 1.0,
                end_fen = '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1',
                end_time = edq.util.time.Timestamp.now(),
                winning_agent_teams = [chessai.core.types.Color.WHITE],
            ),

            # Finished game: black win (negative score from white's perspective).
            chessai.core.game.GameResult(
                5,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 5,
                ),
                termination_reason = chessai.core.types.TerminationReason.CHECKMATE,
                score = -1.0,
                end_time = edq.util.time.Timestamp.now(),
                winning_agent_teams = [chessai.core.types.Color.BLACK],
            ),

            # Draw: stalemate, no winners.
            chessai.core.game.GameResult(
                6,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 6,
                ),
                termination_reason = chessai.core.types.TerminationReason.STALEMATE,
                score = 0.0,
                winning_agent_teams = [],
            ),

            # Game timeout.
            chessai.core.game.GameResult(
                7,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    max_moves = 10,
                    seed = 7,
                ),
                termination_reason = chessai.core.types.TerminationReason.GAME_TIMEOUT,
                game_timeout = True,
            ),

            # Agent timeout.
            chessai.core.game.GameResult(
                8,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 8,
                ),
                termination_reason = chessai.core.types.TerminationReason.AGENT_TIMEOUT,
                timeout_agent_teams = [chessai.core.types.Color.BLACK],
                winning_agent_teams = [chessai.core.types.Color.WHITE],
            ),

            # Agent crash (both teams, to test multi-element lists).
            chessai.core.game.GameResult(
                9,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 9,
                ),
                termination_reason = chessai.core.types.TerminationReason.AGENT_CRASHED,
                crash_agent_teams = [chessai.core.types.Color.WHITE, chessai.core.types.Color.BLACK],
            ),

            # History with records (normal, crashed, and timeout).
            chessai.core.game.GameResult(
                10,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 10,
                ),
                history = [
                    chessai.core.agentaction.AgentActionRecord(
                        chessai.core.types.Color.WHITE,
                        chessai.core.agentaction.AgentAction(
                            other_info = {'note': 'hello', 'depth': 3},
                        ),
                        edq.util.time.Duration(10),
                    ),
                    chessai.core.agentaction.AgentActionRecord(
                        chessai.core.types.Color.BLACK,
                        None,
                        edq.util.time.Duration(0),
                        crashed = True,
                    ),
                    chessai.core.agentaction.AgentActionRecord(
                        chessai.core.types.Color.WHITE,
                        None,
                        edq.util.time.Duration(5000),
                        timeout = True,
                    ),
                ],
            ),

            # Agent completion records (note the enum keys in the dict).
            chessai.core.game.GameResult(
                11,
                chessai.core.game.GameInfo(
                    agent_infos = _get_two_dummy_agents(),
                    seed = 11,
                ),
                agent_complete_records = {
                    chessai.core.types.Color.WHITE: chessai.core.agentaction.AgentActionRecord(
                        chessai.core.types.Color.WHITE,
                        chessai.core.agentaction.AgentAction(other_info = {'learned': True}),
                        edq.util.time.Duration(1),
                    ),
                    chessai.core.types.Color.BLACK: chessai.core.agentaction.AgentActionRecord(
                        chessai.core.types.Color.BLACK,
                        None,
                        edq.util.time.Duration(2),
                    ),
                },
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            expected_game_result = test_case

            with self.subTest(msg = f"Case {i}:"):
                # Convert the game result to a dict.
                dict_game_result = expected_game_result.to_dict()

                # Convert the dict back to a game result.
                actual_game_result = chessai.core.game.GameResult.from_dict(dict_game_result)

                # Compare results.
                self.assertEqual(expected_game_result, actual_game_result)
