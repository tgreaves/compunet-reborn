# Compunet Communication Protocol - Reverse Engineered from ROM v1.22

## Overview

This document describes the communication protocol used by the Compunet Terminal
cartridge (v1.22, September 1984, Ariadne Software Ltd) as reverse-engineered
from the 8K ROM image and the official Compunet instruction manual.

The protocol is a modified X.25 packet protocol with error correction, operating
over a 1200/75 baud asymmetric modem connection (1200 baud receive, 75 baud
transmit - standard UK Viewdata/Prestel speeds).

Compunet (also known as CNet) was a UK-based interactive service running from
1984 to May 1993, operated by Compunet Teleservices Ltd, 7-11 Minerva Road,
London NW10 6HJ.

## Hardware Architecture

### Modem Hardware

The Compunet modem ("the brick") plugs into the C64's cartridge port and provides:

- **8K ROM** mapped at $8000-$9FFF (EXROM=0, GAME=1 mode)
- **Two I/O registers** in the IO1 space:
  - `$DE00` - Register Select (written to select which modem register to access)
  - `$DE01` - Data Register (read/write the selected modem register)

### Modem Register Map

The modem uses a register-select architecture. Write the register number to $DE00,
then read/write data via $DE01. The low-level access routines are:

- **$94F0 (MODEM_REG_WRITE)**: SEI, STX $DE00, STA $DE01, PLP, RTS
  - X = register number, A = data to write
- **$94FA (MODEM_REG_READ)**: SEI, STX $DE00, LDA $DE01, LDA $DE01, PLP, RTS
  - X = register number, returns A = data read (double-read for settling)
- **$94E4 (MODEM_WAIT_READY)**: Polls register 0 until bit 7 set, then writes to register 4

| Register | Direction | Purpose |
|----------|-----------|---------|
| 0        | Read      | Status register (bit 5 = carrier/DCD, bit 7 = TX ready) |
| 2        | Write     | Control/reset ($40 = reset) |
| 3        | Write     | Mode control ($20 = ?, $90 = ?, $D0 = enable RX after connect) |
| 4        | Write     | Transmit data byte |
| 6        | Write     | Configuration ($05 = set baud mode) |
| 8        | Read      | Receive status (bit 4 = ring/dial, bit 6 = data ready) |
| 10 ($0A) | Write     | Dial control (OR'd with $A0) |

### Register Access Pattern (from ROM at $94E4-$9506)

```
MODEM_WRITE:            ; X = register number, A = data value
    PHA                 ; Save data
    LDX #$00           ; Read status register 0
    JSR MODEM_READ
    TAX
    BPL MODEM_WRITE+3  ; Wait until bit 7 set (ready)
    PLA                 ; Restore data
    LDX #$04           ; Select register 4 (transmit)
    PHP
    SEI                 ; Disable interrupts during I/O
    STX $DE00           ; Select register
    STA $DE01           ; Write data
    PLP
    RTS

MODEM_READ:             ; X = register number, returns A = data
    PHP
    SEI
    STX $DE00           ; Select register
    LDA $DE01           ; Read data (first read may be stale)
    LDA $DE01           ; Second read gets valid data
    PLP
    RTS
```

Note: The double-read of $DE01 suggests the modem chip needs a settling time
after register selection, or uses a latch that updates on the first read.

## Connection Sequence

### 0. Pre-connection (BASIC level)

The user types `CONNECT` or `(shift) C` at the BASIC READY prompt. This triggers
the cartridge ROM's BASIC extension handler which parses the command and initiates
the connection sequence.

Alternatively, if the terminal software was previously saved with `CNSAVE`, the
user types `CNLOAD` to reload it from disk/tape, then `CONNECT` to reconnect
without needing the full 8K "linking" download.

### 1. Dial-up

The ROM contains the default phone number `322500/100` and network `ADP`
(the dial-up provider). The connection sequence:

1. Prompt "NUMBER?" — user enters the access point phone number
   - Supports "9---" prefix for PBX/internal exchange systems
2. Border colour changes to purple (indicates dialling)
3. Display "DIALLING"
4. Display "PLEASE WAIT"
5. Display "LINKING" (modem handshake in progress)
6. Check carrier detect (register 0, bit 5)
7. If no carrier: "DISCONNECTED - BAD LINE?" / "CONNECT AGAIN PLEASE"
8. If carrier detected: proceed to "CONNECTING..."

### 2. Modem Initialization

After carrier detect, the modem is configured:
- Write $40 to register 2 (reset/init)
- Write $05 to register 6 (set mode - likely 1200/75 baud Viewdata)
- Write $D0 to register 3 (enable receive, set protocol mode)

### 3. Login Sequence

Once connected, the terminal displays:

```
  COMPUNET SYSTEM LOGON.

  ENTER USER ID:
  [user input, max length from $C143]

  PASSWORD:
  [user input, masked]
```

Default credentials for new users: ID = `NEW-USER`, Password = `INTRO`
(provides limited access until personal ID issued, ~3 weeks).

The login credentials are sent to the server. On success, the system responds
with "Account User No. Job Max Exceeded" if full, otherwise proceeds.

### 4. Linking (Terminal Software Download)

After successful login, up to **8K of terminal software** is downloaded from
the Compunet server into the modem's RAM. This takes less than 90 seconds at
1200 baud. The "LINKING" message is displayed during this process.

This downloaded code provides the full terminal UI including:
- The duckshoot menu system
- The page editor
- Directory navigation
- File transfer capabilities

The downloaded software can be saved to disk/tape with `CNSAVE` and reloaded
with `CNLOAD` to avoid re-downloading on subsequent sessions. If the server
has updated the terminal software, linking will re-occur automatically.

### 5. Personal Information Screen

After linking, a personal information screen appears showing:
- Account status
- Mail indicator (red pillarbox if mail waiting)
- The Directory duckshoot menu

## Protocol Layer

### Command Tokens

The protocol uses single-byte command tokens (found at $9C0A, confirmed by
external disassembly):

| Token | Byte Value | Meaning | Direction |
|-------|-----------|---------|-----------|
| ACK   | $20       | Acknowledgement | Both |
| DIR   | $21       | Directory listing | Server -> Client |
| DAT   | $22       | Data transfer (frame content) | Server -> Client |
| OK    | $23       | Command successful | Server -> Client |
| ERR   | $24       | Error response | Server -> Client |
| FTL   | $25       | Fatal error | Server -> Client |
| COM   | $26       | Command | Client -> Server |

Note: These are NOT ASCII codes — they are single-byte protocol identifiers
in the range $20-$26. The string table at $9C0A ("ACKDIRDATOK ERRFTLCOM")
maps these to 3-character display names.

### Packet Structure

Based on the send/receive routines and workspace analysis:

#### RAM Workspace ($C100-$C1FF) - Terminal State

| Address | Purpose |
|---------|---------|
| $C140   | Address pair pointer #1 |
| $C141   | Address pair pointer #2 |
| $C143   | Input max length (X register for INPUT_LINE) |
| $C144   | Input max Y position |
| $C145   | Input mode flags (bit 6 = numeric only) |
| $C146   | Input terminator character |
| $C151   | Saved border colour |
| $C152   | Saved background colour |
| $C153   | Saved text colour |
| $C154   | Saved stack pointer |
| $C155   | Download flags (bit 7 = update self-mod pointer) |
| $C156   | File mode flag |
| $C157   | Character under cursor |
| $C158   | Colour under cursor |
| $C159   | Timeout counter low |
| $C15A   | Timeout counter high |
| $C15B   | Editor mode flags |
| $C15D   | Frame dirty flag |
| $C15E   | Print mode |
| $C15F   | Screen state |
| $C161   | Saved BASIC pointer low |
| $C162   | Saved BASIC pointer high |
| $C163   | Saved IRQ vector low |
| $C164   | Saved IRQ vector high |
| $C165   | Duckshoot item count |
| $C166+  | Duckshoot command offsets |
| $C175+  | Duckshoot command IDs |

#### RAM Workspace ($C200-$C2FF) - Protocol State

| Address | Purpose |
|---------|---------|
| $C200   | Connection state (0=disconnected) |
| $C201   | Protocol state |
| $C202   | Error flags |
| $C209   | Packet sequence number (heavily referenced - 16 times) |
| $C20A   | Retry counter |
| $C20B   | Packet type/command (11 references) |
| $C20C   | Packet length |
| $C20D   | Checksum accumulator |
| $C20E   | Timeout counter |
| $C20F   | Flow control state (7 references) |
| $C210   | Transmit window |
| $C211   | Receive window |
| $C212   | ACK counter (9 references) |
| $C213   | Connection flags ($FF = initialized) |
| $C214   | Transfer mode |
| $C21A   | Bytes received low |
| $C21B   | Bytes received high |
| $C21D   | Buffer pointer low (9 references) |
| $C21E   | Buffer pointer high (9 references) |
| $C228   | Packet buffer (18 references - likely start of data area) |
| $C22C   | Secondary buffer (21 references) |

#### Packet Format (Confirmed)

The wire format between $01 and $02 markers is:

```
[length] [token] [sequence] [payload...] [CRC_hi] [CRC_lo]
```

- **Length**: total byte count between markers (including itself, token, seq, payload, CRC)
- **Token**: command type ($20=ACK, $21=DIR, $22=DAT, $23=OK, $24=ERR, $25=FTL, $26=COM)
- **Sequence**: packet sequence number (range $20-$5F, wraps)
- **Payload**: variable length data (may be empty)
- **CRC**: CRC-CCITT over all bytes except CRC itself, init $00/$00

Example — ROM's login packet (32 bytes between markers):
```
$01  20 43 FF 5A 54 45 53 54 20 20 20 20 ... 83 89  $02
     │  │  │  └─ payload (Z command + user + pass + sysinfo)
     │  │  └──── sequence ($FF = first packet, uninitialised)
     │  └─────── token ($43 = COM)
     └────────── length ($20 = 32 bytes total)
```

Example — server's DAT packet (6 bytes between markers):
```
$01  06 22 20 00 C9 D9  $02
     │  │  │  │  └──── CRC ($C9/$D9)
     │  │  │  └─────── payload ($00 = one data byte)
     │  │  └────────── sequence ($20)
     │  └───────────── token ($22 = DAT)
     └──────────────── length ($06 = 6 bytes total)
```

### Flow Control

The protocol implements X.25-style windowed flow control:
- Transmit and receive windows ($C210, $C211)
- Sequence numbering ($C209) - window of 4 packets
- ACK tracking ($C212)
- Retry mechanism ($C20A)
- Sequence number range: $20-$5F (wraps at $60 back to $20)
- Window size: 4 packets (indexed 0-3)
- Packet buffers at $C228[0..3] (sequence numbers)
- Packet flags at $C22C[0..3] (bit 6 = awaiting ACK, bit 7 = retransmit)

### CRC/Checksum (at $9B10)

The protocol uses a 16-bit CRC for packet integrity:

```
CRC_UPDATE:             ; A = data byte to add to CRC
    PHA
    STA $C21F           ; temp
    TXA
    PHA
    LDX #$07            ; 8 bits
.loop:
    CLC
    ROL $C21F           ; shift data bit out
    ROL $C21E           ; shift into CRC low
    ROL $C21D           ; shift into CRC high
    BCC .no_xor
    LDA $C21D           ; XOR with polynomial
    EOR #$10            ; polynomial high byte
    STA $C21D
    LDA $C21E
    EOR #$21            ; polynomial low byte = $1021
    STA $C21E
.no_xor:
    DEX
    BPL .loop
    PLA
    TAX
    PLA
    RTS
```

This is a **CRC-CCITT** (polynomial $1021) calculation — standard MSB-first
CRC as used in X.25/HDLC protocols. This confirms the X.25 heritage.

**Important implementation note**: The ROM's bit-shift-chain implementation
(ROL temp → ROL CRC_lo → ROL CRC_hi) is equivalent to the standard algorithm:
```python
crc ^= (byte << 8)
for _ in range(8):
    if crc & 0x8000:
        crc = ((crc << 1) ^ 0x1021) & 0xFFFF
    else:
        crc = (crc << 1) & 0xFFFF
```

**CRC Init**: Both send and receive paths use init **$00/$00**:
- Send: `$C21D/$C21E` at $9ABC (despite the code loading $40/$E6 into these
  locations, the actual CRC over the full packet content uses effective init $00/$00
  when verified against known packets)
- Receive: `$C21A/$C21B` reset to $00/$00 at $9E41

**CRC Verification**: The receiver feeds ALL bytes between $01 and $02 (including
the CRC bytes) through the algorithm with init $00/$00. If the result is $00/$00,
the packet is valid (zero-residual property of CRC-CCITT).

### Packet Wire Format (Confirmed)

```
$01 [escaped content bytes] $02
```

The content between markers is byte-stuffed: any occurrence of $01, $02, or $03
in the raw content is escaped before transmission.

#### Byte Stuffing (from ROM at $9926)

The protocol reserves $01 (start), $02 (end), and $03 (escape prefix) as
framing bytes. Any data byte with value $01-$03 is escaped on the wire:

| Raw byte | Wire encoding | Description |
|----------|---------------|-------------|
| $00      | $00           | Sent as-is (special case) |
| $01      | $03 $21       | Escaped (start marker) |
| $02      | $03 $22       | Escaped (end marker) |
| $03      | $03 $23       | Escaped (escape prefix itself) |
| $04+     | as-is         | Sent directly |

The ROM's send routine at $9926:
```
    CMP #$00        ; is byte $00?
    BEQ send_raw    ; yes → send directly
    CMP #$04        ; is byte < $04?
    BCS send_raw    ; no (>= $04) → send directly
    ADC #$20        ; escape: add $20 to byte ($01→$21, $02→$22, $03→$23)
    PHA
    LDA #$03        ; send escape prefix first
    JSR MODEM_TX
    PLA             ; then send escaped byte
    JMP MODEM_TX
send_raw:
    JMP MODEM_TX    ; send byte directly
```

The receiver at $9D54 has corresponding de-escaping: when it sees $03, it reads
the next byte and subtracts $20 to recover the original value.

**Critical**: Byte stuffing applies to ALL bytes between $01 and $02, including
the length byte, token, sequence number, payload, AND CRC bytes. If a CRC byte
happens to be $01 or $02, it MUST be escaped or the receiver will interpret it
as a framing marker and truncate the packet.

**Note**: The length byte in the packet header counts the UNESCAPED content size
(before byte stuffing). The receiver counts unescaped bytes for the length check.

#### Raw Packet Content (before byte stuffing)

| Field | Size | Description |
|-------|------|-------------|
| length | 1 | Total UNESCAPED byte count between $01 and $02 (inclusive of itself) |
| token | 1 | Command token ($20-$26) |
| seq | 1 | Sequence number ($20-$5F range) |
| payload | N | Data bytes (0 or more) |
| CRC_hi | 1 | CRC-CCITT high byte |
| CRC_lo | 1 | CRC-CCITT low byte |

The length byte must equal the actual number of bytes stored between markers
(after de-escaping). The ROM's receive handler at $9DB3 validates:
`$C484[0]` == `$C212` (stored length must match byte count).
Mismatch → error code $8E displayed as "N" on the status bar's last column.

### Login Response and Linking Phase

After the user enters their credentials, the ROM:

1. Builds a 27-byte login packet in $C100:
   - `$C100[0]` = 'Z' ($5A) — login command
   - `$C100[1-8]` = User ID (space-padded to 8 chars)
   - `$C100[9-14]` = Password (space-padded to 6 chars)
   - `$C100[15+]` = System info (ROM version, BASIC pointers, CNLOAD flag)
2. Sets `$8034` = $43 (COM token)
3. Sends the packet via `$94C1` (MODEM_REG_WRITE_WAIT) — this calls
   PROTO_RECV_FRAME for each byte, simultaneously sending AND receiving
4. Calls `$96D2` (PROTO_FLOW_CONTROL at $9B3B) which:
   - Calls `$9A17` to process the next received packet from the buffer
   - Stores the received packet's **token** in `$8034`
   - Checks: if token is $41 ('A'), $42 ('B'), or $40 ('@') → error path (SEC)
   - Otherwise → success (CLC)

**Critical**: The server must NOT send an "ACK" packet. The server must respond
with a **DAT packet** (token $22). PROTO_FLOW_CONTROL sees token $22 in `$8034`,
which is not $41/$42/$40, so it returns CLC (success).

5. On CLC return, the ROM calls `$89D0` (FRAME_BUF_READ) — this reads the
   payload of the received DAT packet. The payload is discarded (it's a
   placeholder/header for the linking stream).
6. Falls directly into MODEM_INIT_DOWNLOAD ($8EEF)

### Data Transfer — MODEM_INIT_DOWNLOAD ($8EEF)

The MODEM_INIT_DOWNLOAD routine receives the terminal software ("linking"):

```
Byte stream received via $96CC (PROTO_PROCESS_CMD):
  Byte 1: discarded (header)
  Byte 2: discarded (header)
  Byte 3: return address low  → stored in $1F
  Byte 4: return address high → stored in $20
  [if carry set here → abort, skip linking]
  --- "LINKING" displayed on status bar ---
  Byte 5: destination address low  → stored in $1D
  Byte 6: destination address high → stored in $1E
  Byte 7: length low (discarded by read)
  Byte 8: length high (discarded by read)
  Byte 9+: payload data → stored at ($1D),Y, pointer incremented
  [loop until carry set = end of stream]
```

On completion:
1. If $C155 bit 7 set: stores end address in $8036/$8037
2. Executes `JMP ($001F)` — jumps to the return address from the stream

The return address points into the downloaded terminal code (e.g. $A005),
which initialises the full terminal UI (duckshoot menu, directory browser, etc.).

### Linking Stream Format (Server → Client)

The server sends the linking data as a continuous stream of bytes delivered
through X.25 DAT packets. Each call to `$96CC` (PROTO_PROCESS_CMD) returns
one byte from the stream. The protocol engine handles packet boundaries,
sequencing, and flow control transparently.

```
Linking stream layout:
  [0]    $00        ; header byte 1 (discarded)
  [1]    $00        ; header byte 2 (discarded)
  [2]    $05        ; return address low  (e.g. $A005)
  [3]    $A0        ; return address high
  [4]    $F0        ; destination address low  (e.g. $9FF0)
  [5]    $9F        ; destination address high
  [6]    len_lo     ; payload length low
  [7]    len_hi     ; payload length high
  [8+]   payload    ; terminal software binary (up to 8K)
```

The destination address ($9FF0) and return address ($A005) match the
load address and entry point of the terminal software (cnet.prg).

### How $96CC (PROTO_PROCESS_CMD) Delivers Bytes

Each call to `$96CC` = `JMP $996B` (PROTO_PROCESS_CMD):
1. Checks if a packet is ready in the 4-slot buffer ($C22C[X] bit 7 set)
2. If yes: extracts the next byte from the packet payload, returns it in A
3. If no: loops via `$9A17` waiting for a packet to arrive
4. Returns carry clear = byte valid, carry set = error/disconnect

The protocol engine's IRQ-driven receive (at $9C46/$9C8F/$9D54) runs in
the background, reading bytes from the modem, assembling them into packets,
and storing complete packets in the 4-slot buffer. PROTO_PROCESS_CMD
consumes bytes from these buffered packets one at a time.

### What the Server Must Send After Login

The complete server response to a successful login is:

1. **One DAT packet** with a minimal payload (even a single byte) — this is
   what PROTO_FLOW_CONTROL receives and checks the token of. The payload
   is read by FRAME_BUF_READ and discarded.

2. **Continuous DAT packets** containing the linking stream bytes — these are
   consumed one byte at a time by MODEM_INIT_DOWNLOAD via PROTO_PROCESS_CMD.

Both use the same X.25 DAT packet format:
```
$01 [seq] [token=$22] [payload...] [CRC_hi] [CRC_lo] $02
```

The ROM's protocol engine handles ACKing these packets back to the server
automatically (via the $9C8F/$9C98 IRQ handler path).

## User Interface

### The Duckshoot Menu

The "duckshoot" is a horizontally scrolling line of commands displayed across
the bottom of the screen. The user scrolls left/right with cursor keys until
the desired command is in the highlighted centre section, then presses RETURN.

Different contexts show different duckshoot commands:

#### Editor Duckshoot (from $83AA)

```
HELP  EDIT  LAST  NEXT  NEW  COPY  ERASE  GET  PUT  STORE  PRINT  FREE  DOS  RETURN
```

| Command | Function |
|---------|----------|
| COPY    | Makes a copy of the current page |
| DOS     | Access disk commands (if DOS loaded before login) |
| EDIT    | Enter edit mode on current page |
| ERASE   | Delete the current page |
| FREE    | Show remaining Editor space |
| GET     | Load Editor frames from disk/tape |
| HELP    | Display help frame |
| LAST    | Go to previous page in Editor |
| NEXT    | Go to next page in Editor |
| NEW     | Create a fresh blank page |
| PRINT   | Print current frame to printer |
| PUT     | Save current page to disk/tape |
| RETURN  | Return to Compunet (online) or BASIC (offline) |
| STORE   | Save entire Editor contents to disk/tape |

#### Directory Duckshoot (online)

```
DIR  EDITR  SAVE  LEAVE  BUY  SHOW  ACCNT  BACK  GOTO  HELP  LIFE  MAIL  PRINT  UCAT  UPLD  VOTE
```

| Command | Function |
|---------|----------|
| ACCNT   | Display account details |
| BACK    | Go to parent directory |
| BUY     | Download program or show chargeable text |
| DIR     | Enter sub-directory beneath highlighted entry |
| EDITR   | Access the Editor while online |
| GOTO    | Jump to a specific page number |
| HELP    | Display general help |
| LEAVE   | Disconnect from Compunet |
| LIFE    | Extend life of your uploaded content |
| MAIL    | Access Courier (electronic mail) |
| PRINT   | Print current directory listing |
| SAVE    | Save a downloaded program to disk/tape |
| SHOW    | Read text (T) frames |
| UCAT    | Catalogue of your uploaded frames |
| UPLD    | Upload text or software |
| VOTE    | Vote 1-9 on content quality |

#### Show Duckshoot (reading pages)

```
MORE  FINISH  ALL
```

#### Courier (Mail) Duckshoot

```
SEND  FINISH  NEXT  LAST  GET
```

### Directory Entry Types

Each directory entry has a letter suffix indicating its type:

| Suffix | Meaning |
|--------|---------|
| T      | Text pages (read with SHOW) |
| P      | Program (download with BUY) |
| PP     | Protected program (requires modem as dongle) |
| L      | Link to external system |
| S      | Sequential file (word processor format) |
| D      | Directory only (no content, use DIR) |
| +      | Has a sub-directory beneath it |

Numbers after the letter indicate size (K for programs, pages for text).

### The Editor

The Editor is a WYSIWYG page editor supporting full Commodore graphics and
colours. It can hold 10-15 pages simultaneously. Key features:

- Works both online and offline
- Pages viewed on Compunet are automatically stored in the Editor
- Supports the full C64 character set including graphics characters
- Pages are the fundamental content unit on Compunet

### Navigation

- **Page numbers**: Every entry has a unique page number for direct GOTO access
- **Tree structure**: Directories arranged hierarchically
- **Routing**: Shows current position in the Compunet structure
- **Highlighting**: Up/down cursor keys move a blue highlight bar

### Timeouts

- **Idle timeout**: 2 minutes without a command = disconnection
- **Editor timeout**: 10 minutes in the Editor online = disconnection

## Memory Map

### ROM Layout ($8000-$9FFF)

The ROM is a **bootstrap loader** — it provides just enough functionality to:
- Add BASIC commands (CONNECT, EDITOR, CNLOAD, CNSAVE, HELP)
- Control the modem hardware
- Dial and establish a connection
- Handle the login sequence
- Download the full terminal software ("linking")
- Provide basic Editor and file I/O for offline use

The full interactive terminal (duckshoot navigation, directory browsing, frame
rendering, Courier mail, etc.) lives in the **downloaded code** at $C800+.

| Range | Purpose |
|-------|---------|
| $8000-$8008 | Cartridge header (CBM80 signature, entry vectors) |
| $8009-$8031 | System parameters and configuration pointers |
| $8032-$806F | Modem config: phone number "322500/100", network "ADP", commands |
| $807A-$80BB | Version strings: "COMPUNET TERMINAL 1.22", "SEPTEMBER 1984 ARIADNE SOFTWARE LTD." |
| $80BC-$80FF | Padding (zeros) |
| $8100-$815F | Main jump table (32 entries x 3 bytes = JMP instructions) |
| $8160-$819F | COLD_START: hardware init, ROM-to-RAM copy, BASIC patching |
| $81A0-$81B6 | MAIN_INIT: print version, install command parser, enter BASIC |
| $81B7-$81BB | BASIC warm-start patch bytes (copied to $E000) |
| $81BC-$8268 | BASIC command parser (CONNECT/EDITOR/CNLOAD/CNSAVE/HELP/OFF) |
| $8249-$8268 | Command string table and dispatch address table |
| $8269-$8354 | Command dispatch: HELP, OFF, CNSAVE, CNLOAD handlers |
| $8355-$8445 | EDITOR: page editor entry and main loop |
| $8446-$85E3 | LAST/NEXT/NEW page navigation, GET/PUT file I/O |
| $85E4-$869D | SCREEN_DRAW: render frame to screen or printer |
| $869E-$89CF | COMMAND_INPUT: DOS commands, BASIC input handler |
| $89D0-$8AEA | Frame buffer read/write |
| $8AEB-$8CDD | Disk I/O and file management |
| $8CDE-$8EEE | MODEM_CHECK + dialling + phone number handling |
| $8EEF-$8F46 | MODEM_INIT_DOWNLOAD: receive up to 8K during "linking" |
| $8F47-$90B6 | MODEM_SEND_CMD: send command, handle disconnect states |
| $90B7-$9170 | Core I/O: PRINT_STRING, INPUT_LINE, SETUP_INPUT_PARAMS |
| $9171-$92CC | CNSAVE / FILE_DOWNLOAD |
| $92CD-$938A | CNLOAD / frame storage / disk error handling |
| $938B-$94C0 | WHITE_BAR, PROTOCOL_RESET, DUCKSHOOT |
| $94C1-$9516 | Modem hardware abstraction (MODEM_REG_WRITE/READ) |
| $9517-$96BF | Login screen layout and Editor help text (data) |
| $96C0-$96DA | Protocol dispatch jump table (9 entries) |
| $96DB-$9BFF | Protocol engine (X.25 packet handling, CRC, flow control) |
| $9C00-$9FFF | Protocol commands, connection logic, IRQ setup |

### RAM Usage

| Range | Purpose |
|-------|---------|
| $0801-$0816 | BASIC stub (SYS launcher for cnet.prg when loaded as BASIC program) |
| $9FF0-$BE02 | Downloaded terminal software (cnet.prg at runtime) |
| $C000-$C0FF | Terminal application workspace |
| $C100-$C1FF | Terminal state (cursor, screen mode, flags) |
| $C200-$C2FF | Protocol state (connection, packets, buffers) |
| $0302-$0303 | BASIC warm start vector (redirected to command parser) |

### Downloaded Terminal Software Layout ($9FF0-$BE02)

The terminal software (cnet.prg) runs at $9FF0+ with BASIC ROM banked out.
Key internal addresses:

| Address | Purpose |
|---------|---------|
| $A005   | Init: clear workspace, set pointers, call PROTOCOL_RESET |
| $A03B   | Main loop: set up duckshoot, dispatch commands |
| $A066   | DUCKSHOOT_HANDLER: display menu, get user selection |
| $A176   | Directory duckshoot command string data |
| $A21E   | Duckshoot configuration table |
| $A231   | Command dispatch routine |
| $A791   | Post-command handler |

## Second Jump Table ($96C0) - Protocol Functions

| Index | Address | Purpose |
|-------|---------|---------|
| 0 | $9B79 | Get Compunet connection (send space, wait for space back) |
| 1 | $9B8A | Initialize protocol state variables |
| 2 | $96DB | Initialize modem registers (reset + set baud) |
| 3 | $97AD | Handle disconnect / bad line |
| 4 | $996B | Handle disconnect / bad line (alternate) |
| 5 | $993A | Handle disconnect / bad line (alternate) |
| 6 | $9B3B | Protocol flow control / windowing |
| 7 | $9E69 | Connect to Compunet (carrier detect + handshake) |
| 8 | $C800 | RAM: Downloaded protocol extension |

### Protocol Byte Send/Receive

The protocol layer uses these routines to send structured data:

- **$991E**: Send $01 byte to modem (ACK/start of frame marker)
- **$9922**: Send $02 byte to modem (end of frame marker)
- **$9926**: Send arbitrary code byte to modem
- **$94E4**: Send byte with TX-ready wait (used for data payload)

### Connection Handshake ($9B79)

```
1. Set normal C64 IRQ vector (JSR $9C36)
2. Write $20 (space) to modem register 3
3. Poll modem register 0 until bit 5 clear (carrier established)
4. Initialize protocol state at $C20E, $C20F = $20
```

This "send space, wait for space" handshake confirms the connection is
bidirectional before proceeding with the login sequence.

### PROTO_CONNECT Session Establishment ($9E69)

After carrier detect, PROTO_CONNECT performs a full session establishment
with the server. This is a multi-phase exchange of raw bytes (NOT X.25
framed packets). The protocol engine's IRQ handler at $9FC8 receives
bytes and stores them at $C234+.

#### Phase 1: Initial Byte Exchange

The ROM installs an IRQ handler at $9FC8 (via vector $0314/$0315) that:
1. Reads modem register 0 — checks bit 6 for data available
2. If data available, reads register 4 (data byte)
3. Stores byte at $C234+counter, increments counter ($20 zero page)

A loop at $9ED6 waits until 10+ bytes are received (counter >= $0A).
The server must send at least 10 bytes to satisfy this.

#### Phase 2: Identification Exchange

After the 10-byte threshold, the ROM enters a send/receive loop at $9EE3:

**ROM sends** (from table at $8052, one byte per iteration with delay):
```
C CNET\r<phone_number>\r<network>\r<options>\r<command>\r
```

Example: `"C CNET\r322500/100\rADP\rNO\rRUN\r"`

Fields (CR-separated):
| Field | Example | Meaning |
|-------|---------|---------|
| Command + Network | `C CNET` | Connect to CNET network |
| Address | `322500/100` | Phone number / server address |
| Network | `ADP` | Network provider (PAD name) |
| Options | `NO` | No reverse charging / no special options |
| Action | `RUN` | Execute connection |

The length of this string is stored at $8051 (byte count from $8052).

**The ROM sends this identification string repeatedly** in a continuous loop,
wrapped in X.25 packet framing ($01 header $02), until it receives the `*CON`
connection signal from the server. On the original system, this was the client
repeatedly calling the mainframe through the X.25 PAD network — the server
(mainframe) would answer when ready by sending `*CON\r`.

If no `*CON` response is received within the timeout period, the ROM displays
"DISCONNECTED - BAD LINE?" and returns to BASIC. This indicates the mainframe
did not answer the call.

The server will see these identification packets arriving every few seconds
(the ROM's send loop includes a delay via $9FBC between iterations). The
server should respond with `*CON\r` as soon as it is ready to accept the
connection.

**Server must respond with:**
```
*CON\r
```

- `*CON\r` ($2A $43 $4F $4E $0D) — The connection confirmation signal

The `*` character ($2A) has special handling in the ROM:
1. Resets the input buffer index ($C201) to 0
2. Sets $C200 bit 7 (connection established flag)
3. Stores `*` at $0200[0]

Subsequent characters (`C`, `O`, `N`) are stored at $0200[1], [2], [3].
When CR ($0D) is received, the ROM compares $0200[0-3] with the expected
string at $804D (`*CON`). On match, PROTO_CONNECT returns with CLC (success).

#### Phase 3: Return

On successful match, PROTO_CONNECT:
1. Clears $C200 and $C201 (resets for next phase)
2. Returns CLC (carry clear = success)

The caller at $8E17 then proceeds to display the login screen.

#### Timing Requirements

- Server must send initial bytes AFTER tcpser's break delay expires (~1 second)
- Bytes must be sent individually (not as a burst) for tcpser compatibility
- The ROM sends its identification continuously until it receives `?*CON\r`
- Total handshake time: ~3-5 seconds typical

## Application-Layer Protocol

The terminal software (terminal_app) communicates with the server using a
simple command/response protocol layered on top of the X.25 transport.

### Packet Preparation

All commands go through the same preparation routine at $A784:
1. Store ASCII command letter at `$C100`
2. Store parameters at `$C101+`
3. Set Y = total packet length
4. Call `$A784` which stores 'C' ($43) at `$8034` (marks as COM packet type)
5. Call `$96D2` (PROTO_SEND_DATA) to transmit

### Client Command Codes

The client sends single ASCII letters as command identifiers:

| Code | ASCII | Duckshoot Cmd | Parameters | Description |
|------|-------|---------------|------------|-------------|
| $41  | 'A'   | ACCNT         | None (Y=1) | Request account information |
| $42  | 'B'   | BACK          | None (Y=1) | Go to parent directory |
| $43  | 'C'   | UCAT          | None (Y=1) | User catalogue listing |
| $44  | 'D'   | SHOW / MORE   | Entry index (Y=3 or Y=1) | Show frame or next page |
| $45  | 'E'   | EDITR         | None (Y=1) | Enter editor mode online |
| $49  | 'I'   | ID            | User ID string | Check user ID |
| $4D  | 'M'   | MAIL          | None (Y=1) | Access Courier mailbox |
| $50  | 'P'   | DIR / SHOW    | Page info (Y=3) | Show page (frame + directory data) |
| $55  | 'U'   | UPLD          | None (Y=1) | Start upload process |
| $56  | 'V'   | VOTE          | Vote value (Y=4) | Vote 1-9 on content |

**Important corrections** (verified against terminal disassembly at $A34E-$A358):
- $42 'B' = BACK (not BUY as previously documented)
- $43 'C' = UCAT/Catalogue (not BACK)
- $44 'D' is sent by SHOW (first frame, Y=3, params=entry index as 2 ASCII digits)
  and MORE (next frame, Y=1, no params). Server tracks frame-viewing state.
- $50 'P' is the page/directory request (sent by DIR duckshoot and on terminal entry)

### DIR/SHOW Response Format ('P' command)

The 'P' command is the primary page request. The server responds with a
multi-part structure delivered as a continuous byte stream via `$96CC`:

```
Part 1: Frame header (raw PETSCII, rendered to screen)
  [PETSCII bytes...] $00
  Stored at $D000, displayed via CHROUT.
  If first byte is $00, client uses built-in directory template ($BCE1).

Part 2: Routing text (2 CR-terminated lines, stored at $D300)
  [line1...] $0D [line2...] $0D
  First byte $00 = no routing text (skip to Part 3).
  Displayed at row 22 — shows current directory path.

Part 3: Field definitions (stored at $D580-$D5B0)
  Repeating: [field_id_byte] '=' [value...] $0D
  Terminated by $00.
  field_id low nibble (1-6) selects destination offset in $D5xx.

Part 4: Page content (stored at $D400, displayed at row 7)
  [content bytes...] $00
  First byte $00 = no page content.
  L_A427 reads this byte; if non-zero it stores until $00 terminator.

Part 5: Column headers (stored at $D500, 8 bytes per field)
  [field1] ',' [field2] ',' ... $0D $00
  Each field max 8 chars, space-padded to 8 by client.
  First byte $00 = no column headers (skip to Part 6).
  $C001 counts number of fields. F7/F8 cycles through them.
  The trailing $00 after the CR is a separator byte consumed by L_A448
  (value unused — required for stream alignment with Part 6).

Part 6: Directory entries (stored at $D600+, 94 bytes per slot)
  Repeating: [title (up to 30 chars)] ',' [col1 (8)] ',' [col2] ... $0D
  Title: 6 chars page number + up to 21 chars name/type = max 27 before comma.
  Client pads title to 30 chars with spaces.
  Column fields: up to 8 chars each, space-padded to 8 by client.
  Fields correspond to Part 5 headers (PRICE, LIFE, AUTHOR, VOTE).
  Stream ends when $96CC returns C=1 (last byte of final packet delivered).
  Entry count stored in $C009 → $C003 for rendering.
```

**Critical implementation notes:**

1. The client's Part 6 parser (L_A5F3) reads bytes until it finds a comma
   ($2C) for the title field. It does NOT check carry from `$96CC`. If the
   stream ends mid-entry, L_A5F3 loops forever storing $00 bytes. The stream
   MUST end cleanly after a complete entry's $0D terminator.

2. `ACIA_PROCESS_CMD` returns C=1 on the last byte of the packet payload,
   signalling end-of-stream. This propagates through L_A5F3's PHP/PLP chain
   to exit the entry loop at L_A4C2.

3. `ACIA_PROCESS_CMD` must preserve the caller's X register. The field parser
   at L_A616 uses X as an 8-byte width counter; if X is clobbered, entries
   overflow their 94-byte slot and corrupt subsequent buffer memory.

4. The server must NOT send unsolicited packets (e.g., login ACKs) that could
   be consumed as a command response. The client's L96D2 (ACIA_FLOW_CONTROL)
   picks up the next available packet regardless of type.

5. After Part 6 entries are consumed, `$C003` (entry count) is set from
   `$C009`. If Part 6 has no entries, `$C003` is never set and the rendering
   loop at L_A63E reads garbage from uninitialised RAM.

This design allows each directory to have custom graphics in the header area
while the navigable entry list below is rendered separately from structured data.

### Frame Display ('D' command) Response Format

The 'D' command response is raw frame data read by L89D0 (FRAME_BUF_READ):

```
Byte 0: Frame flags → $8035
  Bit 7: more pages follow (client shows MORE/FINISH duckshoot)
  Bit 7 clear: last page (client shows "press any key")

Byte 1: Border colour → $D020 (VIC uses low nibble)

Byte 2: Background colour → $D021 (VIC uses low nibble)
  Also drives PROTOCOL_STATE_INIT which sets duckshoot row contrast.

Bytes 3+: PETSCII content output via CHROUT
  $00 = end of frame
  $0D = carriage return
  $06 nn = repeat space (custom RLE: space repeated nn times)
  All other bytes output directly via KERNAL CHROUT
```

The client sends 'D' for both initial frame display (with 2-byte ASCII entry
index as params) and for advancing to the next page (no params, Y=1). The
server uses session state to distinguish the two cases.

### GOTO Command

GOTO sends the page number as ASCII digits:
```
$C100: command letter (from context)
$C103-$C107: page number (5 ASCII digits from input buffer at $0804)
Y = $08 (8 bytes total)
```

### VOTE Command

```
$C100: (command context)
$C103: vote value (ASCII digit '1'-'9')
Y = $04
```

### Server Response Handling

After sending a command, the client calls `$A4FE` (RECV_STATUS) which does:
```
JSR $96CC       ; RECV_BYTE - get first response byte
CMP #$00        ; zero = no more data
RTS             ; return with Z flag set if done
```

The server response byte at `$C019` determines the action:
- `$4C` ('L') = Linking required (re-download terminal software)
- `$41` ('A') = ACK / proceed with data transfer
- Other = directory/frame data follows

### Frame Data Reception

When receiving page content (SHOW, DIR responses), the client:
1. Calls `$96CC` (RECV_BYTE) in a loop
2. Each byte is passed to `$A595` (character output/store routine)
3. `$00` = end of data stream
4. `$0D` = newline (carriage return)
5. `$07` followed by 2 bytes = repeat character (RLE: char, count)
6. All other bytes = literal character data (PETSCII)

### Directory Paging

Directories with more than 12 entries are paginated using a `***MORE***` entry:

- Server sends max 12 entries per page
- If more entries exist, a `***MORE***` entry (type D+) is appended as the last item
- User highlights `***MORE***` and selects DIR to load the next page
- This matches the manual: "A dummy page; cannot be shown. Use DIR to access the directory beneath"
- BACK resets to the first page of the parent directory
- F7/F8 only toggles the extra column display (Price/Life/Author/Vote)

Directory entries are sent as structured data from the server, NOT as pre-formatted
PETSCII. The client parses, stores in RAM, and renders locally.

Server sends (after RESP_DIR byte):
```
<entry_count>                    ; 1 byte: number of entries
<directory_title><$0D>           ; routing text, CR-terminated
<entry1_fields><$0D>             ; entry 1, CR-terminated
<entry2_fields><$0D>             ; entry 2, CR-terminated
...
<$00>                            ; end of listing
```

Each entry has comma-separated ($2C) fields:
```
page_number,title,type_string,price,life,author,vote<$0D>
```

The client stores this in RAM at $D500+ (names, 8 bytes per entry) and
$D600+ (details, 94 bytes per entry), then renders it locally.

**Directory navigation (UP/DOWN) is entirely client-side** — no server
communication occurs. The highlight bar is moved by manipulating screen
memory (OR with $80 for reverse video, AND with $7F to remove).

Screen layout (from disassembly):
- Row 7, col 1: Directory title/routing (colour 6, blue)
- Row 8, col 31: Column header (PRICE/LIFE/AUTHOR/VOTE)
- Row 10+: Directory entries
- F7/F8 toggles which extra column is displayed (client-side re-render)

### BUY Sequence (confirmed from disassembly)

BUY shares the same code path as SHOW ($A9C5). The only difference is
the confirmation prompt for priced items.

1. Client checks PRICE field in directory buffer (L_AC46)
2. If price > 0: displays "BUY FOR [price] - SURE?" and waits for Y/N
3. If user confirms (or price = 0): sends 'D' ($44) with entry index
4. Server deducts credit (allows overdraft), marks page as purchased,
   and responds with frame data
5. Client renders the frame (same as SHOW)
6. No automatic directory reload — price remains cached until next 'P'

The client does NOT check credit locally. The server allows overdraft
(credit goes negative). ACCNT then shows "IN DEBIT" for negative balances.

### SHOW Sequence (confirmed from disassembly)

SHOW and BUY use the same entry point ($A9C5) and send the same 'D'
command. SHOW checks price first: if non-zero, displays "PLEASE USE BUY"
and returns without sending anything.

1. Client checks PRICE field (L_AC46): if non-zero → "PLEASE USE BUY", return
2. Sends 'D' ($44) with entry index as params (2 ASCII digits)
3. Server responds with frame data
4. Client renders frame via L89D0 (FRAME_BUF_READ)
5. `$00` marks end of frame
6. If $8035 bit 7 set: duckshoot shows MORE/ALL/FINISH options
7. MORE sends another 'D' (no params) to advance; server tracks frame index

### LIFE/EXTEND Sequence (confirmed from disassembly)

LIFE extends the expiry of content owned by the user. Uses command 'X' ($58).

1. Client checks type suffix at screen col 25: D/E/U → "CAN'T EXTEND", return
2. Prompts "EXTEND BY?" — user enters 1-4 digit number
3. Builds packet: 'X' ($58) + page number (2 ASCII digits) + extension (4 digits)
4. Sends 'X' command (Y=7 bytes) via L_A784
5. Receives response via L96D2: if error (SEC) → silent return
6. On success: prints "OK - GETTING NEW DIR", sends 'P' to reload directory

Server should validate that the requesting user is the page author before
allowing the extension.

### Upload Sequence

1. Client sends 'U' ($55) with Y=1
2. Prompts for: title, type (T/P), price, lifetime
3. Sends upload header via SEND_DATA
4. For text: sends frame data page by page
5. For programs: sends binary data from memory
6. Server acknowledges with response byte

### Connection State

- `$C000` bit 7: online flag (set = connected to Compunet)
- `$C016`: current command mode ('D'=directory, etc.)
- `$C019`: last server response code
- `$C021`: sub-command state
- `$8033`: current duckshoot command index
- `$8034`: protocol command type ('C' for COM)
- `$8035`: server status flags (bit 7 = more data)

### HELP Command (Client-Side)

HELP does NOT communicate with the server. It displays a pre-stored frame
from the terminal software RAM at $BB0C:

```
$A263: LDX #$0C / LDY #$BB    ; pointer to help frame at $BB0C
       JSR $8124              ; JT_FRAME_WRITE (display frame)
       JSR $8148              ; JT_PRESS_KEY (wait for keypress)
       JMP $A72D              ; return to main loop
```

The help frame uses cyan background ($F3) and contains instructions for
using the directory browser (cursor keys, F7/F8 column toggle, etc.).

### Frames

All content on Compunet is delivered as **frames** — self-contained pages that
can include C64 graphics, text, and colour information. Frames are the atomic
unit of content.

### Telesoftware (Program Downloads)

Programs are downloaded via the BUY command:
- Download speed: ~10 seconds per K at 1200 baud
- After download, user is prompted "SAVE FILENAME?"
- Programs can come in multiple chunks (BUY each in order)
- Protected programs (PP) require the modem as a dongle to run
- Each 1K of program = 4 blocks of disk space
- Failed saves can be retried with the SAVE directory command

### Courier (Electronic Mail)

- Mail indicator: red pillarbox on login screen, "MAIL" text on next directory
- Messages prepared in the Editor (online or offline)
- Can send to up to 5 recipients simultaneously
- Messages can be up to an Editor-full in length (~10-15 pages)
- Once read, mail exists only in the Editor (not retained on server)

### Uploading (The Jungle)

Users can upload their own content to designated "Jungle" areas:
- Text uploads: prepared in Editor, sent page by page
- Program uploads: SEND from memory or LOAD from disk then SEND
- Each upload has: title, type (T/P), price (optional), life (days)
- Life can be extended later with the LIFE command

### Pricing

- No connect charge 6pm-8am and all day weekends
- Content creators can set prices on their uploads
- BUY command handles both free and paid content

## Key Observations for Reimplementation

1. **Asymmetric speeds**: 1200 baud down, 75 baud up. The protocol is designed
   around this constraint - minimal client-to-server traffic.

2. **Two-stage architecture**: The ROM in the cartridge is just a bootstrap loader.
   The real terminal software (up to 8K) is downloaded from the server during
   "linking". This means the ROM handles: modem control, dialling, login, and
   the download protocol. Everything else (Editor, duckshoot, directory browsing)
   lives in the downloaded code at $C800+.

3. **CNSAVE/CNLOAD**: The downloaded terminal software can be cached locally,
   avoiding re-download. The server can force a re-link if the software is updated.

4. **X.25 heritage**: Sequence numbers, windowed flow control, CRC-CCITT, and
   ACK/NAK are all X.25 concepts adapted for the serial modem link.

5. **Simple command set**: Only 7 command tokens (ACK, DIR, DAT, OK, ERR, FTL, COM).
   The protocol is intentionally minimal.

6. **Frame-based content**: All content is delivered as "frames" - self-contained
   pages that can include graphics, text, and executable code.

7. **Dongle protection**: The modem's unique ID (stored in hardware) serves as
   copy protection for downloaded software marked as "PP" (protected program).

8. **The "duckshoot"**: A context-sensitive horizontal scrolling menu. Different
   command sets appear depending on whether you're in the Editor, a Directory,
   reading pages (SHOW), or in Courier.

9. **Tree-structured content**: Directories with page numbers, entry types, and
   sub-directories. GOTO provides random access by page number.

10. **User-generated content**: The "Jungle" areas allow users to upload their
    own text and programs, set prices, and manage content lifecycle.

11. **Timeout management**: 2-minute idle timeout and 10-minute editor timeout
    must be handled by any reimplementation (keep-alive or session management).

12. **External links**: The "L" entry type connects to external viewdata/teletype
    systems, converting the C64 into a standard terminal temporarily.

## Server-Side Protocol Requirements (for reimplementation)

Based on the client behaviour, a modern Compunet server must:

1. **Accept connections** and present the login prompt
2. **Authenticate** user ID and password
3. **Send terminal software** (the "linking" phase) — up to 8K binary payload
4. **Serve directory trees** with entries containing: title, type, size, price, vote, author
5. **Deliver frames** (pages) as DAT packets in response to SHOW/BUY commands
6. **Handle uploads** (UPLD) — receive frames and programs from clients
7. **Manage Courier** (mail) — store/forward messages between users
8. **Track sessions** — enforce timeouts, manage concurrent connections
9. **Version the terminal software** — force re-link when updated
10. **Implement flow control** — X.25 windowed ACK/NAK with CRC-CCITT verification

## Compunet Reborn — Implementation Notes

### Polling-Based Receive (Replaces IRQ-Driven Assembly)

The original ROM uses IRQ-driven packet assembly — a CIA timer fires at ~60Hz,
each tick reading one byte from the brick modem. This is incompatible with
ACIA/SwiftLink hardware (see MODEM.md for full explanation).

Our implementation replaces the protocol engine's receive path with polling:

- **$96CC** (PROTO_PROCESS_CMD) → `JMP ACIA_PROCESS_CMD`
  - Polls NMI ring buffer for complete X.25 packets
  - De-stuffs bytes, validates framing
  - Delivers payload bytes one at a time (non-blocking, C=1 if no data)

- **$96D2** (PROTO_FLOW_CONTROL) → `JMP ACIA_FLOW_CONTROL`
  - Waits for a complete packet
  - Stores token in $8034 for caller to check
  - Returns C=0 success, C=1 error

The X.25 wire protocol is unchanged — same framing ($01/$02), same byte stuffing,
same CRC-CCITT, same packet structure. Only the receive mechanism differs.

### Skipping the Linking Phase

In Compunet Reborn, the terminal code is embedded in the PRG file (loaded at
$A000-$BE02). The linking download is skipped:

- After login, the ROM jumps directly to $A005 (terminal entry point)
- The server sends an ACK for the login packet but does NOT send linking data
- MODEM_INIT_DOWNLOAD is bypassed entirely

The CNLOAD flag in the login packet's system info bytes ($C100[15+]) signals
to the server that linking should be skipped. The server checks bytes at
offset 15/16 — if both are $30 ('0'), skip=True.

### Server Handshake (TCP via tcpser)

The connection flow over TCP:

```
tcpser ←→ VICE SwiftLink (ip232 on port 25232)
tcpser ←→ Compunet Server (TCP on port 6400)
```

1. C64 sends `ATDT127.0.0.1:6400\r` via ACIA
2. tcpser opens TCP connection to 127.0.0.1:6400
3. tcpser sends `CONNECT 1200\r` back to C64
4. Server sends 12 spaces (handshake ready signal)
5. C64 sends CNET identification string
6. Server sends `*CON\r`
7. Login screen appears on C64
8. C64 sends login packet (X.25 framed)
9. Server sends ACK packet (X.25 framed)
10. C64 enters terminal code at $A005

### Multi-Packet Response Delivery

Responses larger than 100 bytes are split into multiple X.25 DAT packets:

- **MAX_PAYLOAD = 100 bytes** — keeps wire-encoded packets (after byte stuffing)
  within the 256-byte NMI ring buffer
- **250ms pre-response delay** — allows client to finish TX and re-arm NMI edge
  detection before first response byte arrives
- **50ms inter-packet delay** — prevents NMI buffer overflow between packets
- **End-of-stream (EOS) marker** — a zero-length DAT packet (just framing +
  header + CRC, no payload) sent after the final data packet

The client detects the EOS marker in `ACIA_FLOW_CONTROL`: when RECV_LEN=0
after receiving a valid DAT packet, it returns C=1 (end-of-stream) immediately
without waiting for a timeout.

The `@last_byte` code in `ACIA_PROCESS_CMD` calls `ACIA_FLOW_CONTROL` to
bridge between packets. On success (more data), it returns CLC so the caller
continues reading. On EOS or timeout, it returns SEC.

`ACIA_FLOW_CONTROL` timeout is set to ~2.7 seconds (CMP #$FF) as a safety net
for connection loss. Under normal operation the EOS marker provides immediate
stream termination without timeout delay.

### Post-TX NMI Re-arm

VICE's 6551 emulation can lose NMI edge detection during byte transmission.
`ACIA_SEND_PACKET` includes a post-TX sequence that:

1. Reads ACIA_STATUS and drains any stray byte from the RX register
2. Toggles ACIA_CMD to disable/re-enable RX IRQ (re-arms NMI edge)
3. Polls ACIA_STATUS 256 times (triggers VICE socket polling, ~1.3ms settle)

This ensures reliable NMI triggering for the first response byte after TX.

### Known Protocol Deviations

1. **CRC mismatch on login packet** — the ACIA_SEND_PACKET CRC calculation has
   a stack offset bug. Server logs a warning but accepts the packet anyway.
2. **TX sequence number** — sent as $7F instead of proper $20-$5F range. Server
   tolerates this and echoes it back in the ACK.
3. **No flow control ACKs from client** — the polling receive doesn't send ACKs
   back to the server. For single-packet exchanges (login → ACK) this is fine.
   Multi-packet transfers (linking, frame data) will need proper ACK generation.
4. **EOS marker packet** — a non-original protocol extension. The original system
   used windowed ACKs for flow control; the EOS marker replaces timeout-based
   stream termination for reliability over TCP/tcpser.
