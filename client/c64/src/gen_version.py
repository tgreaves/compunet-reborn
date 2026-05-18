"""Generate build/version.inc from the VERSION file for ca65 assembly.

Produces exactly 37 bytes: zero padding + version string.
This fills the fixed region from $806F to $8093 (inclusive).
Format: [padding zeros] $0D [" COMPUNET REBORN  " + version + spaces] $0D $00
"""
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
version_file = os.path.join(script_dir, '..', '..', '..', 'VERSION')
out_file = os.path.join(script_dir, 'build', 'version.inc')

TOTAL_BYTES = 37

version = open(version_file).read().strip()
label = ' COMPUNET REBORN  ' + version.upper() + ' '

# Version string bytes: $0D + label + $0D + $00
string_bytes = [0x0D] + [ord(c) for c in label] + [0x0D, 0x00]
padding_needed = TOTAL_BYTES - len(string_bytes)

if padding_needed < 0:
    # Truncate label to fit
    excess = -padding_needed
    label = label[:len(label) - excess]
    string_bytes = [0x0D] + [ord(c) for c in label] + [0x0D, 0x00]
    padding_needed = TOTAL_BYTES - len(string_bytes)

# Generate assembly
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

print('Generated %s: v%s (%d padding + %d string = %d bytes)' %
      (out_file, version, padding_needed, len(string_bytes), TOTAL_BYTES))
