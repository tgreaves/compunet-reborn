#!/usr/bin/env python3
"""Generate a self-running PRG with BASIC stub + relocator.

Creates a PRG that loads at $0801 with:
  - BASIC line: 10 SYS <relocator_addr>
  - Machine language relocator: copies code to $8000 and JMP to entry
  - The actual ROM+ACIA code (trimmed)

Usage: gen_sfx.py <input.bin> <output.prg> <entry_addr_decimal>
"""
import sys
import struct

bin_path = sys.argv[1]
out_path = sys.argv[2]
entry_addr = int(sys.argv[3])

# Read and trim the binary (strip trailing zeros, CODE+ACIA only)
rom_data = open(bin_path, 'rb').read()[:0x2000].rstrip(b'\x00')
rom_size = len(rom_data)
end_page = 0x80 + (rom_size + 255) // 256

# Build relocator (copies rom_data from source to $8000, then JMP entry)
# Uses ZP $FB/$FC as source ptr, $FD/$FE as dest ptr
relocator = bytearray([
    0xA9, 0x00,       #  0: LDA #<src_lo>  (patched below)
    0x85, 0xFB,       #  2: STA $FB
    0xA9, 0x00,       #  4: LDA #<src_hi>  (patched below)
    0x85, 0xFC,       #  6: STA $FC
    0xA9, 0x00,       #  8: LDA #$00
    0x85, 0xFD,       # 10: STA $FD
    0xA9, 0x80,       # 12: LDA #$80
    0x85, 0xFE,       # 14: STA $FE
    0xA0, 0x00,       # 16: LDY #$00
    0xB1, 0xFB,       # 18: LDA ($FB),Y    <- inner loop start
    0x91, 0xFD,       # 20: STA ($FD),Y
    0xC8,             # 22: INY
    0xD0, 0xF9,       # 23: BNE -7 (-> offset 18)
    0xE6, 0xFC,       # 25: INC $FC
    0xE6, 0xFE,       # 27: INC $FE
    0xA5, 0xFE,       # 29: LDA $FE
    0xC9, end_page,   # 31: CMP #end_page
    0xD0, 0xEF,       # 33: BNE -17 (-> offset 18)
    0x4C,             # 35: JMP
    entry_addr & 0xFF,
    (entry_addr >> 8) & 0xFF,
])

# BASIC stub at $0801
basic_start = 0x0801

# Calculate relocator address (after BASIC line + end marker)
# BASIC line: [next_ptr 2] [line_num 2] [SYS $9E] [digits] [null $00]
# Then end marker: [0x00 0x00]
# Try with 5 digits first
for num_digits in range(4, 6):
    # next_ptr + line_num + SYS + digits + null = 2+2+1+num_digits+1
    basic_line_size = 2 + 2 + 1 + num_digits + 1
    end_marker_size = 2
    relocator_addr = basic_start + basic_line_size + end_marker_size
    if len(str(relocator_addr)) == num_digits:
        break

# Build BASIC line
addr_str = str(relocator_addr).encode('ascii')
next_ptr = basic_start + basic_line_size
basic_line = struct.pack('<H', next_ptr)  # next line pointer
basic_line += struct.pack('<H', 10)       # line number 10
basic_line += b'\x9e'                     # SYS token
basic_line += addr_str                    # address as ASCII
basic_line += b'\x00'                     # end of line
end_marker = b'\x00\x00'

# Patch source address into relocator
src_addr = basic_start + basic_line_size + end_marker_size + len(relocator)
relocator[1] = src_addr & 0xFF
relocator[5] = (src_addr >> 8) & 0xFF

# Verify
assert relocator_addr == basic_start + len(basic_line) + len(end_marker)
assert src_addr == relocator_addr + len(relocator)

# Build final PRG
prg = bytearray()
prg.extend(struct.pack('<H', basic_start))  # Load address ($0801)
prg.extend(basic_line)
prg.extend(end_marker)
prg.extend(relocator)
prg.extend(rom_data)

open(out_path, 'wb').write(prg)
