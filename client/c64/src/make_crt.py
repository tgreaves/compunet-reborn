"""
Convert a raw 8K ROM binary to VICE CRT format.
Usage: python3 make_crt.py input.bin output.crt
"""

import sys
import struct

if len(sys.argv) != 3:
    print("Usage: python3 make_crt.py input.bin output.crt")
    sys.exit(1)

input_bin = sys.argv[1]
output_crt = sys.argv[2]

with open(input_bin, 'rb') as f:
    rom_data = f.read()

assert len(rom_data) == 8192, f"ROM must be exactly 8192 bytes, got {len(rom_data)}"

# CRT file header (64 bytes)
crt_header = bytearray(64)
crt_header[0:16] = b'C64 CARTRIDGE   '  # Signature
struct.pack_into('>I', crt_header, 16, 64)  # Header length
struct.pack_into('>H', crt_header, 20, 0x0100)  # Version 1.0
struct.pack_into('>H', crt_header, 22, 0)  # Hardware type: generic
crt_header[24] = 0  # EXROM line: 0 (active)
crt_header[25] = 1  # GAME line: 1 (inactive) → 8K mode
crt_header[32:64] = (b'COMPUNET REBORN\x00' + b'\x00' * 16)[:32]  # Name

# CHIP packet header (16 bytes)
chip_header = bytearray(16)
chip_header[0:4] = b'CHIP'
struct.pack_into('>I', chip_header, 4, 16 + 8192)  # Total packet length
struct.pack_into('>H', chip_header, 8, 0)  # Chip type: ROM
struct.pack_into('>H', chip_header, 10, 0)  # Bank number: 0
struct.pack_into('>H', chip_header, 12, 0x8000)  # Load address
struct.pack_into('>H', chip_header, 14, 0x2000)  # ROM size: 8K

with open(output_crt, 'wb') as f:
    f.write(crt_header)
    f.write(chip_header)
    f.write(rom_data)

print(f"Created {output_crt} ({len(rom_data)} bytes ROM)")
