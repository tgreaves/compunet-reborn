"""Generate build/version.inc and build/ident.inc from VERSION file.

version.inc: exactly 37 bytes: zero padding + version string.
  Fills the fixed region from $806F to $8093 (inclusive).
  Format: [padding zeros] $0D [" COMPUNET REBORN  " + version + spaces] $0D $00

ident.inc: CNET identification string with content hash in field[1].
  The hash is derived from compunet.s source — changes only when client code changes.
  Also writes server/cfg/client_version.txt for server-side verification.
"""
import os
import hashlib
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
version_file = os.path.join(script_dir, '..', '..', '..', 'VERSION')
source_file = os.path.join(script_dir, 'compunet.s')
out_file = os.path.join(script_dir, 'build', 'version.inc')
ident_file = os.path.join(script_dir, 'build', 'ident.inc')
client_version_file = os.path.join(script_dir, '..', '..', '..', 'server', 'cfg', 'client_version.txt')

TOTAL_BYTES = 37

version = open(version_file).read().strip()

# Generate a 6-char hash from the client source file
# This only changes when client code actually changes
# Override with --hash=XXXX argument for testing against a specific server version
import sys
source_hash = ''
for arg in sys.argv[1:]:
    if arg.startswith('--hash='):
        source_hash = arg.split('=', 1)[1].upper()
if not source_hash:
    source_hash = hashlib.sha256(open(source_file, 'rb').read()).hexdigest()[:6].upper()

# --- version.inc ---
label = ' COMPUNET REBORN  ' + version.upper() + ' '
string_bytes = [0x0D] + [ord(c) for c in label] + [0x0D, 0x00]
padding_needed = TOTAL_BYTES - len(string_bytes)

if padding_needed < 0:
    excess = -padding_needed
    label = label[:len(label) - excess]
    string_bytes = [0x0D] + [ord(c) for c in label] + [0x0D, 0x00]
    padding_needed = TOTAL_BYTES - len(string_bytes)

lines = []
if padding_needed > 0:
    pad_hex = ', '.join('$00' for _ in range(padding_needed))
    lines.append('    .byte %s' % pad_hex)
lines.append('L807A:')
str_hex = ', '.join('$%02X' % b for b in string_bytes)
lines.append('    .byte %s' % str_hex)

os.makedirs(os.path.dirname(out_file), exist_ok=True)
with open(out_file, 'w') as f:
    f.write('\n'.join(lines) + '\n')

# --- ident.inc ---
# CNET identification: "C CNET\r{hash6}/100\rADP\rNO\rRUN\r"
# Field[1] must be exactly 10 chars to maintain binary size.
# Use 6 chars of source hash + "/100" = 10 chars.
ident_str = 'C CNET\r' + source_hash + '/100\rADP\rNO\rRUN\r'
ident_bytes = []
for ch in ident_str:
    if ch == '\r':
        ident_bytes.append(0x0D)
    else:
        ident_bytes.append(ord(ch))

ident_lines = []
ident_lines.append('; CNET identification string (generated — source hash in field[1])')
ident_lines.append('    .byte $%02X                            ; length (%d bytes)' % (len(ident_bytes), len(ident_bytes)))
ident_hex = ', '.join('$%02X' % b for b in ident_bytes)
ident_lines.append('    .byte %s' % ident_hex)

with open(ident_file, 'w') as f:
    f.write('\n'.join(ident_lines) + '\n')

# --- client_version.txt ---
with open(client_version_file, 'w') as f:
    f.write(source_hash.lower() + '\n')

print('Generated %s: v%s (%d padding + %d string = %d bytes)' %
      (out_file, version, padding_needed, len(string_bytes), TOTAL_BYTES))
print('Generated %s: source_hash=%s (%d bytes ident)' % (ident_file, source_hash, len(ident_bytes)))
