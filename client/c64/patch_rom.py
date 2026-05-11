"""
Patch the Compunet Terminal ROM for use with 6551 ACIA (SwiftLink/C64 Ultimate).

MINIMAL PATCH: Only the hardware layer is replaced. The X.25 protocol engine
remains completely intact. The server speaks the same wire protocol over TCP.

Changes:
  $94E4 -> ACIA TX with delay
  $94F0 -> Filter: only TX for register 3/4
  $94FA -> JMP to extended handler at $8E00
  $8D30 -> ACIA init + NMI handler install
  $8DA6 -> Hayes ATDT dial sequence
  $8E00 -> Extended register read handler (30 bytes, overwrites $8E17)
  $913C/$9140/$8D79 -> Input filter for IP addresses
  $807B -> Version string

The dial code replicates the original $8E17-$8E1E logic (JSR $96D5 + error
handling) inline, so overwriting $8E17 is safe.
"""

import os

ORIGINAL_CRT = os.path.join(os.path.dirname(__file__), '..', '..', 'historical', 'Compunet Terminal.crt')
OUTPUT_CRT = os.path.join(os.path.dirname(__file__), 'compunet-reborn.crt')

with open(ORIGINAL_CRT, 'rb') as f:
    crt_data = bytearray(f.read())

ROM_OFFSET = 64 + 16
ROM_BASE = 0x8000
rom = crt_data[ROM_OFFSET:ROM_OFFSET + 8192]


def patch(addr, data):
    off = addr - ROM_BASE
    for i, b in enumerate(data):
        rom[off + i] = b


# ============================================================
# 1. VERSION STRING
# ============================================================
ver = [ord(c) - 32 if 97 <= ord(c) <= 122 else ord(c)
       for c in ' COMPUNET REBORN 1.00  ']
patch(0x807B, ver)


# ============================================================
# 2. NMI HANDLER at $80BC (38 bytes, copied to $CF00 at runtime)
# ============================================================
patch(0x80BC, [
    0x48,               # PHA
    0x8A,               # TXA
    0x48,               # PHA
    0xAD, 0x01, 0xDE,   # LDA $DE01 (ACK interrupt)
    0xAD, 0x02, 0xDE,   # LDA $DE02
    0x09, 0x02,         # ORA #$02 (disable RX IRQ)
    0x8D, 0x02, 0xDE,   # STA $DE02
    0xAD, 0x00, 0xDE,   # LDA $DE00 (read byte)
    0xAE, 0x9B, 0x02,   # LDX $029B (tail)
    0x9D, 0x00, 0xCE,   # STA $CE00,X
    0xEE, 0x9B, 0x02,   # INC $029B
    0xAD, 0x02, 0xDE,   # LDA $DE02
    0x29, 0xFD,         # AND #$FD (re-enable RX IRQ)
    0x8D, 0x02, 0xDE,   # STA $DE02
    0x68,               # PLA
    0xAA,               # TAX
    0x68,               # PLA
    0x40,               # RTI
])
NMI_LEN = 38


# ============================================================
# 3. ACIA INIT CONTINUATION at $80E2 (28 bytes)
# ============================================================
patch(0x80E2, [
    0xA9, 0x00, 0x8D, 0x18, 0x03,   # STA $0318 = $00
    0xA9, 0xCF, 0x8D, 0x19, 0x03,   # STA $0319 = $CF (NMI -> $CF00)
    0xA9, 0x00, 0x8D, 0x02, 0xDE,   # STA $DE02 (reset)
    0xA9, 0x1F, 0x8D, 0x03, 0xDE,   # STA $DE03 (19200 8N1)
    0xA9, 0x09, 0x8D, 0x02, 0xDE,   # STA $DE02 (DTR+RX IRQ)
    0x4C, 0x52, 0x8D,               # JMP $8D52 (number prompt)
])


# ============================================================
# 4. MODEM_CHECK at $8D30
# ============================================================
patch(0x8D30, [
    0xBA, 0x8E, 0x54, 0xC1,         # TSX / STX $C154
    0xA9, 0x00,
    0x8D, 0x9B, 0x02,               # STA $029B (tail=0)
    0x8D, 0x9C, 0x02,               # STA $029C (head=0)
    0xA2, NMI_LEN - 1,              # LDX #37
    0xBD, 0xBC, 0x80,               # LDA $80BC,X (loop)
    0x9D, 0x00, 0xCF,               # STA $CF00,X
    0xCA,                            # DEX
    0x10, 0xF7,                      # BPL loop
    0x4C, 0xE2, 0x80,               # JMP $80E2
])
patch(0x8D4A, [0xEA] * 8)


# ============================================================
# 5. HARDWARE LAYER
# ============================================================
# $94E4: TX with delay
patch(0x94E4, [
    0x8D, 0x00, 0xDE, 0xA0, 0xFF, 0x88, 0xD0, 0xFD, 0x60, 0xEA, 0xEA, 0xEA,
])
# $94F0: register write filter
# Only TX for register 4 (transmit data). Register 3 was modem mode control
# on the original hardware — NOT data. Sending it confuses tcpser's break delay.
patch(0x94F0, [
    0xE0, 0x04, 0xF0, 0xF0, 0x60, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA,
])

# $9FB7: Keep the byte send — the ACIA TX activates the receive path.
# Without any TX, VICE's ACIA emulation may not trigger NMIs for RX.
# Send $20 (space) instead of $0D (CR) to avoid break delay issues.
patch(0x9FB8, [0x20])  # Change operand from $0D to $20
# $94FA: JMP to extended handler
patch(0x94FA, [0x4C, 0x00, 0x8E] + [0xEA] * 9)


# ============================================================
# 6. EXTENDED MODEM_REG_READ at $8E00 (30 bytes)
#
# Overwrites $8E00-$8E1D. The dial code replicates the original
# $8E17-$8E1E logic (JSR $96D5 / BCC / JMP $96C0) inline.
#
# Register 0: check buffer, return $E0 (data ready) or $A0 (empty)
# Register 8: check buffer, return $40 or $00
# Register 4: blocking read from ring buffer (data byte)
# Other: blocking read from ring buffer
# ============================================================
handler = bytearray()

# Reg 0: buffer-aware status (15 bytes)
# Bit 7=TX ready, Bit 6=RX data available, Bit 5=carrier
# IRQ handler at $9FC8 checks bit 6 to decide whether to read data!
# BUG FIX: BEQ must come right after CMP, before any LDA (which clears Z)!
handler.extend([0xE0, 0x00])         # CPX #$00
bne_to_reg8 = len(handler)
handler.extend([0xD0, 0x00])         # BNE -> reg8 (placeholder)
handler.extend([0xAD, 0x9C, 0x02])   # LDA $029C (head)
handler.extend([0xCD, 0x9B, 0x02])   # CMP $029B (tail)
handler.extend([0xF0, 0x03])         # BEQ +3 -> empty (Z set from CMP!)
handler.extend([0xA9, 0xE0])         # LDA #$E0 (data: bits 7+6+5)
handler.extend([0x60])               # RTS
handler.extend([0xA9, 0xA0])         # LDA #$A0 (empty: bits 7+5)
handler.extend([0x60])               # RTS

# Reg 8: buffer check (same logic, return $40/$00) (12 bytes)
reg8_pos = len(handler)
handler.extend([0xE0, 0x08])         # CPX #$08
bne_to_data = len(handler)
handler.extend([0xD0, 0x00])         # BNE -> data_read (placeholder)
handler.extend([0xAD, 0x9C, 0x02])   # LDA $029C
handler.extend([0xCD, 0x9B, 0x02])   # CMP $029B
handler.extend([0xA9, 0x00])         # LDA #$00 (empty)
handler.extend([0xF0, 0x02])         # BEQ +2
handler.extend([0xA9, 0x40])         # LDA #$40 (has data)
handler.extend([0x60])               # RTS

# Data read: NON-BLOCKING (returns $00 if empty)
# CRITICAL: called from IRQ handler — must NOT spin-wait!
data_read_pos = len(handler)
handler.extend([0xAD, 0x9C, 0x02])   # LDA $029C (head)
handler.extend([0xCD, 0x9B, 0x02])   # CMP $029B (tail)
bne_got = len(handler)
handler.extend([0xD0, 0x00])         # BNE -> got_data (placeholder)
handler.extend([0xA9, 0x00])         # LDA #$00 (empty)
handler.extend([0x60])               # RTS
got_data_pos = len(handler)
handler.extend([0xAA])               # TAX
handler.extend([0xBD, 0x00, 0xCE])   # LDA $CE00,X
handler.extend([0xEE, 0x9C, 0x02])   # INC $029C
handler.extend([0x60])               # RTS

# Fix branch offsets
handler[bne_to_reg8 + 1] = (reg8_pos - (bne_to_reg8 + 2)) & 0xFF
handler[bne_to_data + 1] = (data_read_pos - (bne_to_data + 2)) & 0xFF
handler[bne_got + 1] = (got_data_pos - (bne_got + 2)) & 0xFF

print(f"Handler: {len(handler)} bytes, ends at ${0x8E00 + len(handler) - 1:04X}")
patch(0x8E00, list(handler))


# ============================================================
# 7. INPUT FILTER + DEFAULT ADDRESS
# ============================================================
patch(0x913C, [0x20])
patch(0x9140, [0x7B])
patch(0x8D79, [0x1E])

# Default "phone number" (server address) at $8059
# Original: "322500/100\rADP\rNO\rRUN\r"
# New: "127.0.0.1:6400\rADP\rNO\rRUN\r"
# Also update the length byte at $8051 to cover the full string.
default_fields = b'127.0.0.1:6400\rADP\rNO\rRUN\r'
patch(0x8059, list(default_fields))
# Length at $8051: counts from $8052 to end of string (including "C CNET\r" prefix)
# "C CNET\r" (7) + our fields (28) = 35. But original was 29 for "C CNET\r322500/100\rADP\rNO\r"
# The ROM sends from $8052 for $8051 bytes. We need all fields included.
# "C CNET\r" = 7 bytes (at $8052-$8058, unchanged)
# + "127.0.0.1:6400\rADP\rNO\rRUN\r" = 28 bytes
# Total = 35 bytes. But wait - does it include the trailing \r of RUN?
# Let's just set it to cover everything up to and including the last \r.
total_len = 7 + len(default_fields)  # "C CNET\r" + our fields
patch(0x8051, [total_len])


# ============================================================
# 8. DIAL SEQUENCE at $8DA6
# ============================================================
dial = bytearray()

# Send "ATDT"
for ch in [0x41, 0x54, 0x44, 0x54]:
    dial += bytes([0xA9, ch, 0x20, 0xE4, 0x94])

# Send user input
dial += bytes([0xA2, 0x00])
input_loop = len(dial)
dial += bytes([0xEC, 0xF0, 0x9F])
dial += bytes([0xF0, 0x0A])
dial += bytes([0xBD, 0xF1, 0x9F])
dial += bytes([0x20, 0xE4, 0x94])
dial += bytes([0xE8])
dial += bytes([0x4C, (0x8DA6 + input_loop) & 0xFF, ((0x8DA6 + input_loop) >> 8) & 0xFF])

# Send CR
dial += bytes([0xA9, 0x0D, 0x20, 0xE4, 0x94])

# Wait for CONNECT response: read from buffer until LF ($0A)
wait_start = len(dial)
dial += bytes([0xAD, 0x9C, 0x02])   # LDA $029C (head)
dial += bytes([0xCD, 0x9B, 0x02])   # CMP $029B (tail)
dial += bytes([0xF0, (wait_start - (len(dial) + 2)) & 0xFF])  # BEQ wait_start (spin)
dial += bytes([0xAA])                # TAX
dial += bytes([0xBD, 0x00, 0xCE])   # LDA $CE00,X
dial += bytes([0xEE, 0x9C, 0x02])   # INC $029C
dial += bytes([0xC9, 0x0D])         # CMP #$0D (CR? - end of CONNECT response)
dial += bytes([0xD0, (wait_start - (len(dial) + 2)) & 0xFF])  # BNE wait_start

# After CR found, drain any remaining bytes (LF, etc.) with a short timeout
drain2_start = len(dial)
dial += bytes([0xAD, 0x9C, 0x02])   # LDA $029C (head)
dial += bytes([0xCD, 0x9B, 0x02])   # CMP $029B (tail)
dial += bytes([0xF0, 0x06])         # BEQ done (buffer empty)
dial += bytes([0xEE, 0x9C, 0x02])   # INC $029C (discard)
dial += bytes([0x4C, (0x8DA6 + drain2_start) & 0xFF, ((0x8DA6 + drain2_start) >> 8) & 0xFF])
# done:

# Protocol connect (replicates original $8E17-$8E1E)
dial += bytes([0x20, 0xD5, 0x96])   # JSR $96D5 (PROTO_CONNECT)
dial += bytes([0x90, 0x03])         # BCC +3 (success)
dial += bytes([0x4C, 0xC0, 0x96])   # JMP $96C0 (error)
# Success: jump to login screen (skip $96D2 send for now)
dial += bytes([0x20, 0x50, 0x90])   # JSR $9050 (replicate overwritten $8E35)
dial += bytes([0x4C, 0x38, 0x8E])   # JMP $8E38 (continue with login screen)

# Pad to 90 bytes
while len(dial) < 90:
    dial += bytes([0xEA])
assert len(dial) == 90, f"Dial is {len(dial)} bytes!"
patch(0x8DA6, list(dial))


# ============================================================
# OUTPUT
# ============================================================
crt_data[ROM_OFFSET:ROM_OFFSET + 8192] = rom
crt_data[32:64] = (b'COMPUNET REBORN\x00' + b'\x00' * 16)[:32]

with open(OUTPUT_CRT, 'wb') as f:
    f.write(crt_data)

OUTPUT_PRG = os.path.join(os.path.dirname(__file__), 'compunet-reborn.prg')
with open(OUTPUT_PRG, 'wb') as f:
    f.write(bytearray([0x00, 0x80]) + rom)

OUTPUT_LOADER = os.path.join(os.path.dirname(__file__), 'compunet-loader.prg')
loader = bytearray([0x01, 0x08, 0x0B, 0x08, 0x0A, 0x00, 0x9E])
loader += bytearray(b'33184') + bytearray([0x00, 0x00, 0x00])
with open(OUTPUT_LOADER, 'wb') as f:
    f.write(loader)

print('Done. CRT:', OUTPUT_CRT)
print('Protocol engine INTACT. Server must speak X.25 framing.')
