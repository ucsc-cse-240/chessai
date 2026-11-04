import unittest

import chessai.chess.gamestate
import chessai.core.gameannotation
import chessai.core.gameparser


class GameRatingAnnotationTest(unittest.TestCase):
    """ Test game rating annotations and their PGN representation. """

    def test_header_round_trip(self) -> None:
        """ An annotation can be serialized to a PGN header and restored. """

        annotation = chessai.core.gameannotation.GameRatingAnnotation(
            engine = chessai.core.gameannotation.RatingEngine('Stockfish', 'abc123'),
            depth = 15,
            annotations = [
                chessai.core.gameannotation.MoveRatingAnnotation(
                    0, 0.25, description = 'The position is about equal'),
                chessai.core.gameannotation.MoveRatingAnnotation(
                    1, 'M3', 'e2e4', 'White has a forced checkmate in 3 moves'),
            ],
        )

        escaped_header_value = annotation.to_header_value().replace('\\', '\\\\').replace('"', '\\"')
        pgn = ('[Event "Test"]\n[Site "Local"]\n[Date "2026.01.01"]\n[Round "1"]\n'
               '[White "White"]\n[Black "Black"]\n[Result "*"]\n'
               f'[{chessai.core.gameannotation.GAME_RATING_ANNOTATION_HEADER} '
               f'"{escaped_header_value}"]\n\n*\n')

        parsed_pgn = chessai.core.gameparser.parse_pgn(pgn, chessai.chess.gamestate.GameState)
        self.assertIsNotNone(parsed_pgn)
        self.assertEqual(annotation, parsed_pgn.get_game_rating_annotation())

    def test_header_without_description(self) -> None:
        """ Older annotations remain readable when descriptions are introduced. """

        annotation = chessai.core.gameannotation.GameRatingAnnotation.from_header_value(
            '{"schema_version":"0.0.4","score_perspective":"white",'
            '"engine":{"name":"Stockfish","commit":"abc123"},"depth":15,'
            '"annotations":[{"ply":0,"rating":0.25,"move":null}]}')

        self.assertIsNone(annotation.annotations[0].description)
