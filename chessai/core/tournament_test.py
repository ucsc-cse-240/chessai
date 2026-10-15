import typing

import edq.testing.unittest

import chessai.core.tournament
import chessai.tournament.bin


class TournamentTest(edq.testing.unittest.BaseTest):
    """ Test tournament schedule and reporting behavior. """

    def test_game_dict_conversion(self):
        """ Tournament games retain scheduling and result information. """

        # [(name, input dict, expected attributes), ...]
        test_cases: list[tuple[str, dict[str, typing.Any], dict[str, typing.Any]]] = [
            # Full game
            (
                {
                    'id': 'round-1',
                    'player_one': 'agent-random',
                    'player_two': 'agent-aggressive',
                    'seed': 7,
                    'results': [{'score': 1.0, 'history': [], 'start_time': 1, 'end_time': 2}],
                    'status': 'succeeded',
                },
                {
                    'id': 'round-1',
                    'player_one': 'agent-random',
                    'player_two': 'agent-aggressive',
                    'seed': 7,
                    'results': [{'score': 1.0, 'history': [], 'start_time': 1, 'end_time': 2}],
                    'status': 'succeeded',
                },
            ),

            # Input form only (defaults)
            (
                {
                    'player_one': 'agent-random',
                    'player_two': 'agent-aggressive',
                },
                {
                    'id': None,
                    'player_one': 'agent-random',
                    'player_two': 'agent-aggressive',
                    'seed': None,
                    'results': [],
                    'status': 'pending',
                },
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            input_dict, expected_attributes = test_case
            with self.subTest(msg = f"Case {i}:"):
                game = chessai.core.tournament.Game.from_dict(input_dict)

                for (attribute, expected_value) in expected_attributes.items():
                    self.assertEqual(expected_value, getattr(game, attribute), f"Attribute '{attribute}' mismatch.")

    def test_summary(self):
        """ Summary scores remain in player one's perspective after rotation. """

        # [(kwargs, rotate sides, expected summary fields), ...]
        test_cases: list[tuple[str, dict[str, typing.Any], bool, dict[str, typing.Any]]] = [
            # Rotated sides preserve agent one wins.
            (
                {
                    'player_one': 'agent-one',
                    'player_two': 'agent-two',
                    'results': [
                        {'score': 1.0, 'history': [None], 'start_time': 1000, 'end_time': 3000},
                        {'score': 0.0, 'history': [None, None], 'start_time': 5000, 'end_time': 8000},
                    ],
                    'status': 'succeeded',
                },
                True,
                {
                    'player_one_wins': 2,
                    'player_one_losses': 0,
                    'player_one_score': 1.0,
                    'average_moves': 1.5,
                    'average_duration_secs': 2.5,
                },
            ),
        ]

        for (i, test_case) in enumerate(test_cases):
            game_kwargs, rotate_sides, expected_fields = test_case
            with self.subTest(msg = f"Case {i}:"):
                game = chessai.core.tournament.Game(**game_kwargs)
                summary = chessai.tournament.bin._summary(game, rotate_sides = rotate_sides)

                for (key, expected_value) in expected_fields.items():
                    self.assertEqual(expected_value, summary[key], f"Summary field '{key}' mismatch.")

    def test_game_validation(self):
        """ Invalid participants or ids are rejected. """

        # [(constructor kwargs, expected error regex), ...]
        test_cases: list[tuple[dict[str, typing.Any], str]] = [
            # Empty player one
            ({'player_one': '', 'player_two': 'agent-random'}, 'player_one'),

            # Whitespace player one
            ({'player_one': '   ', 'player_two': 'agent-random'}, 'player_one'),

            # Non-string player one
            ({'player_one': 5, 'player_two': 'agent-random'}, 'player_one'),

            # Empty player two
            ({'player_one': 'agent-random', 'player_two': ''}, 'player_two'),

            # Whitespace player two
            ({'player_one': 'agent-random', 'player_two': '   '}, 'player_two'),

            # Non-string player two
            ({'player_one': 'agent-random', 'player_two': None}, 'player_two'),

            # Empty id
            ({'player_one': 'agent-one', 'player_two': 'agent-two', 'id': ''}, 'id'),

            # Non-string id
            ({'player_one': 'agent-one', 'player_two': 'agent-two', 'id': 7}, 'id'),
        ]

        for (i, test_case) in enumerate(test_cases):
            kwargs, error_regex = test_case
            with self.subTest(msg = f"Case {i}:"):
                with self.assertRaisesRegex(ValueError, error_regex):
                    chessai.core.tournament.Game(**kwargs)
