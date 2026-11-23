import typing

import edq.testing.unittest

import chessai.chess.piece
import chessai.core.gamestate
import chessai.core.types
import chessai.core.ui

class _TestUI(chessai.core.ui.UI):
    """A UI implementation used to exercise shared image helpers."""

    def draw(self, state: chessai.core.gamestate.GameState, **kwargs: typing.Any) -> None:
        """Do nothing; this test only loads sprites."""

class UITest(edq.testing.unittest.BaseTest):
    """Test UI image helpers."""

    def test_loads_bundled_png_sprite(self):
        """Load a shipped PNG piece without requiring CairoSVG."""

        ui = _TestUI()
        piece = chessai.chess.piece.Pawn(chessai.core.types.Color.WHITE)

        sprite = ui._get_sprite(piece)

        self.assertEqual((chessai.core.ui.SQUARE_SIZE, chessai.core.ui.SQUARE_SIZE), sprite.size)
        self.assertEqual('RGBA', sprite.mode)
