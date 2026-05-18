# ROM Rewrite — Compunet Reborn

## Rationale

The original approach patched the 8K ROM binary in-place using Python. This became
unmanageable — no free space, branch offsets breaking, no labels or structure.

The current approach generates full ca65 assembly source from the original ROM via
recursive-descent disassembly, then builds a single combined PRG containing ROM +
terminal + ACIA driver.

## Architecture — Single PRG File

Instead of an 8K cartridge ROM, we produce a single PRG file (~16KB) that loads
at $8000 and contains everything needed:

```
$8000-$9FFF  ROM code (8K) — BASIC commands, protocol engine, frame renderer
$A000-$BE02  Terminal code — duckshoot, directory navigation, frame display
$BE03+       ACIA driver — polling-based SwiftLink communication
```

### Boot Sequence
```
LOAD "COMPUNET",8,1
SYS 33184
```

- `LOAD "...",8,1` loads the PRG at its embedded address ($8000)
- `SYS 33184` ($81A0) enters MAIN_INIT

### Why Not a Cartridge?

A cartridge ROM is limited to exactly 8K ($8000-$9FFF). The terminal code and
ACIA driver don't fit. A PRG file has no size limit and loads everything in one
shot.

## Build System

### Toolchain
- **ca65** — assembler (from cc65 suite)
- **ld65** — linker (from cc65 suite)
- **gen_source.py** — recursive-descent disassembler for ROM binary
- **gen_terminal.py** — disassembler for terminal code (cnet.prg)

### Linker Configuration (compunet.cfg)

```
MEMORY {
    MAIN: start = $8000, size = $5000, type = rw, fill = yes, fillval = $00;
}

SEGMENTS {
    HEADER:   load = MAIN, type = ro, start = $8000;
    CODE:     load = MAIN, type = ro;
    TERMINAL: load = MAIN, type = ro, start = $A000;
    ACIA:     load = MAIN, type = ro, start = $C900;
}
```

- **HEADER** — cartridge signature at $8000 (CBM80 + vectors)
- **CODE** — ROM code ($8009-$9FFF)
- **TERMINAL** — terminal code, forced to $A000
- **ACIA** — ACIA driver, forced to $C900 (safe from terminal workspace clearing)

The memory area uses `fill = yes` to zero-fill gaps between segments. This
creates a ~20KB PRG (gap from $BE02 to $C900 is zeros). $9FF0-$9FFF is phone
number storage written at runtime.

### Build Command

```bash
cd client/c64/src
make
# Output: ../compunet-reborn.prg
```

The Makefile:
1. Assembles `compunet.s` → `build/compunet.o`
2. Links with `compunet.cfg` → `build/compunet.bin`
3. Prepends 2-byte load address ($00 $80) → `../compunet-reborn.prg`

## Source Generation

### gen_source.py — ROM Disassembler

Performs recursive-descent disassembly of the original 8K ROM binary:

1. **Entry point discovery** — starts from known entry points (reset vector,
   jump table entries, dispatch tables)
2. **Code tracing** — follows branches, JSR targets, JMP targets
3. **Data identification** — bytes not reached by code tracing are data
4. **Label generation** — every referenced address gets a label (L8000, L8123, etc.)
5. **Address table detection** — identifies lo/hi byte table pairs and generates
   `.lobyte(label)/.hibyte(label)` expressions

Output: `compunet_rom.s` — complete ca65 source that assembles to the exact
same bytes as the original ROM.

**Statistics**: ~6843 bytes identified as code (83% of ROM), remainder is data
(strings, tables, screen layouts).

### gen_terminal.py — Terminal Disassembler

Same approach for the terminal code (cnet.prg, loaded at $9FF0-$BE02):

1. Traces from known entry points ($A005, $A03B, etc.)
2. Generates `terminal.s` with full labels
3. Handles the jump table at $A000-$A004

### Address Relocation

When modem routines are shortened (replaced by JMP to ACIA code), subsequent
code shifts. ALL hardcoded address references must use labels:

- **RTS-trick dispatch tables** ($8269, $841D, $88BC) — use
  `.lobyte(label-1), .hibyte(label-1)` (RTS adds 1)
- **LDA #lo; STA; LDA #hi; STA patterns** — frame buffer callbacks at $C140/$C141
- **LDX #lo; LDY #hi patterns** — PRINT_STRING addresses, frame data pointers (41 instances)
- **LDA #lo; LDY #hi patterns** — IRQ handler addresses ($9C46, $9C5A, $9C63, $9FC8)

**Critical**: Must use `.lobyte()/.hibyte()` NOT `<`/`>` in `.byte` directives.
ca65's `<`/`>` operators don't handle relocatable expressions correctly in data
contexts.

## ROM Modifications

The combined source (`compunet.s`) contains the original ROM code with targeted
patches. Each patch replaces a small section of the original with a JMP or JSR
to the ACIA driver code.

### Hardware Layer Replacements

| Original Routine | Patch | Purpose |
|-----------------|-------|---------|
| MODEM_CHECK ($8CDE) | `JSR ACIA_INIT; JMP L8D52` | Skip brick modem detection |
| MODEM_WAIT_READY ($94E4) | `JMP ACIA_WAIT_READY` | TX with delay + NMI re-arm |
| MODEM_REG_WRITE ($94F0) | `JMP ACIA_REG_WRITE` | Transmit byte (X=4 only) |
| MODEM_REG_READ ($94FA) | `JMP ACIA_REG_READ` | Status/data from ring buffer |

### Protocol Engine Replacements

| Original Routine | Patch | Purpose |
|-----------------|-------|---------|
| $96CC (PROTO_PROCESS_CMD) | `JMP ACIA_PROCESS_CMD` | Deliver payload bytes |
| $96D2 (PROTO_FLOW_CONTROL) | `JMP ACIA_FLOW_CONTROL` | Receive complete packet |

### Connection Flow Patches

| Location | Patch | Purpose |
|----------|-------|---------|
| Dial sequence | `JSR ACIA_DIAL; BCS fail; JSR ACIA_PROTO_CONNECT` | Hayes dial + handshake |
| L8E1F (post-login) | Skip PROTO_FLOW_CONTROL, JMP L8EE8 | Can't use original receive |
| L8EE8 (post-login) | Skip L89D0, JMP $A005 | Skip linking, enter terminal |
| L9FA9 | Send $20 not $0D | Avoid tcpser break delay |
| L9FBC | RTS | Neutered delay (deadlocks with ACIA) |

### Input Filter Patch

| Location | Patch | Purpose |
|----------|-------|---------|
| L913B | Allow dots/colons in phone input | IP addresses (127.0.0.1:6400) |

## ACIA Driver Components

The ACIA driver lives in the ACIA segment ($BE03+) and provides:

| Routine | Purpose |
|---------|---------|
| ACIA_INIT | Reset ACIA, set 19200/8N1, install NMI handler at $CF00 |
| ACIA_REG_WRITE | Transmit byte with delay, preserve Y |
| ACIA_REG_READ | Map ring buffer status to modem register format |
| ACIA_WAIT_READY | TX + delay + NMI re-arm |
| ACIA_DIAL | Send ATDT + address, wait for CONNECT |
| ACIA_PROTO_CONNECT | Receive 12 spaces, send CNET ID, wait for *CON |
| ACIA_SEND_PACKET | Build and send complete X.25 packet with CRC |
| ACIA_FLOW_CONTROL | Receive complete X.25 packet, de-stuff, validate |
| ACIA_PROCESS_CMD | Deliver payload bytes one at a time (non-blocking) |

### NMI Handler (at $CF00)

Copied to always-visible RAM at init. Reads $DE01 (acknowledge) and $DE00 (data),
stores in ring buffer at $CE00. Toggles $DE02 to re-arm NMI edge detection.

Must be in RAM that's visible regardless of ROM banking ($CF00 is always accessible).

## Memory Map (Runtime)

```
$0000-$00FF  Zero page (shared with BASIC/Kernal)
$029B        Ring buffer tail pointer (NMI writes)
$029C        Ring buffer head pointer (main code reads)
$0801-$7FFF  BASIC RAM
$8000-$9FEF  ROM code (loaded from PRG)
$9FF0-$9FFF  Phone number storage (written at runtime)
$A000-$BE02  Terminal code (loaded from PRG)
$BE03-$BFFF  Unused (gap between terminal and ACIA)
$C000-$C0FF  Terminal workspace (zeroed by terminal init)
$C100-$C1FF  Terminal state (cursor, screen mode, flags)
$C200-$C2FF  Protocol state (connection, packets, buffers)
$C300-$C3FF  Receive packet buffer (RECV_BUF)
$C900-$CC6A  ACIA driver code (loaded from PRG at $C900)
$CE00-$CEFF  NMI ring buffer (256 bytes)
$CF00-$CF2F  NMI handler code (copied from ACIA driver at init)
$D000-$D0FF  Frame rendering buffer
$D300-$D5FF  Directory entry data (structured, for cursor navigation)
```

**Why ACIA is at $C900**: The terminal init at $A005 writes to $C000 (workspace).
If ACIA code were at $BE03+ it would extend past $BFFF into $C000+, and the
terminal init would overwrite it. Placing ACIA at $C900 keeps it safe. The gap
$BE03-$BFFF is filled with zeros in the PRG (adds ~2.5KB to file size).

### Protocol Dispatch Table (Must Stay at $96C0)

The terminal code contains hardcoded `JSR $96CC`, `JSR $96D2`, and `JSR $96C9`
in `.byte` data blocks that cannot use labels. The protocol dispatch table MUST
remain at its original address $96C0. If ROM modifications shift code, padding
is NOT used — instead, all decodable references use labels (L96CC, L96D2, L96C9)
which resolve correctly regardless of position. The remaining hardcoded references
in `.byte` data blocks are fixed by ensuring the dispatch table stays at $96C0
through careful code sizing.

## What's Preserved from Original

- All user-facing functionality (CONNECT, EDITOR, HELP, CNLOAD, CNSAVE)
- X.25 wire protocol (framing, CRC-CCITT, byte stuffing, sequencing)
- Login screen layout and input handling
- Terminal code (duckshoot, directory, frame display)
- Jump table at $8100 (32 entries, addresses relocated via labels)
- Protocol dispatch table at $96C0
- All RAM workspace layouts ($C100-$C2FF)

## What's Replaced

| Original | Replacement | Reason |
|----------|-------------|--------|
| Brick modem register access | ACIA register access | Different hardware |
| IRQ-driven packet assembly | Polling from ring buffer | ACIA/NMI incompatibility |
| Pulse dialling | Hayes AT commands via tcpser | Modern connectivity |
| PROTO_CONNECT (IRQ-based) | Polling handshake | No IRQ involvement |
| Linking download | Embedded terminal code | Already in PRG |

## Known Issues

1. **CRC mismatch** — ACIA_SEND_PACKET has a stack offset bug at `@update_crc`.
   Server accepts packets despite CRC errors (logs warning).
2. **TX sequence number** — $C20E not properly initialised, sends as $7F instead
   of $20-range. Server tolerates this.
3. **No welcome frame** — server needs to send initial frame after login for
   proper terminal initialisation.
5. **tcpser break delay** — reduced to 50ms, may need further tuning.

## Design Principles

1. **Preserve the original UX** — the C64 user sees the same screens, same flow
2. **Replace only the hardware layer** — ACIA instead of brick modem
3. **Do things the CCGMS way** — polling, not IRQ-driven receive
4. **Verify against the disassembly** — don't guess behaviour, check the code
5. **Keep the X.25 wire protocol** — server and client speak the same language
