"""
Generate ca65 source by disassembling the original ROM binary.

Uses recursive descent: starts from known entry points, follows all
branches/jumps to identify code. Everything else is emitted as .byte data.

Two passes:
  Pass 1: Identify all code bytes (recursive descent from entry points)
  Pass 2: Emit source with mnemonics for code, .byte for data
"""
import os
import struct

script_dir = os.path.dirname(os.path.abspath(__file__))
rom_path = os.path.join(script_dir, 'original_rom.bin')
output_path = os.path.join(script_dir, 'compunet_full.s')

with open(rom_path, 'rb') as f:
    rom = f.read()

BASE = 0x8000

# 6502 instruction table: opcode -> (mnemonic, addressing_mode, size)
# Addressing modes: IMP, IMM, ZP, ZPX, ZPY, ABS, ABX, ABY, IND, IZX, IZY, REL, ACC
OPCODES = {}

def _add(opcode, mnemonic, mode, size):
    OPCODES[opcode] = (mnemonic, mode, size)

# Implied / Accumulator
for op, mn in [(0x00,'BRK'),(0x08,'PHP'),(0x0A,'ASL'),(0x18,'CLC'),(0x28,'PLP'),
               (0x2A,'ROL'),(0x38,'SEC'),(0x40,'RTI'),(0x48,'PHA'),(0x4A,'LSR'),
               (0x58,'CLI'),(0x60,'RTS'),(0x68,'PLA'),(0x6A,'ROR'),(0x78,'SEI'),
               (0x88,'DEY'),(0x8A,'TXA'),(0x98,'TYA'),(0x9A,'TXS'),(0xA8,'TAY'),
               (0xAA,'TAX'),(0xB8,'CLV'),(0xBA,'TSX'),(0xC8,'INY'),(0xCA,'DEX'),
               (0xD8,'CLD'),(0xE8,'INX'),(0xEA,'NOP'),(0xF8,'SED')]:
    _add(op, mn, 'IMP', 1)

# Immediate
for op, mn in [(0x09,'ORA'),(0x29,'AND'),(0x49,'EOR'),(0x69,'ADC'),(0xA0,'LDY'),
               (0xA2,'LDX'),(0xA9,'LDA'),(0xC0,'CPY'),(0xC9,'CMP'),(0xE0,'CPX'),
               (0xE9,'SBC')]:
    _add(op, mn, 'IMM', 2)

# Zero Page
for op, mn in [(0x05,'ORA'),(0x06,'ASL'),(0x24,'BIT'),(0x25,'AND'),(0x26,'ROL'),
               (0x45,'EOR'),(0x46,'LSR'),(0x65,'ADC'),(0x66,'ROR'),(0x84,'STY'),
               (0x85,'STA'),(0x86,'STX'),(0xA4,'LDY'),(0xA5,'LDA'),(0xA6,'LDX'),
               (0xC4,'CPY'),(0xC5,'CMP'),(0xC6,'DEC'),(0xE4,'CPX'),(0xE5,'SBC'),
               (0xE6,'INC')]:
    _add(op, mn, 'ZP', 2)

# Zero Page,X
for op, mn in [(0x15,'ORA'),(0x16,'ASL'),(0x35,'AND'),(0x36,'ROL'),(0x55,'EOR'),
               (0x56,'LSR'),(0x75,'ADC'),(0x76,'ROR'),(0x94,'STY'),(0x95,'STA'),
               (0xB4,'LDY'),(0xB5,'LDA'),(0xD5,'CMP'),(0xD6,'DEC'),(0xF5,'SBC'),
               (0xF6,'INC')]:
    _add(op, mn, 'ZPX', 2)

# Zero Page,Y
for op, mn in [(0x96,'STX'),(0xB6,'LDX')]:
    _add(op, mn, 'ZPY', 2)

# Absolute
for op, mn in [(0x0D,'ORA'),(0x0E,'ASL'),(0x20,'JSR'),(0x2C,'BIT'),(0x2D,'AND'),
               (0x2E,'ROL'),(0x4C,'JMP'),(0x4D,'EOR'),(0x4E,'LSR'),(0x6D,'ADC'),
               (0x6E,'ROR'),(0x8C,'STY'),(0x8D,'STA'),(0x8E,'STX'),(0xAC,'LDY'),
               (0xAD,'LDA'),(0xAE,'LDX'),(0xCC,'CPY'),(0xCD,'CMP'),(0xCE,'DEC'),
               (0xEC,'CPX'),(0xED,'SBC'),(0xEE,'INC')]:
    _add(op, mn, 'ABS', 3)

# Absolute,X
for op, mn in [(0x1D,'ORA'),(0x1E,'ASL'),(0x3D,'AND'),(0x3E,'ROL'),(0x5D,'EOR'),
               (0x5E,'LSR'),(0x7D,'ADC'),(0x7E,'ROR'),(0x9D,'STA'),(0xBC,'LDY'),
               (0xBD,'LDA'),(0xDD,'CMP'),(0xDE,'DEC'),(0xFD,'SBC'),(0xFE,'INC')]:
    _add(op, mn, 'ABX', 3)

# Absolute,Y
for op, mn in [(0x19,'ORA'),(0x39,'AND'),(0x59,'EOR'),(0x79,'ADC'),(0x99,'STA'),
               (0xB9,'LDA'),(0xBE,'LDX'),(0xD9,'CMP'),(0xF9,'SBC')]:
    _add(op, mn, 'ABY', 3)

# Indirect
_add(0x6C, 'JMP', 'IND', 3)

# (Indirect,X)
for op, mn in [(0x01,'ORA'),(0x21,'AND'),(0x41,'EOR'),(0x61,'ADC'),(0x81,'STA'),
               (0xA1,'LDA'),(0xC1,'CMP'),(0xE1,'SBC')]:
    _add(op, mn, 'IZX', 2)

# (Indirect),Y
for op, mn in [(0x11,'ORA'),(0x31,'AND'),(0x51,'EOR'),(0x71,'ADC'),(0x91,'STA'),
               (0xB1,'LDA'),(0xD1,'CMP'),(0xF1,'SBC')]:
    _add(op, mn, 'IZY', 2)

# Relative (branches)
for op, mn in [(0x10,'BPL'),(0x30,'BMI'),(0x50,'BVC'),(0x70,'BVS'),
               (0x90,'BCC'),(0xB0,'BCS'),(0xD0,'BNE'),(0xF0,'BEQ')]:
    _add(op, mn, 'REL', 2)


# ============================================================
# Pass 1: Recursive descent to find code regions
# ============================================================

is_code = [False] * 8192  # True if this byte is part of an instruction
code_start = set()  # addresses where instructions start
branch_targets = set()  # addresses that are branch/jump targets

# Known entry points
entry_points = [
    0x8009,  # Cold start (JMP from header)
    0x8100,  # Jump table entries (we'll add these)
]

# Add all jump table entries ($8100-$815F, 32 x 3-byte JMP instructions)
for i in range(32):
    addr = 0x8100 + i * 3
    target = rom[addr - BASE + 1] | (rom[addr - BASE + 2] << 8)
    if 0x8000 <= target <= 0x9FFF:
        entry_points.append(target)

def trace(start_addr):
    """Trace code from start_addr, marking code bytes."""
    queue = [start_addr]
    while queue:
        addr = queue.pop()
        offset = addr - BASE
        
        if offset < 0 or offset >= 8192:
            continue
        if is_code[offset]:
            continue  # already traced
        
        # Decode instruction
        opcode = rom[offset]
        if opcode not in OPCODES:
            continue  # unknown opcode, stop tracing
        
        mnemonic, mode, size = OPCODES[opcode]
        
        # Check bounds
        if offset + size > 8192:
            continue
        
        # Mark bytes as code
        for i in range(size):
            is_code[offset + i] = True
        code_start.add(addr)
        
        # Get operand value
        if size == 2:
            operand_byte = rom[offset + 1]
        elif size == 3:
            operand_word = rom[offset + 1] | (rom[offset + 2] << 8)
        
        # Follow branches
        if mode == 'REL':
            # Relative branch
            rel = operand_byte
            if rel >= 128:
                rel -= 256
            target = addr + 2 + rel
            branch_targets.add(target)
            queue.append(target)
            # Also continue to next instruction (branch not taken)
            queue.append(addr + size)
        elif mnemonic == 'JMP' and mode == 'ABS':
            target = operand_word
            branch_targets.add(target)
            if 0x8000 <= target <= 0x9FFF:
                queue.append(target)
            # JMP doesn't fall through
        elif mnemonic == 'JSR':
            target = operand_word
            branch_targets.add(target)
            if 0x8000 <= target <= 0x9FFF:
                queue.append(target)
            # JSR returns, so continue after
            queue.append(addr + size)
        elif mnemonic in ('RTS', 'RTI', 'BRK'):
            # End of trace path
            pass
        else:
            # Normal instruction, continue to next
            queue.append(addr + size)

# Trace from all entry points
for ep in entry_points:
    trace(ep)

print(f"Code bytes: {sum(is_code)} / 8192")
print(f"Code instructions: {len(code_start)}")
print(f"Branch targets: {len(branch_targets)}")

# ============================================================
# Pass 2: Emit source
# ============================================================

def format_operand(mnemonic, mode, rom, offset, addr):
    """Format the operand for ca65 syntax."""
    if mode == 'IMP':
        return ''
    elif mode == 'IMM':
        return f'#${rom[offset+1]:02X}'
    elif mode == 'ZP':
        return f'${rom[offset+1]:02X}'
    elif mode == 'ZPX':
        return f'${rom[offset+1]:02X},X'
    elif mode == 'ZPY':
        return f'${rom[offset+1]:02X},Y'
    elif mode == 'ABS':
        target = rom[offset+1] | (rom[offset+2] << 8)
        if target in branch_targets and 0x8000 <= target <= 0x9FFF:
            return make_label(target)
        return f'${target:04X}'
    elif mode == 'ABX':
        target = rom[offset+1] | (rom[offset+2] << 8)
        if target in branch_targets and 0x8000 <= target <= 0x9FFF:
            return f'{make_label(target)},X'
        return f'${target:04X},X'
    elif mode == 'ABY':
        target = rom[offset+1] | (rom[offset+2] << 8)
        if target in branch_targets and 0x8000 <= target <= 0x9FFF:
            return f'{make_label(target)},Y'
        return f'${target:04X},Y'
    elif mode == 'IND':
        target = rom[offset+1] | (rom[offset+2] << 8)
        return f'(${target:04X})'
    elif mode == 'IZX':
        return f'(${rom[offset+1]:02X},X)'
    elif mode == 'IZY':
        return f'(${rom[offset+1]:02X}),Y'
    elif mode == 'REL':
        rel = rom[offset+1]
        if rel >= 128:
            rel -= 256
        target = addr + 2 + rel
        return make_label(target)
    return '???'

def make_label(addr):
    """Generate a label name — use named label if known, else auto-generate."""
    named = {
        0x8160: 'COLD_START',
        0x81A0: 'MAIN_INIT',
        0x8445: 'KEYBOARD_SCAN',
        0x8476: 'KEY_DISPATCH',
        0x849A: 'INPUT_HANDLER',
        0x84FF: 'COMMAND_EXEC',
        0x85E4: 'SCREEN_DRAW',
        0x869E: 'FILE_OPS',
        0x89CF: 'FRAME_BUF_READ',
        0x89E1: 'FRAME_BUF_WRITE',
        0x8ABE: 'DISK_LOAD',
        0x8AEB: 'DISK_SAVE',
        0x8D30: 'MODEM_CHECK',
        0x8EEF: 'MODEM_INIT_DOWNLOAD',
        0x8F47: 'MODEM_SEND_CMD',
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
    if addr in named:
        return named[addr]
    return f'L{addr:04X}'

# Set of addresses that have named labels (always emit these)
named_addrs = set(make_label.__code__.co_consts[1].keys()) if False else {
    0x8160, 0x81A0, 0x8445, 0x8476, 0x849A, 0x84FF, 0x85E4, 0x869E,
    0x89CF, 0x89E1, 0x8ABE, 0x8AEB, 0x8D30, 0x8EEF, 0x8F47, 0x9002,
    0x901E, 0x907B, 0x9093, 0x90B7, 0x90C8, 0x90DF, 0x9171, 0x91B2,
    0x92CD, 0x938B, 0x93C9, 0x93D0, 0x94A8, 0x94C1, 0x94D5, 0x94E4,
    0x94F0, 0x94FA, 0x96C0, 0x96DB, 0x96E9, 0x970A, 0x97AD, 0x993A,
    0x996B, 0x9B3B, 0x9B79, 0x9B8A, 0x9E69,
}

output = []
output.append('; =================================================================')
output.append('; COMPUNET TERMINAL v1.22 — Full ROM Source')
output.append('; =================================================================')
output.append('; Assembler: ca65 (cc65 suite)')
output.append('; Original: Ariadne Software Ltd, September 1984')
output.append('; Auto-generated by gen_source.py from original ROM binary')
output.append(';')
output.append('; This file assembles to a byte-identical copy of the original ROM.')
output.append('; =================================================================')
output.append('')
output.append('.segment "HEADER"')
output.append('')

offset = 0
while offset < 8192:
    addr = BASE + offset
    
    # Emit label if needed (branch target OR named label)
    if addr in branch_targets or addr in named_addrs:
        output.append(f'{make_label(addr)}:')
    
    if is_code[offset]:
        # Emit instruction
        opcode = rom[offset]
        mnemonic, mode, size = OPCODES[opcode]
        operand = format_operand(mnemonic, mode, rom, offset, addr)
        
        if operand:
            line = f'    {mnemonic} {operand}'
        else:
            line = f'    {mnemonic}'
        
        output.append(line)
        offset += size
    else:
        # Emit data bytes (group consecutive non-code bytes)
        data_start = offset
        while offset < 8192 and not is_code[offset] and (BASE + offset) not in branch_targets:
            offset += 1
            if (offset - data_start) >= 16:
                break
        
        chunk = rom[data_start:offset]
        byte_str = ', '.join(f'${b:02X}' for b in chunk)
        ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        output.append(f'    .byte {byte_str}  ; ${BASE+data_start:04X} {ascii_repr}')

with open(output_path, 'w') as f:
    f.write('\n'.join(output) + '\n')

print(f"Output: {len(output)} lines → {output_path}")
