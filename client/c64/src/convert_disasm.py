"""
Convert modem_bootstrap.asm (annotated disassembly) to ca65 source.

The disassembly has lines like:
    20 84 FF      JSR $FF84 ; KERNAL_IOINIT
    .byte 4C A0 81 4C 55 83 ...  ; $8100 L..LU.

This converts them to ca65 syntax:
    JSR $FF84               ; KERNAL_IOINIT
    .byte $4C, $A0, $81, $4C, $55, $83, ...

Labels are preserved. Comments are preserved.
"""

import re
import sys

def convert_line(line):
    """Convert one line of disassembly to ca65 syntax."""
    
    # Empty lines
    if not line.strip():
        return line
    
    # Pure comment lines (starting with ;)
    if line.strip().startswith(';'):
        return line
    
    # Label lines (no leading whitespace, ends with :)
    if not line.startswith(' ') and not line.startswith('\t') and ':' in line.split(';')[0]:
        return line
    
    # .byte lines: ".byte XX XX XX ... ; comment"
    m = re.match(r'\s+\.byte\s+([0-9A-Fa-f ]+)\s*;?(.*)', line)
    if m:
        hex_bytes = m.group(1).strip().split()
        comment = m.group(2).strip()
        # Convert to ca65 .byte with $XX format
        byte_str = ', '.join(f'${b}' for b in hex_bytes)
        if comment:
            return f'    .byte {byte_str}    ; {comment}'
        else:
            return f'    .byte {byte_str}'
    
    # Instruction lines: "    XX XX XX      MNEMONIC OPERAND ; comment"
    # Format: leading whitespace, hex bytes, then mnemonic
    m = re.match(r'\s+([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)\s{2,}(\w{3})\s*(.*)', line)
    if m:
        hex_part = m.group(1)
        mnemonic = m.group(2)
        rest = m.group(3).strip()
        
        # Split rest into operand and comment
        if ';' in rest:
            operand, comment = rest.split(';', 1)
            operand = operand.strip()
            comment = comment.strip()
        else:
            operand = rest
            comment = ''
        
        # Build the ca65 instruction line
        if operand:
            instr = f'    {mnemonic} {operand}'
        else:
            instr = f'    {mnemonic}'
        
        if comment:
            # Pad to column 40 for comment alignment
            instr = instr.ljust(40) + f'; {comment}'
        
        return instr
    
    # If nothing matched, return as-is (with a warning comment)
    return line


def convert_file(input_path, output_path):
    """Convert entire disassembly file."""
    
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    output = []
    output.append('; =================================================================')
    output.append('; COMPUNET REBORN — Full ROM source (converted from disassembly)')
    output.append('; =================================================================')
    output.append('; Assembler: ca65 (cc65 suite)')
    output.append('; Original: Compunet Terminal v1.22, Ariadne Software Ltd, 1984')
    output.append('; =================================================================')
    output.append('')
    output.append('.segment "HEADER"')
    output.append('')
    
    in_code_segment = False
    
    for line in lines:
        line = line.rstrip('\n')
        converted = convert_line(line)
        output.append(converted)
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(output))
    
    print(f"Converted {len(lines)} lines → {output_path}")


if __name__ == '__main__':
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, '..', '..', '..', 'modem_bootstrap.asm')
    output_path = os.path.join(script_dir, 'compunet_full.s')
    convert_file(input_path, output_path)
