"""Flatten an Amiga HUNK executable into a single pre-relocated raw image.

Each hunk is placed at a fixed base address; RELOC32 entries are applied so that
every absolute reference is correct for that layout. The result imports into any
raw 68000 (big-endian) disassembler/decompiler at BASE with no HUNK loader.

Outputs:
  <out>.bin  - the flat relocated image
  <out>.map  - hunk -> address, sizes, entry point, section kinds (JSON)
"""
import sys, struct, json

BASE = 0x00100000          # load address of hunk 0
ALIGN = 0x1000             # pad each hunk to a page so boundaries are obvious

def u32(b, o): return struct.unpack('>I', b[o:o+4])[0]

def parse(b):
    o = 4
    while u32(b, o) != 0:                       # resident lib names
        o += 4 + u32(b, o) * 4
    o += 4
    o += 4                                       # table_size
    first = u32(b, o); o += 4
    last = u32(b, o); o += 4
    decl = []
    for _ in range(first, last + 1):
        sz = u32(b, o); o += 4
        decl.append(sz & 0x3fffffff)             # longwords
    hunks = []                                    # (kind, bytes, alloc_longs)
    idx = 0
    while o < len(b):
        t = u32(b, o) & 0x3fffffff; o += 4
        if t in (0x3e9, 0x3ea):                   # CODE / DATA
            n = u32(b, o); o += 4
            data = b[o:o+n*4]; o += n*4
            hunks.append({'kind': 'CODE' if t == 0x3e9 else 'DATA',
                          'data': bytearray(data), 'alloc': decl[idx], 'relocs': []})
            idx += 1
        elif t == 0x3eb:                          # BSS
            u32(b, o); o += 4
            hunks.append({'kind': 'BSS', 'data': bytearray(),
                          'alloc': decl[idx], 'relocs': []})
            idx += 1
        elif t == 0x3ec:                          # RELOC32 (belongs to last hunk)
            while True:
                cnt = u32(b, o); o += 4
                if cnt == 0: break
                target = u32(b, o); o += 4
                for _ in range(cnt):
                    off = u32(b, o); o += 4
                    hunks[-1]['relocs'].append((off, target))
        elif t == 0x3f0:                          # SYMBOL
            while True:
                l = u32(b, o); o += 4
                if l == 0: break
                o += l*4 + 4
        elif t == 0x3f1:                          # DEBUG
            n = u32(b, o); o += 4; o += n*4
        elif t == 0x3f2:                          # END
            pass
        else:
            break
    return hunks

def main():
    b = open(sys.argv[1], 'rb').read()
    out = sys.argv[2] if len(sys.argv) > 2 else 'flat'
    hunks = parse(b)
    # assign addresses
    addr = BASE
    for h in hunks:
        h['addr'] = addr
        size = max(len(h['data']), h['alloc']*4)
        h['size'] = size
        addr += (size + ALIGN - 1) & ~(ALIGN - 1)
    total = addr - BASE
    img = bytearray(total)
    for h in hunks:
        off = h['addr'] - BASE
        img[off:off+len(h['data'])] = h['data']
    # apply relocations
    nrel = 0
    for h in hunks:
        base_off = h['addr'] - BASE
        for (roff, target) in h['relocs']:
            tgt_addr = hunks[target]['addr']
            p = base_off + roff
            val = struct.unpack('>I', img[p:p+4])[0]
            struct.pack_into('>I', img, p, (val + tgt_addr) & 0xffffffff)
            nrel += 1
    open(out + '.bin', 'wb').write(img)
    mp = {'base': BASE, 'entry': hunks[0]['addr'], 'total': total,
          'hunks': [{'i': i, 'kind': h['kind'], 'addr': h['addr'],
                     'data_len': len(h['data']), 'alloc_bytes': h['alloc']*4,
                     'nrelocs': len(h['relocs'])} for i, h in enumerate(hunks)]}
    json.dump(mp, open(out + '.map', 'w'), indent=1)
    print(f"wrote {out}.bin ({total} bytes), {len(hunks)} hunks, {nrel} relocs applied")
    print(f"BASE=0x{BASE:x} entry=0x{hunks[0]['addr']:x}")
    for i, h in enumerate(hunks[:6]):
        print(f"  hunk{i:2} {h['kind']:4} @0x{h['addr']:x} data={len(h['data'])} relocs={len(h['relocs'])}")
    print(f"  ... ({len(hunks)} total)")

if __name__ == '__main__':
    main()
