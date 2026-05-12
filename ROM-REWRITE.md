# ROM Rewrite Plan — Compunet Reborn

## Rationale

The current approach patches the original 8K ROM binary in-place using Python.
This has become unmanageable:
- No free space for new code (every addition overwrites something)
- Branch offsets break when code moves
- No labels, no structure, no comments in the output
- Impossible to see the full picture or reason about interactions
- Each fix breaks something else

A clean rewrite from source gives us full control over the memory layout while
preserving the original Compunet UX and functionality.

## Design Principles

1. **Preserve all user-facing functionality** — the C64 user experience must be
   identical to the original: CONNECT, login screen, LINKING, duckshoot, etc.
2. **Replace only the hardware layer** — ACIA/SwiftLink instead of brick modem
3. **Replace the receive path** — direct buffer polling instead of IRQ-driven
   slot assembly (incompatible with ACIA, as documented in MODEM.md)
4. **Keep the X.25 wire protocol** — framing, CRC, byte stuffing, sequencing
5. **Keep the original ROM's application code** — editor, duckshoot setup,
   CNSAVE/CNLOAD, frame rendering, etc. (included as binary blobs)

## Architecture

### Memory Map ($8000-$9FFF, 8K cartridge ROM)

```
$8000-$8008  Cartridge header (CBM80 signature)
$8009-$8031  System parameters (phone number, network, flags)
$8032-$806F  Configuration data (CNET identification string, etc.)
$8070-$807F  Reserved
$807A-$80BB  Version string + startup messages
$80BC-$80FF  ACIA driver (NMI handler, init, helpers)
$8100-$815F  Jump table (32 entries, unchanged)
$8160-$819F  COLD_START (hardware init, BASIC patching)
$81A0-$81BB  MAIN_INIT (print version, install command parser)
$81BC-$8268  BASIC command parser (CONNECT/EDITOR/CNLOAD/CNSAVE/HELP)
$8269-$8354  Command dispatch (HELP, OFF, CNSAVE, CNLOAD handlers)
$8355-$86FF  Editor, page navigation, screen draw (original binary)
$8700-$8CFF  Disk I/O, frame buffer, command input (original binary)
$8D00-$8DFF  MODEM_CHECK + dial sequence (new: ACIA init + Hayes ATDT)
$8E00-$8EFF  Login screen + MODEM_INIT_DOWNLOAD (mostly original)
$8F00-$90FF  MODEM_SEND_CMD, I/O routines (original binary)
$9100-$92FF  CNSAVE, FILE_DOWNLOAD, CNLOAD (original binary)
$9300-$94BF  Protocol state, duckshoot (original binary)
$94C0-$9520  Hardware abstraction layer (NEW: ACIA read/write/status)
$9520-$96BF  Login screen data, editor help text (original data)
$96C0-$96DA  Protocol dispatch table (redirected to new receive engine)
$96DB-$9BFF  Protocol engine (SEND path preserved, RECEIVE path replaced)
$9C00-$9DFF  New receive engine (polling-based, replaces IRQ assembly)
$9E00-$9FFF  PROTO_CONNECT + IRQ handlers (adapted for ACIA)
```

### What's New (written from scratch)

| Component | Location | Size | Description |
|-----------|----------|------|-------------|
| ACIA Driver | $80BC | ~60 bytes | NMI handler, init, ring buffer management |
| Dial Sequence | $8D30 | ~90 bytes | Hayes ATDT, CONNECT response parsing |
| Hardware Layer | $94C0 | ~96 bytes | Register read/write abstraction for ACIA |
| Receive Engine | $9C00 | ~200 bytes | Polling-based packet receive, de-stuffing |
| PROTO_CONNECT adapt | $9E69 | ~100 bytes | Adapted for ACIA (direct buffer read) |

### What's Preserved (from original ROM binary)

| Component | Location | Description |
|-----------|----------|-------------|
| Jump table | $8100-$815F | All 32 entry points unchanged |
| Editor | $8355-$86FF | Full page editor |
| Disk I/O | $8700-$8CFF | Load/save, directory |
| Login screen | $8E38-$8EEE | User input, buffer build |
| MODEM_INIT_DOWNLOAD | $8EEF-$8F46 | Linking byte receive loop |
| MODEM_SEND_CMD | $8F47-$90B6 | Command dispatch, disconnect |
| I/O routines | $90B7-$9170 | PRINT_STRING, INPUT_LINE |
| CNSAVE/CNLOAD | $9171-$92CC | File operations |
| Protocol state | $938B-$94BF | WHITE_BAR, PROTOCOL_RESET |
| Protocol send | $96DB-$9BFF | Packet send, CRC, flow control |
| Status display | $9BA4-$9C09 | Status bar rendering |
| Data tables | $9C0A-$9C1F | Token name table |

### What's Replaced (rewritten for ACIA)

| Original | New | Reason |
|----------|-----|--------|
| Modem register read ($94E4-$9506) | ACIA read/write | Different hardware |
| IRQ packet assembly ($9C46-$9D53) | Polling receive engine | Incompatible with NMI buffer |
| $9D54-$9E68 (byte receive + assembly) | New receive engine | Direct buffer polling |
| PROTO_CONNECT ($9E69-$9FFF) | Adapted version | Uses ACIA instead of modem regs |

## New Receive Engine Design

The receive engine replaces the IRQ-driven packet assembly with direct polling,
matching how CCGMS handles bulk data transfer:

```
RECV_BYTE:
    ; Called from $96CC (PROTO_PROCESS_CMD replacement)
    ; Returns one payload byte in A, carry clear
    ; Or carry set on error/timeout

    ; If we have buffered payload bytes, deliver next one
    LDA recv_state
    BNE deliver_next

    ; Need a new packet — poll the NMI ring buffer
read_packet:
    JSR get_buffer_byte     ; get next byte from NMI buffer
    BCS read_packet         ; empty → keep polling
    CMP #$01                ; start marker?
    BNE read_packet         ; no → discard, keep looking

    ; Found $01 — read packet content until $02
    LDY #$00                ; packet buffer index
read_content:
    JSR get_buffer_byte
    BCS read_content        ; empty → keep polling
    CMP #$02                ; end marker?
    BEQ packet_complete
    CMP #$03                ; escape prefix?
    BNE store_byte
    JSR get_buffer_byte     ; get escaped byte
    BCS read_content
    SEC
    SBC #$20                ; de-stuff
store_byte:
    STA pkt_buffer,Y
    INY
    BNE read_content        ; (max 256 bytes)

packet_complete:
    ; pkt_buffer has: [length] [token] [seq] [payload...] [CRC_hi] [CRC_lo]
    ; Validate CRC (optional — server already computes correctly)
    ; Set up payload delivery
    STY pkt_total           ; total bytes received
    LDA pkt_buffer+1        ; token
    STA $8034               ; store for PROTO_FLOW_CONTROL
    LDA #3                  ; payload starts at offset 3
    STA recv_pos
    TYA
    SEC
    SBC #2                  ; subtract CRC bytes
    STA recv_end            ; payload ends here
    LDA #1
    STA recv_state          ; state = delivering

deliver_next:
    LDX recv_pos
    LDA pkt_buffer,X
    INX
    STX recv_pos
    CPX recv_end
    BNE :+
    LDA #0
    STA recv_state          ; done with this packet
:   CLC                     ; byte valid
    RTS

get_buffer_byte:
    ; Read one byte from NMI ring buffer at $CE00
    ; Returns: A = byte, C clear. Or C set if empty.
    LDA $029C               ; head
    CMP $029B               ; tail
    BEQ @empty
    TAX
    LDA $CE00,X
    INC $029C
    CLC
    RTS
@empty:
    SEC
    RTS
```

### RECV_FLOW (replacement for PROTO_FLOW_CONTROL):

```
RECV_FLOW:
    ; Wait for first packet, check token
    JSR RECV_BYTE           ; triggers packet read
    ; Token is now in $8034
    LDA $8034
    CMP #$41                ; error tokens
    BEQ @error
    CMP #$42
    BEQ @error
    CMP #$40
    BEQ @error
    CLC                     ; success
    RTS
@error:
    SEC
    RTS
```

## ACIA Driver Design

### NMI Handler (at $CF00, copied from ROM)

```
nmi_handler:
    PHA
    TXA
    PHA
    LDA $DE01               ; read status (acknowledge interrupt)
    AND #$08                ; RDRF set?
    BEQ @done               ; no data → exit
    LDA $DE00               ; read data byte
    LDX $029B               ; tail pointer
    STA $CE00,X             ; store in ring buffer
    INC $029B               ; advance tail
@done:
    PLA
    TAX
    PLA
    RTI
```

Key difference from current: checks RDRF (bit 3) before reading data.
This prevents reading garbage on spurious NMIs.

### TX with Conditional Re-arm

```
acia_tx:
    STA $DE00               ; transmit byte
    LDA rearm_flag          ; check if re-arm needed
    BEQ @done               ; no → return
    LDA #$09
    STA $DE02               ; re-arm NMI edge detection
@done:
    RTS
```

The `rearm_flag` is set after PROTO_CONNECT completes. During PROTO_CONNECT,
TX does not re-arm (prevents spurious NMI interference).

### ACIA Init

```
acia_init:
    LDA #$00
    STA $DE02               ; reset ACIA
    LDA #$1F
    STA $DE03               ; 19200 baud, 8N1
    LDA #$09
    STA $DE02               ; DTR + RX IRQ enabled
    ; Set NMI vector
    LDA #<nmi_handler
    STA $0318
    LDA #>nmi_handler
    STA $0319
    ; Clear buffer pointers
    LDA #$00
    STA $029B               ; tail = 0
    STA $029C               ; head = 0
    STA rearm_flag          ; re-arm disabled initially
    RTS
```

## Toolchain

### Assembler: ca65 (from cc65 suite)

- **Why**: Industry standard for C64 development, supports segments,
  macros, includes, and produces relocatable object files
- **Install**: `brew install cc65` (macOS) or from https://cc65.github.io/
- **Linker**: ld65 with a custom linker config for 8K cartridge

### Build Process

```
ca65 -t c64 compunet_reborn.s -o compunet_reborn.o
ld65 -C cartridge.cfg compunet_reborn.o -o compunet_reborn.bin
python3 make_crt.py compunet_reborn.bin compunet_reborn.crt
```

### Linker Config (cartridge.cfg)

```
MEMORY {
    CARTROM: start = $8000, size = $2000, type = ro, fill = yes, fillval = $FF;
}
SEGMENTS {
    HEADER:   load = CARTROM, type = ro, start = $8000;
    CONFIG:   load = CARTROM, type = ro;
    JUMPTBL:  load = CARTROM, type = ro, start = $8100;
    CODE:     load = CARTROM, type = ro;
    ORIGINAL: load = CARTROM, type = ro;
    DATA:     load = CARTROM, type = ro;
}
```

### Source File Structure

```
client/c64/src/
├── compunet_reborn.s      # Main file — includes everything
├── header.s               # Cartridge header ($8000-$8008)
├── config.s               # System parameters, CNET string
├── version.s              # Version string, startup messages
├── acia.s                 # ACIA driver (NMI handler, init, TX)
├── jumptable.s            # 32-entry jump table
├── coldstart.s            # COLD_START, MAIN_INIT, command parser
├── dial.s                 # Hayes ATDT dial sequence
├── login.s                # Login screen (mostly original binary)
├── recv_engine.s          # New polling-based receive engine
├── proto_connect.s        # PROTO_CONNECT adapted for ACIA
├── proto_send.s           # Protocol send path (original, with byte stuffing)
├── original_code.s        # .incbin blocks for preserved original code
├── cartridge.cfg          # Linker configuration
└── make_crt.py            # Convert raw binary to CRT format
```

### Original Code Inclusion

Large blocks of original ROM code that don't need modification are included
as binary blobs:

```asm
.segment "ORIGINAL"
; Editor, disk I/O, frame buffer — unchanged from original ROM
.incbin "original_editor.bin"      ; $8355-$86FF
.incbin "original_diskio.bin"      ; $8700-$8CFF
; ... etc
```

These are extracted from the original ROM image by a preparation script.

## Migration Strategy

1. **Extract original binary blocks** — split the original ROM into segments
   that don't need modification
2. **Write new components** — ACIA driver, dial, receive engine, PROTO_CONNECT
3. **Write adapter shims** — thin wrappers where new code interfaces with
   original code (e.g., the hardware abstraction at $94C0)
4. **Assemble and link** — produce the 8K binary
5. **Wrap as CRT** — add VICE cartridge header
6. **Test incrementally** — verify each phase (dial, connect, login, linking)

## What This Fixes

- **ACIA overrun** — receive engine polls at its own pace, no IRQ race
- **NMI re-arm** — conditional re-arm with proper flag, plenty of code space
- **Slot overflow** — no slots! Direct buffer → packet → payload delivery
- **Byte stuffing** — handled cleanly in the receive engine
- **Version string** — full "COMPUNET REBORN 1.00" with room to spare
- **Code maintainability** — labelled, commented, structured source

## Risks

- **Address sensitivity** — some original code uses absolute addresses.
  The jump table at $8100 and dispatch table at $96C0 must stay fixed.
  Other code may reference specific addresses that we need to preserve.
- **Zero page usage** — original code uses specific ZP locations ($19-$24).
  New code must avoid conflicts.
- **Workspace RAM** — $C100-$C2FF layout must be preserved (protocol state).
- **Downloaded code interface** — the terminal software at $9FF0+ calls back
  into the ROM via the jump table. Those entry points must not move.
