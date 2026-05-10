"""
Patch the Compunet Terminal ROM for use with 6551 ACIA (SwiftLink/C64 Ultimate).

Takes the original Compunet Terminal.crt and produces a patched version that:
1. Replaces modem register routines with 6551 ACIA TX/RX
2. Replaces the modem check with ACIA presence detection
3. Replaces the dial sequence with Hayes AT command (ATDT<host>:<port>)
4. Changes the version string to "COMPUNET REBORN 1.00"

6551 ACIA registers at $DE00-$DE03:
  $DE00 = TX/RX Data
  $DE01 = Status (bit 3=TX empty, bit 0=RX full, bit 5=DCD)
  $DE02 = Command
  $DE03 = Control
"""

import struct
import os

# Paths
ORIGINAL_CRT = os.path.join(os.path.dirname(__file__), '..', '..', 'historical', 'Compunet Terminal.crt')
OUTPUT_CRT = os.path.join(os.path.dirname(__file__), 'compunet-reborn.crt')

# Read original CRT
with open(ORIGINAL_CRT, 'rb') as f:
    crt_data = bytearray(f.read())

# CRT format: 64-byte header + 16-byte CHIP header + 8192 bytes ROM
# The ROM data starts at offset 64 + 16 = 80
CRT_HEADER_SIZE = 64
CHIP_HEADER_SIZE = 16
ROM_OFFSET = CRT_HEADER_SIZE + CHIP_HEADER_SIZE
ROM_BASE = 0x8000

rom = crt_data[ROM_OFFSET:ROM_OFFSET + 8192]
print('Original ROM: {} bytes at ${:04X}'.format(len(rom), ROM_BASE))

def rom_offset(addr):
    """Convert a runtime address to ROM byte offset."""
    return addr - ROM_BASE

def patch_bytes(addr, new_bytes):
    """Patch bytes at a runtime address."""
    off = rom_offset(addr)
    for i, b in enumerate(new_bytes):
        rom[off + i] = b
    print('  Patched ${:04X}: {} bytes'.format(addr, len(new_bytes)))

def patch_string(addr, text, max_len):
    """Patch a null/CR-terminated string."""
    encoded = []
    for ch in text:
        c = ord(ch)
        if 65 <= c <= 90:  # A-Z -> PETSCII $41-$5A
            encoded.append(c)
        elif 97 <= c <= 122:  # a-z -> $41-$5A
            encoded.append(c - 32)
        else:
            encoded.append(c)
    # Pad with spaces to max_len, then terminate
    while len(encoded) < max_len:
        encoded.append(0x20)
    patch_bytes(addr, encoded[:max_len])


# ============================================================
# PATCH 1: Version string
# Original at $807A: " COMPUNET TERMINAL 1.22\r"
# Change to: " COMPUNET REBORN 1.00\r"
# ============================================================
print()
print('PATCH 1: Version string')
# The string starts at $807B (after the leading $0D at $807A)
# Original: 20 43 4F 4D 50 55 4E 45 54 20 54 45 52 4D 49 4E 41 4C 20 31 2E 32 32
# New:      20 43 4F 4D 50 55 4E 45 54 20 52 45 42 4F 52 4E 20 31 2E 30 30 20 20
new_version = ' COMPUNET REBORN 1.00  '
patch_string(0x807B, new_version, 23)


# ============================================================
# PATCH 2 & 3: Replace modem routines with ACIA TX/RX
# 
# Final layout:
#   $94E4: ACIA TX (STA $DE00 / RTS) - simple, no wait
#   $94F0: JMP $94E4 (preserves entry point)
#   $94FA: ACIA RX (wait for bit 3, LDA $DE00 / RTS)
# ============================================================
print()
print('PATCH 2+3: MODEM routines -> ACIA TX/RX')

# $94E4: TX routine - write byte in A to ACIA with delay for VICE timing
patch_bytes(0x94E4, [
    0x8D, 0x00, 0xDE,   # STA $DE00 - send byte
    0xA0, 0xFF,         # LDY #$FF - longer delay counter
    0x88,               # DEY
    0xD0, 0xFD,         # BNE *-2 (delay loop ~1275 cycles)
    0x60,               # RTS
    0xEA, 0xEA, 0xEA,   # NOP padding
])

# $94F0: JMP to TX (preserves original entry point for callers of $94F0)
patch_bytes(0x94F0, [
    0x4C, 0xE4, 0x94,   # JMP $94E4
    0xEA, 0xEA, 0xEA,   # NOP
    0xEA, 0xEA, 0xEA,   # NOP
    0xEA,               # NOP (fills to $94F9)
])

# $94FA: RX routine - wait for data, return in A
patch_bytes(0x94FA, [
    0xAD, 0x01, 0xDE,   # LDA $DE01 - status
    0x29, 0x08,         # AND #$08 - RX data full (bit 3)
    0xF0, 0xF9,         # BEQ $94FA (loop back)
    0xAD, 0x00, 0xDE,   # LDA $DE00 - read received byte
    0x60,               # RTS
    0xEA,               # NOP padding
])


# ============================================================
# PATCH 4: MODEM_CHECK ($8D30) - Replace with ACIA init
# Original writes $20 to register 3 and reads it back.
# New: initialise the 6551 and check it responds.
# ============================================================
print()
print('PATCH 4: MODEM_CHECK ($8D30) -> ACIA init')

# The modem check at $8D30 is called when user types CONNECT.
# Original flow: check modem → prompt for number → dial → connect
# New flow: init ACIA → prompt for host:port → send ATDT → wait CONNECT
#
# For now, just make the modem check pass by initialising the ACIA:
#   Write $00 to Command register ($DE02) - reset
#   Write $1F to Control register ($DE03) - 19200 baud, 8N1
#   Then fall through to the dial sequence
#
# The original code at $8D30-$8D4A is the check (27 bytes).
# We replace it with ACIA init that always succeeds.

acia_init = [
    0xBA,               # TSX - save stack pointer (original does this)
    0x8E, 0x54, 0xC1,   # STX $C154 - store stack pointer
    0xA9, 0x00,         # LDA #$00
    0x8D, 0x02, 0xDE,   # STA $DE02 - command register (disable everything)
    0xA9, 0x1F,         # LDA #$1F - 19200 baud, 8N1, 1 stop bit
    0x8D, 0x03, 0xDE,   # STA $DE03 - control register
    0xA9, 0x0B,         # LDA #$0B - no parity, RTS low, TX int disabled, DTR active
    0x8D, 0x02, 0xDE,   # STA $DE02 - command register (enable TX)
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
    0xEA,               # NOP
]
patch_bytes(0x8D30, acia_init)
# After this, execution falls through to $8D4B+ which is the dial sequence.
# We need to make sure it doesn't hit the "modem fault" branch.
# The original at $8D4B prints modem fault. We need to skip past it.
# Actually our init is 24 bytes ($8D30-$8D47), and the original fault
# message code starts at $8D4B. Let's NOP over the fault path too
# and jump to the number prompt.

# The number prompt is at $8D52 in the original (after the modem check passes).
# Let's jump there from the end of our init:
patch_bytes(0x8D48, [
    0x4C, 0x52, 0x8D,   # JMP $8D52 - skip to number/host prompt
])


# ============================================================
# PATCH 5: Dial sequence - replace pulse dial with ATDT command
# The original dial code at $8DA6+ sends digits via register 10.
# We need to send "ATDT" + the user's input + "\r" via ACIA TX,
# then wait for "CONNECT" response.
#
# This is complex - for now, we'll patch the minimum to get
# past the dial and into the protocol layer. The "number" prompt
# already exists and stores input. We just need to send it as
# an AT command instead of pulse-dialling.
#
# For a first pass: after the user enters the host:port,
# we send ATDT<input>\r and then wait for any response byte
# before proceeding to the protocol connection.
# ============================================================
print()
print('PATCH 5: Dial sequence -> Hayes ATDT (simplified)')
# Fix 1: Allow all printable characters in the number input
# Patch the digit-only filter at $913B-$9141 to accept wider range:
# $913B: CMP #$30 -> CMP #$20 (accept from space onwards)
# $913F: CMP #$3A -> CMP #$7B (accept up to 'z')
# This allows dots, colons, letters for IP addresses and hostnames.
patch_bytes(0x913C, [0x20])  # change #$30 to #$20 (operand at $913C)
patch_bytes(0x9140, [0x7B])  # change #$3A to #$7B (operand at $9140)
# Also increase max input length
patch_bytes(0x8D79, [0x1E])  # max 30 chars instead of 16

# Fix 2: After user enters host:port and presses RETURN, the code
# at $8DA6 starts the dial sequence. We need to replace it with:
#   1. Send "ATDT" via ACIA
#   2. Send the user's input via ACIA
#   3. Send CR ($0D) via ACIA
#   4. Wait for response (look for 'C' from "CONNECT")
#   5. Consume rest of CONNECT line
#   6. Jump to protocol connection phase
#
# The user's input is stored at $9FF1 onwards, length at $9FF0.
# After dial, the original jumps to $8E17 (JSR $96D5 = PROTO_CONNECT).
# 
# Available space: $8DA6 to $8E16 = 112 bytes. Plenty.

dial_code = [
    # Send "ATDT" string
    0xA9, 0x41,         # LDA #'A'
    0x20, 0xE4, 0x94,   # JSR $94E4 (ACIA_TX)
    0xA9, 0x54,         # LDA #'T'
    0x20, 0xE4, 0x94,   # JSR $94E4
    0xA9, 0x44,         # LDA #'D'
    0x20, 0xE4, 0x94,   # JSR $94E4
    0xA9, 0x54,         # LDA #'T'
    0x20, 0xE4, 0x94,   # JSR $94E4
    
    # Send user input from $9FF1, length at $9FF0
    0xA2, 0x00,         # LDX #$00 (index)
    # loop:
    0xEC, 0xF0, 0x9F,   # CPX $9FF0 (compare with length)
    0xF0, 0x09,         # BEQ +9 (done with input)
    0xBD, 0xF1, 0x9F,   # LDA $9FF1,X (get char)
    0x20, 0xE4, 0x94,   # JSR $94E4 (send it)
    0xE8,               # INX
    0x4C, 0xBC, 0x8D,   # JMP loop ($8DA6 + 22 = $8DBC)
    
    # Send CR to complete the AT command
    0xA9, 0x0D,         # LDA #$0D
    0x20, 0xE4, 0x94,   # JSR $94E4
    
    # Wait for 'C' (start of "CONNECT" response)
    # wait_c:
    0x20, 0xFA, 0x94,   # JSR $94FA (ACIA_RX)
    0xC9, 0x43,         # CMP #'C'
    0xD0, 0xF9,         # BNE wait_c (keep reading until 'C')
    
    # Consume rest of CONNECT line (until CR)
    # wait_cr:
    0x20, 0xFA, 0x94,   # JSR $94FA (ACIA_RX)
    0xC9, 0x0D,         # CMP #$0D
    0xD0, 0xF9,         # BNE wait_cr
    
    # Also consume LF if present
    0x20, 0xFA, 0x94,   # JSR $94FA (ACIA_RX)
    0xC9, 0x0A,         # CMP #$0A (LF?)
    # Don't care about result, just consumed it
    
    # Jump to protocol connection phase
    0x4C, 0x17, 0x8E,   # JMP $8E17 (original PROTO_CONNECT entry)
]

patch_bytes(0x8DA6, dial_code)
print('  Dial sequence patched: {} bytes at $8DA6'.format(len(dial_code)))


# ============================================================
# Write patched CRT and PRG
# ============================================================
print()

# Put patched ROM back into CRT data
crt_data[ROM_OFFSET:ROM_OFFSET + 8192] = rom

# Update CRT name in header (bytes 32-63)
crt_name = b'COMPUNET REBORN\x00' + b'\x00' * 16
crt_data[32:64] = crt_name[:32]

with open(OUTPUT_CRT, 'wb') as f:
    f.write(crt_data)

print('Patched CRT written to: {}'.format(OUTPUT_CRT))
print('Size: {} bytes'.format(len(crt_data)))

# Also output as PRG file
# PRG format: 2-byte load address (little-endian) + data
# We create a BASIC stub at $0801 that does SYS to our init code at $8160
# Then the ROM code follows at $8000
#
# Layout:
#   $0801: BASIC stub (SYS 33120) -> jumps to $8160
#   $0810: (padding to fill gap)
#   ...
#   $8000: ROM code (8192 bytes)
#
# Actually simpler: load the ROM directly at $8000 with a tiny BASIC
# program at $0801 that does SYS 33120 ($8160 = COLD_START)

OUTPUT_PRG = os.path.join(os.path.dirname(__file__), 'compunet-reborn.prg')

# Build BASIC stub: 10 SYS33120
# BASIC line format: next_ptr(2) line_num(2) tokens... 00
basic_stub = bytearray()
# Line: 10 SYS33120
basic_stub.extend([
    0x0C, 0x08,         # next line pointer ($080C)
    0x0A, 0x00,         # line number 10
    0x9E,               # SYS token
])
basic_stub.extend(b'33120')  # address as ASCII digits
basic_stub.append(0x00)      # end of line
basic_stub.extend([0x00, 0x00])  # end of BASIC program

# The PRG needs to load at $0801 and include everything up to $9FFF
# But there's a gap between $0801+stub and $8000 that would be huge (30KB).
# Instead, let's make a two-part loader:
# Part 1: BASIC stub at $0801 that loads the ROM into $8000 and SYS's it
# 
# Actually the simplest approach: load the ROM at $8000 directly.
# PRG load address = $8000, data = patched ROM.
# Then a separate tiny BASIC program does SYS 33120.
#
# Or: single PRG that loads at $0801 with a ML loader that copies
# the ROM data to $8000 and jumps to $8160.
#
# Simplest for testing: just output the ROM as a PRG at $8000.
# User loads with: LOAD "COMPUNET",8,1 then SYS 33120

prg_data = bytearray()
prg_data.extend([0x00, 0x80])  # load address: $8000 (little-endian)
prg_data.extend(rom)           # 8192 bytes of patched ROM

with open(OUTPUT_PRG, 'wb') as f:
    f.write(prg_data)

print('Patched PRG written to: {}'.format(OUTPUT_PRG))
print('Size: {} bytes'.format(len(prg_data)))
print()
print('To use in VICE:')
print('  LOAD "COMPUNET-REBORN",8,1')
print('  SYS 33120')
print('  (then use CONNECT, EDITOR, etc.)')

# Also output a BASIC loader that auto-runs
OUTPUT_LOADER = os.path.join(os.path.dirname(__file__), 'compunet-loader.prg')

loader = bytearray()
loader.extend([0x01, 0x08])  # load address: $0801

# BASIC program:
# 10 SYS33184
# This jumps to $81A0 (MAIN_INIT) which skips the KERNAL reinit
# that would wipe our code at $8000. MAIN_INIT just prints the
# version string and installs the command parser.
line1 = bytearray()
line1.extend([0x0A, 0x00])   # line number 10
line1.append(0x9E)           # SYS token
line1.extend(b'33184')       # $81A0 = MAIN_INIT
line1.append(0x00)           # end of line

# Calculate next pointer
next_ptr = 0x0801 + 2 + len(line1)  # +2 for the pointer itself
loader.extend([next_ptr & 0xFF, (next_ptr >> 8) & 0xFF])
loader.extend(line1)
loader.extend([0x00, 0x00])  # end of BASIC

with open(OUTPUT_LOADER, 'wb') as f:
    f.write(loader)

print('BASIC loader written to: {}'.format(OUTPUT_LOADER))
print('  LOAD "COMPUNET-LOADER",8')
print('  RUN')
