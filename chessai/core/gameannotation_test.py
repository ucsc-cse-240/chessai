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
                chessai.core.gameannotation.MoveRatingAnnotation(0, 0.25),
                chessai.core.gameannotation.MoveRatingAnnotation(1, 'M3', 'e2e4'),
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
