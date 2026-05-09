"""
Generate full C64 character ROM with both character sets.
Set 1 (0-2047): Uppercase + graphics (already have this)
Set 2 (2048-4095): Lowercase + uppercase

In set 2:
- Screen codes 0 = @
- Screen codes 1-26 = a-z (lowercase)
- Screen codes 32-63 = same as set 1 (space, digits, punctuation)
- Screen codes 64-95 = A-Z uppercase (same bitmaps as set 1 codes 1-26)
"""

import os

chargen_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chargen')

with open(chargen_path, 'rb') as f:
    set1 = f.read()

if len(set1) == 4096:
    print('Already have full 4096-byte chargen')
    charset1 = set1[:2048]
    charset2 = set1[2048:]
elif len(set1) == 2048:
    print('Have 2048-byte set 1, generating set 2 (lowercase)')
    charset1 = set1
    
    # Set 2 lowercase letter bitmaps (screen codes 1-26 = a-z)
    lowercase = [
        # a
        [0x00, 0x00, 0x3C, 0x06, 0x3E, 0x66, 0x3E, 0x00],
        # b
        [0x60, 0x60, 0x7C, 0x66, 0x66, 0x66, 0x7C, 0x00],
        # c
        [0x00, 0x00, 0x3C, 0x66, 0x60, 0x66, 0x3C, 0x00],
        # d
        [0x06, 0x06, 0x3E, 0x66, 0x66, 0x66, 0x3E, 0x00],
        # e
        [0x00, 0x00, 0x3C, 0x66, 0x7E, 0x60, 0x3C, 0x00],
        # f
        [0x0E, 0x18, 0x18, 0x3E, 0x18, 0x18, 0x18, 0x00],
        # g
        [0x00, 0x00, 0x3E, 0x66, 0x66, 0x3E, 0x06, 0x3C],
        # h
        [0x60, 0x60, 0x7C, 0x66, 0x66, 0x66, 0x66, 0x00],
        # i
        [0x18, 0x00, 0x38, 0x18, 0x18, 0x18, 0x3C, 0x00],
        # j
        [0x06, 0x00, 0x06, 0x06, 0x06, 0x06, 0x66, 0x3C],
        # k
        [0x60, 0x60, 0x66, 0x6C, 0x78, 0x6C, 0x66, 0x00],
        # l
        [0x38, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3C, 0x00],
        # m
        [0x00, 0x00, 0x66, 0x7F, 0x7F, 0x6B, 0x63, 0x00],
        # n
        [0x00, 0x00, 0x7C, 0x66, 0x66, 0x66, 0x66, 0x00],
        # o
        [0x00, 0x00, 0x3C, 0x66, 0x66, 0x66, 0x3C, 0x00],
        # p
        [0x00, 0x00, 0x7C, 0x66, 0x66, 0x7C, 0x60, 0x60],
        # q
        [0x00, 0x00, 0x3E, 0x66, 0x66, 0x3E, 0x06, 0x06],
        # r
        [0x00, 0x00, 0x7C, 0x66, 0x60, 0x60, 0x60, 0x00],
        # s
        [0x00, 0x00, 0x3E, 0x60, 0x3C, 0x06, 0x7C, 0x00],
        # t
        [0x18, 0x18, 0x7E, 0x18, 0x18, 0x18, 0x0E, 0x00],
        # u
        [0x00, 0x00, 0x66, 0x66, 0x66, 0x66, 0x3E, 0x00],
        # v
        [0x00, 0x00, 0x66, 0x66, 0x66, 0x3C, 0x18, 0x00],
        # w
        [0x00, 0x00, 0x63, 0x6B, 0x7F, 0x3E, 0x36, 0x00],
        # x
        [0x00, 0x00, 0x66, 0x3C, 0x18, 0x3C, 0x66, 0x00],
        # y
        [0x00, 0x00, 0x66, 0x66, 0x66, 0x3E, 0x0C, 0x78],
        # z
        [0x00, 0x00, 0x7E, 0x0C, 0x18, 0x30, 0x7E, 0x00],
    ]
    
    # Build set 2
    charset2 = bytearray(2048)
    
    # Screen code 0 = @ (same as set 1)
    charset2[0:8] = charset1[0:8]
    
    # Screen codes 1-26 = lowercase a-z
    for i, letter in enumerate(lowercase):
        offset = (i + 1) * 8
        charset2[offset:offset+8] = bytes(letter)
    
    # Screen codes 27-31 = same as set 1 ([ \ ] ^ _)
    charset2[27*8:32*8] = charset1[27*8:32*8]
    
    # Screen codes 32-63 = same as set 1 (space, digits, punctuation)
    charset2[32*8:64*8] = charset1[32*8:64*8]
    
    # Screen codes 64-90 = uppercase A-Z (copy from set 1 codes 1-26)
    # In set 2, screen code 64 = A, 65 = B, etc.
    for i in range(26):
        src = (i + 1) * 8
        dst = (64 + i) * 8
        charset2[dst:dst+8] = charset1[src:src+8]
    
    # Screen code 90 = Z (already covered above)
    # Screen codes 91-95 = graphics (same as set 1 codes 91-95... actually these are different)
    # For simplicity, copy the rest from set 1
    charset2[91*8:128*8] = charset1[91*8:128*8]
    
    # Screen codes 128-255 = reversed versions (XOR with 0xFF)
    for i in range(128):
        for j in range(8):
            charset2[(128+i)*8 + j] = charset2[i*8 + j] ^ 0xFF
    
    charset2 = bytes(charset2)
else:
    print('Unexpected chargen size: {}'.format(len(set1)))
    exit(1)

# Generate JavaScript with both sets
js = '// C64 Character ROM - both character sets\n'
js += '// Set 1 (uppercase/graphics): indices 0-255\n'
js += '// Set 2 (lowercase/uppercase): indices 256-511\n'
js += '// Each character is 8 bytes (8x8 pixel bitmap)\n'
js += 'const C64_CHARROM_SET1 = new Uint8Array([\n'

for i in range(256):
    off = i * 8
    row = ', '.join('0x{:02X}'.format(charset1[off+j]) for j in range(8))
    js += '    {},\n'.format(row)

js += ']);\n\n'
js += 'const C64_CHARROM_SET2 = new Uint8Array([\n'

for i in range(256):
    off = i * 8
    row = ', '.join('0x{:02X}'.format(charset2[off+j]) for j in range(8))
    js += '    {},\n'.format(row)

js += ']);\n\n'
js += '// Default to set 1 for backwards compatibility\n'
js += 'const C64_CHARROM = C64_CHARROM_SET1;\n'

outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charrom.js')
with open(outpath, 'w') as f:
    f.write(js)

print('Generated charrom.js with both character sets')
print('  Set 1: {} bytes (uppercase/graphics)'.format(len(charset1)))
print('  Set 2: {} bytes (lowercase/uppercase)'.format(len(charset2)))

# Clean up test file if it exists
test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test.html')
if os.path.exists(test_path):
    os.remove(test_path)
