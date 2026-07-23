#!/usr/bin/env python3
"""Decruncher for CNETTTY (and supertex) — the *non-PowerPacker* Compunet suite files.

ppdecrunch.py handles the PowerPacker members of the suite (Compunet, CnetEditor,
Access!). CNETTTY uses a DIFFERENT self-decrunching wrapper: a 620-byte HUNK_CODE stub
plus a HUNK_DATA hunk holding the compressed program and a trailing HUNK_BSS that the
decompressed image is unpacked into. The stub is a backwards, marker-bit LZ decompressor
(NOT PowerPacker's 2-bit-selector bitstream).

This is a faithful 1:1 port of that stub's decompressor, verified against the relocated
disassembly of the stub (@0x1001c0-0x100268 in the flattened wrapper). Two independent
oracles confirm correctness: the backwards write pointer lands EXACTLY on the buffer start
(wp==0), and the 5900-byte result parses as a valid HUNK executable (HUNK_HEADER, 8 hunks,
223 relocs) — a single wrong bit would break both.

Stub bitstream model (all offsets from the disassembly):
  - the compressed stream is consumed from the END backwards as big-endian longwords
  - the bit buffer d0 is refilled via `move.w #$10,ccr; roxr.l #1,d0`, which sets a
    sentinel: when d0 shifts down to 0, all payload bits are spent and a refill is due
  - output is written backwards from dst_end; matches copy forward-referenced bytes
  - control structure: 1 marker bit selects match vs literal; sub-selectors pick literal
    run length (3-bit or 8-bit+8) and match length/offset-width (see decrunch()).

Params come from the stub's a5 table (`lea $1001ac(pc),a5`): comp_len (= the DATA hunk
size) and out_len (= the BSS hunk alloc). For CNETTTY: comp_len=0xf40, out_len=0x170c.

Usage:
    python ttydecrunch.py CNETTTY decrunched/CnetTty
"""
import sys, struct


def _u32(b, o):
    return struct.unpack('>I', b[o:o + 4])[0]


def parse_hunks(b):
    """Parse a HUNK executable into [{kind,data,alloc,relocs}] (same shape as flatten.py)."""
    o = 4
    while _u32(b, o) != 0:                       # resident library names
        o += 4 + _u32(b, o) * 4
    o += 4
    o += 4                                       # table_size
    first = _u32(b, o); o += 4
    last = _u32(b, o); o += 4
    decl = []
    for _ in range(first, last + 1):
        decl.append(_u32(b, o) & 0x3fffffff); o += 4
    hunks = []; idx = 0
    while o < len(b):
        t = _u32(b, o) & 0x3fffffff; o += 4
        if t in (0x3e9, 0x3ea):                  # CODE / DATA
            n = _u32(b, o); o += 4
            hunks.append({'kind': 'CODE' if t == 0x3e9 else 'DATA',
                          'data': bytearray(b[o:o + n * 4]), 'alloc': decl[idx], 'relocs': []})
            o += n * 4; idx += 1
        elif t == 0x3eb:                         # BSS
            _u32(b, o); o += 4
            hunks.append({'kind': 'BSS', 'data': bytearray(), 'alloc': decl[idx], 'relocs': []})
            idx += 1
        elif t == 0x3ec:                         # RELOC32
            while True:
                cnt = _u32(b, o); o += 4
                if cnt == 0:
                    break
                tgt = _u32(b, o); o += 4
                for _ in range(cnt):
                    hunks[-1]['relocs'].append((_u32(b, o), tgt)); o += 4
        elif t == 0x3f0:                         # SYMBOL
            while True:
                l = _u32(b, o); o += 4
                if l == 0:
                    break
                o += l * 4 + 4
        elif t == 0x3f1:                         # DEBUG
            n = _u32(b, o); o += 4; o += n * 4
        elif t == 0x3f2:                         # END
            pass
        else:
            break
    return hunks


class _Bits:
    """The stub's backwards longword bit reader (routines @100242 and @10024c)."""
    def __init__(self, comp):
        self.src = comp
        self.sp = len(comp)                      # a0, moves backward
        self.d0 = 0
        self.C = 0

    def _refill(self):                           # @100242: move.l -(a0),d0; #$10->ccr; roxr.l #1,d0
        self.sp -= 4
        self.d0 = struct.unpack('>I', self.src[self.sp:self.sp + 4])[0]
        new_c = self.d0 & 1                       # roxr brings X(=1) into bit31, bit0 -> X/C
        self.d0 = ((self.d0 >> 1) | (1 << 31)) & 0xffffffff
        self.C = new_c

    def bit(self):                               # inline `lsr.l #1,d0; bne .; bsr refill`
        c = self.d0 & 1
        self.d0 >>= 1
        if self.d0 != 0:
            self.C = c
        else:
            self._refill()
        return self.C

    def bits(self, n):                           # @10024c: read n bits MSB-first
        d2 = 0
        for _ in range(n):
            d2 = ((d2 << 1) | self.bit()) & 0xffffffff
        return d2


def decrunch(comp, out_len):
    """Faithful port of the decompressor @0x1001c0-0x100268."""
    m = _Bits(comp)
    out = bytearray(out_len)
    wp = out_len                                 # a2, write pointer, backward; dst_start=0
    # initial `move.l -(a0),d0` @1001cc (once, before the loop-back target 1001ce)
    m.sp -= 4
    m.d0 = struct.unpack('>I', comp[m.sp:m.sp + 4])[0]

    def emit_literals(count):                    # @1001ec: `count`+1 bytes, each 8 bits
        nonlocal wp
        for _ in range(count + 1):
            wp -= 1
            out[wp] = m.bits(8) & 0xff

    def emit_match(length, off):                 # @10022e: copy `length`+1 bytes from wp+off
        nonlocal wp
        for _ in range(length + 1):
            wp -= 1
            out[wp] = out[wp + off]

    while True:
        if m.bit() == 1:                         # @100208 MATCH selector
            sel = m.bits(2)
            if sel < 2:                          # @100224: short match
                emit_match(sel + 2, m.bits(9 + sel))   # len 2/3, offset 9/10 bits
            elif sel == 3:                       # @100202: long literal run
                emit_literals(m.bits(8) + 8)
            else:                                # sel==2 @100218: medium match
                length = m.bits(8)
                emit_match(length, m.bits(8))
        else:                                    # @1001d6: C==0
            if m.bit() == 1:                     # @10022e: 2-byte match, 8-bit offset
                emit_match(1, m.bits(8))
            else:                                # @1001e2: short literal run, 3-bit count
                emit_literals(m.bits(3))
        if wp <= 0:                              # @10023a: while dst_start < wp
            break
    return out, wp


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: ttydecrunch.py <infile> <outfile>")
    b = open(sys.argv[1], 'rb').read()
    hunks = parse_hunks(b)
    if len(hunks) < 3 or hunks[1]['kind'] != 'DATA':
        sys.exit("not a CNETTTY-style wrapper (expected CODE stub + DATA payload + BSS)")
    comp = bytes(hunks[1]['data'])
    out_len = hunks[2]['alloc'] * 4              # BSS alloc = decompressed size
    out, wp = decrunch(comp, out_len)
    if wp != 0:
        sys.exit(f"decrunch failed: write pointer landed at {wp}, not 0")
    inner = parse_hunks(out)                     # oracle: must parse as a HUNK exe
    print(f"comp={len(comp)} bytes -> {len(out)} bytes; inner hunks: "
          f"{[(h['kind'], len(h['data']), sum(len(r) for r in [h['relocs']])) for h in inner]}")
    open(sys.argv[2], 'wb').write(out)
    print(f"wrote {sys.argv[2]} ({len(out)} bytes)")


if __name__ == '__main__':
    main()
