"""
Generate the Compunet welcome/personal information screen as a SEQ file.
Based on the screenshot: purple background, compunet logo, user info box, postbox.
"""

import struct

# PETSCII constants
RET = 0x0D
RVS_ON = 0x12
RVS_OFF = 0x92
UPPER = 0x8E
LOWER = 0x0E

# Colours
BLACK = 0x90
WHITE = 0x05
RED = 0x1C
CYAN = 0x9F
PURPLE = 0x9C
GREEN = 0x1E
BLUE = 0x1F
YELLOW = 0x9E
ORANGE = 0x81
BROWN = 0x95
LRED = 0x96
DGREY = 0x97
MGREY = 0x98
LGREEN = 0x99
LBLUE = 0x9A
LGREY = 0x9B

def spaces(n):
    """Encode N spaces."""
    if n <= 1:
        return bytes([0x20] * n)
    return bytes([0x06, n])

def rle(char, count):
    """RLE encode: repeat char count times."""
    return bytes([0x07, char, count])

def text(s):
    """Convert ASCII string to PETSCII uppercase ($41-$5A range)."""
    result = bytearray()
    for ch in s:
        code = ord(ch)
        if 65 <= code <= 90:      # A-Z -> PETSCII $41-$5A
            result.append(code)
        elif 97 <= code <= 122:   # a-z -> uppercase $41-$5A
            result.append(code - 32)
        elif 32 <= code <= 63:
            result.append(code)
        else:
            result.append(code & 0x7F)
    return bytes(result)

# Build the welcome frame
frame = bytearray()

# Header: $00, border colour | $F0, background colour | $F0
frame.append(0x00)       # frame start
frame.append(0xF4 )      # border = purple (4)
frame.append(0xF4)       # background = purple (4)
frame.append(UPPER)      # uppercase/graphics charset

# === TOP SECTION: Compunet logo area ===

# Blue horizontal line across top
frame.append(LBLUE)
frame.append(RVS_ON)
frame.extend(rle(0x20, 40))  # reversed spaces = solid light blue bar
frame.append(RVS_OFF)
frame.append(RET)

# "compunet" logo in red - simplified block letter version
# Row 1 of logo
frame.append(RED)
frame.append(RVS_ON)
frame.extend(spaces(2))
frame.extend(text(' COMPUNET '))
frame.extend(spaces(2))
frame.append(RVS_OFF)
frame.extend(spaces(14))
frame.append(RET)

# Row 2 - larger text effect
frame.append(RED)
frame.append(RVS_ON)
frame.extend(spaces(1))
frame.extend(text('  COMPUNET  '))
frame.extend(spaces(1))
frame.append(RVS_OFF)
frame.extend(spaces(10))
frame.append(WHITE)
frame.append(RVS_ON)
frame.extend(text(' GOLD '))
frame.append(RVS_OFF)
frame.append(RET)

# Blue line below logo
frame.append(LBLUE)
frame.append(RVS_ON)
frame.extend(rle(0x20, 40))
frame.append(RVS_OFF)
frame.append(RET)

# Blank line (purple bg)
frame.append(RET)

# === BOTTOM SECTION: User info box ===

# White/light grey box background
frame.append(LGREY)
frame.append(RVS_ON)
frame.extend(rle(0x20, 40))  # top border of box
frame.append(RVS_OFF)
frame.append(RET)

# Box content lines (light grey reversed background with blue text)
def box_line(content_bytes, width=38):
    """Create a line inside the info box."""
    line = bytearray()
    line.append(LGREY)
    line.append(RVS_ON)
    line.append(0x20)  # left margin
    line.append(RVS_OFF)
    line.extend(content_bytes)
    # Pad to width
    remaining = width - len(content_bytes)
    if remaining > 0:
        line.extend(spaces(remaining))
    line.append(LGREY)
    line.append(RVS_ON)
    line.append(0x20)  # right margin
    line.append(RVS_OFF)
    line.append(RET)
    return bytes(line)

# Empty line in box
frame.extend(box_line(b''))

# USER : {username}
content = bytearray()
content.append(BLUE)
content.extend(text('USER : '))
content.append(WHITE)
content.extend(text('TEST USER'))
frame.extend(box_line(bytes(content)))

# Empty line
frame.extend(box_line(b''))

# LAST LOGGED ON : {date}
content = bytearray()
content.append(BLUE)
content.extend(text('LAST LOGGED ON : '))
content.append(BROWN)
content.extend(text('09-MAY-26'))
frame.extend(box_line(bytes(content)))

# : {time}
content = bytearray()
content.append(BLUE)
content.extend(spaces(17))
content.extend(text(': '))
content.append(BROWN)
content.extend(text('21:00'))
frame.extend(box_line(bytes(content)))

# Empty line
frame.extend(box_line(b''))

# PAGES/NEAR DEATH : 0/0
content = bytearray()
content.append(BLUE)
content.extend(text('PAGES/NEAR DEATH : '))
content.append(BROWN)
content.extend(text('0/0'))
frame.extend(box_line(bytes(content)))

# FREE STORAGE LEFT : 2000
content = bytearray()
content.append(BLUE)
content.extend(text('FREE STORAGE LEFT : '))
content.append(BROWN)
content.extend(text('2000'))
frame.extend(box_line(bytes(content)))

# NEXT QUARTER : date
content = bytearray()
content.append(BLUE)
content.extend(text('NEXT QUARTER     : '))
content.append(BROWN)
content.extend(text('01-AUG'))
frame.extend(box_line(bytes(content)))

# Empty line in box
frame.extend(box_line(b''))

# Bottom border of box
frame.append(LGREY)
frame.append(RVS_ON)
frame.extend(rle(0x20, 40))
frame.append(RVS_OFF)
frame.append(RET)

# End of frame
frame.append(0x00)

# Write the SEQ file
outpath = r'c:\Users\trist\src\compunet-reborn\server\content\pages\welcome.seq'
with open(outpath, 'wb') as f:
    f.write(bytes(frame))

print('Generated welcome.seq: {} bytes'.format(len(frame)))

# Also write to the test area
import shutil
shutil.copy(outpath, r'c:\Users\trist\src\compunet-reborn\historical\seq\welcome.seq')
print('Copied to historical/seq/welcome.seq')
