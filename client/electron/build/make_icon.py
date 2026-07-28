#!/usr/bin/env python3
"""Generate the Windows application icon from the C64 font.

    python client/electron/build/make_icon.py

⚠ There is no source artwork, deliberately — the icon is DERIVED, the same way
`3dprint/logo3d.py` derives the printable logo from the PETSCII header frame.
The letterform is the genuine Commodore 64 `C` (screen code 3) taken from
`client/web/assets.json`, which the spec carries as data (§A.5). Redraw the font
and the icon follows; there is no second copy to keep in sync.

Why a `C` and not the wordmark: the Compunet logo is a 40-column banner whose
letters are formed by the NEGATIVE SPACE between red wedges. It is beautiful and
completely illegible below about 200 pixels, and an app icon has to work at 16.

Why red on light grey: it is what the service actually looked like. The header
frame draws its wordmark in red (palette 2) on light grey (palette 15) between
two blue rules, so these are the logo's own two colours rather than a pairing
chosen for contrast.

⚠ It is not the highest-contrast option, and that was a deliberate trade. White
on red reads more sharply at 16x16, and red on light grey can sit quietly
against a pale taskbar. Authenticity won: this is a recreation, and the icon
should look like Compunet rather than like a well-behaved modern app icon.
(Red on blue was rejected outright — it goes muddy at small sizes — and a white
ground disappears entirely on a white background.)

Layout is a 10x10 logical grid — one cell of margin around the 8x8 glyph — and
every size is scaled from that by nearest neighbour, so each icon is exact
pixels with no blurring. 16 and 32 divide evenly; the rest are close enough that
the stepping is invisible at those sizes.
"""
import json
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ASSETS = os.path.join(ROOT, 'client', 'web', 'assets.json')
OUT = os.path.join(HERE, 'icon.ico')

GLYPH = 3          # C64 screen code for 'C'
INK = 2            # Compunet red — the wordmark's own ink
GROUND = 15        # light grey — the header frame's own background
SIZES = [256, 128, 64, 48, 32, 24, 16]


def logical_grid(font):
    """The 10x10 colour grid: a margin cell, the 8x8 glyph, a margin cell."""
    px = [[GROUND] * 10 for _ in range(10)]
    bitmap = font[GLYPH]
    for y in range(8):
        for x in range(8):
            if (bitmap[y] >> (7 - x)) & 1:
                px[y + 1][x + 1] = INK
    return px


def png_bytes(size, grid, palette):
    """A square RGBA PNG scaled from the 10x10 grid by nearest neighbour."""
    rows = bytearray()
    for yy in range(size):
        rows.append(0)                                  # filter: none
        sy = yy * 10 // size
        for xx in range(size):
            r, g, b = palette[grid[sy][xx * 10 // size]]
            rows += bytes((r, g, b, 255))

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data)))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(bytes(rows), 9))
            + chunk(b'IEND', b''))


def main():
    assets = json.load(open(ASSETS, encoding='utf-8'))
    palette = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in assets['palette']]
    grid = logical_grid(assets['font'])

    images = [(s, png_bytes(s, grid, palette)) for s in SIZES]

    # ICONDIR, then one 16-byte ICONDIRENTRY per image, then the PNG data.
    # A width/height byte of 0 means 256 — the field is only one byte wide.
    header = struct.pack('<HHH', 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, blob = b'', b''
    for size, data in images:
        dim = 0 if size == 256 else size
        entries += struct.pack('<BBBBHHII', dim, dim, 0, 0, 1, 32, len(data), offset)
        blob += data
        offset += len(data)

    with open(OUT, 'wb') as f:
        f.write(header + entries + blob)
    print('wrote %s (%d bytes, sizes: %s)'
          % (OUT, os.path.getsize(OUT), ', '.join(str(s) for s in SIZES)))


if __name__ == '__main__':
    main()
