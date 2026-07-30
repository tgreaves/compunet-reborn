"""Render a directory header frame to a PNG, for the website's upload page.

Someone uploading a header is working blind otherwise: the file is raw PETSCII
made in another tool, and the only feedback without this is "accepted" or a list
of reasons. This draws what the C64 will actually draw.

⚠ It renders from the SAME data the clients use, deliberately. The 16-colour
palette (§A.3) and the 256 glyph bitmaps (§A.5) are normative parts of the
specification, and `client/web/assets.json` is generated from those appendix
tables by `client/web/gen_assets.py`. Reproducing the font here — or
approximating it with a web font — would create a second source of truth that
could disagree with every real client about what a header looks like.

Neither container has `docs/` in it, so the appendix cannot be read at runtime;
`assets.json` is the copy that ships (server/Dockerfile puts it at `web/`).

No new dependency: the PNG is written with `zlib` and `struct`, which is a few
lines for an image this size and avoids adding Pillow to the server for one
preview.
"""

import json
import os
import struct
import zlib

#: Glyphs are 8x8 in the C64 character set (§A.5).
GLYPH_W = GLYPH_H = 8

#: The header region is rows 0-5 (§7.7) — the only rows a header may draw on,
#: so the only rows worth previewing.
PREVIEW_ROWS = 6
PREVIEW_COLS = 40

#: Drawn at 2x so the preview is legible on a modern display without relying on
#: the browser honouring `image-rendering: pixelated`. Flat 8-colour output, so
#: doubling costs almost nothing once compressed.
SCALE = 2

_assets = None


def _asset_candidates(server_dir, web_client_dir):
    """Where assets.json might be, most authoritative first."""
    seen, out = set(), []
    for path in (
            # What the container has: server/Dockerfile copies it to /app/web.
            os.path.join(web_client_dir, 'assets.json') if web_client_dir else None,
            os.path.join(server_dir, 'web', 'assets.json'),
            # A source checkout, where the client is not staged under server/.
            os.path.join(server_dir, '..', 'client', 'web', 'assets.json'),
    ):
        if path:
            real = os.path.normpath(path)
            if real not in seen:
                seen.add(real)
                out.append(real)
    return out


def load_assets(server_dir, web_client_dir=None):
    """Palette and font from assets.json, or None if it cannot be found.

    Cached: the file is generated at build time and cannot change under a running
    server, unlike the content tree.
    """
    global _assets
    if _assets is not None:
        return _assets
    for path in _asset_candidates(server_dir, web_client_dir):
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            palette = [_hex_to_rgb(c) for c in data['palette']]
            font = data['font']
            if len(palette) == 16 and len(font) == 256:
                _assets = {'palette': palette, 'font': font}
                return _assets
        except (ValueError, KeyError, OSError):
            continue
    return None


def _hex_to_rgb(value):
    value = value.lstrip('#')
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def cells_to_png(cells, assets, rows=PREVIEW_ROWS, cols=PREVIEW_COLS,
                 scale=SCALE):
    """Render a `frame_to_cells` grid's top `rows` rows to PNG bytes.

    Each cell is {g, fg, bg, rv} — glyph index, palette indices, reverse flag —
    exactly as Binding B delivers it, so this preview and the modern client are
    drawing from one description of the screen.
    """
    palette, font = assets['palette'], assets['font']
    width, height = cols * GLYPH_W * scale, rows * GLYPH_H * scale

    raw = bytearray()
    for row in range(rows):
        # Build one glyph-row of pixels, then repeat it `scale` times rather
        # than recomputing it — the vertical scale is pure duplication.
        for y in range(GLYPH_H):
            line = bytearray()
            for col in range(cols):
                cell = cells[row * cols + col]
                bits = font[cell['g'] & 0xFF][y]
                fg = palette[cell['fg'] & 0x0F]
                bg = palette[cell['bg'] & 0x0F]
                if cell.get('rv'):
                    fg, bg = bg, fg
                for x in range(GLYPH_W):
                    colour = fg if bits & (0x80 >> x) else bg
                    line.extend(bytes(colour) * scale)
            for _ in range(scale):
                # Filter byte 0 (None) per scanline — the images are tiny and
                # flat, so a smarter filter buys nothing.
                raw.append(0)
                raw.extend(line)

    return _png(width, height, bytes(raw))


def _png(width, height, raw):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))
