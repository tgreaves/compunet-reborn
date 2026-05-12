"""
Generate ca65 source by disassembling the terminal code from cnet.prg.

Uses recursive descent: starts from the entry point ($A005), follows all
branches/jumps to identify code. Everything else is emitted as .byte data.

Two passes:
  Pass 1: Identify all code bytes (recursive descent from entry points)
  Pass 2: Emit source with mnemonics for code, .byte for data

The terminal code is downloaded during LINKING and loaded at $9FF0.
Entry point is $A005. It calls back into the ROM via the jump table at $8100.
"""
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
prg_path = os.path.join(script_dir, '..', '..', '..', 'historical', 'cnet.prg')
output_path = os.path.join(script_dir, 'terminal.s')

with open(prg_path, 'rb') as f:
    prg_data = f.read()

# Strip 2-byte PRG load address header ($01 $08 = $0801 little-endian)
# The PRG header says $0801 but the terminal code actually loads at $9FF0 in C64 memory
load_addr = prg_data[0] | (prg_data[1] << 8)
assert load_addr == 0x0801, f"Expected PRG header $0801, got ${load_addr:04X}"
code = prg_data[2:]

BASE = 0x9FF0
CODE_SIZE = len(code)  # 7699 bytes
END_ADDR = BASE + CODE_SIZE  # $BE03 (exclusive), last byte at $BE02

print(f"Terminal code: {CODE_SIZE} bytes, ${BASE:04X}-${END_ADDR-1:04X}")
print(f"Entry point: $A005")

# ROM jump table: 32 x 3-byte JMP entries at $8100-$815F
JUMP_TABLE_START = 0x8100
JUMP_TABLE_END = 0x815F
NUM_ROMCALLS = 32

# Generate ROMCALL equate names
ROMCALL_NAMES = {}
for i in range(NUM_ROMCALLS):
    addr = JUMP_TABLE_START + i * 3
    ROMCALL_NAMES[addr] = f'ROMCALL_{i:02d}'

# 6502 instruction table: opcode -> (mnemonic, addressing_mode, size)
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

is_code = [False] * CODE_SIZE
code_start = set()       # addresses where instructions start
branch_targets = set()   # addresses that are branch/jump targets

def in_range(addr):
    """Check if address is within the terminal code range."""
    return BASE <= addr < END_ADDR

def trace(start_addr):
    """Trace code from start_addr, marking code bytes."""
    queue = [start_addr]
    while queue:
        addr = queue.pop()
        offset = addr - BASE

        if offset < 0 or offset >= CODE_SIZE:
            continue
        if is_code[offset]:
            continue  # already traced

        # Decode instruction
        opcode = code[offset]
        if opcode not in OPCODES:
            continue  # unknown opcode, stop tracing

        mnemonic, mode, size = OPCODES[opcode]

        # Check bounds
        if offset + size > CODE_SIZE:
            continue

        # Mark bytes as code
        for i in range(size):
            is_code[offset + i] = True
        code_start.add(addr)

        # Get operand value
        if size == 2:
            operand_byte = code[offset + 1]
        elif size == 3:
            operand_word = code[offset + 1] | (code[offset + 2] << 8)

        # Follow branches
        if mode == 'REL':
            rel = operand_byte
            if rel >= 128:
                rel -= 256
            target = addr + 2 + rel
            branch_targets.add(target)
            if in_range(target):
                queue.append(target)
            # Also continue to next instruction (branch not taken)
            queue.append(addr + size)
        elif mnemonic == 'JMP' and mode == 'ABS':
            target = operand_word
            branch_targets.add(target)
            if in_range(target):
                queue.append(target)
            # JMP doesn't fall through
        elif mnemonic == 'JSR':
            target = operand_word
            branch_targets.add(target)
            if in_range(target):
                queue.append(target)
            # JSR returns, so continue after
            queue.append(addr + size)
        elif mnemonic in ('RTS', 'RTI', 'BRK'):
            # End of trace path
            pass
        else:
            # Normal instruction, continue to next
            queue.append(addr + size)

# Primary entry point
entry_points = [0xA005]

# Trace from entry point first
trace(0xA005)

# Iteratively discover more code by following JSR/JMP targets
found_more = True
while found_more:
    found_more = False
    new_targets = set()
    for addr in sorted(code_start):
        offset = addr - BASE
        opcode = code[offset]
        mnemonic, mode, size = OPCODES[opcode]
        if size == 3 and mnemonic in ('JSR', 'JMP') and mode == 'ABS':
            target = code[offset + 1] | (code[offset + 2] << 8)
            if in_range(target) and not is_code[target - BASE]:
                new_targets.add(target)
    for target in new_targets:
        old_count = len(code_start)
        trace(target)
        if len(code_start) > old_count:
            found_more = True

# Scan data regions for address tables pointing into our code range.
# Look for pairs of bytes (lo, hi) that form addresses within $9FF0-$BE02
# where the target byte is a valid opcode. This catches dispatch tables.
# Only scan data regions that are adjacent to (within 32 bytes of) known code.
def scan_for_address_tables():
    """Scan untraced data near code for embedded address tables."""
    new_entries = set()
    offset = 0
    while offset < CODE_SIZE - 1:
        if not is_code[offset] and not is_code[offset + 1]:
            # Only scan if we're near known code (within 32 bytes)
            near_code = False
            for delta in range(-32, 33):
                check = offset + delta
                if 0 <= check < CODE_SIZE and is_code[check]:
                    near_code = True
                    break
            if near_code:
                # Check if this pair forms an address in our range
                target = code[offset] | (code[offset + 1] << 8)
                if in_range(target) and not is_code[target - BASE]:
                    target_opcode = code[target - BASE]
                    if target_opcode in OPCODES:
                        # Verify the target produces a reasonable trace
                        # (at least 3 instructions before hitting unknown/end)
                        test_off = target - BASE
                        valid_insns = 0
                        for _ in range(10):
                            if test_off < 0 or test_off >= CODE_SIZE:
                                break
                            test_op = code[test_off]
                            if test_op not in OPCODES:
                                break
                            _, _, sz = OPCODES[test_op]
                            if test_off + sz > CODE_SIZE:
                                break
                            valid_insns += 1
                            mn = OPCODES[test_op][0]
                            if mn in ('RTS', 'RTI', 'BRK', 'JMP'):
                                break
                            test_off += sz
                        if valid_insns >= 3:
                            new_entries.add(target)
            offset += 2
        else:
            offset += 1
    return new_entries

# Try to find code via address tables (multiple passes)
for _ in range(5):
    table_targets = scan_for_address_tables()
    # Don't trace anything before the entry point (BASIC stub area)
    table_targets = {t for t in table_targets if t >= 0xA005}
    if not table_targets:
        break
    old_count = len(code_start)
    for target in table_targets:
        trace(target)
    if len(code_start) == old_count:
        break

code_bytes = sum(is_code)
data_bytes = CODE_SIZE - code_bytes
print(f"Code bytes: {code_bytes} / {CODE_SIZE}")
print(f"Data bytes: {data_bytes} / {CODE_SIZE}")
print(f"Instructions: {len(code_start)}")
print(f"Branch targets: {len(branch_targets)}")


# ============================================================
# Pass 2: Emit source
# ============================================================

def make_label(addr):
    """Generate a label name for an address."""
    return f'L_{addr:04X}'

def format_operand(mnemonic, mode, offset, addr):
    """Format the operand for ca65 syntax."""
    if mode == 'IMP':
        return ''
    elif mode == 'IMM':
        return f'#${code[offset+1]:02X}'
    elif mode == 'ZP':
        return f'${code[offset+1]:02X}'
    elif mode == 'ZPX':
        return f'${code[offset+1]:02X},X'
    elif mode == 'ZPY':
        return f'${code[offset+1]:02X},Y'
    elif mode == 'ABS':
        target = code[offset+1] | (code[offset+2] << 8)
        # ROM jump table references
        if JUMP_TABLE_START <= target <= JUMP_TABLE_END:
            idx = (target - JUMP_TABLE_START) // 3
            remainder = (target - JUMP_TABLE_START) % 3
            if remainder == 0 and idx < NUM_ROMCALLS:
                return ROMCALL_NAMES[target]
        # Internal references — ensure label exists
        if in_range(target):
            branch_targets.add(target)  # Ensure label gets emitted
            return make_label(target)
        return f'${target:04X}'
    elif mode == 'ABX':
        target = code[offset+1] | (code[offset+2] << 8)
        if JUMP_TABLE_START <= target <= JUMP_TABLE_END:
            idx = (target - JUMP_TABLE_START) // 3
            remainder = (target - JUMP_TABLE_START) % 3
            if remainder == 0 and idx < NUM_ROMCALLS:
                return f'{ROMCALL_NAMES[target]},X'
        if in_range(target):
            branch_targets.add(target)  # Ensure label gets emitted
            return f'{make_label(target)},X'
        return f'${target:04X},X'
    elif mode == 'ABY':
        target = code[offset+1] | (code[offset+2] << 8)
        if JUMP_TABLE_START <= target <= JUMP_TABLE_END:
            idx = (target - JUMP_TABLE_START) // 3
            remainder = (target - JUMP_TABLE_START) % 3
            if remainder == 0 and idx < NUM_ROMCALLS:
                return f'{ROMCALL_NAMES[target]},Y'
        if in_range(target):
            branch_targets.add(target)  # Ensure label gets emitted
            return f'{make_label(target)},Y'
        return f'${target:04X},Y'
    elif mode == 'IND':
        target = code[offset+1] | (code[offset+2] << 8)
        if in_range(target):
            return f'({make_label(target)})'
        return f'(${target:04X})'
    elif mode == 'IZX':
        return f'(${code[offset+1]:02X},X)'
    elif mode == 'IZY':
        return f'(${code[offset+1]:02X}),Y'
    elif mode == 'REL':
        rel = code[offset+1]
        if rel >= 128:
            rel -= 256
        target = addr + 2 + rel
        return make_label(target)
    return '???'


output = []
output.append('; =================================================================')
output.append('; COMPUNET TERMINAL CODE — Downloaded during LINKING')
output.append('; =================================================================')
output.append('; Assembler: ca65 (cc65 suite)')
output.append('; Load address: $9FF0')
output.append('; Entry point:  $A005')
output.append('; Size:         7699 bytes ($9FF0-$BE02)')
output.append('; Auto-generated by gen_terminal.py from historical/cnet.prg')
output.append('; =================================================================')
output.append('')
output.append('; --- ROM Jump Table Equates ($8100-$815F) ---')
output.append('; 32 x 3-byte JMP entries called by terminal code')
for i in range(NUM_ROMCALLS):
    addr = JUMP_TABLE_START + i * 3
    output.append(f'ROMCALL_{i:02d}      = ${addr:04X}')
output.append('')
output.append('.segment "TERMINAL"')
output.append('')

# Pre-pass: collect ALL internal address references so labels can be emitted
for addr in code_start:
    offset = addr - BASE
    opcode = code[offset]
    mnemonic, mode, size = OPCODES[opcode]
    if size == 3:
        target = code[offset + 1] | (code[offset + 2] << 8)
        if in_range(target) and mode in ('ABS', 'ABX', 'ABY'):
            branch_targets.add(target)

offset = 0
while offset < CODE_SIZE:
    addr = BASE + offset

    # Emit label if this is a branch target within our range
    if addr in branch_targets and in_range(addr):
        output.append(f'{make_label(addr)}:')

    if addr in code_start:
        # Emit instruction
        opcode = code[offset]
        mnemonic, mode, size = OPCODES[opcode]
        operand = format_operand(mnemonic, mode, offset, addr)

        if operand:
            line = f'    {mnemonic} {operand}'
        else:
            line = f'    {mnemonic}'

        output.append(line)
        offset += size
    else:
        # Emit data bytes (group consecutive non-code bytes, max 16 per line)
        data_start = offset
        while offset < CODE_SIZE and (BASE + offset) not in code_start:
            # Stop at branch targets so they get their label
            if (BASE + offset) in branch_targets and offset != data_start:
                break
            offset += 1
            if (offset - data_start) >= 16:
                break

        # Safety: ensure we advance at least 1 byte
        if offset == data_start:
            offset += 1

        chunk = code[data_start:offset]
        byte_str = ', '.join(f'${b:02X}' for b in chunk)
        output.append(f'    .byte {byte_str}')

with open(output_path, 'w') as f:
    f.write('\n'.join(output) + '\n')

print(f"\nOutput: {len(output)} lines -> {output_path}")
print(f"\nStatistics:")
print(f"  Code bytes:      {code_bytes}")
print(f"  Data bytes:      {data_bytes}")
print(f"  Instructions:    {len(code_start)}")
print(f"  Branch targets:  {len(branch_targets)}")
