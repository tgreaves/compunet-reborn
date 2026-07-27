#!/usr/bin/env python3
"""Generate a 3D-printable Compunet logo (3MF, multi-colour + STL fallback).

The logo is not an image in this repository — it is a PETSCII frame, so this
renders it exactly as a client would (§5/§6: glyphs from the appendix font,
colours from the appendix palette) and extrudes the resulting pixels. Change
the spec's font or the header frame and the print follows.

Writes TWO variants side by side in one 3MF — colours inlaid flush with the
plate, and colours standing proud of it — as separate objects, so the user
deletes the one they do not want. Parts within a variant are one object, so a
slicer treats them as parts to assign filaments to rather than as overlapping
models. See README.md for the slicer traps this format hides.

    python 3dprint/logo3d.py [--width MM] [--thickness MM] [--only flush|raised]
"""
import argparse
import json
import os
import struct
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'server'))

# --- geometry defaults (millimetres) ---------------------------------------
PLATE_H = 15.0     # total plate thickness — thick enough to stand on its edge
INK_H = 0.8        # FLUSH: depth the colour is inlaid — 4 layers at 0.2. Shallow
                   # is fine here; the colour reads because it is a colour.
RELIEF_H = 2.5     # RAISED: how far the colour stands proud — 12 layers. Needs to
                   # be deeper than the inlay: relief reads by SHADOW, and 0.8 mm
                   # casts almost none at this size.
MARGIN = 6.0       # plate border around the artwork
BACKPLATE_COLOUR = 15   # palette index for the plate (light grey, the frame's own bg)


def render_pixels(seq_path, rows):
    """Render a PETSCII header frame to [(x, y, colour_index)] ink pixels."""
    import compunet_server as srv
    import api_binding as api
    api._bind_server(srv)
    assets = json.load(open(os.path.join(ROOT, 'client', 'web', 'assets.json')))
    font, palette = assets['font'], assets['palette']

    raw = open(seq_path, 'rb').read()
    # Part-1 headers are body-only; supply the 4-byte header (§A.6 note).
    frame = api.frame_to_cells(bytes([0x00, 0xF4, 0xFF, 0x8E]) + raw)

    COLS = 40
    W, H = COLS * 8, rows * 8
    px = {}
    for r in range(rows):
        for c in range(COLS):
            cell = frame['cells'][r * COLS + c]
            bmp = font[cell['g']]
            for y in range(8):
                bits = bmp[y]
                for x in range(8):
                    on = (bits >> (7 - x)) & 1
                    if cell['rv']:
                        on ^= 1
                    if on:
                        px[(c * 8 + x, r * 8 + y)] = cell['fg']
    return px, W, H, palette


def merge_rects(cells, W, H):
    """Greedy merge of a pixel set into axis-aligned rectangles.

    Without this every pixel becomes 12 triangles; the logo is ~7000 pixels,
    which is 84k triangles of mostly co-planar faces. Merging drops it by
    an order of magnitude and slices far faster.
    """
    used = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        x = 0
        while x < W:
            if (x, y) in cells and not used[y][x]:
                x2 = x
                while x2 + 1 < W and (x2 + 1, y) in cells and not used[y][x2 + 1]:
                    x2 += 1
                y2 = y
                while y2 + 1 < H and all((xx, y2 + 1) in cells and not used[y2 + 1][xx]
                                         for xx in range(x, x2 + 1)):
                    y2 += 1
                for yy in range(y, y2 + 1):
                    for xx in range(x, x2 + 1):
                        used[yy][xx] = True
                out.append((x, y, x2 - x + 1, y2 - y + 1))
                x = x2 + 1
            else:
                x += 1
    return out


def box(x0, y0, z0, dx, dy, dz):
    """A closed box as (vertices, triangles) with outward-facing normals."""
    v = [(x0, y0, z0), (x0 + dx, y0, z0), (x0 + dx, y0 + dy, z0), (x0, y0 + dy, z0),
         (x0, y0, z0 + dz), (x0 + dx, y0, z0 + dz), (x0 + dx, y0 + dy, z0 + dz), (x0, y0 + dy, z0 + dz)]
    t = [(0, 2, 1), (0, 3, 2),          # bottom
         (4, 5, 6), (4, 6, 7),          # top
         (0, 1, 5), (0, 5, 4),          # front
         (1, 2, 6), (1, 6, 5),          # right
         (2, 3, 7), (2, 7, 6),          # back
         (3, 0, 4), (3, 4, 7)]          # left
    return v, t


def mesh_from_rects(rects, scale, H, z0, dz):
    """Build one mesh from a list of pixel rectangles."""
    verts, tris = [], []
    for (x, y, w, h) in rects:
        # image y grows downward; flip so the logo reads correctly on the plate
        v, t = box(x * scale, (H - y - h) * scale, z0, w * scale, h * scale, dz)
        base = len(verts)
        verts.extend(v)
        tris.extend((a + base, b + base, c + base) for (a, b, c) in t)
    return verts, tris


def write_stl(path, meshes):
    """Binary STL — everything merged, single colour (a fallback/preview)."""
    tri_total = sum(len(t) for _, t in meshes)
    with open(path, 'wb') as f:
        f.write(b'Compunet logo - generated from the PETSCII header frame'.ljust(80, b' '))
        f.write(struct.pack('<I', tri_total))
        for verts, tris in meshes:
            for (a, b, c) in tris:
                f.write(struct.pack('<fff', 0.0, 0.0, 0.0))       # normal (slicers recompute)
                for idx in (a, b, c):
                    f.write(struct.pack('<fff', *verts[idx]))
                f.write(struct.pack('<H', 0))


def write_3mf(path, models, palette):
    """3MF carrying real per-part colour, in the form slicers actually read.

    ⚠ The 3MF core `<basematerials>` element is NOT how PrusaSlicer-lineage
    slicers (Bambu Studio, Orca, PrusaSlicer) assign filaments — they ignore it
    and the model loads in a single colour. Those slicers use ONE object whose
    mesh is divided into *volumes* by TRIANGLE RANGE, with the extruder number
    per volume in a sidecar config. So this writes:

      3D/3dmodel.model                 one object, all triangles, each also
                                       tagged pid/p1 for core-spec readers
      Metadata/Slic3r_PE_model.config  volume ranges + extruder (PrusaSlicer)
      Metadata/model_settings.config   the same, Bambu/Orca spelling

    Belt and braces: a slicer that honours core materials colours it from the
    palette, and one that honours the config assigns filaments per part. Both
    are written because they are cheap and are read by different tools.

    `parts` is [(name, colour_index, verts, tris)].
    """
    def esc(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # --- one mesh per model, remembering each part's triangle span within it
    meshes = []
    for (mname, parts) in models:
        verts, tris, spans = [], [], []
        for (name, colour, pv, pt) in parts:
            base = len(verts)
            first = len(tris)
            verts.extend(pv)
            tris.extend(((a + base, b + base, c + base) for (a, b, c) in pt))
            spans.append((name, colour, first, len(tris) - 1))
        meshes.append((mname, verts, tris, spans))
    all_spans = [s for (_m, _v, _t, sp) in meshes for s in sp]

    # ⚠ Colour goes in a MATERIALS-EXTENSION <colorgroup>, not <basematerials>.
    # Bambu Studio rejects a non-Bambu 3MF's part/extruder config outright
    # ("load geometry data and color data only") — but it does load *colour*,
    # and a colorgroup is what the format calls colour. basematerials is a
    # material definition, and gets dropped with the rest of the config.
    # ⚠ Extruders are assigned per COLOUR, not per part. Several parts can share
    # one colour — the flush build has two grey parts (the slab and the top
    # layer that the colours drop into) — and giving each its own extruder would
    # ask for a four-filament print of a three-colour model.
    order = []
    for (_n, colour, _f, _l) in all_spans:
        if colour not in order:
            order.append(colour)
    slot = {c: i for i, c in enumerate(order)}

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="en-US"',
           ' xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"',
           ' xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">',
           '<resources>',
           '<m:colorgroup id="1">']
    for colour in order:
        xml.append('<m:color color="#%sFF"/>' % palette[colour].lstrip('#').upper())
    xml.append('</m:colorgroup>')
    # Each model is its own object and its own build item, so the two variants
    # arrive as two selectable models on the plate — delete the one you do not
    # want. (One object with both inside would be inseparable.)
    for oid, (mname, verts, tris, spans) in enumerate(meshes, start=2):
        xml.append('<object id="%d" type="model" pid="1" pindex="0" name="%s"><mesh><vertices>'
                   % (oid, esc(mname)))
        xml.extend('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % v for v in verts)
        xml.append('</vertices><triangles>')
        tri_material = {}
        for (_n, colour, first, last) in spans:
            for t in range(first, last + 1):
                tri_material[t] = slot[colour]
        for i, t in enumerate(tris):
            xml.append('<triangle v1="%d" v2="%d" v3="%d" pid="1" p1="%d"/>'
                       % (t[0], t[1], t[2], tri_material[i]))
        xml.append('</triangles></mesh></object>')
    xml.append('</resources><build>')
    xml.extend('<item objectid="%d"/>' % oid for oid in range(2, 2 + len(meshes)))
    xml.append('</build></model>')
    model = '\n'.join(xml)

    # --- sidecar config: volumes by triangle range, one extruder each
    def volumes(type_attr):
        out = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>']
        for oid, (mname, _v, _t, spans) in enumerate(meshes, start=2):
            out.append('<object id="%d">' % oid)
            out.append('<metadata type="object" key="name" value="%s"/>' % esc(mname))
            for (name, colour, first, last) in spans:
                out.append('<volume firstid="%d" lastid="%d">' % (first, last))
                out.append('<metadata type="%s" key="name" value="%s"/>' % (type_attr, esc(name)))
                out.append('<metadata type="%s" key="extruder" value="%d"/>'
                           % (type_attr, slot[colour] + 1))
                out.append('<metadata type="%s" key="volume_type" value="ModelPart"/>' % type_attr)
                out.append('</volume>')
            out.append('</object>')
        out.append('</config>')
        return '\n'.join(out)

    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
          '<Default Extension="config" ContentType="application/xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rel0" Target="/3D/3dmodel.model" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '</Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', rels)
        z.writestr('3D/3dmodel.model', model)
        z.writestr('Metadata/Slic3r_PE_model.config', volumes('volume'))
        z.writestr('Metadata/model_settings.config', volumes('part'))
    return meshes, order


def build_variant(style, px, W, H, scale, T, palette, ink_h=None):
    """Build the parts for one variant. style is 'flush', 'raised' or 'bare'."""
    parts = []
    INK = ink_h if ink_h is not None else (RELIEF_H if style != 'flush' else INK_H)
    if style == 'bare':
        ink_z = 0.0
    elif style == 'raised':
        # Colours stand proud on a full-thickness slab.
        m = MARGIN
        v, t = box(-m, -m, 0.0, W * scale + 2 * m, H * scale + 2 * m, T)
        parts.append(('plate', BACKPLATE_COLOUR, v, t))
        ink_z = T
    else:
        # FLUSH: the top face is one continuous plane. The plate is a slab up to
        # T-INK_H, plus a top layer that is the artwork's NEGATIVE — every pixel
        # that is not ink — so the colours drop into the holes it leaves rather
        # than sitting on top of it.
        mp = max(1, int(round(MARGIN / scale)))          # margin in pixels, so the
        PW, PH = W + 2 * mp, H + 2 * mp                  # two layers align exactly
        v, t = box(-mp * scale, -mp * scale, 0.0, PW * scale, PH * scale, T - INK)
        parts.append(('plate', BACKPLATE_COLOUR, v, t))
        ink_shifted = {(x + mp, y + mp) for (x, y) in px}
        negative = {(x, y) for x in range(PW) for y in range(PH)} - ink_shifted
        nrects = merge_rects(negative, PW, PH)
        nv, nt = mesh_from_rects(nrects, scale, PH, T - INK, INK)
        nv = [(x - mp * scale, y - mp * scale, z) for (x, y, z) in nv]
        parts.append(('plate-top', BACKPLATE_COLOUR, nv, nt))
        ink_z = T - INK

    for colour in sorted({c for c in px.values()}):
        cells = {q for q, c in px.items() if c == colour}
        rects = merge_rects(cells, W, H)
        verts, tris = mesh_from_rects(rects, scale, H, ink_z, INK)
        parts.append(('ink-%d' % colour, colour, verts, tris))
    return parts


def translate(parts, dx, dy):
    return [(n, c, [(x + dx, y + dy, z) for (x, y, z) in v], t) for (n, c, v, t) in parts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--width', type=float, default=200.0, help='plaque width in mm (default 200)')
    ap.add_argument('--rows', type=int, default=6, help='character rows of the frame to use')
    ap.add_argument('--seq', default=os.path.join(ROOT, 'server', 'data', 'content', 'root', 'header.seq'))
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument('--thickness', type=float, default=PLATE_H,
                    help='total plate thickness in mm (default %.1f)' % PLATE_H)
    ap.add_argument('--only', choices=['flush', 'raised', 'bare'],
                    help='write just one variant instead of both')
    ap.add_argument('--gap', type=float, default=12.0, help='gap between the two variants in mm')
    ap.add_argument('--relief', type=float, default=RELIEF_H,
                    help='how far the raised variant stands proud, mm (default %.1f)' % RELIEF_H)
    ap.add_argument('--inlay', type=float, default=INK_H,
                    help='how deep the flush variant is inlaid, mm (default %.1f)' % INK_H)
    args = ap.parse_args()

    px, W, H, palette = render_pixels(args.seq, args.rows)
    if not px:
        sys.exit('no ink pixels — wrong frame or row count?')

    scale = args.width / W
    T = args.thickness
    os.makedirs(args.out, exist_ok=True)

    styles = [args.only] if args.only else ['flush', 'raised']
    plate_h = H * scale + 2 * MARGIN

    models, dy = [], 0.0
    for style in styles:
        parts = build_variant(style, px, W, H, scale, T, palette,
                              ink_h=args.inlay if style == 'flush' else args.relief)
        # Variants sit side by side on the plate so both are visible and either
        # can be deleted; they are separate objects, not one merged lump.
        models.append(('Compunet logo (%s)' % style, translate(parts, 0.0, dy)))
        dy += plate_h + args.gap
        tri = sum(len(t) for (_n, _c, _v, t) in parts)
        print('  %-6s %d parts, %5d triangles' % (style, len(parts), tri))

    three = os.path.join(args.out, 'compunet-logo.3mf')
    meshes, order = write_3mf(three, models, palette)

    # Per-part STLs of the FIRST variant — the fallback route if a slicer
    # refuses our part/extruder config (see README).
    partdir = os.path.join(args.out, 'parts')
    os.makedirs(partdir, exist_ok=True)
    for (name, _colour, v, t) in models[0][1]:
        write_stl(os.path.join(partdir, 'compunet-logo-%s.stl' % name), [(v, t)])

    stl = os.path.join(args.out, 'compunet-logo.stl')
    write_stl(stl, [(v, t) for (_m, parts) in models for (_n, _c, v, t) in parts])

    print()
    print('%d filament(s):' % len(order))
    for i, colour in enumerate(order):
        print('  extruder %d  %s' % (i + 1, palette[colour]))
    print()
    print('artwork %dx%d px -> %.1f x %.1f mm  (%.3f mm/pixel)'
          % (W, H, args.width, H * scale, scale))
    print('plate %.1f x %.1f mm, %.1f mm thick' % (args.width + 2 * MARGIN, plate_h, T))
    print('variants: %s  (total footprint %.1f x %.1f mm)'
          % (', '.join(styles), args.width + 2 * MARGIN, dy - args.gap))
    print('wrote %s' % three)
    print('wrote %s' % stl)


if __name__ == '__main__':
    main()
