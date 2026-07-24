"""Build a naming-candidates report for the Compunet Amiga client.

For each function that references strings (via a4xref, which catches more than
Ghidra), print: address, current name, the strings it uses, and its resolved OS
calls (from lvo_callsites via recon.c). This is the raw material for assigning
sensible names in symbols.json — evidence in one place, no guessing.

Usage: python3 name_candidates.py   (uses recon.c, recon_functions.txt, a4xref)
"""
import json, re, subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))

# function ranges from recon_functions.txt: addr -> (name, size)
funcs = []
for line in open(os.path.join(HERE, 'recon_functions.txt')):
    if line.startswith('#'):
        continue
    p = line.split('  ')
    parts = line.split()
    if len(parts) >= 3:
        try:
            addr = int(parts[0]); name = parts[2]; size = int(parts[1])
            funcs.append([addr, name, size])
        except ValueError:
            pass
funcs.sort()

def fn_for(a):
    best = None
    for f in funcs:
        if f[0] <= a:
            best = f
        else:
            break
    return best

# a4xref: string -> [code addrs]. Re-run it in-process would need its globals; just
# call it and parse its stdout ("str" @0xADDR <- FUN_xxxx).
out = subprocess.run([os.path.join(HERE, '.venv/bin/python'),
                      os.path.join(HERE, 'a4xref.py')],
                     capture_output=True, text=True).stdout
str_by_fn = {}
for line in out.splitlines():
    m = re.match(r'"(.*?)"\s*@0x[0-9a-f]+\s*<-\s*(FUN_[0-9a-f]+)', line)
    if m:
        s = m.group(1).strip(); fnname = m.group(2)
        str_by_fn.setdefault(fnname, set()).add(s)

# OS calls per function: parse recon.c headers + the /* = Lib.Func */ comments in
# recon_annotated.c
calls_by_fn = {}
cur = None
for line in open(os.path.join(HERE, 'recon_annotated.c'), encoding='latin-1'):
    h = re.match(r'/\* ===== (\S+) @', line)
    if h:
        cur = h.group(1); continue
    c = re.search(r'/\* = (\w+\.\w+)\(\) \*/', line)
    if c and cur:
        calls_by_fn.setdefault(cur, []).append(c.group(1))

# Report: only functions that have strings or a notable call set, still unnamed.
named = set()
symbols = json.load(open(os.path.join(HERE, 'symbols.json')))
named_addrs = {int(a, 16) for a in symbols['functions']}

rows = []
for fnname, strs in sorted(str_by_fn.items()):
    addr = int(fnname.split('_')[1], 16)
    already = addr in named_addrs
    calls = calls_by_fn.get(fnname, [])
    rows.append((fnname, already, strs, calls))

for fnname, already, strs, calls in rows:
    flag = '(named)' if already else ''
    print(f'{fnname} {flag}')
    print(f'  strings: {" | ".join(sorted(strs))}')
    if calls:
        # de-dup preserving a compact summary
        from collections import Counter
        cc = Counter(calls)
        print(f'  oscalls: {", ".join(f"{k}x{v}" if v>1 else k for k,v in cc.items())}')
    print()
