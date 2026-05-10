"""
Simple TCP listener that captures and displays ALL bytes received.
Listens on port 25232 (where VICE connects for ACIA/IP232).
Shows hex dump of everything received, with timestamps.
"""
import socket
import time
import sys

PORT = 25232

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', PORT))
s.listen(1)
print('Listening on port {}... (waiting for VICE to connect)'.format(PORT))

conn, addr = s.accept()
print('Connected from {}'.format(addr))
conn.settimeout(0.5)  # 500ms timeout for reads

all_data = bytearray()
last_recv = time.time()

print()
print('Receiving data (will stop after 30 seconds of silence, or press Ctrl+C):')
print('=' * 60)

while True:
    try:
        chunk = conn.recv(1024)
        if not chunk:
            print('[Connection closed by remote]')
            break
        all_data.extend(chunk)
        last_recv = time.time()
        
        # Print each byte as it arrives
        for b in chunk:
            if 32 <= b < 127:
                print('  {:02X}  {}'.format(b, chr(b)))
            else:
                print('  {:02X}  (control)'.format(b))
                
    except socket.timeout:
        if time.time() - last_recv > 30.0:
            print('[30 seconds silence - stopping]')
            break

print()
print('=' * 60)
print('Total bytes received: {}'.format(len(all_data)))
print()
print('Full hex dump:')
for i in range(0, len(all_data), 16):
    chunk = all_data[i:i+16]
    hex_str = ' '.join('{:02X}'.format(b) for b in chunk)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
    print('  {:04X}: {:48s} {}'.format(i, hex_str, ascii_str))

print()
print('As text (printable only):')
text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in all_data)
print('  ' + text)

conn.close()
s.close()
