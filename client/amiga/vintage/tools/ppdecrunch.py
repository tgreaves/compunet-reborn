#!/usr/bin/env python3
"""PowerPacker decruncher for the vintage Amiga Compunet suite.

The Compunet suite files on the 17-Bit "Comms Disc III" ADF are PowerPacker
compressed. Two forms occur:

  * PP20 *data* files ("PP20" magic at offset 0) — e.g. Registration, access!me.
  * PowerPacker *self-decrunching executables* — a 524-byte HUNK_CODE decruncher
    stub plus a HUNK_DATA hunk holding the compressed original executable.
    e.g. Compunet, CnetEditor, Access!.

Both use the same PowerPacker bitstream (Stuart Caie's ppdepack algorithm):
bytes are consumed from the END backwards; the buffer is filled LSB-first, but
each field is extracted MSB-first (the first bit read becomes the value's high
bit). A 2-bit selector indexes a 4-entry "efficiency" table of offset bit-widths.

NOTE: two suite files (CNETTTY, supertex) use a DIFFERENT, non-PowerPacker
cruncher (620-byte stub, marker-bit LZ) and are NOT handled here — they need
68k emulation of their stub. See docs/amiga-client.md.

Usage:
    python ppdecrunch.py <infile> [outfile]      # auto-detect data vs exe
"""
import sys, struct


# ---- core PowerPacker bitstream ------------------------------------------
def _pp_decrunch(comp, offset_lens, out_len, skip):
    out = bytearray(out_len)
    src_pos = len(comp)
    bitbuf = 0
    bitcnt = 0

    def get_bits(n):
        nonlocal bitbuf, bitcnt, src_pos
        while bitcnt < n:
            src_pos -= 1
            bitbuf |= comp[src_pos] << bitcnt
            bitcnt += 8
        val = 0
        for _ in range(n):
            val = (val << 1) | (bitbuf & 1)
            bitbuf >>= 1
        bitcnt -= n
        return val

    get_bits(skip)
    dst = out_len
    while dst > 0:
        if get_bits(1) == 0:                       # literal run precedes match
            cnt = 1
            while True:
                t = get_bits(2)
                cnt += t
                if t != 3:
                    break
            while cnt > 0:
                dst -= 1
                out[dst] = get_bits(8)
                cnt -= 1
            if dst <= 0:
                break
        x = get_bits(2)                            # offset-width selector
        off_bits = offset_lens[x]
        todo = x + 2
        if x == 3:
            if get_bits(1) == 0:
                off_bits = 7
            offset = get_bits(off_bits)
            while True:
                t = get_bits(3)
                todo += t
                if t != 7:
                    break
        else:
            offset = get_bits(off_bits)
        for _ in range(todo):
            out[dst - 1] = out[dst + offset]
            dst -= 1
    return bytes(out)


def decrunch_pp20(data):
    """Decrunch a standalone PP20 data file."""
    assert data[:4] == b'PP20', 'not a PP20 file'
    offset_lens = list(data[4:8])
    skip = data[-1]
    out_len = (data[-4] << 16) | (data[-3] << 8) | data[-2]
    return _pp_decrunch(data[8:-4], offset_lens, out_len, skip)


# ---- HUNK executable handling --------------------------------------------
def parse_hunks(b):
    def u32(o):
        return struct.unpack('>I', b[o:o + 4])[0]
    o = 4
    while u32(o) != 0:                              # resident library names
        o += 4 + u32(o) * 4
    o += 4
    o += 4                                          # table_size
    first = u32(o); o += 4
    last = u32(o); o += 4
    for _ in range(first, last + 1):
        o += 4
    hunks = []
    while o < len(b):
        t = u32(o) & 0x3fffffff; o += 4
        if t in (0x3e9, 0x3ea):                     # CODE / DATA
            n = u32(o); o += 4
            hunks.append(('CODE' if t == 0x3e9 else 'DATA', b[o:o + n * 4])); o += n * 4
        elif t == 0x3eb:                            # BSS
            u32(o); o += 4; hunks.append(('BSS', b''))
        elif t == 0x3ec:                            # RELOC32
            while True:
                c = u32(o); o += 4
                if c == 0:
                    break
                o += 4 + c * 4
        elif t == 0x3f0:                            # SYMBOL
            while True:
                l = u32(o); o += 4
                if l == 0:
                    break
                o += l * 4 + 4
        elif t == 0x3f1:                            # DEBUG
            n = u32(o); o += 4; o += n * 4
        elif t == 0x3f2:                            # END
            pass
        else:
            break
    return hunks


def decrunch_pp_exe(b):
    """Decrunch a PowerPacker self-decrunching HUNK executable (524-byte stub).

    The compressed original executable lives in the single HUNK_DATA hunk; its
    trailing longword encodes (decrunched_length << 8) | skip_bits. The stub's
    4-byte efficiency table is located via its `lea disp(pc),a5` instruction.
    """
    hunks = parse_hunks(b)
    code = hunks[0][1]
    comp = next(h[1] for h in hunks if h[0] == 'DATA')
    declen = (comp[-4] << 16) | (comp[-3] << 8) | comp[-2]
    skip = comp[-1]
    # candidate efficiency-table locations: every `lea disp(pc),a5` (0x4bfa)
    targets = []
    for i in range(0, len(code) - 3, 2):
        if code[i] == 0x4b and code[i + 1] == 0xfa:
            disp = struct.unpack('>h', code[i + 2:i + 4])[0]
            tgt = i + 2 + disp
            if 0 <= tgt <= len(code) - 4:
                targets.append(tgt)
    targets.append(0x204)                           # common fixed location
    for tgt in targets:
        eff = list(code[tgt:tgt + 4])
        if not all(1 <= e <= 24 for e in eff):
            continue
        try:
            out = _pp_decrunch(comp[:-4], eff, declen, skip)
        except Exception:
            continue
        if out[:4] == b'\x00\x00\x03\xf3':          # valid HUNK_HEADER
            return out
    raise RuntimeError('could not locate a working efficiency table')


def decrunch_auto(b):
    if b[:4] == b'PP20':
        return decrunch_pp20(b)
    if b[:4] == b'\x00\x00\x03\xf3':
        return decrunch_pp_exe(b)
    raise ValueError('unrecognised file (not PP20 and not a HUNK executable)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    data = open(sys.argv[1], 'rb').read()
    out = decrunch_auto(data)
    kind = 'HUNK exe' if out[:4] == b'\x00\x00\x03\xf3' else 'data'
    print(f'decrunched {len(sys.argv[1])} -> {len(out)} bytes ({kind})')
    if len(sys.argv) > 2:
        open(sys.argv[2], 'wb').write(out)
        print('wrote', sys.argv[2])
