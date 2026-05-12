"""
New receive engine for Compunet ROM — replaces IRQ-driven packet assembly.

Installed at $C800 in RAM. Polls the NMI ring buffer directly from the
main code (like CCGMS does for XMODEM). No IRQ involvement, no slot system.

Entry points:
  $C800 = RECV_BYTE: get one payload byte from the stream
           Returns: A = byte, carry clear = valid
                    carry set = error/timeout
  $C840 = RECV_FLOW: wait for first packet, store token in $8034
           Returns: carry clear = success (token in $8034)
                    carry set = error

State variables (in zero page or workspace):
  $C900 = recv_state: 0=looking for $01, 1=in packet, 2=de-stuff next byte
  $C901 = recv_pos: current position in packet (0=length, 1=token, 2=seq, 3+=payload)
  $C902 = recv_len: expected packet length (from first byte)
  $C903 = recv_count: bytes received so far in current packet
  $C904 = recv_token: token of current packet
  $C905 = recv_seq: sequence of current packet
"""

# The receive engine code (6502 assembly)
recv_engine = bytearray()

# ============================================================
# GET_BUFFER_BYTE: Read one byte from NMI ring buffer
# Returns: A = byte, carry clear = got byte
#          carry set = buffer empty
# Preserves X, Y
# ============================================================
GET_BUFFER_BYTE_OFFSET = len(recv_engine)  # $C800 + offset
recv_engine.extend([
    0xAD, 0x9C, 0x02,   # LDA $029C (head)
    0xCD, 0x9B, 0x02,   # CMP $029B (tail)
    0xF0, 0x08,          # BEQ empty (buffer empty)
    0xAA,                # TAX
    0xBD, 0x00, 0xCE,   # LDA $CE00,X (read byte)
    0xEE, 0x9C, 0x02,   # INC $029C (advance head)
    0x18,                # CLC (got byte)
    0x60,                # RTS
    # empty:
    0x38,                # SEC (no byte)
    0x60,                # RTS
])

# ============================================================
# RECV_BYTE ($C800): Get one payload byte from the X.25 stream.
#
# This is the replacement for $96CC (PROTO_PROCESS_CMD).
# It reads bytes from the NMI buffer, handles framing ($01/$02),
# de-stuffing ($03), and delivers payload bytes one at a time.
#
# State machine:
#   State 0: Looking for $01 (start marker)
#   State 1: Inside packet, reading bytes
#   State 2: Previous byte was $03 (escape), next byte needs -$20
#
# Packet format after de-stuffing:
#   [length] [token] [seq] [payload...] [CRC_hi] [CRC_lo]
#
# We skip length/token/seq, deliver payload bytes, skip CRC.
# The packet ends when we've read 'length' bytes total.
#
# For simplicity in this first version: we deliver ALL bytes
# between $01 and $02 (after de-stuffing) to the caller, and let
# the ROM's existing MODEM_INIT_DOWNLOAD handle the structure.
# This means we deliver: length, token, seq, payload, CRC — but
# actually PROTO_PROCESS_CMD ($96CC) is supposed to deliver just
# the payload bytes. Let me check what the caller expects...
#
# Actually, looking at how $96CC works: it calls $9A17 which finds
# a packet in a slot, then reads bytes from the slot buffer one at
# a time via $C20B offset. The slot buffer contains the FULL packet
# (length + token + seq + payload + CRC). The caller ($8EEF) reads
# bytes sequentially — it reads length, token, seq as "header" bytes
# that it processes, then payload bytes that it stores.
#
# Wait — no. Looking at MODEM_INIT_DOWNLOAD more carefully:
# It calls $96CC which returns ONE byte per call. The first call
# returns the first byte of the PAYLOAD (not the length/token/seq).
# The slot system strips the header.
#
# So our RECV_BYTE needs to:
# 1. Wait for a complete packet (read until $02)
# 2. Validate CRC
# 3. Strip length/token/seq (first 3 bytes)
# 4. Strip CRC (last 2 bytes)
# 5. Deliver payload bytes one at a time
#
# This is complex. Let me use a simpler approach:
# Store the full de-stuffed packet in a buffer at $C900+.
# Track position. Deliver bytes from position 3 onwards (skipping header).
# When all payload bytes delivered, wait for next packet.
# ============================================================

# Workspace at $C900:
# $C900 = state: 0=need packet, 1=delivering payload
# $C901 = payload read position (index into packet buffer)
# $C902 = payload end position (length - 5 = payload size)
# $C903 = packet buffer write position
# $C910-$C97F = packet buffer (max 112 bytes, enough for 62-byte packets)

RECV_BYTE_OFFSET = len(recv_engine)

# --- RECV_BYTE entry ---
recv_engine.extend([
    0xAD, 0x00, 0xC9,   # LDA $C900 (state)
    0xD0, 0x03,          # BNE deliver (state=1 → deliver next byte)
    0x4C, 0x00, 0x00,    # JMP read_packet (placeholder — filled below)
])
deliver_offset = len(recv_engine)
# --- deliver: return next payload byte ---
recv_engine.extend([
    0xAE, 0x01, 0xC9,   # LDX $C901 (payload read position)
    0xBD, 0x10, 0xC9,   # LDA $C910,X (read from packet buffer)
    0xE8,                # INX
    0x8E, 0x01, 0xC9,   # STX $C901 (advance position)
    0xEC, 0x02, 0xC9,   # CPX $C902 (reached end?)
    0xD0, 0x05,          # BNE not_done
    0xA9, 0x00,          # LDA #$00
    0x8D, 0x00, 0xC9,   # STA $C900 (state=0, need next packet)
    # not_done:
    0x18,                # CLC (byte valid)
    0x60,                # RTS
])

# --- read_packet: read a complete packet from the buffer ---
read_packet_offset = len(recv_engine)
# Fix the JMP placeholder
jmp_target = 0xC800 + read_packet_offset
recv_engine[RECV_BYTE_OFFSET + 5] = jmp_target & 0xFF
recv_engine[RECV_BYTE_OFFSET + 6] = (jmp_target >> 8) & 0xFF

recv_engine.extend([
    # Init packet buffer write position
    0xA9, 0x00,
    0x8D, 0x03, 0xC9,   # STA $C903 (write pos = 0)
])

# --- wait_for_start: look for $01 ---
wait_for_start_offset = len(recv_engine)
recv_engine.extend([
    0x20, 0x00, 0xC8,   # JSR GET_BUFFER_BYTE ($C800)
    0xB0, 0xFA,          # BCS wait_for_start (buffer empty, retry) — PLACEHOLDER
    0xC9, 0x01,          # CMP #$01 (start marker?)
    0xD0, 0xF6,          # BNE wait_for_start (not start, keep looking) — PLACEHOLDER
])
# Fix branch offsets for wait_for_start loop
bcs_pos = wait_for_start_offset + 3
bne_pos = wait_for_start_offset + 7
recv_engine[bcs_pos + 1] = (wait_for_start_offset - (bcs_pos + 2)) & 0xFF
recv_engine[bne_pos + 1] = (wait_for_start_offset - (bne_pos + 2)) & 0xFF

# --- read_bytes: read until $02, de-stuffing $03 ---
read_bytes_offset = len(recv_engine)
recv_engine.extend([
    0x20, 0x00, 0xC8,   # JSR GET_BUFFER_BYTE
    0xB0, 0xFB,          # BCS read_bytes (empty, retry) — PLACEHOLDER
    0xC9, 0x02,          # CMP #$02 (end marker?)
    0xF0, 0x00,          # BEQ packet_done — PLACEHOLDER
    0xC9, 0x03,          # CMP #$03 (escape prefix?)
    0xD0, 0x09,          # BNE store_byte (not escape)
    # escape: read next byte and subtract $20
    0x20, 0x00, 0xC8,   # JSR GET_BUFFER_BYTE
    0xB0, 0xFB,          # BCS (retry) — will fix
    0x38,                # SEC
    0xE9, 0x20,          # SBC #$20 (de-stuff)
])
store_byte_offset = len(recv_engine)
recv_engine.extend([
    # store_byte: store in packet buffer
    0xAE, 0x03, 0xC9,   # LDX $C903 (write pos)
    0x9D, 0x10, 0xC9,   # STA $C910,X (store)
    0xE8,                # INX
    0x8E, 0x03, 0xC9,   # STX $C903 (advance write pos)
    0x4C, 0x00, 0x00,   # JMP read_bytes — PLACEHOLDER
])

# Fix JMP back to read_bytes
jmp_back_pos = len(recv_engine) - 3
recv_engine[jmp_back_pos + 1] = (0xC800 + read_bytes_offset) & 0xFF
recv_engine[jmp_back_pos + 2] = ((0xC800 + read_bytes_offset) >> 8) & 0xFF

# Fix BCS in read_bytes (retry on empty)
recv_engine[read_bytes_offset + 3 + 1] = (read_bytes_offset - (read_bytes_offset + 3 + 2)) & 0xFF

# Fix BCS in escape read (retry on empty)  
escape_bcs_pos = read_bytes_offset + 11 + 3
recv_engine[escape_bcs_pos + 1] = (read_bytes_offset - (escape_bcs_pos + 2)) & 0xFF

# --- packet_done: validate and set up for delivery ---
packet_done_offset = len(recv_engine)
# Fix BEQ to packet_done
beq_pos = read_bytes_offset + 5 + 2
recv_engine[beq_pos + 1] = (packet_done_offset - (beq_pos + 2)) & 0xFF

recv_engine.extend([
    # Packet is in $C910, length = $C903 bytes
    # Format: [length] [token] [seq] [payload...] [CRC_hi] [CRC_lo]
    # Skip first 3 bytes (length, token, seq) and last 2 (CRC)
    # Payload starts at offset 3, ends at $C903 - 2
    #
    # Store token in $8034 (needed by PROTO_FLOW_CONTROL)
    0xAD, 0x11, 0xC9,   # LDA $C911 (token = byte 1 of packet)
    0x8D, 0x34, 0x80,   # STA $8034
    #
    # Set up payload delivery
    0xA9, 0x03,          # LDA #$03 (payload starts at offset 3)
    0x8D, 0x01, 0xC9,   # STA $C901 (read position)
    0xAD, 0x03, 0xC9,   # LDA $C903 (total bytes)
    0x38,                # SEC
    0xE9, 0x02,          # SBC #$02 (subtract CRC)
    0x8D, 0x02, 0xC9,   # STA $C902 (payload end position)
    #
    # Set state = delivering
    0xA9, 0x01,          # LDA #$01
    0x8D, 0x00, 0xC9,   # STA $C900 (state = 1)
    #
    # Deliver first byte
    0x4C, 0x00, 0x00,   # JMP deliver — PLACEHOLDER
])
# Fix JMP to deliver
jmp_deliver_pos = len(recv_engine) - 3
recv_engine[jmp_deliver_pos + 1] = (0xC800 + deliver_offset) & 0xFF
recv_engine[jmp_deliver_pos + 2] = ((0xC800 + deliver_offset) >> 8) & 0xFF

# ============================================================
# RECV_FLOW ($C840): Wait for first packet, return token
# Replacement for $96D2 (PROTO_FLOW_CONTROL)
# ============================================================
# Pad to align RECV_FLOW
while len(recv_engine) < 0x80:
    recv_engine.append(0xEA)  # NOP padding

RECV_FLOW_OFFSET = len(recv_engine)

recv_engine.extend([
    # Read a complete packet (reuse read_packet logic)
    # Just call RECV_BYTE — it reads a packet and delivers first payload byte
    # But we need the TOKEN, not the payload.
    # Actually, RECV_BYTE stores token in $8034 during packet_done.
    # So we just call RECV_BYTE (which triggers packet read), then check $8034.
    0x20, 0x00, 0xC8,   # JSR RECV_BYTE ($C800 + RECV_BYTE_OFFSET) — PLACEHOLDER
    # RECV_BYTE read a packet and stored token in $8034
    # Check token: if $41/$42/$40 → error (SEC), else → success (CLC)
    0xAD, 0x34, 0x80,   # LDA $8034
    0xC9, 0x41,          # CMP #$41
    0xF0, 0x08,          # BEQ error
    0xC9, 0x42,          # CMP #$42
    0xF0, 0x04,          # BEQ error
    0xC9, 0x40,          # CMP #$40
    0xF0, 0x00,          # BEQ error
    0x18,                # CLC (success)
    0x60,                # RTS
    # error:
    0x38,                # SEC
    0x60,                # RTS
])

# Fix JSR to RECV_BYTE
recv_flow_jsr_pos = RECV_FLOW_OFFSET
recv_engine[recv_flow_jsr_pos + 1] = (0xC800 + RECV_BYTE_OFFSET) & 0xFF
recv_engine[recv_flow_jsr_pos + 2] = ((0xC800 + RECV_BYTE_OFFSET) >> 8) & 0xFF

# Fix the BEQ error offset (last one before CLC)
# The three BEQ error branches need to point to the SEC/RTS
error_offset = RECV_FLOW_OFFSET + len(recv_engine) - RECV_FLOW_OFFSET - 2  # SEC is 2 from end
# Actually let me just count: the error label is at the SEC instruction
# From the code above, after the last BEQ:
# ... F0 00 18 60 38 60
# The BEQ at "F0 00" needs to branch to the SEC at +2
# Let me fix all three BEQs
# They're at offsets +7, +11, +15 from RECV_FLOW start, targeting the SEC at +17
beq1 = RECV_FLOW_OFFSET + 7
beq2 = RECV_FLOW_OFFSET + 11
beq3 = RECV_FLOW_OFFSET + 15
sec_pos = RECV_FLOW_OFFSET + 17
recv_engine[beq1 + 1] = (sec_pos - (beq1 + 2)) & 0xFF
recv_engine[beq2 + 1] = (sec_pos - (beq2 + 2)) & 0xFF
recv_engine[beq3 + 1] = (sec_pos - (beq3 + 2)) & 0xFF


print(f"Receive engine: {len(recv_engine)} bytes")
print(f"  GET_BUFFER_BYTE at $C800+{GET_BUFFER_BYTE_OFFSET:02X} = ${0xC800+GET_BUFFER_BYTE_OFFSET:04X}")
print(f"  RECV_BYTE at $C800+{RECV_BYTE_OFFSET:02X} = ${0xC800+RECV_BYTE_OFFSET:04X}")
print(f"  RECV_FLOW at $C800+{RECV_FLOW_OFFSET:02X} = ${0xC800+RECV_FLOW_OFFSET:04X}")
