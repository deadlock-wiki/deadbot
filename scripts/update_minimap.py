"""
Regenerate the Midtown base map used by the game_map parser from an installed copy of Deadlock

The minimap texture lives in game/citadel/pak01_*.vpk, which deadbot does not download, so the
map is committed to src/parser/parsers/game_map/assets/minimap_midtown_opaque.png.
Re-run this whenever the map changes.

Requires the Source2Viewer CLI (https://github.com/ValveResourceFormat/ValveResourceFormat/releases),
passed with --decompiler or the DECOMPILER_CMD environment variable:

    python scripts/update_minimap.py --game "C:/Program Files (x86)/Steam/steamapps/common/Deadlock/game" --decompiler Source2Viewer-CLI.exe
"""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

# The street map. Older revisions ship alongside it with a hash suffix, e.g. minimap_midtown_mid_psd_dd4bcbf9.vtex_c
MINIMAP_TEXTURE = 'panorama/images/minimap/base/minimap_midtown_mid_psd.vtex_c'
OUTPUT_PATH = Path('src/parser/parsers/game_map/assets/minimap_midtown_opaque.png')
# The texture is translucent everywhere, so it is drawn onto this colour to make it readable on any page background
BACKGROUND = (175, 161, 144)


def _srgb_to_linear(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> int:
    c = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return round(min(max(c, 0), 1) * 255)


SRGB_TO_LINEAR = [_srgb_to_linear(v) for v in range(256)]


def extract_minimap(decompiler: str, game_dir: str, texture: str) -> Image.Image:
    """Export the minimap texture from pak01 as a PNG with the Source2Viewer CLI"""
    vpk = os.path.join(game_dir, 'citadel', 'pak01_dir.vpk')
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, 'minimap.png')
        # With a --vpk_filepath matching a single file, --output is that file's path
        subprocess.run([decompiler, '-i', vpk, '--vpk_filepath', texture, '-o', png, '-d'], check=True)
        with Image.open(png) as image:
            return image.convert('RGBA')


def flatten(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """
    Draw an RGBA image onto a solid background. Blends in linear light, like image editors do, rather than on the
    raw sRGB values, which would leave the translucent map much darker
    """
    background_linear = [SRGB_TO_LINEAR[c] for c in background]
    rgba = image.convert('RGBA').tobytes()
    pixels = bytearray()
    for i in range(0, len(rgba), 4):
        a = rgba[i + 3] / 255
        pixels += bytes(_linear_to_srgb(SRGB_TO_LINEAR[c] * a + bg * (1 - a)) for c, bg in zip(rgba[i : i + 3], background_linear))
    return Image.frombytes('RGB', image.size, bytes(pixels))


def main():
    parser = argparse.ArgumentParser(description='Regenerate the Midtown base map asset from the game files')
    parser.add_argument('--game', required=True, help='Deadlock game directory, the one containing citadel/')
    parser.add_argument('--decompiler', default=os.getenv('DECOMPILER_CMD'), help='Path to the Source2Viewer CLI (default: $DECOMPILER_CMD)')
    parser.add_argument('--texture', default=MINIMAP_TEXTURE, help=f'Minimap texture inside pak01 (default: {MINIMAP_TEXTURE})')
    parser.add_argument('--out', default=OUTPUT_PATH, type=Path, help=f'Output path (default: {OUTPUT_PATH})')
    args = parser.parse_args()
    if not args.decompiler:
        parser.error('pass --decompiler or set DECOMPILER_CMD to the Source2Viewer CLI')

    image = flatten(extract_minimap(args.decompiler, args.game, args.texture), BACKGROUND)
    image.save(args.out, optimize=True)
    print(f'Wrote {image.width}x{image.height} map to {args.out}')


if __name__ == '__main__':
    main()
