"""Verify the combined PRG against original ROM and terminal code."""
import os

script_dir = os.path.dirname(os.path.abspath(__file__))

rom_bin = os.path.join(script_dir, 'build', 'rom.bin')
term_bin = os.path.join(script_dir, 'build', 'terminal.bin')
orig_rom = os.path.join(script_dir, 'original_rom.bin')
orig_term = os.path.join(script_dir, '..', 'cnet.prg')

with open(rom_bin, 'rb') as f:
    rom = f.read()
with open(orig_rom, 'rb') as f:
    original = f.read()

if rom == original:
    print("✓ ROM: BYTE-IDENTICAL to original")
else:
    diffs = sum(1 for a, b in zip(rom, original) if a != b)
    print(f"✗ ROM: {diffs} bytes differ (modified)")

with open(term_bin, 'rb') as f:
    term = f.read()
with open(orig_term, 'rb') as f:
    orig_t = f.read()[2:]  # strip PRG header

if term == orig_t:
    print("✓ TERMINAL: BYTE-IDENTICAL to original")
else:
    diffs = sum(1 for a, b in zip(term, orig_t) if a != b)
    print(f"✗ TERMINAL: {diffs} bytes differ (modified)")
