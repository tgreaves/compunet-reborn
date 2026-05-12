"""
Verify that .byte regions in the generated source don't contain hidden code.

Strategy:
1. Re-run the tracer to get the is_code[] map
2. Scan all non-code regions for suspicious patterns:
   - JSR $xxxx where target is within ROM ($8000-$9FFF)
   - JMP $xxxx where target is within ROM
   - Sequences of valid opcodes that form plausible instruction runs
3. Report any suspicious regions as potential missed entry points
4. Optionally add them to the tracer and re-verify

This does NOT modify gen_source.py — it's a read-only verification pass.
"""
import os
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
rom_path = os.path.join(script_dir, 'original_rom.bin')

with open(rom_path, 'rb') as f:
    rom = f.read()

BASE = 0x8000
ROM_SIZE = 8192

# ============================================================
# Minimal opcode table (same as gen_source.py)
# ============================================================
OPCODES = {}

def _add(opcode, mnemonic, mode, size):
    OPCODES[opcode] = (mnemonic, mode, size)

for op, mn in [(0x00,'BRK'),(0x08,'PHP'),(0x0A,'ASL'),(0x18,'CLC'),(0x28,'PLP'),
               (0x2A,'ROL'),(0x38,'SEC'),(0x40,'RTI'),(0x48,'PHA'),(0x4A,'LSR'),
               (0x58,'CLI'),(0x60,'RTS'),(0x68,'PLA'),(0x6A,'ROR'),(0x78,'SEI'),
               (0x88,'DEY'),(0x8A,'TXA'),(0x98,'TYA'),(0x9A,'TXS'),(0xA8,'TAY'),
               (0xAA,'TAX'),(0xB8,'CLV'),(0xBA,'TSX'),(0xC8,'INY'),(0xCA,'DEX'),
               (0xD8,'CLD'),(0xE8,'INX'),(0xEA,'NOP'),(0xF8,'SED')]:
    _add(op, mn, 'IMP', 1)

for op, mn in [(0x09,'ORA'),(0x29,'AND'),(0x49,'EOR'),(0x69,'ADC'),(0xA0,'LDY'),
               (0xA2,'LDX'),(0xA9,'LDA'),(0xC0,'CPY'),(0xC9,'CMP'),(0xE0,'CPX'),
               (0xE9,'SBC')]:
    _add(op, mn, 'IMM', 2)

for op, mn in [(0x05,'ORA'),(0x06,'ASL'),(0x24,'BIT'),(0x25,'AND'),(0x26,'ROL'),
               (0x45,'EOR'),(0x46,'LSR'),(0x65,'ADC'),(0x66,'ROR'),(0x84,'STY'),
               (0x85,'STA'),(0x86,'STX'),(0xA4,'LDY'),(0xA5,'LDA'),(0xA6,'LDX'),
               (0xC4,'CPY'),(0xC5,'CMP'),(0xC6,'DEC'),(0xE4,'CPX'),(0xE5,'SBC'),
               (0xE6,'INC')]:
    _add(op, mn, 'ZP', 2)

for op, mn in [(0x15,'ORA'),(0x16,'ASL'),(0x35,'AND'),(0x36,'ROL'),(0x55,'EOR'),
               (0x56,'LSR'),(0x75,'ADC'),(0x76,'ROR'),(0x94,'STY'),(0x95,'STA'),
               (0xB4,'LDY'),(0xB5,'LDA'),(0xD5,'CMP'),(0xD6,'DEC'),(0xF5,'SBC'),
               (0xF6,'INC')]:
    _add(op, mn, 'ZPX', 2)

for op, mn in [(0x96,'STX'),(0xB6,'LDX')]:
    _add(op, mn, 'ZPY', 2)

for op, mn in [(0x0D,'ORA'),(0x0E,'ASL'),(0x20,'JSR'),(0x2C,'BIT'),(0x2D,'AND'),
               (0x2E,'ROL'),(0x4C,'JMP'),(0x4D,'EOR'),(0x4E,'LSR'),(0x6D,'ADC'),
               (0x6E,'ROR'),(0x8C,'STY'),(0x8D,'STA'),(0x8E,'STX'),(0xAC,'LDY'),
               (0xAD,'LDA'),(0xAE,'LDX'),(0xCC,'CPY'),(0xCD,'CMP'),(0xCE,'DEC'),
               (0xEC,'CPX'),(0xED,'SBC'),(0xEE,'INC')]:
    _add(op, mn, 'ABS', 3)

for op, mn in [(0x1D,'ORA'),(0x1E,'ASL'),(0x3D,'AND'),(0x3E,'ROL'),(0x5D,'EOR'),
               (0x5E,'LSR'),(0x7D,'ADC'),(0x7E,'ROR'),(0x9D,'STA'),(0xBC,'LDY'),
               (0xBD,'LDA'),(0xDD,'CMP'),(0xDE,'DEC'),(0xFD,'SBC'),(0xFE,'INC')]:
    _add(op, mn, 'ABX', 3)

for op, mn in [(0x19,'ORA'),(0x39,'AND'),(0x59,'EOR'),(0x79,'ADC'),(0x99,'STA'),
               (0xB9,'LDA'),(0xBE,'LDX'),(0xD9,'CMP'),(0xF9,'SBC')]:
    _add(op, mn, 'ABY', 3)

_add(0x6C, 'JMP', 'IND', 3)

for op, mn in [(0x01,'ORA'),(0x21,'AND'),(0x41,'EOR'),(0x61,'ADC'),(0x81,'STA'),
               (0xA1,'LDA'),(0xC1,'CMP'),(0xE1,'SBC')]:
    _add(op, mn, 'IZX', 2)

for op, mn in [(0x11,'ORA'),(0x31,'AND'),(0x51,'EOR'),(0x71,'ADC'),(0x91,'STA'),
               (0xB1,'LDA'),(0xD1,'CMP'),(0xF1,'SBC')]:
    _add(op, mn, 'IZY', 2)

for op, mn in [(0x10,'BPL'),(0x30,'BMI'),(0x50,'BVC'),(0x70,'BVS'),
               (0x90,'BCC'),(0xB0,'BCS'),(0xD0,'BNE'),(0xF0,'BEQ')]:
    _add(op, mn, 'REL', 2)


# ============================================================
# Re-run the tracer (same logic as gen_source.py)
# ============================================================

is_code = [False] * ROM_SIZE
code_start = set()
branch_targets = set()

entry_points = [0x8009, 0x8160]

# Jump table entries
for i in range(32):
    addr = 0x8100 + i * 3
    entry_points.append(addr)  # The JMP instruction itself
    offset = addr - BASE
    if offset + 2 < ROM_SIZE:
        target = rom[offset + 1] | (rom[offset + 2] << 8)
        if 0x8000 <= target <= 0x9FFF:
            entry_points.append(target)

# Additional entry points (same as gen_source.py)
entry_points += [
    0x81BC, 0x8201, 0x823E, 0x8275, 0x829E, 0x82A9, 0x830F,
    0x8400, 0x8439, 0x843D,
    0x8541, 0x8580, 0x85D4,
    0x875B, 0x8779, 0x8783, 0x87B6, 0x87F7,
    0x8812, 0x886A, 0x88B3, 0x88D5, 0x88EF, 0x893E, 0x8950, 0x895E, 0x8983, 0x899C, 0x89A0,
    0x8A40, 0x8A94, 0x8AAD, 0x8AB6,
    0x9282,
    0x993A,
    0x9C46, 0x9C63, 0x9C71, 0x9C7D, 0x9C8F, 0x9C98, 0x9D00, 0x9D54, 0x9D80, 0x9DA3, 0x9DE9, 0x9E0E, 0x9E50,
    0x9FC8,
    # Second pass
    0x84CB, 0x84D3, 0x8540, 0x857F, 0x869D, 0x88CF, 0x88CB, 0x88E7, 0x88D1,
    0x88BA, 0x88DE, 0x88F0, 0x893D,
    0x9C5A,
    0x8760,
    0x8A8D,
]

# Protocol dispatch table (9 x JMP)
for i in range(9):
    entry_points.append(0x96C0 + i * 3)

def trace(start_addr):
    queue = [start_addr]
    while queue:
        addr = queue.pop()
        offset = addr - BASE
        if offset < 0 or offset >= ROM_SIZE:
            continue
        if is_code[offset]:
            continue
        opcode = rom[offset]
        if opcode not in OPCODES:
            continue
        mnemonic, mode, size = OPCODES[opcode]
        if offset + size > ROM_SIZE:
            continue
        for i in range(size):
            is_code[offset + i] = True
        code_start.add(addr)
        
        if size == 2:
            operand_byte = rom[offset + 1]
        elif size == 3:
            operand_word = rom[offset + 1] | (rom[offset + 2] << 8)
        
        if mode == 'REL':
            rel = operand_byte
            if rel >= 128:
                rel -= 256
            target = addr + 2 + rel
            branch_targets.add(target)
            queue.append(target)
            queue.append(addr + size)
        elif mnemonic == 'JMP' and mode == 'ABS':
            target = operand_word
            branch_targets.add(target)
            if 0x8000 <= target <= 0x9FFF:
                queue.append(target)
        elif mnemonic == 'JSR':
            target = operand_word
            branch_targets.add(target)
            if 0x8000 <= target <= 0x9FFF:
                queue.append(target)
            queue.append(addr + size)
        elif mnemonic in ('RTS', 'RTI', 'BRK'):
            pass
        else:
            queue.append(addr + size)

for ep in entry_points:
    trace(ep)

total_code = sum(is_code)
total_data = ROM_SIZE - total_code
print(f"Tracer results: {total_code} code bytes, {total_data} data bytes")
print()

# ============================================================
# Scan data regions for suspicious patterns
# ============================================================

# Check 1: JSR/JMP to ROM addresses in data regions
print("=" * 60)
print("CHECK 1: JSR/JMP opcodes in data regions targeting ROM")
print("=" * 60)

suspicious_jumps = []
offset = 0
while offset < ROM_SIZE:
    if not is_code[offset]:
        opcode = rom[offset]
        # JSR abs ($20) or JMP abs ($4C)
        if opcode in (0x20, 0x4C) and offset + 2 < ROM_SIZE:
            target = rom[offset + 1] | (rom[offset + 2] << 8)
            if 0x8000 <= target <= 0x9FFF:
                addr = BASE + offset
                mn = 'JSR' if opcode == 0x20 else 'JMP'
                suspicious_jumps.append((addr, mn, target))
    offset += 1

if suspicious_jumps:
    print(f"  FOUND {len(suspicious_jumps)} suspicious JSR/JMP in data regions:")
    for addr, mn, target in suspicious_jumps:
        # Check if target is already traced code
        target_is_code = is_code[target - BASE] if 0x8000 <= target <= 0x9FFF else False
        status = "→ KNOWN CODE" if target_is_code else "→ UNKNOWN TARGET"
        print(f"    ${addr:04X}: {mn} ${target:04X}  {status}")
else:
    print("  ✓ No JSR/JMP to ROM addresses found in data regions")
print()

# Check 2: Runs of valid instructions in data regions
print("=" * 60)
print("CHECK 2: Plausible instruction runs in data regions (≥5 insns)")
print("=" * 60)

def try_decode_run(start_offset):
    """Try to decode a run of valid instructions starting at offset.
    Returns (count, end_offset) — number of valid instructions decoded."""
    off = start_offset
    count = 0
    while off < ROM_SIZE and not is_code[off]:
        opcode = rom[off]
        if opcode not in OPCODES:
            break
        _, mode, size = OPCODES[opcode]
        if off + size > ROM_SIZE:
            break
        # Check if next bytes are also data (not already code)
        all_data = all(not is_code[off + i] for i in range(size))
        if not all_data:
            break
        count += 1
        off += size
        # Stop at RTS/RTI/BRK (natural end of routine)
        if opcode in (0x60, 0x40, 0x00):
            break
    return count, off

suspicious_runs = []
offset = 0
while offset < ROM_SIZE:
    if not is_code[offset]:
        count, end = try_decode_run(offset)
        if count >= 5:
            addr = BASE + offset
            # Decode the first few instructions for display
            insns = []
            off2 = offset
            for _ in range(min(count, 8)):
                opcode = rom[off2]
                mn, mode, size = OPCODES[opcode]
                insns.append(f"{mn}")
                off2 += size
            suspicious_runs.append((addr, count, end - offset, insns))
            offset = end
        else:
            offset += 1
    else:
        offset += 1

if suspicious_runs:
    print(f"  FOUND {len(suspicious_runs)} suspicious instruction runs:")
    for addr, count, byte_len, insns in suspicious_runs:
        insn_str = ' '.join(insns[:8])
        if count > 8:
            insn_str += ' ...'
        print(f"    ${addr:04X}: {count} insns ({byte_len} bytes): {insn_str}")
else:
    print("  ✓ No plausible instruction runs found in data regions")
print()

# Check 3: Look for indirect jump tables (pairs of addresses in ROM range)
print("=" * 60)
print("CHECK 3: Address tables in data regions (potential jump targets)")
print("=" * 60)

address_tables = []
offset = 0
while offset < ROM_SIZE - 1:
    if not is_code[offset] and not is_code[offset + 1]:
        word = rom[offset] | (rom[offset + 1] << 8)
        if 0x8000 <= word <= 0x9FFF and not is_code[word - BASE]:
            # This word points to un-traced ROM code
            addr = BASE + offset
            address_tables.append((addr, word))
    offset += 1

if address_tables:
    # Group consecutive entries
    print(f"  FOUND {len(address_tables)} address words pointing to un-traced ROM:")
    # Show first 20
    for addr, target in address_tables[:20]:
        print(f"    ${addr:04X}: word ${target:04X} (not yet traced)")
    if len(address_tables) > 20:
        print(f"    ... and {len(address_tables) - 20} more")
else:
    print("  ✓ No address tables pointing to un-traced code found")
print()

# Check 4: Known code that references data-region addresses (JSR/JMP from code to data)
print("=" * 60)
print("CHECK 4: Code references to data regions (missed targets)")
print("=" * 60)

code_to_data = []
offset = 0
while offset < ROM_SIZE:
    if is_code[offset]:
        opcode = rom[offset]
        if opcode in OPCODES:
            mn, mode, size = OPCODES[opcode]
            if mode == 'ABS' and size == 3 and mn in ('JSR', 'JMP'):
                target = rom[offset + 1] | (rom[offset + 2] << 8)
                if 0x8000 <= target <= 0x9FFF:
                    target_off = target - BASE
                    if not is_code[target_off]:
                        addr = BASE + offset
                        code_to_data.append((addr, mn, target))
            offset += size
        else:
            offset += 1
    else:
        offset += 1

if code_to_data:
    print(f"  FOUND {len(code_to_data)} code instructions targeting data regions:")
    for addr, mn, target in code_to_data:
        print(f"    ${addr:04X}: {mn} ${target:04X}  ← THIS IS A MISSED ENTRY POINT")
else:
    print("  ✓ No code references to data regions found")
print()

# ============================================================
# Summary and recommendations
# ============================================================
print("=" * 60)
print("SUMMARY")
print("=" * 60)

# Known false positive regions (verified as text/data, not code)
FALSE_POSITIVE_RANGES = [
    (0x8000, 0x80FF),  # Cartridge header + version text
    (0x8249, 0x8274),  # Command name strings (EDITOR, CONNECT, etc.)
    (0x841D, 0x8438),  # RTS dispatch table (addresses are target-1)
    (0x9500, 0x96BF),  # Login screen text strings (ASCII spaces = $20 = JSR opcode)
    (0x8CDC, 0x8D2F),  # "MODEM FAULT", "INPUT PHONE NUMBER", "PLEASE WAIT" text
    (0x8FB0, 0x8FF1),  # "DISCONNECTED - BAD LINE?" text
    (0x9010, 0x901D),  # "PRESS ANY KEY" text
]

def is_false_positive(addr):
    for start, end in FALSE_POSITIVE_RANGES:
        if start <= addr <= end:
            return True
    return False

new_entry_points = set()

# Collect all definite missed entry points (Check 4)
for addr, mn, target in code_to_data:
    new_entry_points.add(target)

# Collect suspicious jumps in data that target known code (likely real code around them)
for addr, mn, target in suspicious_jumps:
    if is_code[target - BASE] and not is_false_positive(addr):
        new_entry_points.add(addr)

# Collect address table targets (excluding known false positive ranges)
for addr, target in address_tables:
    if not is_false_positive(addr) and not is_false_positive(target):
        new_entry_points.add(target)

if new_entry_points:
    print(f"\n  ⚠ {len(new_entry_points)} potential new entry points found.")
    print(f"  Add these to gen_source.py entry_points list and re-run:")
    print()
    for ep in sorted(new_entry_points):
        print(f"    0x{ep:04X},  # discovered by verify_data.py")
    print()
    print("  Then re-run: python3 gen_source.py && make")
else:
    print("\n  ✓ All .byte regions appear to be genuine data.")
    print("  No hidden code detected.")
    print(f"\n  Stats: {total_code} code bytes ({total_code*100//ROM_SIZE}%), "
          f"{total_data} data bytes ({total_data*100//ROM_SIZE}%)")

print()
