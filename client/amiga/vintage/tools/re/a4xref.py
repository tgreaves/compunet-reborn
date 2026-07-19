"""Scan CODE hunks for a4-relative memory operands and resolve them to strings
in the a4 small-data section. Prints, for each interesting string, the code
addresses that reference it (and thus the enclosing function)."""
import json, re, sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000, CS_MODE_BIG_ENDIAN

img = open('compunet_flat.bin', 'rb').read()
mp = json.load(open('compunet_flat.map'))
base = mp['base']; A4 = 0x11d000
md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)

# function boundaries from Ghidra recon (addr -> name)
funcs = []
for line in open('recon_functions.txt'):
    if line.startswith('#'): continue
    parts = line.split()
    if not parts: continue
    try: funcs.append(int(parts[0], 16))
    except ValueError: continue
funcs.sort()
def func_of(addr):
    import bisect
    i = bisect.bisect_right(funcs, addr) - 1
    return funcs[i] if i >= 0 else None

# read a NUL-terminated string at an image address
def strat(addr):
    o = addr - base
    if o < 0 or o >= len(img): return None
    e = img.find(b'\x00', o)
    s = img[o:e]
    try: t = s.decode('latin1')
    except: return None
    if len(s) >= 2 and all(32 <= c < 127 or c in (9,) for c in s): return t
    return None

disp_re = re.compile(r'(-?)(?:0x([0-9a-f]+)|\$([0-9a-f]+)|(\d+))\(a4\)')

xref = {}   # string_addr -> list of code addrs
for h in mp['hunks']:
    if h['kind'] != 'CODE': continue
    start = h['addr']; data = img[start-base:start-base+h['data_len']]
    for ins in md.disasm(data, start):
        m = disp_re.search(ins.op_str)
        if not m: continue
        sign = -1 if m.group(1) == '-' else 1
        hexv = m.group(2) or m.group(3)
        val = int(hexv, 16) if hexv else int(m.group(4))
        disp = sign * val
        tgt = (A4 + disp) & 0xffffffff
        s = strat(tgt)
        if s and len(s) >= 3 and re.search(r'[A-Za-z]{3}', s):
            xref.setdefault(tgt, []).append(ins.address)

interesting = ['cnet.device', 'cnet-configuration', 'Modem', 'Logon', 'CnetTty',
               'CnetEditor', 'No Such User', 'Invalid link', 'Invalid page',
               'download', 'Goto Page', 'Password', 'User ID', 'frame']
seen = set()
for tgt in sorted(xref):
    s = strat(tgt)
    if not any(k.lower() in s.lower() for k in interesting): continue
    callers = sorted(set(func_of(a) for a in xref[tgt] if func_of(a)))
    caller_txt = ' '.join('FUN_%08x' % c for c in callers)
    print(f'"{s[:34]:34}" @0x{tgt:x}  <- {caller_txt}')
