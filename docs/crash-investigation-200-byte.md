# Investigation: CPU JAM Crash at ~200 Bytes

## Summary

The C64 client crashes with a CPU JAM (illegal opcode execution) when receiving
responses larger than approximately 200 bytes — for example, a directory listing
with many entries. This document records the root cause analysis and proposed fix.

## Architecture Overview

### Data Flow: Server → Client

```
Server Python                TCP Wire              C64 Client
─────────────────────────────────────────────────────────────────────
session.handle_command()     
  → bytes response           
                              
x25.make_data_packet()  ───→  $01 [hdr] [payload] $02
                              $01 [hdr] [payload] $02  (if >200 bytes)
                              
                                                   NMI_HANDLER → NMI_BUF ($CE00, 256 bytes)
                                                   ACIA_FLOW_CONTROL reads NMI_BUF → RECV_BUF ($C300)
                                                   ACIA_PROCESS_CMD delivers one byte at a time
```

### Key Memory Regions

| Address     | Purpose                     | Size      |
|-------------|-----------------------------|-----------|
| `$CE00`     | NMI ring buffer             | 256 bytes |
| `$C300`     | RECV_BUF (packet payload)   | 254 bytes |
| `$C3FC`     | SEND_PKT_LEN temp           | 1 byte    |
| `$C3FD`     | NODATA_FLAG                 | 1 byte    |
| `$C3FE`     | RECV_LEN                    | 1 byte    |
| `$C3FF`     | RECV_POS                    | 1 byte    |
| `$C400`     | (next page — unknown usage) | -         |

### Server Send Logic (`compunet_server.py`, lines 951-960)

```python
MAX_PAYLOAD = 200
offset = 0
while offset < len(cmd_response):
    chunk = cmd_response[offset:offset + MAX_PAYLOAD]
    pkt = x25.make_data_packet(chunk, TOKEN_DAT)
    writer.write(pkt)
    await writer.drain()
    offset += MAX_PAYLOAD
```

The server splits responses into 200-byte payload chunks. Each chunk becomes an
X.25 packet on the wire: `$01 + [len,token,seq] + payload + [CRC] + $02`.

After byte stuffing, a 200-byte payload packet could expand to ~215+ bytes on
the wire (any $01/$02/$03 in data adds one escape byte).

**Critical: packets are sent back-to-back with NO inter-packet delay and NO
waiting for client ACK between packets.**

## Root Cause Analysis

### The Problem: NMI Ring Buffer Overflow

The NMI ring buffer at `$CE00` is exactly 256 bytes with 8-bit HEAD and TAIL
pointers (`$029C` and `$029B`). When TAIL wraps past HEAD, data is silently
overwritten.

The overflow sequence:

1. Server sends packet 1 (200-byte payload, ~210 bytes on wire)
2. NMI handler stores bytes in ring buffer as they arrive
3. Server immediately sends packet 2 (remaining bytes)
4. **Before the client finishes processing packet 1**, packet 2 bytes arrive
   via NMI and fill the ring buffer
5. Ring buffer wraps → overwrites unread data from packet 1
6. `ACIA_FLOW_CONTROL` reads corrupted data as packet content
7. Corrupted bytes stored in `RECV_BUF` at `$C300`
8. Application code interprets garbage as PETSCII/control data
9. Eventually an illegal opcode value ends up in an indirect jump or is
   executed as code → **CPU JAM**

### Why ~200 Bytes Is the Trigger

A single packet with 200-byte payload is approximately:
- Wire bytes: 1 (start) + ~210 (stuffed content) + 1 (end) ≈ 212 bytes

This alone nearly fills the 256-byte NMI ring buffer. If a second packet arrives
before the first is fully consumed by `ACIA_FLOW_CONTROL`, the buffer wraps.

For a directory with 11 entries, the response is approximately 300-500 bytes,
requiring 2-3 packets. The second packet arrives while the first is still being
parsed → overflow → JAM.

### Secondary Issue: No ACK/Flow-Control Between Packets

The original Compunet protocol used windowed X.25 with ACKs. The ROM's
`PROTO_RECV_FRAME` / `PROTO_PROCESS_CMD` only delivers data after the windowed
protocol has acknowledged receipt. But:

- The server currently **does not wait for ACKs** between DAT packets
- The client's ACIA layer **does not send ACKs** for received DAT packets
- The server fires all chunks into TCP immediately

TCP's own flow control operates at the OS buffer level (~64KB+), not at the
256-byte granularity the C64 needs.

### Tertiary Issue: ACIA_PROCESS_CMD `@last_byte` Peek Timing

When `ACIA_PROCESS_CMD` delivers the last byte of a packet (line 7301), it
peeks the NMI buffer to check if a `$01` start marker is waiting. If the next
packet hasn't arrived yet (network jitter), it returns C=1 (end-of-stream) even
though more data is coming. This causes:
- Premature stream termination for multi-packet responses
- The `@no_data` path returns fake `$2C`/`$0D` terminators
- Directory parsing truncates mid-entry

## Proposed Fix Options

### Option A: Server-Side Pacing (Simplest, No Client Changes)

Add a delay between packets on the server so the NMI buffer never accumulates
more than one packet at a time.

```python
MAX_PAYLOAD = 200
offset = 0
while offset < len(cmd_response):
    chunk = cmd_response[offset:offset + MAX_PAYLOAD]
    pkt = x25.make_data_packet(chunk, TOKEN_DAT)
    writer.write(pkt)
    await writer.drain()
    await asyncio.sleep(0.05)  # 50ms inter-packet gap
    offset += MAX_PAYLOAD
```

**Pros:** No client code changes. Immediately testable.  
**Cons:** Relies on timing assumptions. If VICE or host system is slow, still
could overflow. Doesn't solve the `@last_byte` peek timing issue. Downloading
8K linking data would take 2+ seconds.

### Option B: ACK-Based Flow Control (Correct Protocol Fix)

Implement proper ACK exchange: server sends one DAT packet, waits for client
ACK, then sends next.

**Server changes:**
- After each `make_data_packet()`, wait for client ACK before sending next
- Add timeout + retransmit logic

**Client changes:**
- After `ACIA_FLOW_CONTROL` successfully receives a DAT packet, send an ACK
  back to the server
- This mirrors what the original ROM's protocol engine does

**Pros:** Correct. Reliable regardless of timing. Matches original protocol.  
**Cons:** Significant implementation effort on both sides. Need to handle the
case where ACIA_SEND_PACKET transmits while also receiving (TX kills NMI edge
detection — see `ACIA_WAIT_READY` line 6802).

### Option C: Reduce MAX_PAYLOAD to Fit One Packet in NMI Buffer (Pragmatic)

Reduce MAX_PAYLOAD so that even after byte stuffing, the wire packet fits
comfortably in the 256-byte ring buffer, combined with inter-packet delay.

Worst case byte stuffing: every byte escapes = 2x expansion.  
Safe payload: 100 bytes → worst case ~210 wire bytes → fits in 256 with margin.

Combined with a modest delay (Option A), this ensures the buffer never overflows.

**Pros:** Simple. Reliable within reasonable assumptions.  
**Cons:** Slower throughput. Still timing-dependent. Doesn't help the peek
problem.

### Option D: Fix the Peek Timing in ACIA_PROCESS_CMD (Companion Fix)

The `@last_byte` code (line 7308) only waits ~4K iterations for the next packet
to begin arriving. This is too short for server-paced delivery.

Fix: When `ACIA_PROCESS_CMD` hits end-of-current-packet, instead of peeking
with a short timeout, unconditionally call `ACIA_FLOW_CONTROL` (which has a
much longer ~10-second timeout). If it succeeds, deliver from the new packet.
If it times out, then declare end-of-stream.

This would replace the `@last_byte` section with:
```asm
@last_byte:
    PHA
    TYA
    PHA                      ; Save caller's Y
    JSR ACIA_FLOW_CONTROL    ; Wait for next packet (10s timeout)
    PLA
    TAY                      ; Restore caller's Y
    BCS @stream_done         ; Timeout → genuine end
    PLA                      ; Restore byte to deliver
    LDX @save_x+1
    CLC                      ; More data follows
    RTS
@stream_done:
    PLA                      ; Restore byte to deliver
    LDX @save_x+1
    SEC                      ; End of stream
    RTS
```

**Pros:** Eliminates premature truncation. Works with any pacing scheme.  
**Cons:** Must be combined with Option A or C to prevent buffer overflow.

## Recommended Approach

**Combine Options A + C + D:**

1. **Reduce MAX_PAYLOAD to 100** (safe single-packet size after stuffing)
2. **Add inter-packet delay of 50ms** on the server
3. **Fix `@last_byte` in ACIA_PROCESS_CMD** to call ACIA_FLOW_CONTROL instead of
   the short peek

This combination:
- Prevents NMI buffer overflow (single packet always fits)
- Allows multi-packet streams to work reliably (proper inter-packet bridging)
- Requires minimal client code change (only the @last_byte section)
- Doesn't require full ACK implementation (can be added later for Option B)

## Why Previous Multi-Packet Attempts Failed (Missing Characters)

Previous attempts to fix this by splitting frames into multiple packets caused
a different symptom: characters missing from rendered frames. This is the
`@last_byte` peek problem manifesting as data loss rather than corruption.

### The Existing Breakage Point

When data is split across packets, `ACIA_PROCESS_CMD` delivers the last byte of
packet 1, then hits the `@last_byte` code (line 7308):

```asm
@last_byte:
    LDY #$10               ; 16 outer rounds
@last_outer:
    LDX #$00
@last_wait:
    LDA NMI_BUF_HEAD
    CMP NMI_BUF_TAIL
    BNE @last_check         ; Something in buffer — peek it
    INX
    BNE @last_wait          ; 256 inner loops
    DEY
    BNE @last_outer         ; Total: ~4K iterations (~4ms at 1MHz)
    BEQ @last_no_more       ; TIMEOUT → SEC (end of stream!)
@last_check:
    TAY
    LDA NMI_BUF,Y
    CMP #$01                ; Is it a start marker?
    BEQ @last_more          ; Yes → CLC (more coming)
@last_no_more:              ; No → SEC (stream done!)
```

This fails in two ways:

1. **Timeout too short** — if the server's inter-packet delay (needed to prevent
   buffer overflow) means packet 2's `$01` hasn't arrived within ~4K CPU
   iterations (~4ms at 1MHz), the peek declares end-of-stream. The frame
   renderer sees C=1, stops reading. Remaining characters in packet 2 are
   never delivered → **missing characters**.

2. **Non-$01 byte in buffer** — if any stray byte is sitting in the NMI buffer
   (e.g., leftover from timing variance), the peek sees non-$01, immediately
   declares end-of-stream. Same result.

### Why Options A+C Alone Recreate This Problem

Even with perfect pacing and small packets, the `@last_byte` peek is a race
condition. The delay between packets is *intentional* (to let the client drain
the NMI buffer), but the peek interprets that delay as "no more data."

You cannot simultaneously:
- Add delay to prevent NMI overflow (Option A)
- Have the peek succeed within its ~4ms window

They directly contradict each other.

### Why Option D Resolves This

Replacing the peek with `JSR ACIA_FLOW_CONTROL`:

- `ACIA_FLOW_CONTROL` has a ~10 second timeout (vs ~4ms for the peek)
- It properly skips non-$01 bytes in its `@wait_start` loop
- On success it sets up RECV_BUF, RECV_LEN, RECV_POS for the new packet
- Next call to `ACIA_PROCESS_CMD` delivers seamlessly from the new buffer

The inter-packet bridge becomes **deterministic** rather than timing-dependent.
The 50ms server delay fits comfortably within 10 seconds, and the client
reliably transitions between packets.

### Both Failure Modes Require Different Fixes

| Problem | Symptom | Fix |
|---------|---------|-----|
| NMI overflow | CPU JAM (corruption) | Options A+C (small packets + delay) |
| Premature end-of-stream | Missing characters | Option D (proper inter-packet wait) |

They are complementary: A+C keep the buffer safe, D keeps the stream intact.
Neither alone is sufficient — which is why previous attempts that only addressed
one side introduced the other failure mode.

## Verification Plan

1. Create a test directory with 11 entries (triggers ~400 byte response)
2. Verify no JAM crash when entering directory
3. Test with a large frame (full 1000-byte PETSCII screen)
4. Test welcome frame (currently ~100 bytes, should still work)
5. Monitor NMI buffer usage with VICE monitor: `m 029b 029c` (HEAD/TAIL)

## Files Involved

| File | Role |
|------|------|
| `client/c64/src/compunet.s` lines 7157-7371 | ACIA_FLOW_CONTROL + ACIA_PROCESS_CMD |
| `client/c64/src/compunet.s` lines 6690-6708 | NMI_HANDLER (ring buffer write) |
| `server/compunet_server.py` lines 931-960 | TCP packet sending loop |
| `server/x25_protocol.py` lines 171-217 | make_data_packet (framing) |
