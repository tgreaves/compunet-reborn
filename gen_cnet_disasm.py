"""
Generate annotated disassembly of cnet.prg at its runtime address.

The code runs at $9FF0+ (confirmed by cross-referencing internal addresses).
File loads at $0801, so runtime_addr = file_addr + $97EF.
Or equivalently: payload offset + $9FF0 = runtime address.
"""

filepath = r'c:\Users\trist\src\compunet-reborn\historical\cnet.prg'
with open(filepath, 'rb') as f:
    data = f.read()

payload = data[2:]  # skip PRG load address
RUNTIME_BASE = 0x9FF0
# The payload maps directly: payload[0] = $9FF0, payload[1] = $9FF1, etc.

OPCODES = {
    0x00: ('BRK', 'IMP', 1), 0x01: ('ORA', 'IZX', 2), 0x05: ('ORA', 'ZP', 2),
    0x06: ('ASL', 'ZP', 2), 0x08: ('PHP', 'IMP', 1), 0x09: ('ORA', 'IMM', 2),
    0x0A: ('ASL', 'ACC', 1), 0x0D: ('ORA', 'ABS', 3), 0x0E: ('ASL', 'ABS', 3),
    0x10: ('BPL', 'REL', 2), 0x11: ('ORA', 'IZY', 2), 0x15: ('ORA', 'ZPX', 2),
    0x16: ('ASL', 'ZPX', 2), 0x18: ('CLC', 'IMP', 1), 0x19: ('ORA', 'ABY', 3),
    0x1D: ('ORA', 'ABX', 3), 0x1E: ('ASL', 'ABX', 3),
    0x20: ('JSR', 'ABS', 3), 0x21: ('AND', 'IZX', 2), 0x24: ('BIT', 'ZP', 2),
    0x25: ('AND', 'ZP', 2), 0x26: ('ROL', 'ZP', 2), 0x28: ('PLP', 'IMP', 1),
    0x29: ('AND', 'IMM', 2), 0x2A: ('ROL', 'ACC', 1), 0x2C: ('BIT', 'ABS', 3),
    0x2D: ('AND', 'ABS', 3), 0x2E: ('ROL', 'ABS', 3),
    0x30: ('BMI', 'REL', 2), 0x31: ('AND', 'IZY', 2), 0x35: ('AND', 'ZPX', 2),
    0x36: ('ROL', 'ZPX', 2), 0x38: ('SEC', 'IMP', 1), 0x39: ('AND', 'ABY', 3),
    0x3D: ('AND', 'ABX', 3), 0x3E: ('ROL', 'ABX', 3),
    0x40: ('RTI', 'IMP', 1), 0x41: ('EOR', 'IZX', 2), 0x45: ('EOR', 'ZP', 2),
    0x46: ('LSR', 'ZP', 2), 0x48: ('PHA', 'IMP', 1), 0x49: ('EOR', 'IMM', 2),
    0x4A: ('LSR', 'ACC', 1), 0x4C: ('JMP', 'ABS', 3), 0x4D: ('EOR', 'ABS', 3),
    0x4E: ('LSR', 'ABS', 3),
    0x50: ('BVC', 'REL', 2), 0x51: ('EOR', 'IZY', 2), 0x55: ('EOR', 'ZPX', 2),
    0x56: ('LSR', 'ZPX', 2), 0x58: ('CLI', 'IMP', 1), 0x59: ('EOR', 'ABY', 3),
    0x5D: ('EOR', 'ABX', 3), 0x5E: ('LSR', 'ABX', 3),
    0x60: ('RTS', 'IMP', 1), 0x61: ('ADC', 'IZX', 2), 0x65: ('ADC', 'ZP', 2),
    0x66: ('ROR', 'ZP', 2), 0x68: ('PLA', 'IMP', 1), 0x69: ('ADC', 'IMM', 2),
    0x6A: ('ROR', 'ACC', 1), 0x6C: ('JMP', 'IND', 3), 0x6D: ('ADC', 'ABS', 3),
    0x6E: ('ROR', 'ABS', 3),
    0x70: ('BVS', 'REL', 2), 0x71: ('ADC', 'IZY', 2), 0x75: ('ADC', 'ZPX', 2),
    0x76: ('ROR', 'ZPX', 2), 0x78: ('SEI', 'IMP', 1), 0x79: ('ADC', 'ABY', 3),
    0x7D: ('ADC', 'ABX', 3), 0x7E: ('ROR', 'ABX', 3),
    0x81: ('STA', 'IZX', 2), 0x84: ('STY', 'ZP', 2), 0x85: ('STA', 'ZP', 2),
    0x86: ('STX', 'ZP', 2), 0x88: ('DEY', 'IMP', 1), 0x8A: ('TXA', 'IMP', 1),
    0x8C: ('STY', 'ABS', 3), 0x8D: ('STA', 'ABS', 3), 0x8E: ('STX', 'ABS', 3),
    0x90: ('BCC', 'REL', 2), 0x91: ('STA', 'IZY', 2), 0x94: ('STY', 'ZPX', 2),
    0x95: ('STA', 'ZPX', 2), 0x96: ('STX', 'ZPY', 2), 0x98: ('TYA', 'IMP', 1),
    0x99: ('STA', 'ABY', 3), 0x9A: ('TXS', 'IMP', 1), 0x9D: ('STA', 'ABX', 3),
    0xA0: ('LDY', 'IMM', 2), 0xA1: ('LDA', 'IZX', 2), 0xA2: ('LDX', 'IMM', 2),
    0xA4: ('LDY', 'ZP', 2), 0xA5: ('LDA', 'ZP', 2), 0xA6: ('LDX', 'ZP', 2),
    0xA8: ('TAY', 'IMP', 1), 0xA9: ('LDA', 'IMM', 2), 0xAA: ('TAX', 'IMP', 1),
    0xAC: ('LDY', 'ABS', 3), 0xAD: ('LDA', 'ABS', 3), 0xAE: ('LDX', 'ABS', 3),
    0xB0: ('BCS', 'REL', 2), 0xB1: ('LDA', 'IZY', 2), 0xB4: ('LDY', 'ZPX', 2),
    0xB5: ('LDA', 'ZPX', 2), 0xB6: ('LDX', 'ZPY', 2), 0xB8: ('CLV', 'IMP', 1),
    0xB9: ('LDA', 'ABY', 3), 0xBA: ('TSX', 'IMP', 1), 0xBC: ('LDY', 'ABX', 3),
    0xBD: ('LDA', 'ABX', 3), 0xBE: ('LDX', 'ABY', 3),
    0xC0: ('CPY', 'IMM', 2), 0xC1: ('CMP', 'IZX', 2), 0xC4: ('CPY', 'ZP', 2),
    0xC5: ('CMP', 'ZP', 2), 0xC6: ('DEC', 'ZP', 2), 0xC8: ('INY', 'IMP', 1),
    0xC9: ('CMP', 'IMM', 2), 0xCA: ('DEX', 'IMP', 1), 0xCC: ('CPY', 'ABS', 3),
    0xCD: ('CMP', 'ABS', 3), 0xCE: ('DEC', 'ABS', 3),
    0xD0: ('BNE', 'REL', 2), 0xD1: ('CMP', 'IZY', 2), 0xD5: ('CMP', 'ZPX', 2),
    0xD6: ('DEC', 'ZPX', 2), 0xD8: ('CLD', 'IMP', 1), 0xD9: ('CMP', 'ABY', 3),
    0xDD: ('CMP', 'ABX', 3), 0xDE: ('DEC', 'ABX', 3),
    0xE0: ('CPX', 'IMM', 2), 0xE1: ('SBC', 'IZX', 2), 0xE4: ('CPX', 'ZP', 2),
    0xE5: ('SBC', 'ZP', 2), 0xE6: ('INC', 'ZP', 2), 0xE8: ('INX', 'IMP', 1),
    0xE9: ('SBC', 'IMM', 2), 0xEA: ('NOP', 'IMP', 1), 0xEC: ('CPX', 'ABS', 3),
    0xED: ('SBC', 'ABS', 3), 0xEE: ('INC', 'ABS', 3),
    0xF0: ('BEQ', 'REL', 2), 0xF1: ('SBC', 'IZY', 2), 0xF5: ('SBC', 'ZPX', 2),
    0xF6: ('INC', 'ZPX', 2), 0xF8: ('SED', 'IMP', 1), 0xF9: ('SBC', 'ABY', 3),
    0xFD: ('SBC', 'ABX', 3), 0xFE: ('INC', 'ABX', 3),
}

def h4(v): return '{:04X}'.format(v)
def h2(v): return '{:02X}'.format(v)

# Known labels for ROM calls
ROM_LABELS = {
    0x8100: 'JT_MAIN_INIT', 0x8103: 'JT_EDITOR', 0x8106: 'JT_MODEM_CHECK',
    0x8109: 'JT_DISCONNECT_MSG', 0x810C: 'JT_MODEM_READ_STATUS',
    0x810F: 'JT_MODEM_INIT_DL', 0x8112: 'JT_MODEM_SEND_CMD',
    0x8115: 'JT_PROTOCOL_RESET', 0x8118: 'JT_DUCKSHOOT',
    0x811B: 'JT_SETUP_INPUT', 0x811E: 'JT_INPUT_LINE',
    0x8121: 'JT_FRAME_READ', 0x8124: 'JT_FRAME_WRITE',
    0x8127: 'JT_DISK_LOAD', 0x812A: 'JT_DISK_SAVE',
    0x812D: 'JT_SCREEN_DRAW', 0x8130: 'JT_NEW_PAGE',
    0x8133: 'JT_LAST_PAGE', 0x8136: 'JT_NEXT_PAGE',
    0x8139: 'JT_GET_FILE', 0x813C: 'JT_CMD_INPUT',
    0x813F: 'JT_PRINT_STR', 0x8142: 'JT_DUCK_ITEM',
    0x8145: 'JT_STATUS_BAR', 0x8148: 'JT_PRESS_KEY',
    0x814B: 'JT_CLEAR_STATUS', 0x814E: 'JT_INPUT_PROMPT',
    0x8151: 'JT_WHITE_BAR', 0x8154: 'JT_MODEM_STATUS',
    0x8157: 'JT_CNSAVE', 0x815A: 'JT_FILE_DL',
    0x815D: 'JT_CNLOAD_ERR',
    0x96C0: 'PROTO_GET_RESP', 0x96C6: 'PROTO_OPEN_LINE',
    0x96C9: 'PROTO_RECV_FRAME', 0x96CC: 'PROTO_RECV_BYTE',
    0x96CF: 'PROTO_DISCONNECT', 0x96D2: 'PROTO_SEND_DATA',
    0x96D5: 'PROTO_CONNECT', 0x96D8: 'PROTO_JMP_C800',
    0x94E4: 'MODEM_WAIT_READY', 0x94F0: 'MODEM_REG_WRITE',
    0x94FA: 'MODEM_REG_READ',
    0xFFD2: 'KERNAL_CHROUT', 0xFFE4: 'KERNAL_GETIN',
    0xFFCC: 'KERNAL_CLRCHN', 0xFFC0: 'KERNAL_OPEN',
    0xFFC3: 'KERNAL_CLOSE', 0xFFC6: 'KERNAL_CHKIN',
    0xFFC9: 'KERNAL_CHKOUT', 0xFFBA: 'KERNAL_SETLFS',
    0xFFBD: 'KERNAL_SETNAM', 0xFFD5: 'KERNAL_LOAD',
    0xFFB7: 'KERNAL_READST', 0xFFF0: 'KERNAL_PLOT',
}

# Trace code from known entry points
def trace(entries):
    code = set()
    queue = list(entries)
    while queue:
        start = queue.pop(0)
        off = start - RUNTIME_BASE
        if start in code or off < 0 or off >= len(payload):
            continue
        while 0 <= off < len(payload):
            addr = RUNTIME_BASE + off
            if addr in code and addr != start:
                break
            code.add(addr)
            op = payload[off]
            if op not in OPCODES:
                break
            mnem, mode, size = OPCODES[op]
            if off + size > len(payload):
                break
            if mode == 'REL':
                rel = payload[off+1]
                if rel >= 128: rel -= 256
                target = addr + 2 + rel
                if target not in code:
                    queue.append(target)
            elif mnem == 'JSR':
                target = payload[off+1] | (payload[off+2] << 8)
                if RUNTIME_BASE <= target < RUNTIME_BASE + len(payload) and target not in code:
                    queue.append(target)
            elif mnem == 'JMP' and mode == 'ABS':
                target = payload[off+1] | (payload[off+2] << 8)
                if RUNTIME_BASE <= target < RUNTIME_BASE + len(payload) and target not in code:
                    queue.append(target)
                break
            off += size
            if mnem in ('RTS', 'RTI', 'BRK', 'JMP'):
                break
    return code

# Entry points: the init code and all internal JSR/JMP targets
entries = [RUNTIME_BASE + 0x15]  # init code at offset $15 ($A005)

# Also find all internal JSR/JMP targets
for off in range(len(payload) - 2):
    op = payload[off]
    if op in (0x20, 0x4C):  # JSR/JMP
        target = payload[off+1] | (payload[off+2] << 8)
        if RUNTIME_BASE <= target < RUNTIME_BASE + len(payload):
            entries.append(target)

code_addrs = trace(entries)
print('Code coverage: {} of {} bytes ({:.1f}%)'.format(
    len(code_addrs), len(payload), 100.0 * len(code_addrs) / len(payload)))

# Find all internal labels (JSR/JMP targets within the code)
internal_labels = {}
for off in range(len(payload) - 2):
    op = payload[off]
    if op in (0x20, 0x4C):
        target = payload[off+1] | (payload[off+2] << 8)
        if RUNTIME_BASE <= target < RUNTIME_BASE + len(payload):
            if target not in internal_labels:
                internal_labels[target] = 'SUB_{}'.format(h4(target))

print('Internal subroutines: {}'.format(len(internal_labels)))
print()

# Generate the disassembly
outpath = r'c:\Users\trist\src\compunet-reborn\cnet_terminal_disasm.asm'
out = []
out.append('; =================================================================')
out.append('; COMPUNET TERMINAL SOFTWARE (cnet.prg) - DISASSEMBLY')
out.append('; =================================================================')
out.append('; Runtime address: $9FF0-${}'.format(h4(RUNTIME_BASE + len(payload) - 1)))
out.append('; Size: {} bytes ({:.1f} KB)'.format(len(payload), len(payload)/1024.0))
out.append('; This is the code downloaded during "linking" phase.')
out.append('; It provides: directory navigation, duckshoot, SHOW, BUY,')
out.append(';   MAIL (Courier), UPLOAD, VOTE, account management, etc.')
out.append(';')
out.append('; Calls ROM routines via jump table at $8100-$815F')
out.append('; Calls protocol layer at $96C0-$96D8')
out.append('; Uses workspace at $C000-$C0FF')
out.append('; =================================================================')
out.append('')
out.append('    * = ${}'.format(h4(RUNTIME_BASE)))
out.append('')

pc = 0
while pc < len(payload):
    addr = RUNTIME_BASE + pc
    
    # Add label if this is a known target
    if addr in internal_labels:
        out.append('')
        out.append(internal_labels[addr] + ':')
    
    if addr in code_addrs:
        op = payload[pc]
        if op in OPCODES:
            mnem, mode, size = OPCODES[op]
            if pc + size <= len(payload):
                raw = payload[pc:pc+size]
                raw_hex = ' '.join(h2(b) for b in raw)
                
                # Format operand
                if mode == 'IMP': operand = ''
                elif mode == 'ACC': operand = 'A'
                elif mode == 'IMM': operand = '#$' + h2(payload[pc+1])
                elif mode == 'ZP': operand = '$' + h2(payload[pc+1])
                elif mode == 'ZPX': operand = '$' + h2(payload[pc+1]) + ',X'
                elif mode == 'ZPY': operand = '$' + h2(payload[pc+1]) + ',Y'
                elif mode == 'ABS':
                    t = payload[pc+1] | (payload[pc+2] << 8)
                    operand = '$' + h4(t)
                elif mode == 'ABX':
                    t = payload[pc+1] | (payload[pc+2] << 8)
                    operand = '$' + h4(t) + ',X'
                elif mode == 'ABY':
                    t = payload[pc+1] | (payload[pc+2] << 8)
                    operand = '$' + h4(t) + ',Y'
                elif mode == 'IND':
                    t = payload[pc+1] | (payload[pc+2] << 8)
                    operand = '($' + h4(t) + ')'
                elif mode == 'IZX': operand = '($' + h2(payload[pc+1]) + ',X)'
                elif mode == 'IZY': operand = '($' + h2(payload[pc+1]) + '),Y'
                elif mode == 'REL':
                    rel = payload[pc+1]
                    if rel >= 128: rel -= 256
                    t = addr + 2 + rel
                    operand = '$' + h4(t)
                else: operand = ''
                
                # Add comment for known targets
                comment = ''
                if mode == 'ABS' and mnem in ('JSR', 'JMP'):
                    t = payload[pc+1] | (payload[pc+2] << 8)
                    if t in ROM_LABELS:
                        comment = ' ; ' + ROM_LABELS[t]
                    elif t in internal_labels:
                        comment = ' ; ' + internal_labels[t]
                
                out.append('    {:12s}  {} {}{}'.format(raw_hex, mnem, operand, comment))
                pc += size
                continue
        out.append('    {:12s}  .byte ${}'.format(h2(payload[pc]), h2(payload[pc])))
        pc += 1
    else:
        # Data region - check for strings
        run_start = pc
        while pc < len(payload) and (RUNTIME_BASE + pc) not in code_addrs:
            pc += 1
        chunk = payload[run_start:pc]
        
        # Check if it's text
        text_count = sum(1 for b in chunk if 32 <= b < 127 or b == 0x0D)
        if text_count > len(chunk) * 0.5 and len(chunk) > 3:
            # Output as text
            i = 0
            while i < len(chunk):
                end = min(i + 40, len(chunk))
                sub = chunk[i:end]
                text = ''
                for b in sub:
                    if b == 0x0D: text += '\\n'
                    elif 32 <= b < 127: text += chr(b)
                    else: text += '.'
                hexs = ' '.join(h2(b) for b in sub[:8])
                out.append('    {:24s}  ; ${} "{}"'.format(
                    '.byte ' + hexs + '...', h4(RUNTIME_BASE + run_start + i), text))
                i += len(sub)
        else:
            # Output as hex
            i = 0
            while i < len(chunk):
                sub = chunk[i:i+16]
                hexs = ' '.join(h2(b) for b in sub)
                out.append('    .byte {:48s}; ${}'.format(hexs, h4(RUNTIME_BASE + run_start + i)))
                i += 16

with open(outpath, 'w') as f:
    for line in out:
        f.write(line + '\n')

print('Disassembly written to: cnet_terminal_disasm.asm ({} lines)'.format(len(out)))
