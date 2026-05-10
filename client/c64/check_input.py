"""Check the phone number input code path."""
import os

rom_path = os.path.join(os.path.dirname(__file__), '..', '..', 'historical', 'chip0_bank0_8000.bin')
with open(rom_path, 'rb') as f:
    rom = f.read()

def h(addr, count=20):
    off = addr - 0x8000
    print('${:04X}: {}'.format(addr, ' '.join('{:02X}'.format(rom[off+i]) for i in range(count))))

print('Phone number input area ($8D52-$8D90):')
h(0x8D52)
h(0x8D66)
h(0x8D7A)
h(0x8D8E)

print()
print('SETUP_INPUT_PARAMS ($90C8-$90DE):')
h(0x90C8)
h(0x90DC)

print()
print('INPUT_LINE filter area ($9128-$9145):')
h(0x9128)
h(0x913C)

print()
# The key: what does the code at $8D7A look like?
# $8D76: A0 00 = LDY #$00
# $8D78: A2 10 = LDX #$10 (max length)
# $8D7A: A9 2D = LDA #$2D (terminator '-')
# $8D7C: 38    = SEC (numeric only flag)
# $8D7D: 20 C8 90 = JSR $90C8
print('Specifically $8D76-$8D7F:')
h(0x8D76, 10)

print()
# Check $90D5-$90DC to understand the flag logic
print('Flag logic at $90D1-$90DE:')
h(0x90D1, 14)
print()
print('$90D1: TAX')
print('$90D2: LDA #$00')
print('$90D4: ROR A (carry -> bit 7)')
print('$90D5: CPX #$00')
print('$90D7: BEQ $90DB (skip ORA if terminator=0)')
print('$90D9: ORA #$40 (set bit 6)')
print('$90DB: STA $C145')

print()
print('INPUT_LINE at $912D-$9143:')
h(0x912D, 22)
print()
print('$912D: BIT $C145 (test bits 7,6)')
print('$9130: BVC $9139 (branch if bit 6 CLEAR -> accept all)')
print('$9132: CMP $C146 (compare with terminator)')
print('$9135: BEQ $9162 (if matches terminator, accept)')
print('$9137: BNE $913B')
print('$9139: BPL $9145 (if char < $80, go to printable check)')
print('$913B: CMP #$30 (< "0"?)')
print('$913D: BCC $90F7 (reject)')
print('$913F: CMP #$3A (>= ":"?)')
print('$9141: BCS $90F7 (reject)')
print('$9143: BCC $9162 (accept digit)')
