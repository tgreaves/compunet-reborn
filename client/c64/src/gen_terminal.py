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

# Command dispatch table targets (from address table at $A23F)
entry_points += [
    0xA262, 0xA357, 0xA98B, 0xA351, 0xA2E9, 0xA34D, 0xADDA,
    0xA89B, 0xAC93, 0xA26F, 0xA2C2, 0xA7C4, 0xB1BC, 0xA9C4,
    0xA29C, 0xB280, 0xA91D, 0xA329, 0xBBA0, 0xA282, 0xAC80,
    0xA981, 0xAD80,
]

# Additional code regions found by analysis
entry_points += [
    0xA595,  # Code after text data
    0xA5EA,  # Code block
    0xA713,  # Code block
    0xA7B0,  # Screen init (LDA #$93; JSR CHROUT)
    0xA791,  # Called from $A7B8
    0xA983,  # Referenced from code (data table)
    0xB29F,  # JSR $FFF0 (KERNAL PLOT) — prevents mis-decode at $B2A0
    # Note: 0xB2A1 is NOT an entry point — it's the middle of JSR $FFF0
]

# Trace from all entry points
for ep in entry_points:
    trace(ep)

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
output.append('; Terminal code calls ROM routines via this jump table')
romcall_descriptions = [
    'MAIN_INIT', 'SCREEN_DRAW_INIT', 'MODEM_CHECK', 'MODEM_REG_WRITE_WAIT',
    'MODEM_REG_READ_STATUS', 'MODEM_INIT_DOWNLOAD', 'MODEM_SEND_CMD',
    'PROTOCOL_RESET', 'PROTOCOL_CLEANUP', 'SETUP_INPUT_PARAMS', 'INPUT_LINE',
    'FRAME_BUF_READ_INIT', 'FRAME_BUF_READ', 'DISK_LOAD', 'DISK_SAVE',
    'SCREEN_DRAW', 'INPUT_HANDLER', 'KEYBOARD_SCAN', 'KEY_DISPATCH',
    'COMMAND_EXEC', 'FILE_OPS', 'PRINT_STRING', 'CURSOR_HOME',
    'PRINT_STATUS_MSG', 'STATUS_CLEAR_1', 'STATUS_CLEAR_2', 'STATUS_LINE',
    'PROTOCOL_STATE_INIT', 'MODEM_STATUS_CHECK', 'FILE_UPLOAD',
    'FILE_DOWNLOAD', 'FRAME_STORE',
]
for i in range(NUM_ROMCALLS):
    addr = JUMP_TABLE_START + i * 3
    desc = romcall_descriptions[i] if i < len(romcall_descriptions) else f'UNKNOWN_{i}'
    output.append(f'ROMCALL_{i:02d}      = ${addr:04X}   ; {desc}')
output.append('')
output.append('.segment "TERMINAL"')
output.append('')

# Force-define labels that are in data regions but referenced from code
# (workaround for tracer edge cases)
forced_data_labels = {0xA983}  # Text lookup table "TCALPSL..."

# Remove A983 from entry_points to avoid tracer conflicts
entry_points = [ep for ep in entry_points if ep != 0xA983]

# Pre-pass: collect ALL internal address references so labels can be emitted
for addr in code_start:
    offset = addr - BASE
    opcode = code[offset]
    mnemonic, mode, size = OPCODES[opcode]
    if size == 3:
        target = code[offset + 1] | (code[offset + 2] << 8)
        if in_range(target) and mode in ('ABS', 'ABX', 'ABY', 'IND'):
            branch_targets.add(target)
    elif size == 2 and mode == 'REL':
        rel = code[offset + 1]
        if rel >= 128:
            rel -= 256
        target = addr + 2 + rel
        if in_range(target):
            branch_targets.add(target)

print(f"  After pre-pass: {len(branch_targets)} branch targets")

# Add forced data labels
branch_targets.update(forced_data_labels)

# Post-fix: for forced labels that the emission loop can't handle due to
# tracer conflicts, insert them directly into the output after generation
_forced_labels_to_insert = forced_data_labels.copy()

offset = 0
while offset < CODE_SIZE:
    addr = BASE + offset

    # Emit label if this is a branch target within our range AND it's code
    # (data labels are emitted inside the data emission loop)
    if addr in branch_targets and in_range(addr) and addr in code_start:
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
        # Emit data bytes — break at branch targets for label emission
        data_end = offset
        while data_end < CODE_SIZE and (BASE + data_end) not in code_start:
            data_end += 1
        # Emit in chunks, breaking at branch targets
        while offset < data_end:
            # Emit label if this position is a branch target
            if (BASE + offset) in branch_targets:
                output.append(f'{make_label(BASE + offset)}:')
            chunk_start = offset
            while offset < data_end and (offset - chunk_start) < 16:
                offset += 1
                if offset < data_end and (BASE + offset) in branch_targets:
                    break
            chunk = code[chunk_start:offset]
            byte_str = ', '.join(f'${b:02X}' for b in chunk)
            ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            addr_comment = f'${BASE+chunk_start:04X}'
            output.append(f'    .byte {byte_str.ljust(55)}; {addr_comment} {ascii_repr}')

with open(output_path, 'w') as f:
    # Post-fix: insert forced data labels that couldn't be emitted normally
    import re
    if _forced_labels_to_insert:
        new_output = []
        for line in output:
            new_output.append(line)
            # Check if this .byte line's address range includes a forced label
            if '.byte' in line and '; $' in line:
                m = re.search(r'; \$([0-9A-F]{4})', line)
                if m:
                    line_addr = int(m.group(1), 16)
                    byte_count = line.split(';')[0].count('$')
                    for lbl_addr in list(_forced_labels_to_insert):
                        if line_addr <= lbl_addr < line_addr + byte_count:
                            # This line contains the forced label address
                            # We need to split it. For simplicity, just insert
                            # the label as an equate at the top instead.
                            pass
        # Simpler approach: just add equates for forced labels
        # Find the .segment line and insert after it
        for i, line in enumerate(output):
            if '.segment' in line:
                for lbl_addr in sorted(_forced_labels_to_insert):
                    output.insert(i+2, f'{make_label(lbl_addr)} = ${lbl_addr:04X}')
                break
    f.write('\n'.join(output) + '\n')

print(f"\nOutput: {len(output)} lines -> {output_path}")
print(f"\nStatistics:")
print(f"  Code bytes:      {code_bytes}")
print(f"  Data bytes:      {data_bytes}")
print(f"  Instructions:    {len(code_start)}")
print(f"  Branch targets:  {len(branch_targets)}")
