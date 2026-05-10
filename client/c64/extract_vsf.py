"""Extract RAM modules from a VICE VSF snapshot file.

VSF format:
  0-18:  "VICE Snapshot File\x1a"
  19-20: major/minor version
  21-36: machine name (16 bytes, null-padded) e.g. "C64SC"

Then modules:
  0-15:  module name (16 bytes, null-padded)
  16:    major version
  17:    minor version
  18-21: total module length including this 22-byte header (little-endian uint32)
  22+:   module data (length - 22 bytes)

Each module has its own data format.
"""
import struct
import sys

def extract_vsf(path):
    with open(path, 'rb') as f:
        data = f.read()

    # Skip top header (37 bytes)
    offset = 37
    modules = []
    
    while offset < len(data) - 22:
        name_bytes = data[offset:offset+16]
        name = name_bytes.split(b'\x00')[0].decode('latin-1', errors='replace')
        major = data[offset+16]
        minor = data[offset+17]
        length = struct.unpack('<I', data[offset+18:offset+22])[0]
        
        if length < 22 or length > 1000000:
            # Probably end or corruption
            break
        
        body_start = offset + 22
        body_end = offset + length
        body_len = length - 22
        modules.append((name, major, minor, length, offset, body_start, body_end))
        print(f'Module: {name!r} v{major}.{minor} total={length} body={body_len} @ {offset}')
        
        offset = body_end
    
    return data, modules

if __name__ == '__main__':
    vsf = sys.argv[1] if len(sys.argv) > 1 else 'client/c64/vice-snapshot-ccmgs.vsf'
    data, modules = extract_vsf(vsf)
    
    # Extract interesting modules
    for name, major, minor, length, offset, body_start, body_end in modules:
        if name in ('C64MEM', 'MAINCPU'):
            body = data[body_start:body_end]
            out_path = f'client/c64/snapshot_{name.lower()}.bin'
            with open(out_path, 'wb') as f:
                f.write(body)
            print(f'  -> {out_path} ({len(body)} bytes)')
