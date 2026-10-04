# Compunet Modem vs 6551 ACIA — Hardware Layer

> **C64 platform note (non-normative).** This is the hardware layer of the C64 client and
> is out of scope for the protocol. The transport a client must implement over TCP is
> specified in **[docs/spec/§2](spec/02-transport.md)**.

## Overview

The Compunet ROM was designed for a custom modem ("the brick") with a register-select
architecture accessed via $DE00/$DE01. We replace this with a 6551 ACIA (SwiftLink)
at $DE00-$DE03, connected **directly to the server over TCP**: VICE's SwiftLink
emulation opens the socket itself, and a C64 Ultimate's SwiftLink bridge dials it from
the `ATDT` command. See *Server Handshake (TCP)* in [PROTOCOL.md](PROTOCOL.md).
tcpser is no longer needed (see *tcpser (legacy)* below).

All communication uses **polling** (like CCGMS) — the NMI handler stores incoming
bytes in a ring buffer, and the main code polls the buffer to assemble packets.

## Original Compunet Modem

### Register Access
- **$DE00** = register select (write a number to choose which register to access)
- **$DE01** = data port (read/write the selected register)

### Key Registers
| Reg | Dir   | Purpose |
|-----|-------|---------|
| 0   | Read  | Status: bit 5=carrier, bit 6=RX data available, bit 7=TX ready |
| 3   | Write | Mode control ($90=enable after connect, $D0=protocol mode) |
| 4   | Write | Transmit data byte |
| 8   | Read  | Receive status: bit 4=ring/dial, bit 6=data ready |

### ROM's Receive Model (Original)
1. IRQ handler at $9C63 fires on CIA timer (~60Hz)
2. Calls $9D00 → $9D54 which polls register 0 (bit 6 = data available)
3. If data available: reads register 4, feeds byte into X.25 packet state machine
4. If no data: returns immediately
5. Complete packets stored in 4-slot buffer ($C22C[0-3])
6. Main code ($9A17) checks slots for complete packets

### Why IRQ-Driven Assembly Breaks with ACIA

The brick modem holds exactly one byte until read. At 1200 baud, bytes arrive
every ~833μs. The 60Hz IRQ reads one byte per tick — plenty of time.

With ACIA + NMI buffer, TCP delivers data in bursts. The NMI handler stores ALL
bytes instantly. When the IRQ fires and calls $9D54, it reads ALL buffered bytes
in one tick — assembling complete packets, filling all 4 slots before the main
code gets a CPU cycle. The main code finds slots already processed/cleared, or
all slots full (triggering protocol reset). **Deadlock.**

## 6551 ACIA (SwiftLink)

### Register Layout
- **$DE00** = Data register (read=RX, write=TX). **Reading it is what clears RDRF.**
- **$DE01** = Status register (read-only). Reading it clears the IRQ bit (7) and
  releases the interrupt line, but does **not** clear RDRF.
- **$DE02** = Command register (read/write)
- **$DE03** = Control register (read/write)

### Key Status Bits ($DE01)
| Bit | Meaning |
|-----|---------|
| 3   | Receive Data Register Full (RDRF) |
| 4   | Transmit Data Register Empty (TDRE) |
| 5   | DCD — the client treats **set** as *no carrier* (`ACIA_REG_READ`) |
| 7   | IRQ occurred |

### Key Command Bits ($DE02)
| Bit | Meaning |
|-----|---------|
| 0   | DTR control (1=active) |
| 1   | RX IRQ disable (0=NMI enabled, 1=disabled) |
| 2-3 | TX IRQ control / RTS (`10` = RTS low, TX IRQ disabled) |

### VICE's SwiftLink Emulation

> **Corrected (#148, #149).** This section used to say VICE only checks the socket for
> new data when the CPU accesses $DE00-$DE03, so register reads "kept receive alive".
> VICE's source (`src/aciacore.c`) says otherwise, and has since at least 2020.

- **Receive is paced by a timer, not by register access.** `int_acia_rx` is an alarm
  that fires once per character time at the programmed rate, takes **at most one
  byte** from the socket, sets RDRF, raises the interrupt (if RX IRQs are enabled) and
  re-arms itself. This is the same whether VICE's ip232 protocol is on or off.
- **The rate depends on VICE's ACIA mode.** In **SwiftLink** mode VICE doubles the
  6551 rate table, as the real cartridge's 3.6864 MHz crystal does. The client's `$1F`
  (19200 in the table, `ACIA_INIT`) then runs at **38400**: 8N1 is 10 bits a byte, so
  ~3840 bytes/s — 256 cycles a byte on a PAL C64, **~64 per 60 Hz jiffy**. (Measured in
  a VICE session: ~60 per jiffy.) In VICE's **Normal** 6551 mode the same `$1F` is
  19200, ~32 per jiffy. The mode is VICE's `Acia1Mode` resource (`-acia1mode`), which
  **defaults to SwiftLink** (`src/c64/cart/c64acia1.c`); `vice_test.sh` does not set it.
- **A byte that arrives while RDRF is still set is discarded** (overrun) — the *new*
  byte is dropped and the old one kept, and the interrupt still fires. Only a read of
  $DE00 clears RDRF, so receive "stops" if nothing reads $DE00 — not because polling
  stops.

The NMI handler empties RDRF for every byte, so the ACIA itself does not overrun in
normal use. The limit is the **256-byte ring** behind it, which has no overflow check:
if the reader falls 256 bytes behind, the tail laps the head, the ring looks empty, and
256 bytes are lost at once.

**The X.25 path survives this** because the server sends one packet and waits for its
ACK before the next ([spec §2.9](spec/02-transport.md)), so the ring only ever has to
hold one packet. Count that in **wire** bytes, not payload: a C64 packet carries at most
100 payload bytes, and byte stuffing turns each `$01`–`$03` into two bytes, so the worst
case is about 210 bytes between the markers — still inside 256. Two caveats: the server
gives up waiting for an ACK after 5 seconds and sends the next packet anyway, so "one
packet at a time" holds only while the client ACKs promptly; and the server never sends an
ACK packet for the client's packets, so nothing paces the other direction at this layer.

**Code that reads the ring with no such flow control** — a raw line session such as
Partyline, whose server pushes lines as events occur ([spec §8.5](spec/08-subsystems.md))
— must drain ~64 bytes per jiffy for as long as the server keeps sending, or lose data.

## Working Implementation — Polling-Based ACIA Driver

> **Corrected (#149).** Until 1.6.0 this section described the driver as it was before
> May 2026: a ring buffer at $CE00, an NMI handler and a transmit routine that toggled
> $DE02 to "re-arm VICE's NMI edge detector", a fixed-delay transmit, and driver code
> "at $BE03+, behind the BASIC ROM". The $DE02 toggling was removed in `35b62fc`
> (C64 Ultimate bridge compatibility — *"NMI handler simplified: no IRQ toggling
> (prevents nested NMI)"*; *"TX routine polls TDRE before writing"*), and the ring and
> segment moved, but this document was not updated. Everything below is checked against
> `client/c64/src/compunet.s`.

### Design (Like CCGMS)

```
NMI fires → handler reads $DE01/$DE00 → byte stored in ring buffer (NMI_BUF, $C500)
Main code polls ring buffer → assembles X.25 packets → delivers payload bytes
```

No IRQ involvement in receive. No slot buffers. Direct buffer → packet → byte delivery.

### Where the driver lives

The driver is the `ACIA` segment, which `compunet.cfg` places directly after the ROM
code — inside the 8K ROM image at $8000-$9FFF (in the current build `ACIA_INIT` is at
$96D8). The terminal code is the separate `TERMINAL` segment at $A000. The ROM's
hardware entry points are trampolines into it: `MODEM_WAIT_READY` → `ACIA_WAIT_READY`,
`MODEM_REG_WRITE` → `ACIA_REG_WRITE`, `MODEM_REG_READ` → `ACIA_REG_READ`, and
`MODEM_REG_WRITE_WAIT` → `ACIA_SEND_PACKET`.

### NMI Handler (copied to $CF00)

`ACIA_INIT` copies `NMI_HANDLER` to $CF00, which the source calls "always-visible RAM",
and points the NMI vector there. It stays reachable whatever the banking: the handler
sets the banking it needs itself and restores it on exit.

```
    PHA
    TXA
    PHA
    LDA #$2F
    STA $00             ; force the DDR (stops $01 becoming read-only)
    LDA $01
    PHA                 ; save the caller's banking
    ORA #$06
    STA $01             ; make I/O and KERNAL visible
    LDA $DE01           ; status: acknowledges the interrupt
    AND #$08            ; RDRF?
    BEQ @not_acia       ; no byte — not ours, just return
    LDA $DE00           ; read the byte: clears RDRF
    LDX $029B           ; ring tail
    STA $C500,X         ; store
    INC $029B           ; advance tail (wraps at 256)
@not_acia:
    PLA
    STA $01             ; restore banking
    PLA
    TAX
    PLA
    RTI
```

The command register is **not** touched: there is no $DE02 toggle in the handler, or
anywhere else after `ACIA_INIT`.

### Ring Buffer
- **$C500-$C5FF** (`NMI_BUF`) — 256-byte ring buffer for received data
- **$029B** (`NMI_BUF_TAIL`) — tail pointer (NMI writes here)
- **$029C** (`NMI_BUF_HEAD`) — head pointer (main code reads from here)
- Buffer empty when head == tail. **No overflow check** — see above.

### ACIA_INIT

Called from `MODEM_CHECK` after the phone number has been entered and "DIALLING"
printed (not during phone-number input, which caused garbage on screen):

```
    LDA #$2F / STA $00  ; force DDR
    LDA #$37 / STA $01  ; I/O visible
    ; zero NMI_BUF_TAIL, NMI_BUF_HEAD and UPLOAD_POS
    ; copy NMI_HANDLER to $CF00
    ; save the old NMI vector ($0318/$0319) to $CFFC/$CFFD
    SEI
    ; point both $0318/$0319 and $FFFA/$FFFB at $CF00
    LDA #$1F            ; 19200 in the table (38400 on SwiftLink), 8N1
    STA $DE03           ; control register
    LDA #$09            ; DTR active, RTS low, TX IRQ off, RX NMI enabled
    STA $DE02           ; command register — the only write to it
    LDA $DE01           ; clear any pending interrupt
    CLI
```

`MODEM_CHECK` then waits for TDRE (the socket connected) before calling `ACIA_DIAL`;
VICE on Windows may not connect the socket immediately.

### ACIA_REG_WRITE (X=4 only — transmit)

Replaces the ROM's `MODEM_REG_WRITE`. Any X other than 4 is ignored (mode control has
no ACIA equivalent):
```
    STA $DE00           ; transmit byte
    ; delay loop (LDY #$FF / DEY / BNE), preserving A and Y
    RTS
```

**Critical**: Must preserve Y register — the dial loop uses Y as its counter.

### ACIA_REG_READ (status mapping)

Replaces the ROM's `MODEM_REG_READ`. Maps ACIA status to what the ROM's protocol engine
expects:

- **X=0** (status): $C0 if the ring has data (bits 7+6), $80 if it is empty (bit 7,
  TX ready). Bit 5 is never set — the ROM loops while bit 5 is set (original "modem
  busy" flag).
- **X=4** (read data): if RDRF is set, reads $DE00 directly; otherwise takes the next
  byte from the ring; otherwise returns $00. Non-blocking.
- **Any other X** (carrier/ring): reads DCD (status bit 5) — $40 (carrier present) if
  clear, $00 if set.

### ACIA_WAIT_READY

Replaces the ROM's `MODEM_WAIT_READY`, and is the transmit primitive every other
routine uses:
```
    PHA
@tx_wait:
    LDA $DE01
    AND #$10            ; TDRE — transmit data register empty?
    BEQ @tx_wait
    PLA
    STA $DE00
    RTS
```

**Never clear $DE02 bit 0 (DTR) or change bits 2-3 (RTS).** The client writes $DE02
exactly once, `$09`, in `ACIA_INIT`. The C64 Ultimate's bridge uses the RTS handshake,
and with tcpser a DTR drop hung up the call.

### ACIA_DIAL

Sends a Hayes dial command — the server, or the Ultimate's bridge, answers it:
```
    Send: "ATDT" + number + CR, in ASCII (not PETSCII)
          number = L9FF0 ($C1E0): length byte, then up to 24 characters;
          A-Z are sent as lower case, '-' becomes ',' (Hayes pause)
    Discard anything received during transmit (echo)
    Wait for: the first CR-terminated line (normally "CONNECT 1200")
    Returns: C=0 success, C=1 timeout
```

The number field holds the server address (e.g. `127.0.0.1:6400` or a host name). The
input filter at `L913B` was modified to accept letters, `.` and `:`.

### ACIA_PROTO_CONNECT

Polling-based handshake replacing the original IRQ-driven PROTO_CONNECT:
```
    1. Wait for the first handshake byte from the server (it sends 12 × $20),
       then drain the rest
    2. Send the CNET identification ($8051 = length, bytes from $8052)
    3. Display '*'-prefixed lines; wait for the line "*CON" + CR
    4. Set $8038 = $C0 (connected); return C=0 success, C=1 timeout
```

### ACIA_SEND_PACKET

Builds and sends a complete X.25 packet (payload length in $C14D, token in $8034,
payload at $C100):
```
    1. Send $01 (start marker)
    2. Send length byte = payload + 5 (with byte stuffing)
    3. Send token (from $8034)
    4. Send sequence number ($C20E)
    5. Send payload bytes (with byte stuffing)
    6. CRC-CCITT (poly $1021, init $0000) is updated over steps 2-5 as it goes
    7. Send CRC high/low (with byte stuffing)
    8. Send $02 (end marker)
    9. Advance $C20E, wrapping $5F → $20
```

It returns as soon as the end marker is sent: there is no post-transmit sequence.

### ACIA_UPLOAD_BYTE

Buffers upload bytes at `UPLOAD_BUF` ($C400) and sends them as a DAT (`$22`) packet
when 100 have accumulated, or at the last byte (C=1). Packets go back to back: nothing
waits for a transport ACK from the server, which does not send one (its "accept" after a
whole frame is a DAT).

### ACIA_FLOW_CONTROL

Receives a complete X.25 packet from the ring buffer:
```
    1. Force the DDR; re-point $FFFA/$FFFB at $CF00 (the ROM's directory buffer
       overwrites them)
    2. Poll for $01 (start marker), with a timeout
    3. Read and de-stuff bytes until $02 (end marker) into RECV_BUF ($C300)
    4. Extract token → $8034
    5. Discard a COM ($43) packet as an echo of our own transmission
    6. Zero-length payload = end of stream (EOS): return C=1
    7. Error tokens ($41/$42/$40): return C=1
    8. ACK a DAT ($22) packet (ACIA_SEND_ACK), return C=0
```

Its byte fetch takes from the ring first and falls back to reading $DE00 directly if the
ring is empty but RDRF is set.

### ACIA_SEND_ACK

Sends `$01 $06 $20 $20 <seq> <CRC hi> <CRC lo> $02`, echoing the sequence number of the
packet just received (RECV_BUF+2). See spec §2.9.

### ACIA_PROCESS_CMD

Delivers payload bytes one at a time:
```
    1. If the packet buffer has undelivered bytes: return the next one, C=0
    2. On the last byte of a packet, fetch the next packet (ACIA_FLOW_CONTROL)
       before returning it: C=0 if one came, C=1 at end of stream or timeout
    3. If the buffer is empty: fetch a packet (skipping COM echoes) and return its
       first byte; if none comes, return C=1 with a fake terminator — $2C (comma)
       on the first such call, $0D (CR) after — so the ROM's field-reading loops exit
```

**Critical**: Must never block indefinitely — every wait is bounded by
`ACIA_FLOW_CONTROL`'s timeout. The terminal code calls this in a loop and checks
carry; if it blocked forever, the C64 would hang.

## tcpser (legacy)

The client used to reach the server through tcpser: VICE's ip232 port → tcpser, which
answered the `ATDT` and connected onward. The server now answers `ATDT` itself (it
auto-detects a first byte of `A`), so VICE connects straight to port 6400 and tcpser is
not needed. The server still accepts a tcpser connection: if the first byte is not `A`,
or nothing arrives within 5 seconds, it proceeds directly to the X.25 handshake. The configuration that was used:

```
tcpser -v 25232 -p 6401 -s 1200 -l 7
```

- `-v 25232` — VICE ip232 port (SwiftLink connects here)
- `-p 6401` — tcpser listens for incoming TCP on this port. ⚠ The server's PETSCII
  terminal now uses 6401 too; on the same host, pick another port.
- `-s 1200` — simulated baud rate (affects timing only)
- `-l 7` — log level

tcpser connects to the Compunet server at the address dialled (e.g., 127.0.0.1:6400).

### tcpser Quirks
- **Echo**: tcpser echoes transmitted bytes back. The ROM sees its own login packet
  as a "received" packet; `ACIA_FLOW_CONTROL` discards COM ($43) packets for this reason.
- **Break delay**: tcpser has a break delay after CONNECT. Reduced to 50ms in our
  setup. The ROM sends $20 (space) not $0D (CR) to avoid triggering this delay.
- **DTR sensitivity**: If $DE02 bit 0 is cleared, tcpser interprets it as DTR drop
  and disconnects. Always keep bit 0 set.
- **Bit 7**: program uploads through VICE's ip232 and tcpser arrived with bit 7
  cleared; connecting VICE directly to the server fixed it
  ([UPLOAD-BIT7-INVESTIGATION.md](historical/UPLOAD-BIT7-INVESTIGATION.md)).

## Key Lessons Learned

1. **Read $DE00 for every byte.** If you intercept reads via a software handler
   without touching $DE00, RDRF stays set and VICE discards every later byte as
   an overrun. (This lesson used to blame VICE's socket polling; see
   *VICE's SwiftLink Emulation*.)

2. **Drain the ring at line rate when nothing paces the sender.** ~64 bytes per jiffy
   at 38400. The X.25 path is paced by ACKs; a raw session is not.

3. **Preserve Y** in TX routines. The ROM's dial loop uses Y as a counter.

4. **ACIA_INIT timing** matters. Must run AFTER phone input, BEFORE dial. Running
   it during phone input caused garbage on screen.

5. **Status bit 5 must be CLEAR**. The ROM's protocol engine loops while bit 5 is
   set (original "modem busy" flag). Return $80/$C0 for data available, never $A0/$E0.

6. **ACIA_PROCESS_CMD must not block indefinitely**. The terminal code expects a
   bounded return with C=1 if no data. Blocking causes hangs.

7. **The NMI handler runs from RAM at $CF00** and sets its own banking. The NMI
   vector is installed at both $0318/$0319 and $FFFA/$FFFB, and `ACIA_FLOW_CONTROL`
   re-installs $FFFA/$FFFB because the ROM's directory buffer overwrites it.

> **Retired lesson.** An earlier lesson 2 said *"NMI re-arm is essential after TX —
> VICE's edge detection can get stuck after writing to $DE00; the $DE02 toggle
> re-arms it."* The client has not done this since `35b62fc`, and works.
