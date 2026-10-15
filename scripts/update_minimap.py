"""
Regenerate the Midtown base map used by the game_map parser from an installed copy of Deadlock

The minimap texture lives in game/citadel/pak01_*.vpk, which deadbot does not download, so the
extracted image is committed to src/parser/parsers/game_map/assets/minimap_midtown.png.
Re-run this whenever the map changes:

    python scripts/update_minimap.py --game "C:/Program Files (x86)/Steam/steamapps/common/Deadlock/game"
"""

import argparse
import mmap
import os
import re
import struct
from pathlib import Path

from PIL import Image

MINIMAP_PREFIX = 'panorama/images/minimap/base/'
# The street map. The other families in that folder are the tunnel overlays
MINIMAP_FAMILY = 'minimap_midtown_mid'
OUTPUT_PATH = Path('src/parser/parsers/game_map/assets/minimap_midtown.png')
CANDIDATE_SIZES = (2048, 1024, 512, 256)

# Deadlock's VPKs put a 28-byte header at offset 0, followed by a flat stream of 18-byte entry
# records interleaved with NUL-terminated path strings. An empty string inherits the previous value
VPK_HEADER = struct.Struct('<7I')
VPK_ENTRY = struct.Struct('<IHHIIH')
VPK_SIGNATURE = 0x55AA1234
SELF_ARCHIVE = 0x7FFF


class Vpk:
    """Read-only view of a VPK v2 set: <name>_dir.vpk plus <name>_NNN.vpk"""

    def __init__(self, path: str):
        self._fh = open(path, 'rb')
        self._mm = mmap.mmap(self._fh.fileno(), 0, access=mmap.ACCESS_READ)
        sig, ver, dir_size, *_ = VPK_HEADER.unpack(self._mm[: VPK_HEADER.size])
        if sig != VPK_SIGNATURE or ver != 2:
            raise ValueError(f'{path} is not a v2 VPK')
        self._dir_end = VPK_HEADER.size + dir_size
        self._stem = path[: -len('_dir.vpk')]
        self._chunks = {}

        # entry offsets address the chunk files, which dwarf the directory file
        folder = os.path.dirname(path)
        prefix = os.path.basename(self._stem) + '_'
        self._max_chunk = max(
            [len(self._mm)] + [os.path.getsize(os.path.join(folder, n)) for n in os.listdir(folder) if n.startswith(prefix) and n.endswith('.vpk')]
        )

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for fh, mm in self._chunks.values():
            mm.close()
            fh.close()
        self._mm.close()
        self._fh.close()

    def _read_entry(self, pos: int):
        if pos + VPK_ENTRY.size > self._dir_end:
            return None
        _crc, preload, archive, offset, length, term = VPK_ENTRY.unpack(self._mm[pos : pos + VPK_ENTRY.size])
        if term != 0xFFFF or preload != 0 or archive > SELF_ARCHIVE:
            return None
        if length == 0 or offset + length > self._max_chunk:
            return None
        return archive, offset, length

    def entries(self):
        """Yield (path, archive, offset, length) for every file in the set"""
        mm = self._mm
        ext = folder = name = ''
        pending = []
        pos = VPK_HEADER.size
        while pos < self._dir_end:
            entry = self._read_entry(pos)
            if entry is not None:
                parts = [s for s in pending if s]
                if len(parts) >= 3:
                    ext, folder, name = parts[-3:]
                elif len(parts) == 2:
                    folder, name = parts
                elif len(parts) == 1:
                    name = parts[0]
                yield (f'{folder}/{name}.{ext}' if folder else f'{name}.{ext}', *entry)
                pending = []
                pos += VPK_ENTRY.size
                continue
            if mm[pos] == 0:
                pending.append('')
                pos += 1
                continue
            end = mm.find(b'\x00', pos, self._dir_end)
            if end < 0:
                break
            raw = mm[pos:end]
            if any(c < 0x20 or c > 0x7E for c in raw):
                break
            pending.append(raw.decode('latin-1'))
            pos = end + 1

    def read(self, archive: int, offset: int, length: int) -> bytes:
        if archive == SELF_ARCHIVE:
            return self._mm[offset : offset + length]
        if archive not in self._chunks:
            fh = open(f'{self._stem}_{archive:03d}.vpk', 'rb')
            self._chunks[archive] = (fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ))
        return self._chunks[archive][1][offset : offset + length]


def family_of(filename: str) -> str:
    """minimap_midtown_mid_psd_dd4bcbf9.vtex_c -> minimap_midtown_mid"""
    return re.sub(r'_psd(?:_[0-9a-fA-F]{8})?$', '', filename.removesuffix('.vtex_c'))


def decode_texture(data: bytes) -> Image.Image:
    """The pixel payload is the trailing W*W*4 bytes of the file, an uncompressed square RGBA8 image"""
    for size in CANDIDATE_SIZES:
        need = size * size * 4
        if len(data) >= need:
            return Image.frombytes('RGBA', (size, size), data[len(data) - need :])
    raise ValueError('no trailing square RGBA8 block found')


def extract_minimap(game_dir: str) -> Image.Image:
    """
    Several revisions of each map ship side by side. The texture compiler version
    (first u32 of every .vtex_c) identifies which is newest
    """
    newest = None
    with Vpk(os.path.join(game_dir, 'citadel', 'pak01_dir.vpk')) as vpk:
        for path, *location in vpk.entries():
            filename = path.rsplit('/', 1)[-1]
            if not path.startswith(MINIMAP_PREFIX) or not filename.endswith('.vtex_c') or family_of(filename) != MINIMAP_FAMILY:
                continue
            data = vpk.read(*location)
            (revision,) = struct.unpack_from('<I', data, 0)
            if newest is None or revision > newest[0]:
                newest = (revision, filename, data)

    if newest is None:
        raise FileNotFoundError(f'No {MINIMAP_FAMILY} texture found under {MINIMAP_PREFIX}')
    revision, filename, data = newest
    print(f'Using {filename} (revision {revision})')
    return decode_texture(data)


def main():
    parser = argparse.ArgumentParser(description='Regenerate the Midtown base map asset from the game files')
    parser.add_argument('--game', required=True, help='Deadlock game directory, the one containing citadel/')
    parser.add_argument('--out', default=OUTPUT_PATH, type=Path, help=f'Output path (default: {OUTPUT_PATH})')
    args = parser.parse_args()

    image = extract_minimap(args.game)
    image.save(args.out)
    print(f'Wrote {image.width}x{image.height} map to {args.out}')


if __name__ == '__main__':
    main()
