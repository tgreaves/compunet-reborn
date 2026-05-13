# Compunet Modem vs 6551 ACIA — Hardware Layer

## Overview

The Compunet ROM was designed for a custom modem ("the brick") with a register-select
architecture accessed via $DE00/$DE01. We replace this with a 6551 ACIA (SwiftLink)
at $DE00-$DE03, connected to a TCP server via tcpser and VICE's ip232 emulation.

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
- **$DE00** = Data register (read=RX, write=TX)
- **$DE01** = Status register (read-only, cleared on read)
- **$DE02** = Command register (read/write)
- **$DE03** = Control register (read/write)

### Key Status Bits ($DE01)
| Bit | Meaning |
|-----|---------|
| 3   | Receive Data Register Full (RDRF) |
| 4   | Transmit Data Register Empty (TDRE) |
| 5   | DCD (carrier) |
| 7   | IRQ occurred |

### Key Command Bits ($DE02)
| Bit | Meaning |
|-----|---------|
| 0   | DTR control (1=active) |
| 1   | RX IRQ disable (0=NMI enabled, 1=disabled) |
| 2-3 | TX IRQ control |

### VICE's SwiftLink Emulation
VICE emulates the 6551 connected via ip232 (TCP socket to tcpser). Critical
behaviour: **VICE only checks the ip232 socket for new data when the emulated
CPU accesses ACIA registers ($DE00-$DE03)**. This means the NMI handler's reads
of $DE01/$DE00 are what keep the receive cycle alive.

## Working Implementation — Polling-Based ACIA Driver

### Design (Like CCGMS)

```
NMI fires → handler reads $DE01/$DE00 → byte stored in ring buffer ($CE00)
Main code polls ring buffer → assembles X.25 packets → delivers payload bytes
```

No IRQ involvement in receive. No slot buffers. Direct buffer → packet → byte delivery.

### NMI Handler (at $CF00, always-visible RAM)

The handler is copied to $CF00 at init time because the ACIA driver code lives
at $BE03+ which is behind the BASIC ROM when banked in.

```
    PHA
    TXA
    PHA
    LDA $DE01           ; read status (acknowledge NMI, triggers VICE socket poll)
    LDA $DE02
    ORA #$02            ; disable RX IRQ temporarily
    STA $DE02
    LDA $DE00           ; read received byte
    LDX $029B           ; ring buffer tail pointer
    STA $CE00,X         ; store byte
    INC $029B           ; advance tail (wraps at 256)
    LDA $DE02
    AND #$FD            ; re-enable RX IRQ (re-arms NMI edge)
    STA $DE02
    PLA
    TAX
    PLA
    RTI
```

The $DE02 toggle (disable then re-enable RX IRQ) is essential — it re-arms
VICE's NMI edge detector so the next byte triggers another NMI.

### Ring Buffer
- **$CE00-$CEFF** — 256-byte ring buffer for received data
- **$029B** — tail pointer (NMI writes here)
- **$029C** — head pointer (main code reads from here)
- Buffer empty when head == tail

### ACIA_INIT

Called just before dialling (NOT during phone number input — causes garbage):
```
    ; Reset ACIA
    STA $DE00           ; soft reset
    LDA #$1F            ; 19200 baud, 8N1, internal clock
    STA $DE03           ; control register
    LDA #$09            ; DTR active + RX NMI enabled
    STA $DE02           ; command register
    ; Install NMI handler at $CF00
    ; Copy handler bytes to $CF00
    ; Set NMI vector $0318/$0319 → $CF00
    ; Clear ring buffer pointers
    LDA #$00
    STA $029B
    STA $029C
```

### ACIA_REG_WRITE (X=4 only — transmit)

Replaces the ROM's `MODEM_REG_WRITE` at $94F0:
```
    STA $DE00           ; transmit byte
    ; TX delay (Y loop) — gives ACIA time, preserves Y
    PHA
    TYA
    PHA
    LDY #$40
@delay: DEY
    BNE @delay
    PLA
    TAY
    PLA
    RTS
```

**Critical**: Must preserve Y register — the dial loop uses Y as its counter.

### ACIA_REG_READ (status mapping)

Replaces the ROM's `MODEM_REG_READ` at $94FA. Maps ACIA status to what the
ROM's protocol engine expects:

- **X=0** (status register 0): Returns $80 if buffer has data (TX ready + data),
  $C0 if buffer has data (with bit 6), or $00 if empty. Bit 5 must be CLEAR —
  the ROM loops while bit 5 is set (original "modem busy" flag).
- **X=4** (read data): Polls ring buffer, returns next byte. Non-blocking.
- **X=8** (carrier/ring): Returns $40 (carrier present).

### ACIA_WAIT_READY

Replaces the ROM's `MODEM_WAIT_READY` at $94E4. Transmits with delay and
NMI re-arm:
```
    STA $DE00           ; transmit byte
    ; Delay
    PHA
    TYA
    PHA
    LDY #$40
@delay: DEY
    BNE @delay
    PLA
    TAY
    PLA
    ; Re-arm NMI
    LDA #$01
    STA $DE02           ; disable RX IRQ (keep DTR!)
    LDA #$09
    STA $DE02           ; re-enable RX IRQ
    RTS
```

**Must NOT write $00 to $DE02** — that clears DTR (bit 0), causing tcpser to
drop the TCP connection.

### ACIA_DIAL

Sends Hayes AT command through the ACIA to tcpser:
```
    Send: "ATDT" + phone_number_from_$9FF0 + CR
    Wait for: "CONNECT" response (character-by-character match)
    Timeout: ~10 seconds
    Returns: C=0 success, C=1 failure
```

The phone number at $9FF0 contains the server address (e.g., "127.0.0.1:6400").
Dots and colons are allowed in the input filter (patched at L913B).

### ACIA_PROTO_CONNECT

Polling-based handshake replacing the original IRQ-driven PROTO_CONNECT:
```
    1. Wait for 12 spaces ($20) from server (connection ready signal)
    2. Send CNET identification string (from $8052): "C CNET\r<address>\r..."
    3. Wait for "*CON\r" response
    4. Returns: C=0 success, C=1 timeout
```

### ACIA_SEND_PACKET

Builds and sends a complete X.25 packet:
```
    1. Send $01 (start marker)
    2. Send length byte (with byte stuffing)
    3. Send token ($43 = COM)
    4. Send sequence number
    5. Send payload bytes (with byte stuffing)
    6. Compute CRC-CCITT over all content
    7. Send CRC high/low (with byte stuffing)
    8. Send $02 (end marker)
```

### ACIA_FLOW_CONTROL

Receives a complete X.25 packet from the ring buffer:
```
    1. Poll buffer for $01 (start marker)
    2. Read and de-stuff bytes until $02 (end marker)
    3. Store complete packet in RECV_BUF ($C300)
    4. Extract token → $8034
    5. Check for error tokens ($41/$42/$40)
    6. Returns: C=0 success, C=1 error
```

### ACIA_PROCESS_CMD

Delivers payload bytes one at a time (non-blocking):
```
    1. If packet buffer has undelivered bytes: return next byte, C=0
    2. If buffer exhausted: poll for new packet
    3. If no data available: return C=1 immediately (non-blocking!)
```

**Critical**: Must be non-blocking. The terminal code calls this in a loop
and checks carry — if it blocks forever, the C64 hangs.

## tcpser Configuration

```
tcpser -v 25232 -p 6401 -s 1200 -l 7
```

- `-v 25232` — VICE ip232 port (SwiftLink connects here)
- `-p 6401` — tcpser listens for incoming TCP on this port
- `-s 1200` — simulated baud rate (affects timing only)
- `-l 7` — log level

tcpser connects to the Compunet server at the address dialled (e.g., 127.0.0.1:6400).

### tcpser Quirks
- **Echo**: tcpser echoes transmitted bytes back. The ROM sees its own login packet
  as a "received" packet. Harmless if sequence numbers are properly initialised.
- **Break delay**: tcpser has a break delay after CONNECT. Reduced to 50ms in our
  setup. The ROM sends $20 (space) not $0D (CR) to avoid triggering this delay.
- **DTR sensitivity**: If $DE02 bit 0 is cleared, tcpser interprets it as DTR drop
  and disconnects. Always keep bit 0 set.

## Key Lessons Learned

1. **VICE's socket polling** requires real ACIA register access. If you intercept
   reads via a software handler without touching $DE00-$DE03, VICE stops polling
   the ip232 socket and no more bytes arrive. The NMI handler's reads keep it alive.

2. **NMI re-arm** is essential after TX. VICE's edge detection can get stuck after
   writing to $DE00. The $DE02 toggle ($01 then $09) re-arms it.

3. **Preserve Y** in TX routines. The ROM's dial loop uses Y as a counter.

4. **ACIA_INIT timing** matters. Must run AFTER phone input, BEFORE dial. Running
   during MODEM_CHECK (before phone input) causes garbage on screen.

5. **Status bit 5 must be CLEAR**. The ROM's protocol engine loops while bit 5 is
   set (original "modem busy" flag). Return $80/$C0 for data available, never $A0/$E0.

6. **Non-blocking ACIA_PROCESS_CMD**. The terminal code expects immediate return
   with C=1 if no data. Blocking causes hangs.

7. **NMI handler must be in always-visible RAM** ($CF00). Code at $BE03+ is behind
   the BASIC ROM when banked in — NMI can't reach it.
