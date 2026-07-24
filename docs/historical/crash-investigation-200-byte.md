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

## Implementation Attempt (2026-05-14)

Applied Options A+C+D:
- Server: MAX_PAYLOAD reduced to 100, 50ms inter-packet delay
- Client: `@last_byte` replaced with `JSR ACIA_FLOW_CONTROL`

### Result: Intermittent Success

- 5-entry directory (284 bytes, 3 packets) works sometimes but JAMs intermittently
- Welcome frame (281 bytes, 3 packets) usually works
- Increasing delay to 1 second made things WORSE: only half the welcome frame
  renders, then DIR crashes reliably

### Root Cause: ACIA_FLOW_CONTROL Timeout Is Wrong

The `@wait_start` timeout in `ACIA_FLOW_CONTROL` is much shorter than documented:

```
Timeout = $A2 reaching $40 (64) × $A1 wrapping (256) = 16,384 empty @get_byte calls

Each @get_byte call when buffer empty:
  JSR(6) + LDA ACIA_STATUS(4) + LDA NMI_BUF_HEAD(3) + CMP NMI_BUF_TAIL(3)
  + BEQ(3) + SEC(2) + RTS(6) = ~27 cycles
Plus @wait_start → @timeout_check overhead: ~15 cycles
Total per iteration: ~42 cycles

16,384 × 42 = ~688,000 cycles = ~0.69 seconds at 1MHz
```

**The timeout is ~0.7 seconds, NOT ~10 seconds as commented.**

### Why 1-Second Delay Breaks

At 1200 baud (tcpser -s 1200), one byte takes ~8.33ms to transmit. A 100-byte
payload packet is ~112 bytes on the wire = ~933ms delivery time through tcpser.

With 1-second server delay between packets:
1. Server sends packet 1 → tcpser delivers over ~933ms → client processes
2. Server waits 1 second, sends packet 2 → tcpser starts delivering
3. Client hits `@last_byte`, calls `ACIA_FLOW_CONTROL`
4. `ACIA_FLOW_CONTROL` waits for $01 start marker...
5. Packet 2's $01 won't arrive for up to 1.0s (server delay) + 0.93s (tcpser
   delivery of remaining packet 1 bytes still in tcpser buffer)
6. **Timeout fires at 0.7s** → declares end-of-stream prematurely
7. Client gets truncated data → eventual JAM

### Why 50ms Delay Is Intermittent

With 50ms server delay, total time before packet 2's $01 appears depends on:
- How much of packet 1 tcpser has already delivered when the server sends packet 2
- tcpser's internal buffering and scheduling

Sometimes the $01 arrives within 0.7s (works). Sometimes it doesn't (JAM).
The race window depends on VICE execution speed, host system load, and tcpser
thread scheduling — all non-deterministic.

### Revised Understanding

The original investigation identified two contradicting problems:
1. Delay too short → NMI overflow
2. Delay too long → premature timeout

But the **actual constraint** is tighter than documented:
- NMI buffer = 256 bytes (sets maximum in-flight data)
- `ACIA_FLOW_CONTROL` timeout = ~0.7s (NOT 10s)
- tcpser at 1200 baud = ~8.33ms per byte

For reliable multi-packet delivery, the next packet's $01 marker must appear
in the NMI buffer within 0.7 seconds of the previous packet's last byte being
consumed. This means the server delay PLUS remaining tcpser delivery time must
be under 0.7s.

### Revised Fix Options

#### Option E: Increase ACIA_FLOW_CONTROL Timeout

Increase `$A2` comparison from `$40` to a much larger value, giving genuinely
long timeout (e.g., `$FF` × 256 = 65,280 iterations ≈ 2.7 seconds). Combined
with moderate server delay this would be reliable.

However: this also affects the end-of-stream detection. When the server has
truly finished sending (last packet of a response), the client will spin for
the full timeout before declaring end-of-stream. This adds perceptible lag
after every response.

**Mitigation**: Use a two-tier approach — short timeout for "is more data
coming?" (Option D peek replacement) and long timeout for initial packet
receipt. Or: have the server send an explicit end-of-stream marker.

#### Option F: Server End-of-Stream Marker

After the final packet of a response, send a special short packet that signals
"no more data follows." The client's `@last_byte` / `ACIA_FLOW_CONTROL` can
then distinguish "more packets coming" from "stream complete" without relying
on timeout.

Possible implementation: send a zero-length DAT packet (just framing + header,
no payload) as the terminal marker. `ACIA_FLOW_CONTROL` would receive it,
see RECV_LEN=0, and return C=1.

**Pros:** Eliminates ALL timing dependencies. No timeout needed for stream end.
Works at any baud rate or delay combination.
**Cons:** Adds a non-original protocol element (zero-length DAT). Must verify
the client handles RECV_LEN=0 gracefully.

#### Option G: Remove Server-Side Splitting Entirely

Instead of splitting large responses into multiple packets at the server layer,
send the entire response as a single large packet. Increase RECV_BUF to handle
the maximum possible response size (~600 bytes for an 11-entry directory).

**Problem:** RECV_BUF is 254 bytes ($C300-$C3FD). Expanding it requires finding
free RAM and ensuring no collision with other data structures. The NMI ring
buffer at $CE00 (256 bytes) also cannot hold a full large packet — this is the
original overflow problem.

**Verdict:** Not feasible without significant client memory reorganisation.

#### Option H: Baud-Rate-Aware Delay Calculation

Calculate the server-side delay based on the wire size of the packet just sent.
At 1200 baud: delay = (wire_bytes × 8.33ms) + safety_margin.

For a 112-byte wire packet: 112 × 8.33ms = 933ms + 200ms margin = ~1133ms.

But as shown above, this exceeds the 0.7s ACIA_FLOW_CONTROL timeout. So this
option REQUIRES Option E (increased timeout) to work.

### Revised Recommended Approach

**Combine Options E + F + A + C + I (TX re-arm):**

1. **Increase ACIA_FLOW_CONTROL timeout** to ~2.7 seconds (CMP #$FF).
2. **Implement end-of-stream marker** (Option F) — server sends zero-length DAT
   packet after every response. Client detects RECV_LEN=0 → C=1 immediately.
3. **Keep MAX_PAYLOAD at 100** — ensures each wire packet fits in NMI buffer.
4. **50ms inter-packet delay** on the server between data packets.
5. **250ms pre-response delay** on the server before first data packet.
6. **Post-TX NMI re-arm** (Option I) on the client after ACIA_SEND_PACKET.

## Implemented Fix (2026-05-14)

### Changes Applied

**Server (`compunet_server.py`):**
- MAX_PAYLOAD = 100
- 250ms delay before first response packet (after receiving command)
- 50ms delay between subsequent packets
- Zero-length DAT packet (EOS marker) sent after every response stream

**Client (`compunet.s`):**
- `ACIA_FLOW_CONTROL` timeout increased: CMP #$40 → CMP #$FF (~2.7s)
- `ACIA_FLOW_CONTROL` `@pkt_complete`: detects RECV_LEN=0 as EOS, returns C=1
- `@last_byte` in `ACIA_PROCESS_CMD`: replaced peek loop with JSR ACIA_FLOW_CONTROL
- `ACIA_SEND_PACKET`: post-TX NMI re-arm + 256-iteration settle delay (Option I)

### Third Root Cause: TX Kills NMI Edge Detection (Option I)

In addition to the timeout and overflow issues, a third intermittent cause was
discovered: **VICE's 6551 emulation loses NMI edge detection during TX**.

The 6551 ACIA fires NMI on a falling edge of its /IRQ output. During byte
transmission, this edge detection can be disrupted. `ACIA_WAIT_READY` re-arms
NMI after each TX byte by toggling ACIA_CMD bits 1-0 (RX IRQ enable). However,
there is a race window between the last TX byte and when the caller enters
`ACIA_FLOW_CONTROL` to wait for the response.

If the server responds before the NMI edge is properly re-armed, the first
response byte arrives at the ACIA but does NOT trigger an NMI. The byte sits
in the ACIA receive buffer unreported. Subsequent bytes may or may not trigger
NMI depending on whether the edge has re-established. This causes:

1. Lost bytes in the packet stream → framing corruption → JAM
2. Intermittent behaviour (depends on exact timing of server response vs VICE
   emulation cycle)

**Evidence:**
- Adding 100ms server-side pre-response delay helped (gave NMI time to settle)
  but did not eliminate crashes — VICE timing is non-deterministic
- Increasing to 250ms improved reliability further but still intermittent
- The welcome frame (sent with the same delays) worked reliably because the
  login processing time on the server provides a natural delay
- The DIR response (near-instant server processing) crashed more often because
  the response arrives sooner after TX completes

**Fix (Option I):** Add explicit NMI re-arm + settle loop at the end of
`ACIA_SEND_PACKET`:

```asm
    ; Re-arm NMI after TX and settle
    LDA #$01
    STA ACIA_CMD            ; Disable RX IRQ
    LDA #$09
    STA ACIA_CMD            ; Re-enable (re-arms edge)
    LDY #$00
@post_tx_settle:
    LDA ACIA_STATUS         ; Poke VICE to trigger socket poll
    DEY
    BNE @post_tx_settle     ; ~256 iterations settle delay
```

This ensures:
- NMI edge detection is explicitly re-armed after all TX activity
- ACIA_STATUS reads trigger VICE's socket poll (ensures pending RX bytes are
  presented to the emulated ACIA)
- 256 iterations (~1.3ms) provides settling time before ACIA_FLOW_CONTROL runs

Combined with the 250ms server-side pre-response delay, this provides defence
in depth: the client-side fix handles the hardware-level edge detection, while
the server delay provides additional margin for the emulation layer.

### Summary: All Three Root Causes

| # | Problem | Symptom | Fix |
|---|---------|---------|-----|
| 1 | NMI buffer overflow | CPU JAM (data corruption) | Small packets (100 bytes) + inter-packet delay |
| 2 | Premature end-of-stream | Missing characters / truncation | EOS marker packet + increased timeout |
| 3 | TX kills NMI edge detection | Intermittent JAM on first packet after TX | Post-TX re-arm + settle + server pre-response delay |

All three must be addressed together. Fixes 1 and 2 are complementary (as
documented earlier). Fix 3 is orthogonal — it explains the intermittent nature
that persisted even after fixes 1 and 2 were applied.

### Further Findings (2026-05-14, later session)

**Inter-packet delay must be 500ms** — 200ms inter-packet caused intermittent
DIR crashes. 500ms is reliable. This is significantly longer than expected and
suggests tcpser's baud-rate throttling introduces buffering that requires the
gap to allow the client to fully drain each packet from the NMI buffer before
the next begins arriving.

**VICE socket polling requires 500ms pre-response delay** — even for single-
packet ACK responses. Confirmed via VICE monitor: NMI buffer HEAD==TAIL (empty)
after timeout, proving the ACK bytes never reached the emulated ACIA. The issue
is that VICE's ip232 socket polling doesn't deliver incoming data immediately
after the C64 finishes transmitting. A 500ms server-side delay before ALL
responses (including ACKs) is necessary to ensure VICE has re-established
socket polling after the TX activity.

**Client-side post-TX re-arm is minimal** — aggressive settle loops that read
ACIA_DATA or ACIA_STATUS repeatedly caused regressions (welcome frame
corruption). The current fix is a simple ACIA_CMD toggle (disable/re-enable RX
IRQ) which re-arms the NMI edge. The real reliability comes from the server-side
500ms delay, not from client-side polling.

**EOS marker must NOT be sent after ACK responses** — the client only calls
L96D2 once for ACKs. If an EOS follows, it sits in the NMI buffer and corrupts
the next command's response. EOS is only sent for multi-part streamed responses
(directories, frames).

## Verification Plan

1. Create a test directory with 11 entries (triggers ~400 byte response)
2. Verify no JAM crash when entering directory
3. Test with a large frame (full 1000-byte PETSCII screen)
4. Test welcome frame (currently ~100 bytes, should still work)
5. Monitor NMI buffer usage with VICE monitor: `m 029b 029c` (HEAD/TAIL)
6. Measure end-of-stream latency (time between last character rendered and
   cursor/prompt appearing)
7. Test at different baud rates if tcpser config changes
8. Rapid DIR/SHOW cycling to stress-test the TX→RX transition

## Files Involved

| File | Role |
|------|------|
| `client/c64/src/compunet.s` lines 7157-7371 | ACIA_FLOW_CONTROL + ACIA_PROCESS_CMD |
| `client/c64/src/compunet.s` lines 6690-6708 | NMI_HANDLER (ring buffer write) |
| `client/c64/src/compunet.s` lines 7087-7096 | ACIA_SEND_PACKET post-TX re-arm |
| `server/compunet_server.py` lines 931-970 | TCP packet sending loop + EOS |
| `server/x25_protocol.py` lines 171-217 | make_data_packet (framing) |
