"""
Combine ROM binary and terminal binary into a single PRG file.

Layout in memory:
  $8000-$9FFF: ROM code (8192 bytes)
  $9FF0-$BE02: Terminal code (7699 bytes, overlaps last 16 bytes of ROM)

The PRG loads at $8000. The terminal code overwrites $9FF0-$9FFF
(which is the phone number area — writable RAM in the original system).

Usage: python3 make_prg.py rom.bin terminal.bin output.prg
"""
import sys
import os

if len(sys.argv) != 4:
    print("Usage: python3 make_prg.py rom.bin terminal.bin output.prg")
    sys.exit(1)

rom_path = sys.argv[1]
term_path = sys.argv[2]
output_path = sys.argv[3]

with open(rom_path, 'rb') as f:
    rom = bytearray(f.read())

with open(term_path, 'rb') as f:
    terminal = bytearray(f.read())

assert len(rom) == 8192, f"ROM must be 8192 bytes, got {len(rom)}"
assert len(terminal) == 7699, f"Terminal must be 7699 bytes, got {len(terminal)}"

# Build the combined memory image from $8000 to $BE02
# Total size: $BE03 - $8000 = $3E03 = 15875 bytes
LOAD_ADDR = 0x8000
END_ADDR = 0xBE03
total_size = END_ADDR - LOAD_ADDR

image = bytearray(total_size)

# Place ROM at $8000 (offset 0)
image[0:8192] = rom

# Place terminal at $9FF0 (offset $1FF0)
# This overwrites the last 16 bytes of ROM area — that's intentional
term_offset = 0x9FF0 - LOAD_ADDR
image[term_offset:term_offset + len(terminal)] = terminal

# Write PRG file (2-byte load address + data)
with open(output_path, 'wb') as f:
    f.write(bytes([LOAD_ADDR & 0xFF, (LOAD_ADDR >> 8) & 0xFF]))
    f.write(image)

print(f"Created {output_path} ({len(image) + 2} bytes, load at ${LOAD_ADDR:04X}, SYS {0x8160})")
