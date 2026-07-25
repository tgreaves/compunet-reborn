#!/usr/bin/env python3
"""Generate client/web/assets.json from the spec appendix (single source of
truth): the 16-colour palette (§A.3), the 256-glyph C64 font (§A.5), and the
built-in directory template (§A.6) rendered to a 40x24 chrome cell grid via
the server's frame renderer. Re-run after any appendix change.

    python client/web/gen_assets.py
"""
import os, re, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'server'))
import api_binding as api  # noqa: E402

APPX = os.path.join(ROOT, 'docs', 'spec', '99-appendices.md')
OUT = os.path.join(ROOT, 'client', 'web', 'assets.json')
txt = open(APPX, encoding='utf-8').read()
lines = txt.splitlines()

pal = {int(m.group(1)): '#' + m.group(2).upper()
       for m in re.finditer(r'\|\s*(\d+)\s*\|\s*[A-Za-z ]+\|\s*`?#([0-9A-Fa-f]{6})', txt)}
palette = [pal[i] for i in range(16)]

def parse_set(tag):
    i = next(k for k, l in enumerate(lines) if re.search(tag, l))
    out = {}
    for l in lines[i:i + 400]:
        m = re.match(r'\s*\$([0-9A-Fa-f]{2}):\s*((?:[0-9A-Fa-f]{2}\s*){8})', l)
        if m:
            out[int(m.group(1), 16)] = [int(x, 16) for x in m.group(2).split()]
        elif l.strip().startswith('### Set') and out:
            break
    return out
s1, s2 = parse_set(r'### Set 1'), parse_set(r'### Set 2')
font = [(s1 if g < 128 else s2)[g & 0x7F] for g in range(256)]

tb, in_a6 = [], False
for l in lines:
    if l.startswith('## §A.6'):
        in_a6 = True
    elif l.startswith('## §A.7'):
        break
    if in_a6:
        m = re.match(r'\s*\$B[0-9A-Fa-f]{3}:\s*((?:[0-9A-Fa-f]{2}\s*)+)', l)
        if m:
            tb += [int(x, 16) for x in m.group(1).split()]
template = api.frame_to_cells(bytes(tb))

# HELP frame (§A.8) — a client asset like the template; the server never sends it
help_path = os.path.join(ROOT, 'server', 'cfg', 'help.pet')
help_frame = api.frame_to_cells(open(help_path, 'rb').read()) if os.path.exists(help_path) else None

json.dump({'palette': palette, 'font': font, 'template': template, 'help': help_frame},
          open(OUT, 'w'), separators=(',', ':'))
print('wrote %s (palette %d, font %d, template %d cells, help %s)' %
      (OUT, len(palette), len(font), len(template['cells']),
       'yes' if help_frame else 'MISSING'))
