"""
Combine ROM, terminal, and ACIA driver binaries into a single PRG file.

Layout in memory:
  $8000-$9FFF: ROM code (8192 bytes)
  $9FF0-$BE02: Terminal code (7699 bytes, overlaps last 16 bytes of ROM)
  $BE03+:      ACIA driver (variable size)

Usage: python3 make_prg.py rom.bin terminal.bin acia.bin output.prg
"""
import sys

if len(sys.argv) != 5:
    print("Usage: python3 make_prg.py rom.bin terminal.bin acia.bin output.prg")
    sys.exit(1)

rom_path, term_path, acia_path, output_path = sys.argv[1:5]

with open(rom_path, 'rb') as f:
    rom = f.read()
with open(term_path, 'rb') as f:
    terminal = f.read()
with open(acia_path, 'rb') as f:
    acia = f.read()

assert len(rom) == 8192, f"ROM must be 8192 bytes, got {len(rom)}"
assert len(terminal) == 7699, f"Terminal must be 7699 bytes, got {len(terminal)}"

# Build memory image from $8000 to end of ACIA driver
LOAD_ADDR = 0x8000
TERM_ADDR = 0x9FF0
ACIA_ADDR = 0xBE03

end_addr = ACIA_ADDR + len(acia)
total_size = end_addr - LOAD_ADDR

image = bytearray(total_size)

# Place ROM at $8000
image[0:8192] = rom

# Place terminal at $9FF0 (overwrites last 16 bytes of ROM — intentional)
term_offset = TERM_ADDR - LOAD_ADDR
image[term_offset:term_offset + len(terminal)] = terminal

# Place ACIA driver at $BE03
acia_offset = ACIA_ADDR - LOAD_ADDR
image[acia_offset:acia_offset + len(acia)] = acia

# Write PRG file
with open(output_path, 'wb') as f:
    f.write(bytes([LOAD_ADDR & 0xFF, (LOAD_ADDR >> 8) & 0xFF]))
    f.write(image)

print(f"Created {output_path} ({len(image) + 2} bytes, ${LOAD_ADDR:04X}-${end_addr-1:04X}, SYS 33184)")
print(f"  ROM: ${LOAD_ADDR:04X}-$9FFF ({len(rom)} bytes)")
print(f"  Terminal: ${TERM_ADDR:04X}-${TERM_ADDR+len(terminal)-1:04X} ({len(terminal)} bytes)")
print(f"  ACIA: ${ACIA_ADDR:04X}-${end_addr-1:04X} ({len(acia)} bytes)")
