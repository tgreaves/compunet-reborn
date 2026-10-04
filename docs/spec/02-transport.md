# §2 — Transport

**Layer — Binding-A wire format** (X.25-over-TCP). The service *semantics* these bytes carry are shared model; a modern binding replaces this section (§1.8).

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority: `server/x25_protocol.py` (framing, CRC, stuffing, sequencing) and the packet
> dispatch in `server/compunet_server.py`. All byte values below were verified against
> that code.

This section defines the wire transport: how a client and the server exchange **packets**
over a TCP connection. Everything above this layer — commands (§4), frames (§6),
directories (§7) — is carried as the payload of the packets defined here.

## 2.1 Connection

- A client **MUST** connect to the server over **TCP** and exchange the byte streams
  defined in this specification. The default protocol port is **6400**.
- TCP provides reliable, ordered delivery. The framing in this section therefore exists
  to mark **packet boundaries**, carry a **token** and **sequence number**, and protect
  each packet with a **CRC** — not to recover lost bytes.
- The connection opens with a one-byte handshake exchange (§2.9) before any framed packet
  is sent. The full connect/identify/login sequence is specified in [§3](03-session.md).

*(Non-normative: the server also exposes a server-rendered PETSCII terminal on TCP port
6401. That endpoint does not use the framing in this section and is out of scope — see
§1.3.)*

## 2.2 Packet framing

Every packet is delimited on the wire by two marker bytes:

```
$01  <byte-stuffed content>  $02
```

- `$01` (`PKT_START`) marks the start of a packet.
- `$02` (`PKT_END`) marks the end.
- The bytes between the markers are the **byte-stuffed** form (§2.3) of the packet
  **content** (§2.4).

A receiver **MUST** locate packets by scanning for `$01`, then reading up to the next
`$02`. Any bytes received before a `$01` **MUST** be discarded. Because the content is
byte-stuffed, a genuine `$01` or `$02` never occurs inside a packet, so the markers are
unambiguous.

## 2.3 Byte stuffing

The three byte values `$01`, `$02`, and `$03` are reserved for framing and **MUST NOT**
appear literally inside packet content on the wire. Before framing, a sender **MUST**
escape them; after de-framing, a receiver **MUST** unescape them:

| Content byte | On the wire | Note |
|---|---|---|
| `$00` | `$00` | sent as-is |
| `$01` | `$03 $21` | escaped (would otherwise be a start marker) |
| `$02` | `$03 $22` | escaped (would otherwise be an end marker) |
| `$03` | `$03 $23` | escaped (the escape byte itself) |
| `$04`–`$FF` | unchanged | sent as-is |

The rule is: a content byte `b` in the range `$01`–`$03` is transmitted as `$03` followed
by `b + $20`. On receive, a `$03` followed by a byte in the range `$20`–`$2F` is decoded
back to `(next byte) − $20`.

Byte stuffing applies to **all** content bytes between the markers — the length byte, the
token, the sequence number, the payload, **and the two CRC bytes**. A CRC byte that
happens to equal `$01`–`$03` **MUST** be stuffed, or the receiver will mistake it for a
marker.

## 2.4 Packet content

The **content** of a packet (before byte stuffing, between the markers) is:

| Offset | Field | Size | Description |
|---|---|---|---|
| 0 | `length` | 1 | Total unescaped content length, in bytes, **including this byte and the two CRC bytes** |
| 1 | `token` | 1 | Packet type (§2.5) |
| 2 | `seq` | 1 | Sequence number (§2.8) |
| 3 | `payload` | N ≥ 0 | Command / frame / directory data |
| −2 | `crc_hi` | 1 | CRC-CCITT high byte (§2.6) |
| −1 | `crc_lo` | 1 | CRC-CCITT low byte |

Therefore `length = N + 5` where `N` is the payload length. The minimum content length is
5 (an empty-payload packet: `length`, `token`, `seq`, `crc_hi`, `crc_lo`). A receiver
**MUST** reject content shorter than 5 bytes.

The `length` field counts **unescaped** bytes (the content as laid out above), not the
possibly-longer byte-stuffed form seen on the wire.

> **⚠ `length` is ONE BYTE and WRAPS. It is advisory — do not derive the payload length
> from it.** Payloads larger than 250 are legal and routine (§2.4.1), so `N + 5` does not fit
> and the field carries `(N + 5) mod 256`. A 4000-byte payload transmits `length = $A5`
> (165). Receivers **MUST** determine the payload length from where the `$02` end marker
> fell, after de-stuffing, and **MUST NOT** reject a packet because `length` disagrees.
> Senders **MUST** transmit the truncated value and **MUST** include it, as truncated, in
> the CRC — a sender that computed the CRC over an untruncated length would fail every
> frame against a conforming receiver.
>
> Both of this project's implementations frame on the markers and always have, which is why
> 4000-byte uploads worked from the start. The trap is on the *sending* side: the reference
> server built its length byte without masking, which raised on any payload over 250 and
> dropped the connection mid-transfer. That went unnoticed for as long as every send was
> 100 bytes, and surfaced the moment program downloads were widened.

### 2.4.1 Payload size

There is no protocol maximum beyond what the framing and the receiver's buffer allow. In
practice:

- **C64 clients: 100 bytes.** The ROM's receive path expects it; a server **MUST NOT** send
  more to a C64 session.
- **Amiga: up to 4000 bytes.** This is the client's own send size and its safe ceiling —
  `net_recv_frame` collects into an 8302-byte buffer, and worst-case stuffing (every byte
  in `$01`–`$03`) doubles a 4005-byte content to 8010.

Size matters far more than it appears: each packet costs a round trip, and on an emulated
Amiga each round trip costs one ~20 ms frame tick, because `bsdsocket.library` emulation
services socket I/O once per frame. At 100 bytes a 166K download took 36 seconds; at 4000 it
takes 0.9. A client that is slow to receive should look at packet count before anything
else.

## 2.5 Tokens

The `token` byte identifies the packet type. The values a conforming client must handle
are:

| Token | Value | Direction | Meaning |
|---|---|---|---|
| **ACK** | `$20` | either | Acknowledgement of a received `DAT` packet (§2.9) |
| **DAT** | `$22` | server → client | Data — carries frames, directory listings, command responses, and the LINKING stream |
| **COM** | `$43` | client → server | Command — carries login and every single-letter command (§4) |

> **Normative clarification (resolves a documented inconsistency).** Historical notes and
> an enumeration in the server source list a `$20`–`$26` token range
> (`ACK=$20, DIR=$21, DAT=$22, OK=$23, ERR=$24, FTL=$25, COM=$26`). That range is the
> original ROM's internal **display-name table**, not the set of values used on the wire by
> Reborn. The values that the Reborn server actually acts on are `ACK=$20`, `DAT=$22`
> (server → client), and **`COM=$43`** (client → server) — the server keys its command
> dispatch off token `$43` (`compunet_server.py`), and the `TOKEN_COM = $26` constant in
> `x25_protocol.py` is **not** the value clients send and is not used on the command path.
> A conforming client **MUST** send commands with token `$43` and **MUST** treat
> server data as token `$22`.

Two further client → server token values appear only within the program-download
subsystem — `$40` ("proceed / send the data") and `$41` ("abort") — and are specified in
[§8](08-subsystems.md) rather than here, because they are meaningful only in that exchange.

Every substantive server → client response in Reborn is delivered as one or more **DAT**
(`$22`) packets, including responses the ROM enumeration would have labelled `DIR`/`OK`/
`ERR`. A client **MUST NOT** rely on receiving `$21`/`$23`/`$24`/`$25` tokens.

## 2.6 CRC

Each packet carries a 16-bit **CRC-CCITT** (polynomial `$1021`, MSB-first) in its last two
content bytes, high byte first.

- The CRC is computed over the packet content **from the `length` byte up to but not
  including the two CRC bytes**, in unescaped form.
- The initialisation value is **`$0000`**. *(Non-normative: `x25_protocol.py` defines a
  default init of `$40E6`, but every call site — packet build, ACK build, and receive
  verification — passes `$0000`, so `$0000` is the effective, authoritative value.)*
- Byte stuffing is applied **after** the CRC is computed and appended; de-stuffing is
  applied **before** the CRC is checked.

Reference algorithm (non-normative, but produces the required values):

```python
def crc_ccitt(data, crc=0x0000):
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return (crc >> 8) & 0xFF, crc & 0xFF
```

A receiver **MAY** verify by re-running the CRC over the whole content including the two
received CRC bytes: with init `$0000`, a valid packet yields a `$0000` residual (the
zero-residual property of CRC-CCITT).

*(Non-normative compatibility note: the reference server does **not** reject a packet
whose CRC fails — it logs a warning and processes the packet anyway (PROTOCOL.md, *Known
Protocol Deviations*) — and it compares modulo bit 7, so a mismatch confined to bit 7 is
not even logged. The bit-7 tolerance dates from C64 uploads made through VICE's ip232
protocol and tcpser, which arrived with bit 7 cleared; connecting VICE directly to the
server over TCP preserves all 8 bits (`docs/historical/UPLOAD-BIT7-INVESTIGATION.md`). A
client SHOULD send correct 8-bit CRC bytes.)*

> **Corrected.** This note used to say *"VICE's SwiftLink emulation strips bit 7 from
> transmitted bytes"*. It does not: at the client's 8-bit word length VICE's ACIA sends
> `txdata & datamask` with `datamask = $FF` (`int_acia_tx`, `src/aciacore.c`), and the
> project's own investigation placed the loss in the ip232/tcpser path. It also read as
> though the bit-7 comparison decided whether a packet was accepted; it only decides
> whether a mismatch is logged.

## 2.7 Worked examples

**Server → client DAT packet, one payload byte `$00`** (verified form):

```
$01  06 22 20 00 C9 D9  $02
     │  │  │  │  └──┴── CRC-CCITT ($C9D9)
     │  │  │  └──────── payload (1 byte: $00)
     │  │  └─────────── seq ($20)
     │  └────────────── token ($22 = DAT)
     └───────────────── length ($06 = 6 unescaped content bytes)
```

**Client → server ACK for sequence `$20`** (as built by `make_ack`):

```
content : 06 20 20 20 <crc_hi> <crc_lo>
          │  │  │  └── seq being acked ($20)
          │  │  └───── fixed byte ($20)
          │  └──────── token ($20 = ACK)
          └─────────── length ($06)
wire    : $01 <byte-stuffed content> $02
```

## 2.8 Sequence numbers

- Sequence numbers occupy the range **`$20`–`$5F`** inclusive. Incrementing past `$5F`
  wraps back to `$20`.
- **There is no window.** The server → client direction is stop-and-wait (§2.9): the
  server waits for each `DAT`'s ACK (up to its 5-second timeout) before sending the next,
  so a client that ACKs promptly needs to hold only one packet at a time. The server never sends an ACK (`$20`) packet for the
  client's packets — the "accept" it returns after a whole uploaded frame is an
  application-level `DAT` (§8.3.2), not a transport ACK — so nothing at this layer paces
  client → server; TCP does.

  > **Corrected.** This section used to say *"The window size is 4"*, which contradicted
  > §2.9's *"no windowing"*. The 4 is the original ROM's protocol engine (a 4-slot packet
  > buffer, `$C210`/`$C211`; PROTOCOL.md *Flow Control*). Reborn does not use it in either
  > direction: `WINDOW_SIZE = 4` in `x25_protocol.py` is defined and never read. Do not
  > read it as permission to send ahead — four 100-byte packets, stuffed, can exceed the
  > C64 client's 256-byte receive ring.
- The server's transmit sequence starts at **`$21`** (it reserves `$20` to avoid a
  collision with the login echo; see §3).
- A client **MUST** echo the received `DAT` sequence number in the ACK it returns (§2.9)
  and **MUST** keep its own transmit sequence within the `$20`–`$5F` range with the same
  wrap.
- A client **MAY** begin its transmit sequence at any value in range (`$20` is fine). The
  server does not reject an out-of-order client sequence — it reads the number rather than
  validating it — so the client's starting value is not significant for interoperation.

## 2.9 Flow control (ACK pacing)

Reborn paces the server → client data stream with a stop-and-wait ACK, so a slow client is
not overrun regardless of link speed — provided it ACKs within the server's timeout (below):

1. The server sends a `DAT` (`$22`) packet with sequence `seq`.
2. The client receives it, de-stuffs it, and validates the **CRC**. It does *not* validate
   the `length` byte, which is advisory and wraps (§2.4).
3. The client sends an **ACK** (`$20`) packet echoing `seq`.
4. The server, on receiving the ACK, sends the next packet.

⚠ **This is stop-and-wait, so throughput is bounded by round-trip latency, not by
bandwidth** — one round trip per packet, no windowing. Where a round trip is expensive the
packet size dominates everything else: on an emulated Amiga each costs one ~20 ms frame
tick, making a 166K download take 36 seconds at 100-byte packets and 0.9 seconds at 4000
(§2.4.1). Implementers tuning a slow transfer should count packets first.

The ACK packet has a **fixed 6-byte content**: `length = $06`, `token = $20` (ACK), a fixed
byte `$20`, the `seq` being acknowledged, then the two CRC bytes (framed and byte-stuffed like
any packet, §2.2–2.4). In other words its payload is the two bytes `$20 seq`. The worked
bytes are in §2.7.

Rules a conforming client **MUST** follow:

- **Only** `DAT` (`$22`) packets are acknowledged. A client **MUST NOT** ACK anything else.
- A **zero-length-payload `DAT`** is the **end-of-stream (EOS)** marker for a multi-packet
  response. It signals the end of the data and **MUST NOT** be acknowledged; the client
  treats it as "stream complete" (see §4, §6).
- Command echoes and error responses are not acknowledged.

*(Non-normative: the server waits up to 5 seconds for each ACK. On timeout it **carries on
and sends the next packet** — `send_pkt_with_ack` does not check the result of
`wait_for_ack`. A client that fails to ACK therefore sees each packet delayed by 5 seconds,
not a stalled stream; and a client that takes longer than 5 seconds to ACK can receive the
next packet while still holding the last.)*

> **Corrected.** This note used to say the server *"logs a warning and continues"* and that
> a client that fails to ACK *"will stall the stream at that packet"*. The two contradicted
> each other, and the second was wrong: the stream does not stall. (The timeout is logged at
> debug level, not as a warning.)

## 2.10 Connection handshake

Immediately after the TCP connection is established, a short space-byte (`$20`) handshake
is exchanged before any framed packet. The client emits the handshake byte and the server
replies in kind, after which the protocol state is initialised and framed packets flow.
The exact byte counts and the identification that follows are specified in
[§3 — Session lifecycle](03-session.md).
