"""Generate the final annotated disassembly of the Compunet Terminal ROM."""
import struct

filepath = r'c:\Users\trist\src\compunet-reborn\historical\chip0_bank0_8000.bin'
with open(filepath, 'rb') as f:
    rom = f.read()

BASE = 0x8000

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

def get_operand(mode, pc, addr):
    if mode == 'IMP': return ('', None)
    if mode == 'ACC': return ('A', None)
    if mode == 'IMM': return ('#$' + h2(rom[pc+1]), None)
    if mode == 'ZP':  return ('$' + h2(rom[pc+1]), rom[pc+1])
    if mode == 'ZPX': return ('$' + h2(rom[pc+1]) + ',X', rom[pc+1])
    if mode == 'ZPY': return ('$' + h2(rom[pc+1]) + ',Y', rom[pc+1])
    if mode == 'ABS':
        t = rom[pc+1] | (rom[pc+2] << 8)
        return ('$' + h4(t), t)
    if mode == 'ABX':
        t = rom[pc+1] | (rom[pc+2] << 8)
        return ('$' + h4(t) + ',X', t)
    if mode == 'ABY':
        t = rom[pc+1] | (rom[pc+2] << 8)
        return ('$' + h4(t) + ',Y', t)
    if mode == 'IND':
        t = rom[pc+1] | (rom[pc+2] << 8)
        return ('($' + h4(t) + ')', t)
    if mode == 'IZX': return ('($' + h2(rom[pc+1]) + ',X)', rom[pc+1])
    if mode == 'IZY': return ('($' + h2(rom[pc+1]) + '),Y', rom[pc+1])
    if mode == 'REL':
        off = rom[pc+1]
        if off >= 128: off -= 256
        t = addr + 2 + off
        return ('$' + h4(t), t)
    return ('', None)

# Known labels
LABELS = {
    # KERNAL
    0xFF81: 'KERNAL_CINT', 0xFF84: 'KERNAL_IOINIT', 0xFF87: 'KERNAL_RAMTAS',
    0xFF8A: 'KERNAL_RESTOR', 0xFFD2: 'KERNAL_CHROUT', 0xFFE4: 'KERNAL_GETIN',
    0xFFCC: 'KERNAL_CLRCHN', 0xFFC0: 'KERNAL_OPEN', 0xFFC3: 'KERNAL_CLOSE',
    0xFFC6: 'KERNAL_CHKIN', 0xFFC9: 'KERNAL_CHKOUT', 0xFFCF: 'KERNAL_CHRIN',
    0xFFBA: 'KERNAL_SETLFS', 0xFFBD: 'KERNAL_SETNAM', 0xFFD5: 'KERNAL_LOAD',
    0xFFD8: 'KERNAL_SAVE', 0xFFE1: 'KERNAL_STOP', 0xFFB7: 'KERNAL_READST',
    # VIC-II
    0xD011: 'VIC_CTRL1', 0xD012: 'VIC_RASTER', 0xD018: 'VIC_MEMSETUP',
    0xD020: 'VIC_BORDER', 0xD021: 'VIC_BGCOL0',
    # CIA
    0xDC00: 'CIA1_PRA', 0xDC01: 'CIA1_PRB', 0xDC0D: 'CIA1_ICR',
    0xDD00: 'CIA2_PRA',
    # Modem
    0xDE00: 'MODEM_REG_SELECT', 0xDE01: 'MODEM_DATA',
    # BASIC
    0xE453: 'BASIC_RUNC', 0xE3BF: 'BASIC_MAIN', 0xE422: 'BASIC_LINKPRG',
    0xA474: 'BASIC_READY',
    # Compunet ROM entry points
    0x8160: 'COLD_START',
    0x81A0: 'MAIN_INIT',
    0x8355: 'CONNECT_MANAGER',
    0x8446: 'KEYBOARD_SCAN',
    0x8477: 'KEY_DISPATCH',
    0x849B: 'INPUT_HANDLER',
    0x8500: 'COMMAND_EXEC',
    0x85E4: 'SCREEN_DRAW',
    0x869E: 'FILE_OPS',
    0x89D0: 'FRAME_BUF_READ',
    0x89E2: 'FRAME_BUF_WRITE',
    0x8ABE: 'DISK_LOAD',
    0x8AEB: 'DISK_SAVE',
    0x8D30: 'FRAME_RENDER',
    0x8EEF: 'MODEM_INIT_DOWNLOAD',
    0x8F47: 'MODEM_SEND_CMD',
    0x8FFB: 'WAIT_KEYPRESS',
    0x9002: 'CLEAR_STATUS',
    0x901E: 'STATUS_LINE',
    0x907B: 'PRINT_STATUS_MSG',
    0x9093: 'CURSOR_HOME',
    0x90B7: 'PRINT_STRING',
    0x90C8: 'SETUP_INPUT_PARAMS',
    0x90DF: 'INPUT_LINE',
    0x9171: 'FILE_UPLOAD',
    0x91B2: 'FILE_DOWNLOAD',
    0x92CD: 'FRAME_STORE',
    0x938B: 'PROTOCOL_STATE_INIT',
    0x93C9: 'PROTOCOL_RESET',
    0x93D0: 'PROTOCOL_CLEANUP',
    0x94A8: 'MODEM_STATUS_CHECK',
    0x94C1: 'MODEM_REG_WRITE_WAIT',
    0x94D5: 'MODEM_REG_READ_STATUS',
    0x94E4: 'MODEM_WAIT_READY',
    0x94F0: 'MODEM_REG_WRITE',
    0x94FA: 'MODEM_REG_READ',
    0x96C0: 'PROTO_DISPATCH_TABLE',
    0x96DB: 'PROTO_INIT_REGS',
    0x96E9: 'PROTO_START_SESSION',
    0x970A: 'PROTO_DISCONNECT',
    0x97AD: 'PROTO_RECV_FRAME',
    0x993A: 'PROTO_ERROR_RECOVERY',
    0x996B: 'PROTO_PROCESS_CMD',
    0x9B3B: 'PROTO_FLOW_CONTROL',
    0x9B79: 'PROTO_SEND_PACKET',
    0x9B8A: 'PROTO_RECV_PACKET',
    0x9E69: 'PROTO_CONNECT',
}

# Data regions (not code)
DATA_REGIONS = [
    (0x8000, 0x8009, 'Cartridge header'),
    (0x8009, 0x8032, 'System parameters and pointers'),
    (0x8032, 0x8070, 'Modem config: phone, network, commands'),
    (0x807A, 0x80BC, 'Version strings'),
    (0x80BC, 0x8100, 'Padding'),
    (0x8100, 0x8160, 'Main jump table (32 x JMP)'),
    (0x81B7, 0x81BC, 'BASIC stub bytes'),
    (0x83AA, 0x8404, 'Duckshoot menu text'),
    (0x8FBA, 0x8FFC, 'Status messages'),
    (0x9517, 0x96C0, 'Login screen layout and help text'),
    (0x9C0A, 0x9C22, 'Protocol command tokens'),
]

def is_in_data_region(addr):
    for start, end, _ in DATA_REGIONS:
        if start <= addr < end:
            return True
    return False

def get_data_region_name(addr):
    for start, end, name in DATA_REGIONS:
        if start <= addr < end:
            return name
    return None

# Trace code from all known entry points
def trace_code(entries):
    code = set()
    queue = list(entries)
    while queue:
        start = queue.pop(0)
        if start in code or start < BASE or start >= BASE + len(rom):
            continue
        if is_in_data_region(start):
            continue
        pc = start - BASE
        while 0 <= pc < len(rom):
            addr = BASE + pc
            if addr in code and addr != start:
                break
            if is_in_data_region(addr):
                break
            code.add(addr)
            op = rom[pc]
            if op not in OPCODES:
                break
            mnem, mode, size = OPCODES[op]
            if pc + size > len(rom):
                break
            _, target = get_operand(mode, pc, addr)
            if mode == 'REL' and target is not None:
                if target not in code:
                    queue.append(target)
            elif mnem == 'JSR' and target is not None:
                if BASE <= target < BASE + len(rom) and target not in code:
                    queue.append(target)
            elif mnem == 'JMP' and mode == 'ABS' and target is not None:
                if BASE <= target < BASE + len(rom) and target not in code:
                    queue.append(target)
                break
            pc += size
            if mnem in ('RTS', 'RTI', 'BRK', 'JMP'):
                break
    return code

# Get all entry points
entries = list(LABELS.keys())
# Add jump table targets
for off in range(0x100, 0x160, 3):
    if rom[off] == 0x4C:
        t = rom[off+1] | (rom[off+2] << 8)
        if t not in entries:
            entries.append(t)
for off in range(0x16C0, 0x16E0, 3):
    if rom[off] == 0x4C:
        t = rom[off+1] | (rom[off+2] << 8)
        if BASE <= t < BASE + len(rom) and t not in entries:
            entries.append(t)

code_addrs = trace_code(entries)

# Second pass - find more code in gaps
common_starts = {0xA9, 0xA2, 0xA0, 0x48, 0x08, 0x78, 0x18, 0x38, 0x20, 0x4C, 0xAD, 0xAE, 0x85, 0x86}
gap_entries = []
for off in range(len(rom)):
    addr = BASE + off
    if addr not in code_addrs and not is_in_data_region(addr) and rom[off] in common_starts and rom[off] != 0x00:
        if off > 0 and (BASE + off - 1) in code_addrs:
            continue  # skip if previous byte was code (we're mid-instruction)
        gap_entries.append(addr)

code_addrs |= trace_code(gap_entries)

print('Code coverage: {} of {} bytes ({:.1f}%)'.format(
    len(code_addrs), len(rom), 100.0 * len(code_addrs) / len(rom)))

# Generate output
out = []
out.append('; =================================================================')
out.append('; COMPUNET TERMINAL CARTRIDGE v1.22 - ANNOTATED DISASSEMBLY')
out.append('; =================================================================')
out.append('; ROM: 8192 bytes at $8000-$9FFF')
out.append('; Mode: EXROM=0, GAME=1 (8K cartridge)')
out.append('; Developer: Ariadne Software Ltd, September 1984')
out.append('; Hardware: Custom 1200/75 baud modem (Viewdata chipset)')
out.append(';')
out.append('; Modem I/O:')
out.append(';   $DE00 = Register select (write register number)')
out.append(';   $DE01 = Data read/write (access selected register)')
out.append(';')
out.append('; Protocol: Modified X.25 with windowed flow control')
out.append('; Commands: ACK, DIR, DAT, OK, ERR, FTL, COM')
out.append(';')
out.append('; RAM workspace:')
out.append(';   $C100-$C1FF = Terminal state')
out.append(';   $C200-$C2FF = Protocol state')
out.append(';   $C800+      = Downloaded code extensions')
out.append('; =================================================================')
out.append('')
out.append('    * = $8000')
out.append('')

pc = 0
prev_was_data = False

while pc < len(rom):
    addr = BASE + pc
    
    # Check for label
    if addr in LABELS:
        out.append('')
        out.append('; ' + '=' * 60)
        out.append('; ' + LABELS[addr])
        out.append('; ' + '=' * 60)
        out.append(LABELS[addr] + ':')
    
    # Check for data region
    region_name = get_data_region_name(addr)
    if region_name:
        if not prev_was_data:
            out.append('')
            out.append('; --- {} ---'.format(region_name))
        
        # Find end of this data region
        for start, end, name in DATA_REGIONS:
            if start <= addr < end:
                region_end = end
                break
        
        # Output data
        chunk_end = min(region_end, BASE + len(rom))
        while addr < chunk_end:
            off = addr - BASE
            line_end = min(off + 16, chunk_end - BASE)
            chunk = rom[off:line_end]
            hexs = ' '.join(h2(b) for b in chunk)
            # Try ASCII interpretation
            ascii_str = ''
            for b in chunk:
                if b == 0x0D:
                    ascii_str += '\\n'
                elif 32 <= b < 127:
                    ascii_str += chr(b)
                elif b == 0x00:
                    ascii_str += '.'
                else:
                    ascii_str += '.'
            out.append('    {:48s}; ${} {}'.format(
                '.byte ' + hexs, h4(addr), ascii_str))
            addr += len(chunk)
        
        pc = chunk_end - BASE
        prev_was_data = True
        continue
    
    prev_was_data = False
    
    if addr in code_addrs:
        op = rom[pc]
        if op in OPCODES:
            mnem, mode, size = OPCODES[op]
            if pc + size <= len(rom):
                raw = rom[pc:pc+size]
                raw_hex = ' '.join(h2(b) for b in raw)
                operand_str, target = get_operand(mode, pc, addr)
                
                comment = ''
                if target is not None and target in LABELS:
                    comment = ' ; ' + LABELS[target]
                elif target is not None and mode == 'ABS' and 0xDE00 <= target <= 0xDE01:
                    if target == 0xDE00:
                        comment = ' ; MODEM register select'
                    else:
                        comment = ' ; MODEM data'
                elif target is not None and mode == 'ABS' and 0xC100 <= target <= 0xC2FF:
                    comment = ' ; workspace'
                
                out.append('    {:12s}  {} {}{}'.format(raw_hex, mnem, operand_str, comment))
                pc += size
                continue
        
        out.append('    {:12s}  .byte ${}'.format(h2(rom[pc]), h2(rom[pc])))
        pc += 1
    else:
        # Unidentified region - output as bytes
        run_start = pc
        while pc < len(rom) and (BASE + pc) not in code_addrs and not is_in_data_region(BASE + pc):
            pc += 1
        
        chunk = rom[run_start:pc]
        if len(chunk) > 0:
            i = 0
            while i < len(chunk):
                sub = chunk[i:i+16]
                hexs = ' '.join(h2(b) for b in sub)
                a = BASE + run_start + i
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in sub)
                out.append('    .byte {:48s}; ${} {}'.format(hexs, h4(a), ascii_str))
                i += 16

# Write output
outpath = r'c:\Users\trist\src\compunet-reborn\compunet_terminal_v122.asm'
with open(outpath, 'w') as f:
    for line in out:
        f.write(line + '\n')

print('Written {} lines to compunet_terminal_v122.asm'.format(len(out)))
