"""Extract the help frame from cnet.prg and save as a SEQ file."""

with open(r'c:\Users\trist\src\compunet-reborn\historical\cnet.prg', 'rb') as f:
    data = f.read()[2:]  # skip PRG load address

# Help frame is at runtime $BB0C = offset $1B1C
offset = 0x1B1C

# Find the end of the frame (terminated by $00)
end = offset
while end < len(data) and data[end] != 0x00:
    end += 1
    # Safety: the frame header starts with $00, so skip the first byte
    if end == offset + 1:
        continue
    # Look for $00 that's not the header
    if end > offset + 3 and data[end] == 0x00:
        break

# Actually the frame starts WITH $00 as the header byte
# So we need to find the SECOND $00 which terminates it
pos = offset + 1  # skip the initial $00
while pos < len(data):
    if data[pos] == 0x00:
        break
    pos += 1

frame_data = data[offset:pos+1]  # include the terminating $00
print('Help frame: {} bytes (offset ${:04X} to ${:04X})'.format(len(frame_data), offset, offset+len(frame_data)))
print('Header: {:02X} {:02X} {:02X}'.format(frame_data[0], frame_data[1], frame_data[2]))

# Save as SEQ
outpath = r'c:\Users\trist\src\compunet-reborn\server\content\pages\help.seq'
with open(outpath, 'wb') as f:
    f.write(frame_data)
print('Saved to: {}'.format(outpath))

# Also show the decoded text for verification
print('\nDecoded content:')
i = 3  # skip header
line = ''
while i < len(frame_data) - 1:
    b = frame_data[i]
    if b == 0x0D:
        print('  ' + line)
        line = ''
    elif b == 0x06:
        # space run
        if i + 1 < len(frame_data) - 1:
            count = frame_data[i+1]
            if count < 0x20:
                line += ' ' * count
                i += 1
            else:
                line += ' '
        else:
            line += ' '
    elif b == 0x07:
        # RLE
        if i + 2 < len(frame_data) - 1:
            char = frame_data[i+1]
            count = frame_data[i+2]
            line += chr(char) * count if 32 <= char < 127 else '.' * count
            i += 2
    elif 0x41 <= b <= 0x5A:
        line += chr(b + 32)  # lowercase
    elif 0xC1 <= b <= 0xDA:
        line += chr(b - 0x80)  # uppercase
    elif 32 <= b < 127:
        line += chr(b)
    elif b == 0x0E or b == 0x8E:
        pass  # charset switch
    elif b in (0x05, 0x1C, 0x1E, 0x1F, 0x90, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9E, 0x9F, 0x81, 0x12, 0x92):
        pass  # colour/control codes
    else:
        line += '.'
    i += 1
if line:
    print('  ' + line)
