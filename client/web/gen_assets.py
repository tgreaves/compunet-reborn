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
# ⚠ EVERY .pet here is now the ORIGINAL frame, lifted whole out of the vintage
# binaries — header and all — so all four are fed in RAW. Nothing is prepended.
#
#   help.pet         cnet.prg $BB0C   00 F3 F3 0E   cyan border, cyan bg
#   editor-help.pet  ROM      $9589   00 F6 FC 0E   blue border, mid-grey bg
#   courier.pet      cnet.prg $BDD6   00 F4 F1 8E
#   courier-send.pet cnet.prg $BD77   00 F4 F1 8E
#
# The first two used to be hand-retyped bodies with a header invented here, and
# both inventions were wrong: help got a purple border on a light grey page
# where the original is cyan on cyan, editor-help the same. The retyped bodies
# were no better — help.pet had 13 colour switches against the original's 3,
# cyan where the original uses brown, "AT CONNECT" for "At Connect", and 113
# extra bytes. Reconstructions look right until someone holds a photograph of
# the real screen up next to them. Do not reconstruct these; extract them.
help_frame = (api.frame_to_cells(open(help_path, 'rb').read())
              if os.path.exists(help_path) else None)

# Editor help frame (§A.9) — a DIFFERENT asset from §A.8, shown by the editor's
# own HELP command (§8.4.1). Blue and brown ink, exactly as §A.8 uses.
ehelp_path = os.path.join(ROOT, 'server', 'cfg', 'editor-help.pet')
editor_help = (api.frame_to_cells(open(ehelp_path, 'rb').read())
               if os.path.exists(ehelp_path) else None)

# COURIER frame (§A.10) — the mail screen the C64 embeds at $BDD6. Unlike §A.8
# and §A.9 this one DOES carry its own 4-byte header, so it is fed in raw.
courier_path = os.path.join(ROOT, 'server', 'cfg', 'courier.pet')
courier = (api.frame_to_cells(open(courier_path, 'rb').read())
           if os.path.exists(courier_path) else None)

# COURIER SEND frame (§A.11) — a DIFFERENT, larger frame from the ID one: it
# carries FROM / DATE / TIME / SUBJECT / TO labels above the five slots.
send_path = os.path.join(ROOT, 'server', 'cfg', 'courier-send.pet')
courier_send = (api.frame_to_cells(open(send_path, 'rb').read())
                if os.path.exists(send_path) else None)

json.dump({'palette': palette, 'font': font, 'template': template, 'help': help_frame,
           'editorHelp': editor_help, 'courier': courier, 'courierSend': courier_send},
          open(OUT, 'w'), separators=(',', ':'))
print('wrote %s (palette %d, font %d, template %d cells, help %s, editorHelp %s, '
      'courier %s, courierSend %s)' %
      (OUT, len(palette), len(font), len(template['cells']),
       'yes' if help_frame else 'MISSING', 'yes' if editor_help else 'MISSING',
       'yes' if courier else 'MISSING', 'yes' if courier_send else 'MISSING'))
