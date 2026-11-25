#!/usr/bin/env python3

"""
Render the bundled SVG chess pieces as PNG sprites.

CairoSVG is only a development requirement, as it does not work well on non-linux distros.
Use this script to generate PNGs for future usage.
"""

import os
import sys

import cairosvg

SQUARE_SIZE: int = 72
THIS_DIR: str = os.path.dirname(os.path.realpath(__file__))
SPRITES_DIR: str = os.path.join(THIS_DIR, '..', 'chessai', 'resources', 'sprites')

def main() -> None:
    """ Render each source SVG into the matching PNG sprite. """

    for name in sorted(os.listdir(SPRITES_DIR)):
        if (not name.endswith('.svg')):
            continue

        source_path = os.path.join(SPRITES_DIR, name)
        destination_name = f"{os.path.splitext(name)[0]}.png"
        destination_path = os.path.join(SPRITES_DIR, destination_name)
        cairosvg.svg2png(
            url = source_path,
            write_to = destination_path,
            output_width = SQUARE_SIZE,
            output_height = SQUARE_SIZE,
        )
        print(f"{name} -> {destination_name}")

    return 0

if (__name__ == '__main__'):
    sys.exit(main())
