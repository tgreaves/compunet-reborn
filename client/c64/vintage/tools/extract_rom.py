"""
Extract the raw 8K ROM binary from the original CRT file.
This is our reference — the assembled source must match this exactly.
"""
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
crt_path = os.path.join(script_dir, '..', 'Compunet Terminal.crt')
out_path = os.path.join(script_dir, 'original_rom.bin')

with open(crt_path, 'rb') as f:
    crt = f.read()

# CRT header is 64 bytes, CHIP header is 16 bytes, then 8192 bytes of ROM
rom = crt[64 + 16: 64 + 16 + 8192]
assert len(rom) == 8192, f"Expected 8192 bytes, got {len(rom)}"

with open(out_path, 'wb') as f:
    f.write(rom)

print(f"Extracted {len(rom)} bytes to {out_path}")
