#!/usr/bin/env python3
"""
coverage_census.py — authoritative application-function census for the Amiga
Compunet client reconstruction.

A function is APPLICATION logic (as opposed to SAS/C runtime or OS-call glue)
iff it does one of two observable things:
  1. references a string literal  (has a  /* strings: ... */  annotation), or
  2. calls the transport          (serial_write / serial_io_c / send_dat_packet).
Everything else has no strings and no sends -> runtime/library/OS-thunk glue.

The UNION of those two sets is therefore the complete application surface that a
faithful reconstruction must cover. Re-run this against recon_annotated.c any time
to verify coverage; diff its output against client/amiga/src/ modules.

Usage:  python3 coverage_census.py [recon_annotated.c]
"""
import re, sys

path = sys.argv[1] if len(sys.argv) > 1 else 'recon_annotated.c'
lines = open(path).read().split('\n')

hdrs = []
for i, l in enumerate(lines):
    m = re.match(r'/\* ===== (\S+) @ (\w+) \(size (\d+)', l)
    if m:
        hdrs.append((i, m.group(1), m.group(2), int(m.group(3))))

def enclosing(lineno):
    cur = None
    for (ln, name, addr, sz) in hdrs:
        if ln <= lineno: cur = (name, addr, sz)
        else: break
    return cur

defs = {a: (n, s) for (i, n, a, s) in hdrs if not n.startswith('thunk_') and s > 6}

# (1) string-anchored functions
strset = set()
for i, l in enumerate(lines):
    m = re.match(r'/\* ===== (\S+) @ (\w+) ', l)
    if m and i + 1 < len(lines) and lines[i + 1].startswith('/* strings:'):
        if not m.group(1).startswith('thunk_'):
            strset.add(m.group(2))

# (2) transport-calling functions (resolve thunk aliases back to real addr)
send = set()
for i, l in enumerate(lines):
    if re.search(r'(serial_write|serial_io_c|send_dat_packet)\(', l) \
            and 'undefined' not in l and '=====' not in l:
        if not re.search(r'0x[0-9a-f]|,\d', l):
            continue
        fn = enclosing(i)
        if not fn:
            continue
        n, a, s = fn
        if n in ('serial_write', 'serial_io_c', 'send_dat_packet'):
            continue
        mm = re.match(r'thunk_FUN_(\w+)', n)
        if mm: a = mm.group(1)
        send.add(a)

allset = strset | send

def strings_of(addr):
    for i, l in enumerate(lines):
        if re.match(r'/\* ===== (\S+) @ ' + addr + r' ', l) \
                and i + 1 < len(lines) and lines[i + 1].startswith('/* strings:'):
            return lines[i + 1].replace('/* strings: ', '').replace(' */', '')
    return ''

print(f"APPLICATION-FUNCTION CENSUS ({path}): {len(allset)} functions")
print(f"  string-anchored={len(strset)}  transport-calling={len(send)}  union={len(allset)}\n")
for a in sorted(allset):
    n, s = defs.get(a, ('(alias/small)', '?'))
    print(f"  {a}  {n:<22} sz={s:<4} {strings_of(a)[:70]}")
