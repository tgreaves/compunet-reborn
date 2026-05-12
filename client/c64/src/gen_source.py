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
    0x8160,  # COLD_START (reached from cartridge header vectors at $8000/$8002)
]

# Add all jump table entries ($8100-$815F, 32 x 3-byte JMP instructions)
# Also add the JMP instructions themselves as code
for i in range(32):
    addr = 0x8100 + i * 3
    entry_points.append(addr)  # The JMP instruction itself
    target = rom[addr - BASE + 1] | (rom[addr - BASE + 2] << 8)
    if 0x8000 <= target <= 0x9FFF:
        entry_points.append(target)

# Additional entry points discovered by verify_data.py
# These are routines reachable via indirect dispatch or from downloaded terminal code
entry_points += [
    # BASIC/init routines (called from COLD_START area)
    0x81BC,  # Routine after COLD_START setup
    0x8201,  # JSR $8ED0 — init routine
    0x823E,  # Called from $8216
    0x8275,  # String print sequence
    0x829E,  # Short routine (STX/STY/RTS)
    0x82A9,  # Protocol/command handler
    0x830F,  # Called from JMP $830F
    # Keyboard/input handlers
    0x8400,  # Referenced from dispatch table
    0x8439,  # JSR sequence
    0x843D,  # JSR $89E2 sequence
    # File/disk operations
    0x8541,  # File operation routine
    0x8580,  # File operation routine
    0x85D4,  # Called from $855B, $85A1, $85C4
    # Frame/screen routines
    0x875B,  # Large routine (120 insns)
    0x8779,  # Called from JMP $8779
    0x8783,  # Called from JMP $8783
    0x87B6,  # Called from JMP $87B6
    0x87F7,  # JSR $938B sequence
    # Editor/mode handlers
    0x8812,  # Referenced from dispatch table
    0x886A,  # Compare/branch dispatch
    0x88B3,  # Called from JSR $88B3
    0x88D5,  # JSR $938B / JMP $907B
    0x88EF,  # Large routine (42 insns)
    0x893E,  # LDA/STA init sequence
    0x8950,  # Called from JMP $8950
    0x895E,  # JSR $8983 sequence
    0x8983,  # Called from $890C, $895E
    0x899C,  # Routine with JSR $9093
    0x89A0,  # JSR $9093
    # Disk/buffer routines
    0x8A40,  # Short buffer routine
    0x8A94,  # JSR/BCS sequence
    0x8AAD,  # BIT/BPL/LDA/CLC/RTS
    0x8AB6,  # JSR $96CC
    # Modem/protocol routines
    0x9282,  # JSR $938B / JSR $90AF
    # NOTE: $9500-$96BF is text strings (login prompts, editor help) — NOT code
    0x993A,  # PROTO_ERROR_RECOVERY (PHA/TXA/PHA/TYA/PHA...)
    # IRQ-driven slot assembly ($9C46-$9E50)
    0x9C46,  # IRQ handler entry
    0x9C63,  # JSR $9D00 — main IRQ dispatch
    0x9C71,  # Called from JMP $9C71
    0x9C7D,  # Subroutine (LDA/CMP/BNE/CMP/BEQ/RTS)
    0x9C8F,  # JSR $9D54
    0x9C98,  # Large routine (41 insns)
    0x9D00,  # Slot assembly main (JSR $9D54)
    0x9D54,  # Byte receive/process subroutine
    0x9D80,  # LDX/JMP error handler
    0x9DA3,  # Compare/dispatch routine
    0x9DE9,  # Loop routine
    0x9E0E,  # STA/INC/STA sequence
    0x9E50,  # Called from $9DA9, $9DE0, $9E39
    # Post-connect routines
    0x9FC8,  # LDX/JSR sequence
    # Additional missed code (second pass verification)
    0x84CB,  # JSR $849B; JSR $8ABE; JMP $89DC
    0x84D3,  # Continuation after JMP
    0x8540,  # Referenced from address table
    0x857F,  # Referenced from address table
    0x869D,  # Referenced from address table
    0x88CF,  # JMP $88D5
    0x88CB,  # Dispatch target
    0x88E7,  # Dispatch target
    0x88D1,  # Dispatch target
    0x88BA,  # Dispatch target (from address table at $88BC)
    0x88DE,  # Dispatch target (from address table at $88BC)
    0x88F0,  # Dispatch target (from address table at $88BC)
    0x893D,  # Dispatch target (from address table at $88BC)
    0x9C5A,  # IRQ handler: JSR $9C7D; JSR $9C8F; JMP $9C71
    # Routines called from downloaded terminal code (not reachable from ROM alone)
    0x8760,  # Screen setup (LDA #$09; JSR CHROUT; ...)
    0x8A8D,  # Small subroutine (LDA $C1,X; BEQ; LDA #$00; RTS)
]

# The protocol dispatch table at $96C0 has 9 x JMP instructions
# Trace each one individually
for i in range(9):
    addr = 0x96C0 + i * 3
    entry_points.append(addr)

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
# Extract comments from annotated disassembly
# ============================================================

disasm_path = os.path.join(script_dir, '..', '..', '..', 'modem_bootstrap.asm')
addr_comments = {}  # addr -> inline comment for that instruction
section_comments = {}  # addr -> section header comment block

if os.path.exists(disasm_path):
    import re
    with open(disasm_path, 'r') as f:
        disasm_lines = f.readlines()
    
    current_addr = 0x8000
    pending_section = []
    
    for line in disasm_lines:
        line = line.rstrip('\n')
        
        # Section headers (lines of ===== or starting with ; that describe routines)
        if line.strip().startswith('; ====') or (line.strip().startswith(';') and 
            any(kw in line.upper() for kw in ['PROTO_', 'MODEM_', 'COLD_START', 'MAIN_INIT',
                'EDITOR', 'KEYBOARD', 'SCREEN', 'FRAME', 'DISK', 'FILE', 'INPUT', 'PRINT',
                'PROTOCOL', 'DISPATCH'])):
            pending_section.append(line)
            continue
        
        # Label lines — attach pending section comments
        if line and not line[0].isspace() and ':' in line.split(';')[0]:
            if pending_section:
                section_comments[current_addr] = pending_section[:]
                pending_section = []
            continue
        
        # .byte lines — track address
        m = re.match(r'\s+\.byte\s+([0-9A-Fa-f][0-9A-Fa-f ]+)\s*;?(.*)', line)
        if m:
            hex_bytes = m.group(1).strip().split()
            current_addr += len(hex_bytes)
            pending_section = []
            continue
        
        # Instruction lines — extract comment
        m = re.match(r'\s+([0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2}){0,2})\s{2,}(\w{3})\s*(.*)', line)
        if m:
            hex_part = m.group(1).strip()
            size = len(hex_part.split())
            rest = m.group(3).strip()
            
            # Extract comment
            if '; ' in rest:
                _, comment = rest.split('; ', 1)
                addr_comments[current_addr] = comment.strip()
            elif rest.startswith(';'):
                addr_comments[current_addr] = rest[1:].strip()
            
            if pending_section:
                section_comments[current_addr] = pending_section[:]
                pending_section = []
            
            current_addr += size
            continue
        
        # Other lines clear pending section
        if line.strip() and not line.strip().startswith(';'):
            pending_section = []

    print(f"Comments extracted: {len(addr_comments)} inline, {len(section_comments)} sections")

# Section descriptions for named labels
LABEL_DESCRIPTIONS = {
    'COLD_START': 'Initialize C64 hardware, BASIC, and install command extensions',
    'MAIN_INIT': 'Print version string, install BASIC command parser, enter READY prompt',
    'KEYBOARD_SCAN': 'Scan keyboard for input',
    'KEY_DISPATCH': 'Dispatch key press to handler',
    'INPUT_HANDLER': 'Handle user input',
    'COMMAND_EXEC': 'Execute parsed command',
    'SCREEN_DRAW': 'Render frame/page to screen',
    'FILE_OPS': 'File operations dispatcher',
    'FRAME_BUF_READ': 'Read from frame buffer',
    'FRAME_BUF_WRITE': 'Write to frame buffer',
    'DISK_LOAD': 'Load file from disk',
    'DISK_SAVE': 'Save file to disk',
    'MODEM_CHECK': 'Verify modem present, initialize hardware',
    'MODEM_INIT_DOWNLOAD': 'Receive terminal software during LINKING phase',
    'MODEM_SEND_CMD': 'Send command packet, handle disconnect states',
    'CLEAR_STATUS': 'Clear the status bar',
    'STATUS_LINE': 'Display status line',
    'PRINT_STATUS_MSG': 'Print message on status bar',
    'CURSOR_HOME': 'Move cursor to home position',
    'PRINT_STRING': 'Print null-terminated string (X=lo, Y=hi)',
    'SETUP_INPUT_PARAMS': 'Configure input line parameters',
    'INPUT_LINE': 'Read a line of user input',
    'FILE_UPLOAD': 'Upload file to server (CNSAVE)',
    'FILE_DOWNLOAD': 'Download file from server',
    'FRAME_STORE': 'Store frame data',
    'PROTOCOL_STATE_INIT': 'Initialize protocol state variables',
    'PROTOCOL_RESET': 'Reset protocol to idle state',
    'PROTOCOL_CLEANUP': 'Clean up protocol resources',
    'MODEM_STATUS_CHECK': 'Check modem status register',
    'MODEM_REG_WRITE_WAIT': 'Send bytes from $C100 buffer via protocol engine',
    'MODEM_REG_READ_STATUS': 'Read modem status into $C100 buffer',
    'MODEM_WAIT_READY': 'Wait for modem TX ready, then send byte',
    'MODEM_REG_WRITE': 'Write value to modem register (X=reg, A=value)',
    'MODEM_REG_READ': 'Read modem register (X=reg, returns A=value)',
    'PROTO_DISPATCH_TABLE': 'Protocol function dispatch (9 x JMP)',
    'PROTO_INIT_REGS': 'Initialize modem registers for protocol mode',
    'PROTO_START_SESSION': 'Start protocol session (set connected state)',
    'PROTO_DISCONNECT': 'Handle disconnect / check connection state',
    'PROTO_RECV_FRAME': 'Send one byte and process receive (called per byte)',
    'PROTO_ERROR_RECOVERY': 'Handle protocol errors, check for retransmit',
    'PROTO_PROCESS_CMD': 'Process received command — delivers one byte to caller',
    'PROTO_FLOW_CONTROL': 'Wait for response packet, check token',
    'PROTO_SEND_PACKET': 'Send complete packet with framing ($01...$02)',
    'PROTO_RECV_PACKET': 'Initialize protocol receive state',
    'PROTO_CONNECT': 'Connection handshake — wait for *CON from server',
}

# ============================================================
# Pass 2: Emit source
# ============================================================

# Address-to-equate name mapping for readable output
EQUATES = {
    0xFF84: 'KERNAL_IOINIT', 0xFF87: 'KERNAL_RAMTAS', 0xFF8A: 'KERNAL_RESTOR',
    0xFF81: 'KERNAL_CINT', 0xFFD2: 'KERNAL_CHROUT', 0xFFCF: 'KERNAL_CHRIN',
    0xFFE4: 'KERNAL_GETIN', 0xFFCC: 'KERNAL_CLRCHN', 0xFFBA: 'KERNAL_SETLFS',
    0xFFBD: 'KERNAL_SETNAM', 0xFFD5: 'KERNAL_LOAD', 0xFFD8: 'KERNAL_SAVE',
    0xFFEA: 'KERNAL_UDTIM', 0xFFE1: 'KERNAL_STOP',
    0xE453: 'BASIC_RUNC', 0xE3BF: 'BASIC_MAIN', 0xE422: 'BASIC_LINKPRG',
    0xA474: 'BASIC_READY',
    0xD020: 'VIC_BORDER', 0xD021: 'VIC_BGCOL0',
    0xDC00: 'CIA1_PRA', 0xDC01: 'CIA1_PRB', 0xDC04: 'CIA1_TALO',
    0xDC05: 'CIA1_TAHI', 0xDC0D: 'CIA1_ICR',
    0xDE00: 'ACIA_DATA', 0xDE01: 'ACIA_STATUS', 0xDE02: 'ACIA_CMD', 0xDE03: 'ACIA_CTRL',
    0x0314: 'IRQ_VECTOR', 0x0318: 'NMI_VECTOR',
}

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
        if target in EQUATES:
            return EQUATES[target]
        return f'${target:04X}'
    elif mode == 'ABX':
        target = rom[offset+1] | (rom[offset+2] << 8)
        if target in branch_targets and 0x8000 <= target <= 0x9FFF:
            return f'{make_label(target)},X'
        if target in EQUATES:
            return f'{EQUATES[target]},X'
        return f'${target:04X},X'
    elif mode == 'ABY':
        target = rom[offset+1] | (rom[offset+2] << 8)
        if target in branch_targets and 0x8000 <= target <= 0x9FFF:
            return f'{make_label(target)},Y'
        if target in EQUATES:
            return f'{EQUATES[target]},Y'
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
output.append('; --- KERNAL Routines ---')
output.append('KERNAL_IOINIT   = $FF84')
output.append('KERNAL_RAMTAS   = $FF87')
output.append('KERNAL_RESTOR   = $FF8A')
output.append('KERNAL_CINT     = $FF81')
output.append('KERNAL_CHROUT   = $FFD2')
output.append('KERNAL_CHRIN    = $FFCF')
output.append('KERNAL_GETIN    = $FFE4')
output.append('KERNAL_CLRCHN   = $FFCC')
output.append('KERNAL_SETLFS   = $FFBA')
output.append('KERNAL_SETNAM   = $FFBD')
output.append('KERNAL_LOAD     = $FFD5')
output.append('KERNAL_SAVE     = $FFD8')
output.append('KERNAL_UDTIM    = $FFEA')
output.append('KERNAL_STOP     = $FFE1')
output.append('')
output.append('; --- BASIC ROM ---')
output.append('BASIC_RUNC      = $E453')
output.append('BASIC_MAIN      = $E3BF')
output.append('BASIC_LINKPRG   = $E422')
output.append('BASIC_READY     = $A474')
output.append('')
output.append('; --- VIC-II Registers ---')
output.append('VIC_BORDER      = $D020')
output.append('VIC_BGCOL0      = $D021')
output.append('')
output.append('; --- CIA Registers ---')
output.append('CIA1_PRA        = $DC00')
output.append('CIA1_PRB        = $DC01')
output.append('CIA1_TALO       = $DC04')
output.append('CIA1_TAHI       = $DC05')
output.append('CIA1_ICR        = $DC0D')
output.append('')
output.append('; --- ACIA (SwiftLink) Registers ---')
output.append('ACIA_DATA       = $DE00')
output.append('ACIA_STATUS     = $DE01')
output.append('ACIA_CMD        = $DE02')
output.append('ACIA_CTRL       = $DE03')
output.append('')
output.append('; --- System Vectors ---')
output.append('IRQ_VECTOR      = $0314')
output.append('NMI_VECTOR      = $0318')
output.append('')
output.append('; --- Compunet Workspace ($C100-$C2FF) ---')
output.append('CMD_BUFFER      = $C100   ; Command/login buffer')
output.append('PROTO_STATE     = $C200   ; Protocol connection state')
output.append('PROTO_SEQ_TX    = $C20E   ; Transmit sequence number')
output.append('PROTO_SEQ_RX    = $C20F   ; Expected receive sequence')
output.append('PROTO_SLOT_SEQ  = $C228   ; Slot sequence numbers (4 slots)')
output.append('PROTO_SLOT_FLAG = $C22C   ; Slot status flags (4 slots)')
output.append('PROTO_SLOT_IDX  = $C209   ; Current slot index')
output.append('PROTO_PKT_HDR   = $C203   ; Packet header buffer (6 bytes)')
output.append('PROTO_FLAGS     = $8038   ; Protocol state flags')
output.append('')
output.append('; --- NMI Ring Buffer ---')
output.append('NMI_BUF         = $CE00   ; 256-byte ring buffer')
output.append('NMI_BUF_TAIL    = $029B   ; Write pointer (NMI handler advances)')
output.append('NMI_BUF_HEAD    = $029C   ; Read pointer (main code advances)')
output.append('')
output.append('.segment "HEADER"')
output.append('')

offset = 0
while offset < 8192:
    addr = BASE + offset
    
    # Emit section header if this address has one
    if addr in section_comments:
        output.append('')
        for comment_line in section_comments[addr]:
            output.append(comment_line)
    
    # Emit label if needed (branch target OR named label)
    if addr in branch_targets or addr in named_addrs:
        label = make_label(addr)
        # Add description comment for named labels
        if label in LABEL_DESCRIPTIONS:
            output.append('')
            output.append(f'; --- {label} ---')
            output.append(f'; {LABEL_DESCRIPTIONS[label]}')
        output.append(f'{label}:')
    
    if is_code[offset]:
        # Emit instruction
        opcode = rom[offset]
        mnemonic, mode, size = OPCODES[opcode]
        operand = format_operand(mnemonic, mode, rom, offset, addr)
        
        if operand:
            line = f'    {mnemonic} {operand}'
        else:
            line = f'    {mnemonic}'
        
        # Add inline comment from disassembly
        if addr in addr_comments:
            line = line.ljust(40) + f'; {addr_comments[addr]}'
        
        output.append(line)
        offset += size
    else:
        # Emit data bytes (group consecutive non-code bytes)
        data_start = offset
        while offset < 8192 and not is_code[offset] and (BASE + offset) not in branch_targets and (BASE + offset) not in named_addrs:
            offset += 1
            if (offset - data_start) >= 16:
                break
        
        # Safety: ensure we advance at least 1 byte
        if offset == data_start:
            offset += 1
        
        chunk = rom[data_start:offset]
        byte_str = ', '.join(f'${b:02X}' for b in chunk)
        ascii_repr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        output.append(f'    .byte {byte_str}  ; ${BASE+data_start:04X} {ascii_repr}')

with open(output_path, 'w') as f:
    f.write('\n'.join(output) + '\n')

print(f"Output: {len(output)} lines → {output_path}")
