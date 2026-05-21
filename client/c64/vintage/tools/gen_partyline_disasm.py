"""
Generate ca65 source by disassembling the Compunet Partyline Demo PRG.

Uses recursive descent: starts from the entry point ($0868), follows all
branches/jumps to identify code. Everything else is emitted as .byte data.

Two passes:
  Pass 1: Identify all code bytes (recursive descent from entry points)
  Pass 2: Emit source with mnemonics for code, .byte for data

The partyline demo is a standalone program that loads at $0801 (standard
BASIC area) with a SYS 2152 ($0868) stub. It's a chat/party-line demo
with UI elements, text strings, and screen data.
"""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
prg_path = os.path.join(script_dir, '..', '..', '..', '..', 'historical', 'partyline-demo.prg')
output_path = os.path.join(script_dir, 'partyline_demo.s')

with open(prg_path, 'rb') as f:
    prg_data = f.read()

# Strip 2-byte PRG load address header ($01 $08 = $0801 little-endian)
load_addr = prg_data[0] | (prg_data[1] << 8)
assert load_addr == 0x0801, f"Expected PRG header $0801, got ${load_addr:04X}"
code = prg_data[2:]

BASE = 0x0801
CODE_SIZE = len(code)
END_ADDR = BASE + CODE_SIZE  # exclusive

ENTRY_POINT = 0x0868
BASIC_STUB_END = 0x080F  # First byte after BASIC stub (zeros start here)

print(f"Partyline Demo: {CODE_SIZE} bytes, ${BASE:04X}-${END_ADDR-1:04X}")
print(f"Entry point: ${ENTRY_POINT:04X} (SYS 2152)")

# ============================================================
# C64 Hardware and KERNAL equates
# ============================================================

C64_EQUATES = {
    # VIC-II registers ($D000-$D02E)
    0xD000: 'VIC_SPR0_X',
    0xD001: 'VIC_SPR0_Y',
    0xD002: 'VIC_SPR1_X',
    0xD003: 'VIC_SPR1_Y',
    0xD004: 'VIC_SPR2_X',
    0xD005: 'VIC_SPR2_Y',
    0xD006: 'VIC_SPR3_X',
    0xD007: 'VIC_SPR3_Y',
    0xD008: 'VIC_SPR4_X',
    0xD009: 'VIC_SPR4_Y',
    0xD00A: 'VIC_SPR5_X',
    0xD00B: 'VIC_SPR5_Y',
    0xD00C: 'VIC_SPR6_X',
    0xD00D: 'VIC_SPR6_Y',
    0xD00E: 'VIC_SPR7_X',
    0xD00F: 'VIC_SPR7_Y',
    0xD010: 'VIC_SPR_XMSB',
    0xD011: 'VIC_CTRL1',
    0xD012: 'VIC_RASTER',
    0xD013: 'VIC_LIGHT_X',
    0xD014: 'VIC_LIGHT_Y',
    0xD015: 'VIC_SPR_ENA',
    0xD016: 'VIC_CTRL2',
    0xD017: 'VIC_SPR_YEXP',
    0xD018: 'VIC_MEMPTR',
    0xD019: 'VIC_IRQ',
    0xD01A: 'VIC_IRQMASK',
    0xD01B: 'VIC_SPR_PRIO',
    0xD01C: 'VIC_SPR_MCOLOR',
    0xD01D: 'VIC_SPR_XEXP',
    0xD01E: 'VIC_SPR_COLL',
    0xD01F: 'VIC_SPR_BG_COLL',
    0xD020: 'VIC_BORDER',
    0xD021: 'VIC_BG0',
    0xD022: 'VIC_BG1',
    0xD023: 'VIC_BG2',
    0xD024: 'VIC_BG3',
    0xD025: 'VIC_SPR_MCOL0',
    0xD026: 'VIC_SPR_MCOL1',
    0xD027: 'VIC_SPR0_COL',
    0xD028: 'VIC_SPR1_COL',
    0xD029: 'VIC_SPR2_COL',
    0xD02A: 'VIC_SPR3_COL',
    0xD02B: 'VIC_SPR4_COL',
    0xD02C: 'VIC_SPR5_COL',
    0xD02D: 'VIC_SPR6_COL',
    0xD02E: 'VIC_SPR7_COL',
    # SID registers ($D400-$D418)
    0xD400: 'SID_V1_FREQ_LO',
    0xD401: 'SID_V1_FREQ_HI',
    0xD402: 'SID_V1_PW_LO',
    0xD403: 'SID_V1_PW_HI',
    0xD404: 'SID_V1_CTRL',
    0xD405: 'SID_V1_AD',
    0xD406: 'SID_V1_SR',
    0xD407: 'SID_V2_FREQ_LO',
    0xD408: 'SID_V2_FREQ_HI',
    0xD409: 'SID_V2_PW_LO',
    0xD40A: 'SID_V2_PW_HI',
    0xD40B: 'SID_V2_CTRL',
    0xD40C: 'SID_V2_AD',
    0xD40D: 'SID_V2_SR',
    0xD40E: 'SID_V3_FREQ_LO',
    0xD40F: 'SID_V3_FREQ_HI',
    0xD410: 'SID_V3_PW_LO',
    0xD411: 'SID_V3_PW_HI',
    0xD412: 'SID_V3_CTRL',
    0xD413: 'SID_V3_AD',
    0xD414: 'SID_V3_SR',
    0xD415: 'SID_FILT_LO',
    0xD416: 'SID_FILT_HI',
    0xD417: 'SID_FILT_CTRL',
    0xD418: 'SID_VOL',
    # Colour RAM
    0xD800: 'COLOR_RAM',
    # CIA1 ($DC00-$DC0F)
    0xDC00: 'CIA1_PRA',
    0xDC01: 'CIA1_PRB',
    0xDC02: 'CIA1_DDRA',
    0xDC03: 'CIA1_DDRB',
    0xDC04: 'CIA1_TIMER_A_LO',
    0xDC05: 'CIA1_TIMER_A_HI',
    0xDC06: 'CIA1_TIMER_B_LO',
    0xDC07: 'CIA1_TIMER_B_HI',
    0xDC08: 'CIA1_TOD_10TH',
    0xDC09: 'CIA1_TOD_SEC',
    0xDC0A: 'CIA1_TOD_MIN',
    0xDC0B: 'CIA1_TOD_HR',
    0xDC0C: 'CIA1_SDR',
    0xDC0D: 'CIA1_ICR',
    0xDC0E: 'CIA1_CRA',
    0xDC0F: 'CIA1_CRB',
    # CIA2 ($DD00-$DD0F)
    0xDD00: 'CIA2_PRA',
    0xDD01: 'CIA2_PRB',
    0xDD02: 'CIA2_DDRA',
    0xDD03: 'CIA2_DDRB',
    0xDD04: 'CIA2_TIMER_A_LO',
    0xDD05: 'CIA2_TIMER_A_HI',
    0xDD06: 'CIA2_TIMER_B_LO',
    0xDD07: 'CIA2_TIMER_B_HI',
    0xDD08: 'CIA2_TOD_10TH',
    0xDD09: 'CIA2_TOD_SEC',
    0xDD0A: 'CIA2_TOD_MIN',
    0xDD0B: 'CIA2_TOD_HR',
    0xDD0C: 'CIA2_SDR',
    0xDD0D: 'CIA2_ICR',
    0xDD0E: 'CIA2_CRA',
    0xDD0F: 'CIA2_CRB',
    # KERNAL routines
    0xFF81: 'KERNAL_CINT',
    0xFF84: 'KERNAL_IOINIT',
    0xFF87: 'KERNAL_RAMTAS',
    0xFF8A: 'KERNAL_RESTOR',
    0xFF8D: 'KERNAL_VECTOR',
    0xFF90: 'KERNAL_SETMSG',
    0xFF93: 'KERNAL_SECOND',
    0xFF96: 'KERNAL_TKSA',
    0xFF99: 'KERNAL_MEMTOP',
    0xFF9C: 'KERNAL_MEMBOT',
    0xFF9F: 'KERNAL_SCNKEY',
    0xFFA2: 'KERNAL_SETTMO',
    0xFFA5: 'KERNAL_ACPTR',
    0xFFA8: 'KERNAL_CIOUT',
    0xFFAB: 'KERNAL_UNTLK',
    0xFFAE: 'KERNAL_UNLSN',
    0xFFB1: 'KERNAL_LISTEN',
    0xFFB4: 'KERNAL_TALK',
    0xFFB7: 'KERNAL_READST',
    0xFFBA: 'KERNAL_SETLFS',
    0xFFBD: 'KERNAL_SETNAM',
    0xFFC0: 'KERNAL_OPEN',
    0xFFC3: 'KERNAL_CLOSE',
    0xFFC6: 'KERNAL_CHKIN',
    0xFFC9: 'KERNAL_CHKOUT',
    0xFFCC: 'KERNAL_CLRCHN',
    0xFFCF: 'KERNAL_CHRIN',
    0xFFD2: 'KERNAL_CHROUT',
    0xFFD5: 'KERNAL_LOAD',
    0xFFD8: 'KERNAL_SAVE',
    0xFFDB: 'KERNAL_SETTIM',
    0xFFDE: 'KERNAL_RDTIM',
    0xFFE1: 'KERNAL_STOP',
    0xFFE4: 'KERNAL_GETIN',
    0xFFE7: 'KERNAL_CLALL',
    0xFFEA: 'KERNAL_UDTIM',
    0xFFF0: 'KERNAL_PLOT',
    # Common zero-page locations
}

# Screen RAM location (default)
SCREEN_RAM = 0x0400

# ============================================================
# 6502 instruction table: opcode -> (mnemonic, addressing_mode, size)
# ============================================================
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
    """Check if address is within the program range."""
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
        operand_byte = 0
        operand_word = 0
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
        elif mnemonic == 'JMP' and mode == 'IND':
            # Indirect jump - can't follow statically, stop
            pass
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
entry_points = [ENTRY_POINT]

# Trace from all entry points
for ep in entry_points:
    trace(ep)

# Iteratively discover more code by following JSR/JMP targets
found_more = True
iterations = 0
while found_more and iterations < 20:
    found_more = False
    iterations += 1
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
    # Don't trace anything in the BASIC stub or zero gap
    table_targets = {t for t in table_targets if t >= ENTRY_POINT}
    if not table_targets:
        break
    old_count = len(code_start)
    for target in table_targets:
        trace(target)
    if len(code_start) == old_count:
        break

# Also try scanning for RTS-separated code blocks after known code
# (common pattern: subroutine ends with RTS, next one starts immediately)
def scan_after_rts():
    """Find code that starts immediately after an RTS instruction."""
    new_entries = set()
    for addr in sorted(code_start):
        offset = addr - BASE
        opcode = code[offset]
        if opcode not in OPCODES:
            continue
        mnemonic, mode, size = OPCODES[opcode]
        if mnemonic == 'RTS':
            next_offset = offset + size
            next_addr = BASE + next_offset
            if next_addr >= ENTRY_POINT and next_offset < CODE_SIZE and not is_code[next_offset]:
                next_opcode = code[next_offset]
                if next_opcode in OPCODES:
                    # Verify it's plausible code
                    test_off = next_offset
                    valid_insns = 0
                    for _ in range(5):
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
                        new_entries.add(next_addr)
    return new_entries

# Run RTS-following passes
for _ in range(10):
    rts_targets = scan_after_rts()
    if not rts_targets:
        break
    old_count = len(code_start)
    for target in rts_targets:
        trace(target)
    if len(code_start) == old_count:
        break

# Re-run address table scan after RTS discovery
for _ in range(3):
    table_targets = scan_for_address_tables()
    table_targets = {t for t in table_targets if t >= ENTRY_POINT}
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
# String detection heuristic
# ============================================================

def is_petscii_printable(b):
    """Check if a byte is a printable PETSCII character."""
    # Standard ASCII printable range (space through tilde)
    if 0x20 <= b <= 0x7E:
        return True
    # PETSCII upper-case letters (shifted) $C1-$DA
    if 0xC1 <= b <= 0xDA:
        return True
    # Common control codes used in strings
    if b in (0x0D, 0x0A, 0x00):  # CR, LF, null terminator
        return True
    # PETSCII colour/control codes commonly embedded in strings
    if b in (0x05, 0x1C, 0x1E, 0x1F, 0x81, 0x90, 0x91, 0x92, 0x93,
             0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C,
             0x9D, 0x9E, 0x9F):
        return True
    return False

def petscii_to_display(b):
    """Convert PETSCII byte to display character for comments."""
    if 0x20 <= b <= 0x7E:
        return chr(b)
    if 0xC1 <= b <= 0xDA:
        return chr(b - 0xC0 + 0x40)  # Map to uppercase ASCII
    ctrl_names = {
        0x00: '<NUL>', 0x0D: '<CR>', 0x0A: '<LF>',
        0x05: '<WHT>', 0x1C: '<RED>', 0x1E: '<GRN>', 0x1F: '<BLU>',
        0x81: '<ORG>', 0x90: '<BLK>', 0x91: '<UP>', 0x92: '<RVOFF>',
        0x93: '<CLR>', 0x94: '<INS>', 0x95: '<BRN>', 0x96: '<LRED>',
        0x97: '<GRY1>', 0x98: '<GRY2>', 0x99: '<LGRN>', 0x9A: '<LBLU>',
        0x9B: '<GRY3>', 0x9C: '<PUR>', 0x9D: '<LEFT>', 0x9E: '<YEL>',
        0x9F: '<CYN>',
    }
    if b in ctrl_names:
        return ctrl_names[b]
    return f'<${b:02X}>'

# Identify likely string regions in data areas
MIN_STRING_LEN = 4

def detect_strings(data_start_offset, data_end_offset):
    """Detect runs of printable PETSCII in a data region.
    Returns list of (start_offset, end_offset) tuples."""
    strings = []
    i = data_start_offset
    while i < data_end_offset:
        if is_code[i]:
            i += 1
            continue
        # Check for string start
        run_start = i
        printable_count = 0
        while i < data_end_offset and not is_code[i]:
            b = code[i]
            if is_petscii_printable(b):
                printable_count += 1
                i += 1
            elif b == 0x00 and printable_count >= MIN_STRING_LEN:
                # Null terminator after sufficient printable chars
                i += 1
                break
            else:
                break
        if printable_count >= MIN_STRING_LEN:
            strings.append((run_start, i))
        else:
            i = run_start + 1
    return strings


# ============================================================
# Pass 2: Emit source
# ============================================================

# Pre-pass: collect ALL internal address references so labels can be emitted
for addr in list(code_start):
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
        # C64 hardware equates
        if target in C64_EQUATES:
            return C64_EQUATES[target]
        # Colour RAM range (use base + offset)
        if 0xD800 < target <= 0xDBFF:
            return f'COLOR_RAM+${target-0xD800:04X}'
        # Internal references
        if in_range(target):
            return make_label(target)
        return f'${target:04X}'
    elif mode == 'ABX':
        target = code[offset+1] | (code[offset+2] << 8)
        if target in C64_EQUATES:
            return f'{C64_EQUATES[target]},X'
        if 0xD800 < target <= 0xDBFF:
            return f'COLOR_RAM+${target-0xD800:04X},X'
        if in_range(target):
            return f'{make_label(target)},X'
        return f'${target:04X},X'
    elif mode == 'ABY':
        target = code[offset+1] | (code[offset+2] << 8)
        if target in C64_EQUATES:
            return f'{C64_EQUATES[target]},Y'
        if 0xD800 < target <= 0xDBFF:
            return f'COLOR_RAM+${target-0xD800:04X},Y'
        if in_range(target):
            return f'{make_label(target)},Y'
        return f'${target:04X},Y'
    elif mode == 'IND':
        target = code[offset+1] | (code[offset+2] << 8)
        if target in C64_EQUATES:
            return f'({C64_EQUATES[target]})'
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


# Build output
output = []
output.append('; =================================================================')
output.append('; COMPUNET PARTYLINE DEMO - Disassembly')
output.append('; =================================================================')
output.append('; Assembler: ca65 (cc65 suite)')
output.append('; Load address: $0801 (standard BASIC area)')
output.append('; Entry point:  $0868 (SYS 2152)')
output.append(f'; Size:         {CODE_SIZE} bytes (${BASE:04X}-${END_ADDR-1:04X})')
output.append('; Auto-generated by gen_partyline_disasm.py')
output.append('; =================================================================')
output.append('')

# Emit hardware equates
output.append('; --- C64 Hardware Equates ---')
output.append('')
output.append('; VIC-II ($D000-$D02E)')
vic_equates = [(a, n) for a, n in sorted(C64_EQUATES.items()) if 0xD000 <= a <= 0xD02E]
for addr, name in vic_equates:
    output.append(f'{name:20s} = ${addr:04X}')
output.append('')

output.append('; SID ($D400-$D418)')
sid_equates = [(a, n) for a, n in sorted(C64_EQUATES.items()) if 0xD400 <= a <= 0xD418]
for addr, name in sid_equates:
    output.append(f'{name:20s} = ${addr:04X}')
output.append('')

output.append('; Colour RAM')
output.append(f'{"COLOR_RAM":20s} = $D800')
output.append('')

output.append('; CIA1 ($DC00-$DC0F)')
cia1_equates = [(a, n) for a, n in sorted(C64_EQUATES.items()) if 0xDC00 <= a <= 0xDC0F]
for addr, name in cia1_equates:
    output.append(f'{name:20s} = ${addr:04X}')
output.append('')

output.append('; CIA2 ($DD00-$DD0F)')
cia2_equates = [(a, n) for a, n in sorted(C64_EQUATES.items()) if 0xDD00 <= a <= 0xDD0F]
for addr, name in cia2_equates:
    output.append(f'{name:20s} = ${addr:04X}')
output.append('')

output.append('; KERNAL Routines')
kernal_equates = [(a, n) for a, n in sorted(C64_EQUATES.items()) if 0xFF00 <= a <= 0xFFFF]
for addr, name in kernal_equates:
    output.append(f'{name:20s} = ${addr:04X}')
output.append('')

output.append('; --- Screen RAM ---')
output.append(f'{"SCREEN_RAM":20s} = $0400')
output.append('')

# Collect labels that will be defined inline during emission
# (at branch_targets that start a code_start or are at a data chunk boundary).
# Any remaining undefined labels get emitted as equates here.
# We'll do this as a post-pass after generating the main output.
# Placeholder - equates will be inserted here after main emission.
equate_insert_index = len(output)

# Segment directive
output.append('.segment "CODE"')
output.append('')
output.append(f'; Load address: ${BASE:04X}')
output.append(f'.org ${BASE:04X}')
output.append('')

# BASIC stub ($0801 - $080E)
output.append('; --- BASIC Stub: 10 SYS 2152 ---')
basic_stub = code[0:14]  # $0801 to $080E inclusive (14 bytes)
byte_str = ', '.join(f'${b:02X}' for b in basic_stub)
output.append(f'    .byte {byte_str}')
output.append('')

# Zero-filled gap ($080F - $0867), splitting at any branch targets
gap_start_offset = 0x080F - BASE  # offset 14
gap_end_offset = 0x0868 - BASE    # offset 103
output.append(f'; --- Zero-filled gap (${0x080F:04X}-${0x0867:04X}) ---')
gap_pos = gap_start_offset
while gap_pos < gap_end_offset:
    gap_addr = BASE + gap_pos
    if gap_addr in branch_targets:
        output.append(f'{make_label(gap_addr)}:')
    # Find next label or end of gap
    next_break = gap_end_offset
    for check_pos in range(gap_pos + 1, gap_end_offset):
        if (BASE + check_pos) in branch_targets:
            next_break = check_pos
            break
    chunk_size = next_break - gap_pos
    output.append(f'    .res {chunk_size}, $00')
    gap_pos = next_break
output.append('')

# Main code/data from $0868 onwards
output.append('; =================================================================')
output.append('; MAIN CODE - Entry point at $0868')
output.append('; =================================================================')
output.append('')

offset = ENTRY_POINT - BASE
while offset < CODE_SIZE:
    addr = BASE + offset

    # Emit label if this is a branch target
    label_emitted_this_iter = False
    if addr in branch_targets and in_range(addr):
        output.append(f'{make_label(addr)}:')
        label_emitted_this_iter = True

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
        # Emit data bytes - break at branch targets for label emission
        data_end = offset
        while data_end < CODE_SIZE and (BASE + data_end) not in code_start:
            data_end += 1

        # Check for strings in this data region
        strings = detect_strings(offset, data_end)
        # Build a set of offsets that are within string regions, and a
        # mapping from each offset in a string to its string end
        in_string_end = {}  # offset -> string_end for offsets inside strings
        for s_start, s_end in strings:
            for i in range(s_start, s_end):
                in_string_end[i] = s_end

        # Emit data in chunks, always breaking at branch targets
        first_data_byte = True
        while offset < data_end:
            # Emit label if this position is a branch target
            # (skip if already emitted by the outer loop on the first iteration)
            if (BASE + offset) in branch_targets:
                if not (first_data_byte and label_emitted_this_iter):
                    output.append(f'{make_label(BASE + offset)}:')
            first_data_byte = False

            # Check if this is a zero-fill region (8+ consecutive zeros)
            if code[offset] == 0x00:
                zero_start = offset
                zero_end = offset
                while zero_end < data_end and code[zero_end] == 0x00:
                    zero_end += 1
                    if (BASE + zero_end) in branch_targets:
                        break
                zero_count = zero_end - zero_start
                if zero_count >= 8:
                    output.append(f'    .res {zero_count}, $00        ; ${BASE+zero_start:04X} ({zero_count} zero bytes)')
                    offset = zero_end
                    continue
                # Too few zeros, fall through to emit as .byte

            # Check if we're in a string region
            if offset in in_string_end:
                s_end = in_string_end[offset]
                # Determine line end: min of 16 bytes, s_end, or next branch target
                line_end = min(offset + 16, s_end)
                for i in range(offset + 1, line_end):
                    if (BASE + i) in branch_targets:
                        line_end = i
                        break
                line_chunk = code[offset:line_end]
                byte_str = ', '.join(f'${b:02X}' for b in line_chunk)
                disp = ''.join(petscii_to_display(b) for b in line_chunk)
                addr_comment = f'${BASE+offset:04X}'
                output.append(f'    .byte {byte_str.ljust(55)}; {addr_comment} "{disp}"')
                offset = line_end
                continue

            # Regular data bytes - break at branch targets, strings, and 16-byte boundary
            chunk_start = offset
            chunk_end = offset
            while chunk_end < data_end and (chunk_end - chunk_start) < 16:
                chunk_end += 1
                if chunk_end < data_end and (BASE + chunk_end) in branch_targets:
                    break
                # Don't cross into a string region
                if chunk_end in in_string_end and chunk_end not in in_string_end.get(chunk_start, {}):
                    # Only break if this is the START of a new string
                    if chunk_end not in in_string_end or (chunk_start not in in_string_end):
                        break
                    break
            chunk = code[chunk_start:chunk_end]
            if len(chunk) == 0:
                offset += 1
                continue
            byte_str = ', '.join(f'${b:02X}' for b in chunk)
            ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            addr_comment = f'${BASE+chunk_start:04X}'
            output.append(f'    .byte {byte_str.ljust(55)}; {addr_comment} {ascii_repr}')
            offset = chunk_end

# Post-pass: find labels that are referenced but never defined inline,
# and emit them as equates near the top of the file.
import re

output_text = '\n'.join(output)
defined_labels = set(re.findall(r'^(L_[0-9A-F]{4}):', output_text, re.MULTILINE))
referenced_labels = set(re.findall(r'\b(L_[0-9A-F]{4})\b', output_text))
undefined_labels = referenced_labels - defined_labels

if undefined_labels:
    equates = []
    equates.append('; --- Equates for labels inside multi-byte instructions or unreachable positions ---')
    for lbl in sorted(undefined_labels):
        addr = int(lbl[2:], 16)
        equates.append(f'{lbl:20s} = ${addr:04X}')
    equates.append('')
    # Insert at the equate_insert_index position
    for i, eq_line in enumerate(equates):
        output.insert(equate_insert_index + i, eq_line)
    print(f"  Added {len(undefined_labels)} equates for unreachable labels")

# Write output
with open(output_path, 'w') as f:
    f.write('\n'.join(output) + '\n')

print(f"\nOutput: {len(output)} lines -> {output_path}")
print(f"\nStatistics:")
print(f"  Code bytes:      {code_bytes}")
print(f"  Data bytes:      {data_bytes}")
print(f"  Instructions:    {len(code_start)}")
print(f"  Branch targets:  {len(branch_targets)}")
