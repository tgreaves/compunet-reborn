# Compunet Modem vs 6551 ACIA — Hardware Comparison

## Overview

The Compunet ROM was designed for a custom modem ("the brick") with a register-select
architecture accessed via $DE00/$DE01. We are replacing this with a 6551 ACIA
(SwiftLink) at $DE00-$DE03, connected to a TCP server via tcpser and VICE's ip232
emulation.

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

### Behaviour
- **Single-byte access**: only one byte at a time in the modem's data register
- **Polling-based**: the ROM polls register 0/8 to check for data, then reads register 4
- **No interrupts from modem**: the modem does NOT generate NMI/IRQ. All receive is polled.
- **Exclusive access**: whoever reads register 4 gets the byte. It's consumed. No buffering.
- **TX is blocking**: write to register 4, byte is sent. ROM waits for TX ready (bit 7) before next write.

### ROM's Receive Model
1. IRQ handler at $9C63 fires on CIA timer (~60Hz)
2. Calls $9D00 → $9D54 which polls register 0 (bit 6 = data available)
3. If data available: reads register 4, feeds byte into X.25 packet state machine
4. If no data: returns immediately
5. Complete packets stored in 4-slot buffer ($C22C[0-3])
6. Main code ($9A17) checks slots for complete packets

### Key Property
The modem holds exactly one byte until read. There is no race condition because
there's only one consumer. The IRQ-driven $9D54 is the sole reader during the
X.25 phase.

## 6551 ACIA (SwiftLink)

### Register Layout
- **$DE00** = Data register (read=RX, write=TX)
- **$DE01** = Status register (read-only, cleared on read)
- **$DE02** = Command register (read/write)
- **$DE03** = Control register (read/write)

### Key Status Bits ($DE01)
| Bit | Meaning |
|-----|---------|
| 0   | Parity error |
| 1   | Framing error |
| 2   | Overrun |
| 3   | **Receive Data Register Full (RDRF)** |
| 4   | Transmit Data Register Empty (TDRE) |
| 5   | DCD (carrier) |
| 6   | DSR |
| 7   | IRQ occurred |

### Key Command Bits ($DE02)
| Bit | Meaning |
|-----|---------|
| 0   | DTR control |
| 1   | **RX IRQ disable** (0=enabled, 1=disabled) |
| 2-3 | TX IRQ control |
| 4   | Echo mode |
| 5-7 | Parity |

### NMI-Driven Receive
The 6551 generates an NMI when a byte is received (if RX IRQ enabled in $DE02).
The NMI handler must:
1. Read $DE01 (acknowledges interrupt, clears IRQ flag)
2. Read $DE00 (gets the received byte, clears RDRF)
3. Store byte in a software ring buffer

### VICE's SwiftLink Emulation
VICE emulates the 6551 connected via ip232 (TCP socket to tcpser). Key behaviours:
- NMI is edge-triggered: fires once per received byte
- Reading $DE01 clears the IRQ flag
- Reading $DE00 clears RDRF and allows next NMI
- **VICE only checks the ip232 socket for new data when the emulated CPU accesses
  ACIA registers ($DE00-$DE03)**. This is the critical difference from real hardware.

## Our Current Patch Approach

### NMI Handler (at $CF00, installed from $80BC)
```
PHA / TXA / PHA
LDA $DE01           ; acknowledge interrupt
LDA $DE02
ORA #$02            ; disable RX IRQ
STA $DE02
LDA $DE00           ; read received byte
LDX $029B           ; tail pointer
STA $CE00,X         ; store in ring buffer
INC $029B           ; advance tail
LDA $DE02
AND #$FD            ; re-enable RX IRQ
STA $DE02
PLA / TAX / PLA / RTI
```

### Register Read Handler (at $8E00, jumped from $94FA)
Intercepts the ROM's register reads and returns data from the ring buffer:
- **X=0 (register 0)**: checks buffer pointers, returns $E0 (data) or $A0 (empty)
- **X=8 (register 8)**: same check, returns $40 or $00
- **X=4 (register 4)**: reads next byte from ring buffer, advances head pointer
- **Other X**: reads from ring buffer (non-blocking)

### TX Handler (at $94E4)
```
STA $DE00           ; write byte to ACIA TX
LDY #$FF            ; delay loop
DEY
BNE *-1
RTS
```

## The Problem

### Symptom
After the login packet is sent, the ACIA stops generating NMIs for received data.
The server sends DAT packets, tcpser forwards them to the ip232 socket, but VICE
never delivers them to the emulated ACIA.

### Root Cause (confirmed by debugging)
VICE's SwiftLink emulation only checks the ip232 TCP socket for incoming data when
the emulated CPU accesses the ACIA registers ($DE00-$DE03). Our register read
handler at $8E00 intercepts all calls to `$94FA` (the ROM's modem register read
routine) and returns data from a software ring buffer — **without ever touching
the real ACIA registers**. VICE therefore never polls the ip232 socket, and
incoming bytes pile up in the TCP buffer undelivered.

### Evidence
1. During PROTO_CONNECT: the $9FC8 IRQ handler reads register 0 and 4 via `$94FA`,
   which our handler intercepts. BUT the NMI handler at $CF00 reads `$DE01` and
   `$DE00` directly — these real ACIA accesses trigger VICE to poll the socket.
   As long as NMIs are firing, VICE keeps polling. This is a self-sustaining cycle.
2. After login send: the last NMI fires for the last byte received during
   PROTO_CONNECT. After that, no more NMIs fire. With no NMIs firing, nobody
   reads `$DE01`/`$DE00`. VICE stops polling the ip232 socket. New bytes from
   tcpser sit in the TCP buffer. No NMI fires. Deadlock.
3. The IRQ handler at $9C63 calls $9D54 which calls `$94FA` with X=0 — our
   handler returns buffer status WITHOUT reading `$DE01`. VICE is never poked.
4. Manual access to any ACIA register from the VICE monitor (`>de02 00` / `>de02 09`)
   triggers VICE to check the socket. Bytes arrive, NMI fires, cycle restarts.

### Why CCGMS Doesn't Have This Problem
CCGMS reads `$DE01` (the real ACIA status register) directly in its main polling
loop — constantly, on every iteration. Each read of `$DE01` triggers VICE to check
the ip232 socket for new data. If a byte has arrived, VICE sets bit 3 (RDRF) and
fires an NMI. The NMI handler reads `$DE01` and `$DE00`, which triggers another
socket check. The cycle is self-sustaining because CCGMS never stops accessing
the real ACIA registers.

In our case, the ROM's protocol engine polls via `$94FA` which our handler
intercepts. The real ACIA is never accessed during the X.25 phase. VICE's
emulation goes dormant.

### The Deadlock
```
VICE needs: CPU access to $DE00-$DE03 → triggers ip232 socket poll
NMI needs:  VICE to deliver a byte → fires NMI → handler reads $DE01/$DE00
Our code:   reads from software buffer via $94FA → never touches $DE00-$DE03
Result:     no ACIA access → no socket poll → no byte delivered → no NMI → no ACIA access
```

## Required Fix — ACIA NMI Re-arm After Login TX

### Corrected Understanding

The direct ACIA approach (no NMI, no buffer) does NOT work. VICE's SwiftLink
emulation delivers bytes exclusively via NMI — reading `$DE01` in a polling loop
does not trigger byte delivery. The NMI handler and ring buffer are required.

The NMI-based approach works correctly during PROTO_CONNECT (bytes arrive, NMIs
fire, handler stores them). After PROTO_CONNECT, the login TX writes (27 bytes
to `$DE00`) leave the ACIA's NMI edge detector in a stuck state. When the server
later sends DAT packets, VICE receives them on the ip232 socket but the ACIA
never fires an NMI to deliver them.

### Confirmed Fix

Writing `$00` then `$09` to `$DE02` from the VICE monitor immediately re-arms
the NMI mechanism. After this, bytes arrive and NMIs fire normally.

### Implementation

The 8-byte reset sequence must execute once, after the login TX completes:
```
LDA #$00
STA $DE02       ; reset ACIA command register
LDA #$09
STA $DE02       ; re-enable DTR + RX IRQ (re-arms NMI edge)
```

This must be placed between `$8EDE` (JSR $94C1 — login send) and `$8EE1`
(JSR $96D2 — PROTO_FLOW_CONTROL wait). Since there's no free space there,
a trampoline is needed.

### Trampoline Approach

Redirect `$8EDE` from `JSR $94C1` to `JSR <trampoline>` where the trampoline:
1. Calls `$94C1` (original login send)
2. Resets ACIA (`$00` → `$DE02`, `$09` → `$DE02`)
3. Returns (RTS)

Total trampoline size: 13 bytes (3 + 5 + 5 + 1... wait: `JSR $94C1` = 3,
`LDA #$00` = 2, `STA $DE02` = 3, `LDA #$09` = 2, `STA $DE02` = 3, `RTS` = 1
= 14 bytes).

### Available Space

The dial sequence at $8DA6 currently uses ~77 bytes with ~13 bytes of NOP padding
before the 90-byte limit. The trampoline can be placed in this padding area.
The dial sequence code only runs once (during connection), so the trampoline
at the end of it is safe to call later from $8EDE.
