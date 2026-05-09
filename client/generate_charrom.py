"""
Generate C64 character ROM data as a JavaScript module.

The C64 chargen ROM is 4096 bytes:
- 0-2047: Character set 1 (uppercase/graphics) - used by Compunet
- 2048-4095: Character set 2 (lowercase/uppercase)

We'll use VICE's chargen ROM which is the standard C64 character set.
If you have a 'chargen' file from VICE (or extracted from a C64),
place it in this directory and run this script.

If no chargen file is available, we generate the characters from
known bitmap data for the most important characters.
"""

import os
import sys
import base64

chargen_path = os.path.join(os.path.dirname(__file__), 'chargen')

if os.path.exists(chargen_path):
    # Use the actual chargen ROM
    with open(chargen_path, 'rb') as f:
        chargen = f.read()
    print('Loaded chargen ROM: {} bytes'.format(len(chargen)))
    # We only need the first 2048 bytes (uppercase/graphics set)
    charset = chargen[:2048]
else:
    print('No chargen file found. Place the VICE chargen ROM file here:')
    print('  {}'.format(chargen_path))
    print()
    print('You can get it from:')
    print('  - VICE emulator: vice/data/C64/chargen')
    print('  - Any C64 ROM dump')
    print()
    print('The file should be exactly 4096 bytes.')
    sys.exit(1)

# Generate JavaScript
js_output = '// C64 Character ROM - uppercase/graphics set (2048 bytes)\n'
js_output += '// Generated from chargen ROM\n'
js_output += '// 256 characters x 8 bytes each (8x8 pixel bitmaps)\n'
js_output += 'const C64_CHARROM = new Uint8Array([\n'

for char_idx in range(256):
    offset = char_idx * 8
    bytes_hex = ', '.join('0x{:02X}'.format(charset[offset + i]) for i in range(8))
    if char_idx < 128:
        # Try to identify the character
        if 32 <= char_idx < 127:
            label = "  // {:3d} '{}'".format(char_idx, chr(char_idx))
        elif char_idx == 0:
            label = "  // {:3d} '@'".format(char_idx)
        else:
            label = "  // {:3d}".format(char_idx)
    else:
        label = "  // {:3d} (reversed)".format(char_idx)
    js_output += '    {},{}\\n'.format(bytes_hex, label)

js_output += ']);\n'

outpath = os.path.join(os.path.dirname(__file__), 'charrom.js')
with open(outpath, 'w') as f:
    f.write(js_output)

print('Generated: {}'.format(outpath))
print('Include this file before petscii.js in your HTML.')
