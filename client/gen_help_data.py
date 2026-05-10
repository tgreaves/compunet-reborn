"""Generate help_data.js containing the embedded help frame."""
import os

help_path = os.path.join(os.path.dirname(__file__), 'help.seq')
with open(help_path, 'rb') as f:
    data = f.read()

# Generate as a JavaScript array
js = '// Help frame data extracted from cnet.prg (runtime $BB0C)\n'
js += '// This is displayed when HELP is selected from the directory duckshoot\n'
js += 'const HELP_FRAME_DATA = new Uint8Array([\n'

for i in range(0, len(data), 16):
    chunk = data[i:i+16]
    js += '    ' + ', '.join('0x{:02X}'.format(b) for b in chunk) + ',\n'

js += ']);\n'

outpath = os.path.join(os.path.dirname(__file__), 'help_data.js')
with open(outpath, 'w') as f:
    f.write(js)

print('Generated help_data.js: {} bytes of frame data'.format(len(data)))
