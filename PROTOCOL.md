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

#### Packet Format (Inferred)

Based on the send routines at $9AE8-$9B00:

```
$01 (start marker)
  $C203[0] - header byte 0
  $C203[1] - header byte 1
  $C203[2] - header byte 2
  $C203[3] - header byte 3
  $C203[4] - header byte 4
  $C203[5] - header byte 5
$02 (end marker)
```

The 6-byte header at $C203-$C208 contains:
- Sequence number
- Command type (ACK=$20, DIR=$21, DAT=$22, OK=$23, ERR=$24, FTL=$25, COM=$26)
- Length/flags
- CRC bytes

Framing uses $01 as start-of-packet and $02 as end-of-packet markers,
with the 6-byte header sent between them. Data payloads follow for
DAT and COM packets.

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

This is a **CRC-CCITT** (polynomial $1021) calculation - the same CRC used in
X.25/HDLC protocols. This confirms the X.25 heritage of the protocol.

### Data Transfer (Frame Download)

The MODEM_INIT routine ($8EEF) handles bulk data reception:

1. Receive 3 header bytes (via SUB_96CC - protocol byte receive)
2. Store return address in $1F/$20
3. Display "LINKING" status
4. Receive destination address (2 bytes -> $1D/$1E)
5. Receive length (2 bytes, discarded)
6. Loop: receive bytes, store at ($1D),Y, increment pointer
7. On completion (carry set), check flags at $C155
8. If bit 7 set: update self-modifying pointer at $8036/$8037
9. Jump to return address stored in $1F/$20

This is the mechanism for downloading frames (pages) and also for
**software updates** - the ROM can receive code that overwrites parts
of RAM, including the area where the ROM copies itself.

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
| $C100-$C1FF | Terminal state (cursor, screen mode, flags) |
| $C200-$C2FF | Protocol state (connection, packets, buffers) |
| $0302-$0303 | BASIC warm start vector (redirected) |

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

## Content Model

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
