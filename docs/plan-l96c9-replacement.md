# Plan: Replace L96C9 (PROTO_RECV_FRAME) with ACIA Upload Routine

## Background

`L96C9` is a jump table entry at `$96C9` that currently points to
`PROTO_RECV_FRAME` — the original ROM's half-duplex X.25 protocol engine.
It sends one byte and simultaneously processes any incoming receive data.

This routine is called by the frame upload code at `$B175` which sends
Editor page content to the server byte-by-byte during MAIL SEND (and
potentially content uploads via UPLD).

All other client→server communication already uses our ACIA replacement
routines (`ACIA_SEND_PACKET` for full packets, `ACIA_FLOW_CONTROL` for
receive). Only `L96C9` still uses the old ROM path.

## Current Call Chain

```
$B175 (frame upload):
  Sets $8034 = $22 (DAT token)
  Reads frame data from memory byte-by-byte
  For each byte: JSR L96C9 (with C=0 for more, C=1 for last byte)
  
L96C9:
  JMP PROTO_RECV_FRAME
  
PROTO_RECV_FRAME ($97B2):
  Sends one byte via MODEM_REG_WRITE (→ ACIA_REG_WRITE)
  Processes receive window (checks for incoming ACKs)
  Uses original X.25 windowed flow control state ($C209, $C22C, etc.)
```

## What $B175 Does (Detailed)

```asm
$B175: LDA #$22        ; Token = DAT
       STA $8034
       LDA $8019       ; Frame data pointer (low)
       STA $1D
       LDA $801A       ; Frame data pointer (high)
       STA $1E
       
loop:  LDA #$00
       PHA             ; Push byte counter/state
       INC $1D/1E     ; Advance pointer
       
       SEI
       LDX #$34        ; Bank out ROMs
       STX $01
       LDA ($1D),Y    ; Read byte from frame memory
       LDX #$36        ; Bank ROMs back in
       STX $01
       CLI
       
       CMP #$00        ; End of frame?
       BEQ end
       
       TAX             ; Save byte
       PLA             ; Restore state
       CLC             ; C=0 = more bytes follow
       JSR L96C9       ; SEND THIS BYTE
       TXA
       BNE loop        ; Continue
       
end:   PLA
       SEC             ; C=1 = last byte
       JMP L96C9       ; Send final byte
```

Key observations:
- Byte to send is in A register
- Carry flag: C=0 = more bytes, C=1 = last byte of stream
- L96C9 is called once per byte
- The routine reads from RAM under ROM ($01 banking)

## Replacement Strategy

Replace `L96C9` with a new routine `ACIA_UPLOAD_BYTE` that:

1. Buffers bytes until a full packet is ready (or end-of-frame reached)
2. Sends complete X.25 packets via `ACIA_SEND_PACKET` when buffer is full
3. On the last byte (C=1), sends the final (partial) packet

### Option A: Buffer-and-Send (Recommended)

Accumulate bytes in a buffer. When the buffer reaches MAX_PAYLOAD (100 bytes)
or when C=1 (last byte), send the buffered data as one X.25 packet.

```
ACIA_UPLOAD_BYTE:
    ; Input: A = byte to send, C = 1 if last byte
    PHP                     ; Save carry (last-byte flag)
    LDX upload_buf_pos
    STA upload_buf,X        ; Store byte in buffer
    INX
    STX upload_buf_pos
    PLP                     ; Restore carry
    BCS @send_final         ; Last byte → send now
    CPX #100                ; Buffer full?
    BCC @done               ; No → return
    ; Buffer full — send packet
    JSR @send_buffer
@done:
    RTS
    
@send_final:
    JSR @send_buffer        ; Send remaining bytes
    RTS
    
@send_buffer:
    ; Send buffered bytes as one X.25 DAT packet
    ; Copy upload_buf to $C100, set Y = length, call ACIA_SEND_PACKET
    LDY upload_buf_pos
    BEQ @nothing            ; Empty buffer, nothing to send
    STY $C14D               ; Payload length
    LDA #$22
    STA $8034               ; Token = DAT
    ; Copy buffer to $C100
    LDX #$00
@copy:
    LDA upload_buf,X
    STA $C100,X
    INX
    CPX upload_buf_pos
    BNE @copy
    ; Reset buffer
    LDA #$00
    STA upload_buf_pos
    ; Send packet
    JMP ACIA_SEND_PACKET
@nothing:
    RTS
```

### Buffer Location

Need ~100 bytes of free RAM for the upload buffer. Candidates:
- $C400-$C4FF (if not used during upload — check for conflicts)
- $0400-$07FF (screen memory — but screen is in use during SENDING)
- $C500-$C5FF (directory buffer — not used during mail send)

Check `$C300-$C3FF` usage: RECV_BUF is there but during upload TX we're
not receiving simultaneously, so it might be safe to reuse. However, the
server's ACK response after the upload will need RECV_BUF. Safer to use
a separate area.

**Recommendation:** Use $C400-$C463 (100 bytes). Check the memory map
for conflicts at this address during the upload phase.

### Option B: Send Each Byte Immediately (Simpler but Slower)

Send a 1-byte X.25 packet for each byte. Very inefficient (overhead of
7+ framing bytes per data byte) but simplest to implement.

Not recommended — would make uploads extremely slow and generate massive
TCP traffic.

## Changes Required

### Client (compunet.s)

1. **Replace L96C9 jump target:**
   ```
   L96C9:
       JMP ACIA_UPLOAD_BYTE    ; was: JMP PROTO_RECV_FRAME
   ```

2. **Add ACIA_UPLOAD_BYTE routine** (Option A buffer-and-send)

3. **Add upload buffer** (100 bytes at chosen RAM location)

4. **Initialisation:** `$B175` should reset the buffer position to 0
   before starting the byte loop. Add `LDA #$00; STA upload_buf_pos`
   at the start of `$B175`. But `$B175` is in .byte data — we may need
   to patch it or add initialisation in the jump shim.

### Server (compunet_server.py)

1. Frame upload packets will now arrive as standard COM/DAT packets
   with proper X.25 framing (same as all other traffic)

2. Server needs to identify upload frame packets and accumulate them
   until the full frame is received

3. After receiving the complete frame, send ACK response

### Protocol Change

- Old: frame data sent byte-by-byte through PROTO_RECV_FRAME (X.25 windowed)
- New: frame data sent as one or more X.25 DAT packets (100-byte chunks)
- Server sees standard DAT packets during pending_send
- End of frame signalled by: the client calling L96D2 after $B175 returns
  (expecting final ACK)

## Testing

1. Verify login + DIR + SHOW still work (no regression from L96C9 change)
2. MAIL → SEND → enter dests → validation works
3. Sub-duckshoot SEND → "SENDING" → frame data arrives at server
4. Server ACKs → client returns to sub-duckshoot
5. FINISH → 'N' command → message delivered
6. Log in as recipient → MAIL → verify message readable

## Risks

- `L96C9` might be called from other code paths we haven't identified
  (search for all JSR L96C9 / JMP L96C9 references)
- The carry flag convention (C=0 more, C=1 last) must be preserved
- `$B175` initialisation: need to ensure buffer is reset before each
  frame upload starts
- Buffer RAM conflicts: must verify chosen address is free during upload
- ACIA_SEND_PACKET modifies $C14D, $8034, $C20E — ensure these don't
  conflict with the upload caller's state
