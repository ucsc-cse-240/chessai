import abc
import argparse
import os
import typing

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

import chessai.core.action
import chessai.core.coordinate
import chessai.core.gamestate
import chessai.core.piece
import chessai.util.alias
import chessai.util.reflection

DEFAULT_ANIMATION_FPS: int = 15
DEFAULT_ANIMATION_SKIP_FRAMES: int = 1
DEFAULT_ANIMATION_OPTIMIZE: bool = False
MIN_ANIMATION_FPS: int = 1

ANIMATION_EXTS: list[str] = ['.gif', '.webp']
""" The allowed extensions for animation files. """

SQUARE_SIZE: int = 72
LABEL_SIZE: int = 20
LIGHT_SQUARE: tuple[int, int, int] = (240, 217, 181)
DARK_SQUARE: tuple[int, int, int] = (181, 136, 99)
HIGHLIGHT: tuple[int, int, int] = (246, 246, 105)
LABEL_COLOR: tuple[int, int, int] = (70, 70, 70)
THIS_DIR: str = os.path.dirname(os.path.realpath(__file__))
SPRITES_DIR: str = os.path.join(THIS_DIR, '..', 'resources', 'sprites')

class UI(abc.ABC):
    """
    UIs represent the basic way that a game interacts with the user,
    by displaying the state of the game.
    """

    def __init__(self,
            animation_path: str | None = None,
            animation_optimize: bool = DEFAULT_ANIMATION_OPTIMIZE,
            animation_fps: int = DEFAULT_ANIMATION_FPS,
            animation_skip_frames: int = DEFAULT_ANIMATION_SKIP_FRAMES,
            **kwargs: typing.Any) -> None:
        self._update_count: int = 0
        """ Keep track of the number of times update() has been called. """

        self._animation_path: str | None = animation_path
        """ If specified, create a animation and write it to this location after the game completes. """

        if (self._animation_path is not None):
            if (os.path.splitext(self._animation_path)[-1] not in ANIMATION_EXTS):
                raise ValueError(f"Animation path must have one of the following extensions {ANIMATION_EXTS}, found '{self._animation_path}'.")

        self._animation_optimize: bool = animation_optimize
        """ Optimize the animation output to reduce file size. """

        self._animation_fps: int = max(MIN_ANIMATION_FPS, animation_fps)
        """ The frame rate for the animation. """

        self._animation_skip_frames: int = max(1, animation_skip_frames)
        """
        Skip this many frames between drawing animation frames.
        This can help speed up animation creation by leaving out less important frames.
        For example, this can be set to the number of agents to only draw frames after all agents have moved.
        """

        self._animation_frames: list[PIL.Image.Image] = []
        """ The frames for the animation (one per call to update(). """

        self._static_base_image: PIL.Image.Image | None = None
        """
        Cache an image that has all of the static (non-changing) elements (like walls) drawn.
        This can be reused as the base image every time we draw an image.
        """

        self._static_board_size: tuple[int, int] | None = None
        """ The board dimensions represented by the cached base image. """

        self._sprites: dict[str, PIL.Image.Image] = {}
        """ Piece sprites keyed by their symbol. """

        self._label_font = PIL.ImageFont.load_default()
        """ The available fonts for labels. """

    def update(self,
            state: chessai.core.gamestate.GameState,
            termination_reason: chessai.core.types.TerminationReason | None = None,
            force_draw_image: bool = False,
            ) -> None:
        """
        Update the UI with the current state of the game.
        This is the main entry point for the game into the UI.
        """

        if ((self._animation_path is not None)
                and (force_draw_image or (self._update_count % self._animation_skip_frames == 0))):
            self._animation_frames.append(self.draw_image(state))

        self.draw(state, termination_reason = termination_reason)

        self._update_count += 1

    def game_start(self,
            initial_state: chessai.core.gamestate.GameState,
            ) -> None:
        """ Initialize the UI with the game's initial state. """

        self.update(initial_state, force_draw_image = True)

    def game_complete(self,
            final_state: chessai.core.gamestate.GameState,
            termination_reason: chessai.core.types.TerminationReason,
            ) -> None:
        """ Update the UI with the game's final state. """

        self.update(final_state, termination_reason, force_draw_image = True)

        if ((self._animation_path is not None) and (len(self._animation_frames) > 0)):
            self._animation_frames[0].save(self._animation_path,
                    save_all = True,
                    append_images = self._animation_frames[1:],
                    duration = int(1000 / self._animation_fps),
                    loop = 0,
                    optimize = self._animation_optimize)

    def close(self) -> None:
        """ Close the UI and release all owned resources. """

    def draw_image(self, state: chessai.core.gamestate.GameState) -> PIL.Image.Image:
        """Render a chess position as a Pillow image for web display or animation."""

        image = self._get_static_image(state)
        canvas = PIL.ImageDraw.Draw(image)
        action = state.get_previous_action()
        if (isinstance(action, chessai.core.action.MoveAction)):
            self._draw_square(canvas, state, action.start_coordinate, HIGHLIGHT)
            self._draw_square(canvas, state, action.end_coordinate, HIGHLIGHT)

        for (coordinate, piece) in state.board.get_coordinate_map().items():
            x, y = self._coordinate_to_pixels(state, coordinate)
            sprite = self._get_sprite(piece)
            image.paste(sprite, (x, y), sprite)

        return image

    def _get_static_image(self, state: chessai.core.gamestate.GameState) -> PIL.Image.Image:
        board_size = (state.board.num_files, state.board.num_ranks)
        if ((self._static_base_image is not None) and (self._static_board_size == board_size)):
            return self._static_base_image.copy()

        width = (state.board.num_files * SQUARE_SIZE) + LABEL_SIZE
        height = (state.board.num_ranks * SQUARE_SIZE) + LABEL_SIZE

        image = PIL.Image.new('RGB', (width, height), 'white')
        canvas = PIL.ImageDraw.Draw(image)
        for file in range(state.board.num_files):
            for rank in range(state.board.num_ranks):
                self._draw_square(canvas, state, chessai.core.coordinate.Coordinate(file, rank))

        for file in range(state.board.num_files):
            x = LABEL_SIZE + (file * SQUARE_SIZE) + (SQUARE_SIZE // 2)
            label = chessai.core.coordinate.Coordinate(file, 0).uci(only_file = True)
            canvas.text((x, height - (LABEL_SIZE // 2)), label, fill = LABEL_COLOR,
                    font = self._label_font, anchor = 'mm')

        for rank in range(state.board.num_ranks):
            y = (state.board.num_ranks - rank - 1) * SQUARE_SIZE + (SQUARE_SIZE // 2)
            canvas.text((LABEL_SIZE // 2, y), str(rank + 1), fill = LABEL_COLOR,
                    font = self._label_font, anchor = 'mm')

        self._static_base_image = image.copy()
        self._static_board_size = board_size

        return image

    def _get_sprite(self, piece: chessai.core.piece.Piece) -> PIL.Image.Image:
        """ Get the bundled PNG sprite for a piece. """

        symbol = piece.symbol()
        if (symbol in self._sprites):
            return self._sprites[symbol]

        if (piece.color == chessai.core.types.Color.WHITE):
            color = 'white'
        else:
            color = 'black'

        name = f"{type(piece).__name__.lower()}_{color}.png"
        path = os.path.join(SPRITES_DIR, name)

        if (os.path.isfile(path)):
            with PIL.Image.open(path) as image:
                sprite = image.convert('RGBA')
        else:
            sprite = self._make_default_sprite(piece)

        self._sprites[symbol] = sprite

        return sprite

    def _make_default_sprite(self, piece: chessai.core.piece.Piece) -> PIL.Image.Image:
        """ Create a fallback sprite: a filled circle with the piece's symbol centered on it. """

        if (piece.color == chessai.core.types.Color.WHITE):
            fill = (245, 245, 245, 255)
            outline = (30, 30, 30, 255)
            text_color = (30, 30, 30, 255)
        else:
            fill = (40, 40, 40, 255)
            outline = (225, 225, 225, 255)
            text_color = (245, 245, 245, 255)

        sprite = PIL.Image.new('RGBA', (SQUARE_SIZE, SQUARE_SIZE), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(sprite)

        margin = max(2, SQUARE_SIZE // 10)
        draw.ellipse(
            [margin, margin, SQUARE_SIZE - margin, SQUARE_SIZE - margin],
            fill = fill,
            outline = outline,
            width = max(1, SQUARE_SIZE // 25),
        )

        # Size default supported in Pillow >= 10.1.
        try:
            font = PIL.ImageFont.load_default(size = SQUARE_SIZE // 2)
        except TypeError:
            font = PIL.ImageFont.load_default()

        # Center using anchor 'mm' (middle/middle) and always show the uppercase letter regardless of color.
        draw.text(
            (SQUARE_SIZE / 2, SQUARE_SIZE / 2),
            piece.symbol(),
            fill = text_color,
            font = font,
            anchor = 'mm',
        )

        return sprite

    def _draw_square(self, canvas: PIL.ImageDraw.ImageDraw,
            state: chessai.core.gamestate.GameState,
            coordinate: chessai.core.coordinate.Coordinate,
            color: tuple[int, int, int] | None = None) -> None:
        if (color is None):
            color = LIGHT_SQUARE if ((coordinate.file + coordinate.rank) % 2 == 1) else DARK_SQUARE

        x, y = self._coordinate_to_pixels(state, coordinate)
        canvas.rectangle((x, y, x + SQUARE_SIZE, y + SQUARE_SIZE), fill = color)

    def _coordinate_to_pixels(self, state: chessai.core.gamestate.GameState,
            coordinate: chessai.core.coordinate.Coordinate) -> tuple[int, int]:
        return (LABEL_SIZE + (coordinate.file * SQUARE_SIZE),
                (state.board.num_ranks - coordinate.rank - 1) * SQUARE_SIZE)

    @abc.abstractmethod
    def draw(self, state: chessai.core.gamestate.GameState, **kwargs: typing.Any) -> None:
        """
        Visualize the state of the game to the UI.
        This is the typically the main override point for children.
        Note that how this method visualizes the game completely unrelated
        to how the draw_image() method works.
        draw() will render to whatever the specific UI for the child class is,
        while draw_image() specifically creates an image which will be used for animations.
        If the child UI is also image-based than it can leverage draw_image(),
        but there is no requirement to do that.
        """

def set_cli_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Set common CLI arguments.
    This is a sibling to init_from_args(), as the arguments set here can be interpreted there.
    """

    parser.add_argument('--ui', dest = 'ui',
            action = 'store', type = str, default = chessai.util.alias.UI_STDIO.short,
            help = ('Set the UI/graphics to use (default: %(default)s).'
                    + ' Builtin options:'
                    + f' `{chessai.util.alias.UI_NULL.short}` (`{chessai.util.alias.UI_NULL.long}`)'
                    +       ' -- Do not show any ui/graphics (best if you want to run fast and just need the result),'
                    + f' `{chessai.util.alias.UI_STDIO.short}` (`{chessai.util.alias.UI_STDIO.long}`)'
                    +       ' -- Use stdin/stdout from the terminal (default).'))

    parser.add_argument('--animation-path', type = str, default = None,
            help = 'Save rendered game frames as a .gif or .webp animation.')

    parser.add_argument('--animation-fps', type = int, default = DEFAULT_ANIMATION_FPS,
            help = 'Animation frame rate (default: %(default)s).')

    parser.add_argument('--animation-skip-frames', type = int, default = DEFAULT_ANIMATION_SKIP_FRAMES,
            help = 'Render every Nth UI update into the animation (default: %(default)s).')

    parser.add_argument('--animation-optimize', action = 'store_true', default = DEFAULT_ANIMATION_OPTIMIZE,
            help = 'Optimize the animation to reduce its file size.')

    return parser

def init_from_args(
        args: argparse.Namespace,
        num_uis: int = 0,
        null_out_uis: int = 0,
        additional_args: dict | None = None,
        ) -> argparse.Namespace:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and initialize the proper components.
    Constructed UIs will be placed `args._uis`.
    If `num_uis` is not provided (or <= 0),
    then `args.num_games` will be used.
    If `null_out_uis` is > 0, then at most that number of UIs (starting at the beginning)
    will be converted to null UIs.
    This will not change the total number of UIs, just null out the first number of UIs.
    """

    ui_args = {
        'animation_path': args.animation_path,
        'animation_fps': args.animation_fps,
        'animation_skip_frames': args.animation_skip_frames,
        'animation_optimize': args.animation_optimize,
    }

    if (additional_args is not None):
        ui_args.update(additional_args)

    if (num_uis <= 0):
        num_uis = args.num_games

    uis = []
    for i in range(num_uis):
        ui_name = args.ui
        if (i < null_out_uis):
            ui_name = chessai.util.alias.UI_NULL.long

        uis.append(chessai.util.reflection.new_object(ui_name, **ui_args))

    setattr(args, '_uis', uis)

    return args
