# Investigation: MAIL SEND ACK Delivery Failure

## Problem

After the client sends the 'U' ($55) MAIL SEND command, the server responds
with an ACK packet. The client never receives it — confirmed via VICE monitor
showing NMI ring buffer HEAD==TAIL (empty) after the 2.7-second timeout.

## What Works vs What Doesn't

| Scenario | Packet Size | Delay | Result |
|----------|------------|-------|--------|
| Welcome frame (3 packets) | 107+107+88 wire | 50ms inter-pkt | Works |
| DIR response (3 packets) | 107+107+91 wire | 500ms inter-pkt | Works |
| SHOW frame (1-2 packets) | 97-107 wire | 500ms pre-delay | Works |
| ACK after 'U' (1 packet) | ~11 wire | 500ms pre-delay | **Fails** |

The critical difference: **all working responses are large packets (97+ wire
bytes)**. The ACK is only ~11 wire bytes.

## Root Cause Analysis

The failure is in the VICE ip232/SwiftLink emulation layer. After a TX burst
from the C64, VICE's socket polling doesn't reliably deliver small incoming
packets to the emulated ACIA hardware. Specifically:

1. Client transmits 'U' packet (~33 wire bytes) via ACIA_SEND_PACKET
2. ACIA_SEND_PACKET completes, does minimal NMI re-arm (CMD toggle)
3. Client enters ACIA_FLOW_CONTROL, polling NMI buffer for $01 start marker
4. Server sends 11-byte ACK to TCP socket → tcpser → VICE ip232 socket
5. Bytes sit in the socket buffer but VICE never delivers them to the ACIA
6. Timeout fires after ~2.7 seconds

The ACIA_STATUS reads in @get_byte are supposed to trigger VICE's socket poll,
but for small packets after TX activity, this mechanism is unreliable.

### Why Large Packets Work

Large responses (107+ bytes) appear to trigger a different code path in VICE's
socket handling — possibly a larger recv() return value forces buffer processing,
or the continuous stream of bytes provides enough NMI triggers to keep the
delivery mechanism active.

### Why Welcome Frame Works with 50ms Delay

The welcome frame is sent during a different connection phase — before the
command loop starts. The C64 is in a receive-only state after login (no recent
TX activity on the same socket path). Additionally, it's multi-packet, providing
repeated delivery opportunities.

## Attempted Fixes That Failed

1. **Client-side settle loop (256× ACIA_STATUS poll)** — caused welcome frame
   corruption. The rapid NMI firing during the settle window interfered with
   data already being delivered.

2. **Client-side settle loop with ACIA_DATA drain** — worse corruption. Stealing
   bytes from the NMI handler's delivery path.

3. **Removing pre-response delay for ACKs** — no improvement.

4. **Padding ACK to 4 bytes** — still only 11 wire bytes, still fails.

## Proposed Solution: Pad ACK to Match Working Packet Size

The simplest fix: pad the ACK response payload to ~100 bytes. This makes the
wire packet ~107 bytes — identical in size to the DIR/SHOW packets that work
reliably.

```python
# Instead of:
return bytes([RESP_ACK]) + b'\x00' * 3

# Use:
return bytes([RESP_ACK]) + b'\x00' * 99
```

The client only checks the carry flag from ACIA_FLOW_CONTROL — it doesn't
read the ACK payload bytes. The padding is harmless. After ACIA_FLOW_CONTROL
returns C=0 (success), the client proceeds directly to the Editor setup.
The padded bytes remain in RECV_BUF but are overwritten on the next
ACIA_FLOW_CONTROL call.

### Why This Should Work

- Matches the exact packet size of DIR response packets (which work reliably)
- Same wire encoding, same delivery path through tcpser/VICE
- No client-side changes needed
- No timing assumptions — works regardless of VICE polling cadence

### Additional Measures

1. **Remove `is_ack` special case in TCP send loop** — treat all responses
   identically (500ms pre-delay, 500ms inter-packet if multi-packet, EOS for
   streams). The size-based reliability difference means we should never try
   to optimise ACK delivery by skipping delays.

2. **TCP_NODELAY on the server socket** — disables Nagle's algorithm, ensuring
   small packets are sent immediately without waiting to coalesce. This
   eliminates one potential source of delay in the TCP → tcpser path.

3. **If padding alone fails: treat ACK as a stream** — send the padded ACK
   WITH an EOS marker and full 500ms delays (same as DIR). The extra EOS
   would sit in the NMI buffer after ACIA_FLOW_CONTROL returns, but since
   the client's next action is to SEND (TX), not receive, the stale EOS
   bytes get overwritten by the next response.

## Alternative: Restructure as Non-ACK Response

Instead of an ACK, respond to 'U' with something the client consumes as a
stream. However, this is risky — the disassembly shows L96D2 is called once
and the code proceeds based on carry flag only. The payload is not consumed.
Padding the existing ACK is safer.

## Resolution: Wrong Response Format (Not Timing)

The "stuck" issue was never about timing, overrun, or NMI. It was sending the
wrong response format. The client expects a **user validation stream** after
the first 'U' command.

## Frame Upload: Uses Original ROM Protocol Engine

**Critical finding:** The frame upload at $B175 does NOT use ACIA_SEND_PACKET.
It calls `L96C9` (= `PROTO_RECV_FRAME`) for each byte — the original ROM's
half-duplex X.25 windowed protocol engine.

This means:
- Frame bytes are sent through `MODEM_REG_WRITE` → `ACIA_REG_WRITE` one at a time
- The original protocol engine expects to receive X.25 ACK tokens ($20) with
  matching sequence numbers between bytes (windowed flow control)
- The server sees packets with non-standard tokens ($7F, $62) because the ROM's
  framing is different from our ACIA_SEND_PACKET framing
- The "ECH" status on screen = protocol engine reporting received data

**This requires implementing proper X.25 windowed ACK flow control on the
server side for the upload path.** The server must send ACK packets (token $20)
with the correct sequence numbers as the frame data arrives.

## Full SEND Protocol Flow (Confirmed)

```
1. Client sends 'U' (26 bytes: subject+type+dests) via ACIA_SEND_PACKET [COM]
2. Server responds: validation stream [8-byte ID + status + $1E per dest] [EOS]
3. Client displays results, prompts "OKAY?"
4. Client enters sub-duckshoot (SEND/FINISH/NEXT/LAST/GET)
5. User selects SEND:
   a. Client sends 'U' (1 byte, no params) via ACIA_SEND_PACKET [COM]
   b. Server ACKs (any valid DAT response)
   c. Client prints "SENDING"
   d. Client calls $B175: sends frame byte-by-byte via PROTO_RECV_FRAME [L96C9]
      - Uses original ROM X.25 windowed protocol
      - Server must ACK with proper X.25 ACK tokens
   e. Client calls L96D2 waiting for final server response
6. User selects FINISH:
   - Client sends 'N' command
   - Server delivers message to recipients
```

## Test Plan

1. Implement proper X.25 ACK handling for frame upload data
2. Send MAIL → SEND → enter subject/dest → verify validation
3. Enter sub-duckshoot → SEND frame → verify delivery
4. Test FINISH → verify message appears in recipient's mailbox
5. Verify DIR/SHOW still work (no regression)
