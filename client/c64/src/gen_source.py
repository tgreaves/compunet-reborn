"""
Generate ca65 source from the original ROM binary.
Outputs the entire ROM as .byte directives with address comments.
This is the starting point — sections are then replaced with mnemonics.
"""
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
rom_path = os.path.join(script_dir, 'original_rom.bin')
out_path = os.path.join(script_dir, 'compunet_full.s')

with open(rom_path, 'rb') as f:
    rom = f.read()

lines = []
lines.append('; =================================================================')
lines.append('; COMPUNET TERMINAL v1.22 — Full ROM Source')
lines.append('; =================================================================')
lines.append('; Assembler: ca65 (cc65 suite)')
lines.append('; Original: Ariadne Software Ltd, September 1984')
lines.append(';')
lines.append('; This file assembles to a byte-identical copy of the original ROM.')
lines.append('; Sections are incrementally replaced with proper mnemonics.')
lines.append('; =================================================================')
lines.append('')
lines.append('.segment "HEADER"')
lines.append('')

# Emit 16 bytes per line
for offset in range(0, len(rom), 16):
    chunk = rom[offset:offset+16]
    addr = 0x8000 + offset
    hex_bytes = ', '.join(f'${b:02X}' for b in chunk)
    # ASCII representation for comment
    ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    lines.append(f'    .byte {hex_bytes}  ; ${addr:04X} {ascii_repr}')

with open(out_path, 'w') as f:
    f.write('\n'.join(lines) + '\n')

print(f"Generated {out_path} ({len(lines)} lines)")
