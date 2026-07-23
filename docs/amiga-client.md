# Amiga Compunet Client — Analysis

## Overview

An original **Amiga Compunet client suite** was recovered from a 1989 PD comms
compilation disk ("Comms Disc III", 17-Bit Software). The extracted files are
preserved in [client/amiga/vintage/](../client/amiga/vintage/); the source disk
image is [historical/Comms_Disc_III_1989_17-Bit_Software.adf](../historical/Comms_Disc_III_1989_17-Bit_Software.adf).

The significance for Compunet Reborn: this suite has the **same transport seam**
as the C64 ROM. The application-layer protocol (X.25 framing, CRC, sequencing) is
implemented inside the client, and everything below `cnet.device` is just "get
bytes to/from a serial link". That is the exact boundary Reborn replaces on the
C64 — which opens a path to a working Amiga Reborn client.

## The Suite

The disk (17-Bit Software disc #444) is a menu-driven compilation of **six
independent programs** (from its boot `menu`):

> F1 JrComm · F2 Access · **F3 Compunet** · F4 Newmasters Cruncher ·
> F5 PowerPacker 2.2 · F6 Supertex (Viewdata)

Only **F3 Compunet** is relevant here. Its own submenu (`cmenu`) offers: run
Compunet, read documents, Registration, Modems, About ARexx. The other five
programs (Access! terminal, JrComm, Supertex viewdata, the cruncher, PowerPacker)
and their support files are **not** part of the Compunet client and are not
retained in this repo.

The Compunet client components — identified both by name and by what the decrunched
`Compunet` executable actually references at runtime (`cnet.device`, `CnetEditor`,
`CnetTty`, `cnet-configuration`) — are:

| File | Size | State | Role |
|------|------|-------|------|
| `Compunet` | 34 KB | PowerPacker exe → **decrunched** | Main online client (*"Amiga Compunet Terminal x.xx"*) |
| `devs/cnet.device` | 14 KB | uncompressed | Transport driver — *"cnet device 2.1 (30 January 1989)"* |
| `CnetEditor` | 14 KB | PowerPacker exe → **decrunched** | Frame editor (*"Compunet - editor"*) |
| `CNETTTY` | 4.5 KB | cruncher #2 (not yet unpacked) | TTY / scroll viewer (*"CnetTty"*) |
| `CNet.info` | 1.8 KB | icon | Workbench icon for the Compunet program |
| `Registration` | 1 KB | PowerPacker data → **decrunched** | Registration / demo-login text |
| `Frames/test.frame` | 557 B | binary | Sample frame for the editor |
| `devs/cnet_modems/*` | — | text | Hayes modem init scripts |
| `cnet-configuration` | 54 B | binary | Saved config: phone `019975422` (dial string, `+0x00`), modem `linnet_1200`, user ID `NEW-USER` (`+0x2c`) |

`Converse` (a standalone ARexx utility), `serial.device` (the stock Amiga device
that `cnet.device` wraps), `Access!`/`access!me`, and `supertex`/`stex` are **not**
Compunet — the Compunet executable references none of them — and were removed after
initial extraction.

### Decrunching

The executables are Amiga HUNK binaries (`00 00 03 F3`). Two crunchers were used:

- **PowerPacker self-decrunching exe** (524-byte HUNK_CODE stub + one HUNK_DATA
  hunk holding the compressed original; efficiency table `[9,10,11,11]`). Used by
  `Compunet` and `CnetEditor` (and, on the disk, the unrelated `Access!`). Both
  Compunet files are fully unpacked. The PowerPacker *data* file (`PP20` magic)
  `Registration` decompresses with the same bitstream.
- **A second, non-PowerPacker cruncher** (620-byte stub, marker-bit LZ bitstream,
  `bsr.b $8 / jmp $0` trampoline header). Used by `CNETTTY` (and the unrelated
  `supertex`). Its length/pointer setup is derived from the AmigaDOS segment-loader
  BCPL pointers at runtime, so it needs 68k **emulation** of the stub rather than a
  static port. `CNETTTY` is not yet unpacked.

The decruncher lives at [client/amiga/vintage/tools/ppdecrunch.py](../client/amiga/vintage/tools/ppdecrunch.py);
decrunched outputs are in [client/amiga/vintage/decrunched/](../client/amiga/vintage/decrunched/).
The decrunched `Compunet` is a 36-hunk executable that references `cnet.device`,
`cnet-configuration`, "Goto Page", "File download", "Invalid link", "Invalid page
type", "User ID"/"Password", and the online/offline/logging-on/courier states —
i.e. the full client with the application-layer protocol logic, ready to
disassemble and compare against [docs/PROTOCOL.md](PROTOCOL.md).

`Registration` also yields useful operational detail verbatim: the demo login is
**ID `NEW-USER`, password `INTRO`** (hyphen required).

## Transport model — the key finding

`cnet.device` was disassembled (m68k). It is **not** a custom hardware driver.
It is a standard Amiga message-port device task that:

1. Opens the stock `serial.device` and `timer.device`.
2. Reads a modem script from `DEVS:cnet_modems`.
3. Sends the AT dial string (log string *"Modem command: "*) and waits for `CONNECT`.
4. Then **passes serial bytes straight through** between the client and the port.

Its exec usage (`OpenLibrary`, `AllocMem`/`FreeMem`, `WaitPort`/`GetMsg`/`ReplyMsg`,
`FindTask`, `Enqueue`) is the standard device-task skeleton — an IORequest server
wrapping `serial.device`. No framing, CRC, or protocol state machine is present in
the device.

### Consequence

Because `cnet.device` is a passthrough, the **X.25 framing / CRC / sequencing must
live inside the `Compunet` client binary** — precisely mirroring the C64, where the
ROM protocol engine (`$96C0-$9BFF`) does framing and only the hardware layer
(`$94E4/$94F0/$94FA`) is swappable. See [docs/PROTOCOL.md](PROTOCOL.md) and
[docs/MODEM.md](MODEM.md).

> **Correction (later finding — see
> [re/protocol-analysis.md](../client/amiga/vintage/tools/re/protocol-analysis.md)):**
> `cnet.device` is **not** a pure passthrough. It contains the canonical CRC-CCITT
> table (poly `0x1021`) at file offset `0x333c`, byte-identical to the server/C64
> CRC. So the framing/CRC is (at least partly) **in the device**, not the client.
> The initial disassembly saw the serial-wrapper skeleton but missed the framing
> layer. The transport-swap seam for Reborn is therefore likely **at the
> `cnet.device` level** (a drop-in TCP device that does the same framing), which
> keeps the `Compunet` client unmodified. The client-side `serial_read`/`serial_write`
> routines pass a token (`0x22`=DAT, `0x43`=COM, matching PROTOCOL.md) + data buffer
> to the device.

The abstraction boundary is clean and named: the client does
`OpenDevice("cnet.device")`, and everything below is bytes over a serial link. That
is the same seam Reborn already exploits on the C64 (SwiftLink/ACIA ↔ tcpser ↔ TCP).

## Modem scripts confirm genuine Compunet

The `cnet_modems` scripts use the format `detect,speed:rx:tx:AT-init`. The Compunet
`linnet_1200` script:

```
75,1200:1200:Z,X1,S2=3,S12=20,S57=0,S50=2,S51=5,S10=14
1200,1200:1200:Z,X1,S2=3,S12=20,S57=0,S50=2,S51=4,S10=14
```

The `75,1200` line is the **1275 split-baud** mode (75 baud up / 1200 baud down)
that was Compunet's signature line rate — the same asymmetric link the C64
"brick" modem used. A dedicated `dumb_1275` driver is also present. The saved
`cnet-configuration` selects `linnet_1200` with the 9-digit dial number `019975422`
(`+0x00`) and the `NEW-USER` demo account as the user ID (`+0x2c`), matching the
Compunet login model.

## Feasibility — paths to an Amiga Reborn client

Reborn's premise (per project rules) is "preserve the app-layer protocol, swap only
the transport — TCP instead of the phone line." The Amiga suite has the same seam,
so two paths exist:

1. **Reuse the original `Compunet` binary unchanged**, providing it a transport to the
   Reborn server (e.g. a drop-in replacement `cnet.device` that speaks TCP). Lowest
   effort if the app-layer protocol matches [docs/PROTOCOL.md](PROTOCOL.md).

2. **Reimplement** the Amiga client, using a disassembly of `Compunet` as reference.
   The binary is now decrunched, so this is unblocked. *(This is the chosen path —
   see below.)*

### Transport decision — native TCP/IP via bsdsocket.library

**We are NOT using serial→TCP redirection** (no tcpser / virtual-modem / WiFi-modem
bridge under the emulator). Instead the reconstructed client will get **native TCP/IP
through `bsdsocket.library`** (AmiTCP / Roadshow / Miami) as a proper transport, added
at a later stage. This mirrors the C64 SwiftLink↔TCP seam without a modem-emulation
kludge, and matches "swap only the transport" cleanly.

The transport seam in the reconstruction is `open_transport` (`connect.c`),
`serial_read`/`serial_write` (`transport.c`), and the dial/handshake (`modem.c`). The
bsdsocket transport replaces `OpenDevice("cnet.device")` with
`OpenLibrary("bsdsocket.library")` + `connect()`, and **drops** the modem dial and
carrier polling (a socket has no dial). The `C CNET` identification is **kept** (the
server needs it to recognise the client), and everything above the seam (frame parser,
command dispatch) is unchanged.

> **Correction (2026-07-21):** an earlier version of this note said the swap was just
> "`recv`/`send` for the serial IO". **That is wrong.** The X.25 framing/CRC lives in
> `cnet.device`, not the client, so raw `recv`/`send` would put *unframed* bytes on the
> wire and the server (which speaks X.25-over-TCP) would reject them. The TCP transport
> must **reproduce the framing** `cnet.device` did — matching `server/x25_protocol.py`.
> The full verified design is in
> [client/amiga/src/TCP-TRANSPORT.md](../client/amiga/src/TCP-TRANSPORT.md).

**Progress (2026-07-21):** the transport foundation `client/amiga/src/net.c` (bsdsocket
lifecycle, raw I/O, `net_avail`/FIONREAD polling, and the full X.25 frame TX/RX + CRC +
byte-stuffing + ACK) is built and compiles. **TCP/IP connectivity is proven end to
end**: the `nettest` tool (`client/amiga/src/nettest.c`, staged into the emulation
`hdd/`) connects to the live Reborn server over the internet, and the server receives
and parses the Amiga `C CNET` identification — then rejects it on the version check
(field[1] has no `{hash}/100`), the **live confirmation** that the server needs an
Amiga-detection branch before the hash gate. The remaining work is the read/ack demux
(`serial_io_c`/`serial_read` return semantics) — either reverse `cnet.device`'s receive
engine, or restructure the client's read path to the server's DAT-frame model. See
[client/amiga/emulation/RUNNING.md](../client/amiga/emulation/RUNNING.md) (Stage 0 = the
connectivity test) and TCP-TRANSPORT.md.

**Note (SO_RCVTIMEO):** the tested Amiga TCP stack does not honour `SO_RCVTIMEO`, so the
transport polls `net_avail` (FIONREAD) for readiness rather than relying on recv
timeouts — matching the original client's `modem_read_status` polling.

## Chosen approach — understand fully, reconstruct in C

Mirroring how the C64 client was fully disassembled and rebuilt, the decision is to
**understand the whole client and reconstruct it as recompilable C**, then make the
Reborn changes in that source. Progress so far:

### Reverse-engineering recon (Ghidra)

The decrunched `Compunet` was pre-relocated into a flat image and analysed in Ghidra
(see [client/amiga/vintage/tools/re/](../client/amiga/vintage/tools/re/)):

- **Language: SAS/Lattice C** — ~34 object modules, a4 small-data model, a5 stack
  frames, fully stripped (no symbols/debug).
- **Decompilation is clean** — 222 functions, **0 decompile failures, 0 unrecovered
  control flow**. The one gap is unnamed OS calls (`(**(code**)(libbase+LVO))()`),
  fixable by applying Amiga LVO names.
- **Program mapped** — startup, config load/save, connection setup (device open /
  "Modem error" / "Can't open cnet.device"), the real `cnet.device` open helper
  (`0x1192b6`), connection-state display, file download, login validation
  ("No Such User"), editor/TTY launch, Goto Page. Full map in the `re/` README.

### Round-trip proof

Before committing to a full reconstruction, the decompile → reconstruct → recompile
loop was proven with the **vbcc** m68k-amigaos toolchain: a real client function was
reconstructed as C and recompiled to **functionally-identical** m68k code (same
struct offsets, constants, and control flow; only register-allocation/codegen
differences). See [roundtrip-proof.md](../client/amiga/vintage/tools/re/roundtrip-proof.md)
and [toolchain.md](../client/amiga/vintage/tools/re/toolchain.md).

A C reconstruction will **not** be byte-identical to the SAS/C original (different
compiler), so fidelity is verified per-function by comparing generated code /
behaviour, not by a binary diff. Because only the linked binary survives (no original
`.o` files), the reconstruction is necessarily whole-program.

## Goals for Reborn Amiga support

The end goal is a working **Amiga Compunet Reborn client**: the original 1989 client,
reconstructed as readable C, with the phone-line transport replaced by TCP/IP.
TCP/IP stacks exist on the Amiga (AmiTCP/Roadshow/bsdsocket.library), so pointing the
client at the Reborn server over TCP is a valid strategy — the direct analogue of the
C64 client's SwiftLink/ACIA ↔ TCP seam.

Three focus areas drive the current work:

1. **Readability first — make the C understandable.** Before any reconstruction or
   transport work, the decompiled `recon.c` must read like real source: named OS
   calls, sensible function names, and typed structures. Understanding the client
   completely is the prerequisite for changing it safely.
2. **Transport swap — modem → TCP/IP.** The modem/`cnet.device` calls will be
   replaced with TCP/IP so the Amiga client talks to the Reborn server. Identifying
   every point where the client touches the transport (device open, IO send/receive,
   dial/connect, carrier/hangup) is essential groundwork.
3. **PETSCII handling — ANSWERED: the Amiga DOES use PETSCII (converts it in the
   renderer).** The frame renderer (`FUN_001054f8`) switches on `byte >> 5` and applies
   the canonical **PETSCII → C64 screen-code conversion** (verified to match for
   0x20-0xBF), with PETSCII control codes (colours, cursor, RVS, charset) dispatched
   through two jump tables (0x00-0x1F, 0x80-0x9F). Frames use the same RLE compression
   (`0x06`=repeat space, `0x07`=repeat char) as the C64/server SEQ frames.
   **Implication (good news):** Reborn's existing PETSCII frame content should render
   on the Amiga with **no separate frame format** — pending confirmation of the
   0x80-0x9F control table and colour-palette mapping. (An earlier interim note wrongly
   concluded a non-PETSCII "ESC-code" format; corrected after disassembling the
   renderer.) See
   [re/petscii-frame-format.md](../client/amiga/vintage/tools/re/petscii-frame-format.md).

   *(original question, for reference)* does the `Compunet`
   client translate PETSCII ↔ its own display charset (a lookup table or conversion
   routine), render a custom C64-style font, or handle frames some other way? This
   directly affects how Reborn frames (authored as PETSCII) will render on the Amiga.
   Needs investigation in the decompiled display/frame-rendering code.

## Current status (2026-07-22)

**The client logs in over native TCP, runs online, and navigates.** Verified live
(docker.lan, WinUAE KS3.x): connect → Amiga detected → `*CON` → credentials → `login OK!`
→ welcome frame renders; MAIL, ACCOUNT, the menu bar, and LEAVE all work. **Directory
navigation works**: the `Dir` button sends `P00`, the server returns the root directory,
and clicking entries navigates into sub-directories and reads pages. **Multi-frame text
paging works** via the frame window's `More` button (`D` = MORE). The native bsdsocket
transport, the X.25 read/ACK model, and PETSCII frame rendering are working end to end.
Transport design + RE ground truth:
[client/amiga/src/TCP-TRANSPORT.md](../client/amiga/src/TCP-TRANSPORT.md),
[client/amiga/vintage/tools/re/cnet-device-re.md](../client/amiga/vintage/tools/re/cnet-device-re.md).

**UI / rendering / navigation layer — reconstructed and working.** The directory-
population cluster is done (frame-page buffer sizing that fixed the online Guru;
`init_directory`'s `frame_display_mem`; the `FirstGadget` attach; `dir_preinit`'s action
bar `Dir/Back/Goto/Dnld/Upld`; the directory-row `dir_select`/`parse_directory_frame`
navigation). The frame-window button bar (`Next/Last/More/All/Send/Done`, `FUN_00117000`)
is built and attached, with `Next/Last/More/All` navigation (incl. the "Frame being edited"
RETRY/SKIP/CANCEL requester) and `Send/Done` (text-upload and Courier body-send, per
`g_state`) all wired. Rendering-fidelity fixes landed: button-gadget images (Chip-copy
+ repoint of the stale `0x116xxx` ImageData), the space/cleared-cell **background colour**
(`frame_border` writes `Image.PlaneOnOff`, not `Depth`), and the **colour palette** (the
non-identity C64→pen remap `g_palette` at `DAT_0011e1c0`; identity turned the grey
directory background pink). Systemic gotchas captured in
[client/amiga/vintage/tools/re/ui-audit-plan.md](../client/amiga/vintage/tools/re/ui-audit-plan.md).

**The frame Editor launches, opens, and auto-stores frames.** The `Editor` menu item
now works: `hook_serial_setup` sends editor opcode 2 (open window) — the opcode is a
BYTE at msg+0x14 (an earlier UWORD write sent opcode 0, so nothing happened). The full
editor opcode set is `{0 init, 1 terminate, 2 open, 4 store-frame, 5 set-frame-count}`
(there is no opcode 3). Opcode 4 is the auto-store: `frame_display_done` (`FUN_0011754e`,
previously stubbed) now PutMsgs each displayed frame to the editor and, under the shared
semaphore (`g_edit_proc+0x0e`), makes it the current `g_edit_frame`. So downloaded frames
populate the editor's ring (offline editing to save connect charges, matching the C64).
The client↔editor colour match, previously a known gap, was resolved by other rendering
fixes during development.

**MAIL / Courier — reconstructed and working (verified live).** The full subsystem: the five
action buttons `Done/ID/More/Dnld/Upld` (via `mail_state_enter`'s relabel of the directory
action bar); **ID check** (`mail_read`, `FUN_0010e468`) with recipient-name validation;
**send** (`mail_submit` → the compose dialog `FUN_0010f000/f09e/f23a` with recipient
re-validation, then the state-7 frame-window `Send/Done` driving `mail_field_send/next`);
**receive** (`mail_download`, multi-frame paging via `D`/MORE); and `Done/More`. The mail
window's string-gadget `StringInfo.Buffer`s are repointed at the C globals (the same stale-
blob-pointer fix as the put_frame dialog). Server companions landed the same session, each
`is_amiga`-gated where it diverges so the C64 stream is unchanged: a `@` command-ack before
the ID/mail validation frames (the Amiga's `serial_io_c` was mis-reading an id byte as a
host-error ack), the `courier-header.seq` RLE-terminator fix, an empty-EOS mail-frame guard,
a NO-MAIL frame for download-on-empty, and dropping the C64 SEND-screen date/time from the
Amiga breadcrumb (it was overwriting the message-number column).

**UCAT (user catalogue) — reconstructed and working (verified live).** The `UCat` Online-menu
item (`ucat_command`, recon `FUN_0010a384`) sends the one-byte `'C'` command and renders the
returned directory-format listing of the user's own uploaded pages through the standard
directory parser. It deliberately keeps the usual `Dir/Back/Goto/Dnld/Upld` action bar and
stays in `STATE_ONLINE` (no courier-style relabel — verified: the original handler has no
relabel call), so ordinary navigation works within the catalogue while the server's
`_ucat_active` serves UCat pages. The blob menu-spec entry, previously mis-wired to
`hook_link_entry`, now points at `_ucat_command`. Server companion: the empty-catalogue
`(NO UPLOADS)` placeholder was widened to the full-width DIR/mail format to avoid the Amiga
body-row parser freeze.

**NEXT / outstanding:**
- **Type `'L'` = live interactive terminal (partyline / MUDs):** `download_link`
  (`FUN_0010b66a`) is NOT a file download — after reading the 8-byte header it hands off to
  the **CnetTty viewer** (`g_tty_seg_bptr(screen, link_read_char, serial_io_variant,
  modem_send_delayed)`), a bidirectional read/send terminal loop. This is the mechanism for
  real-time interactive content (Compunet Partyline chat, MUDs, live sessions). It requires
  the header's first long == `0x01000001`; the server currently sends a mismatched `'L'`
  header (`0x00,0x00,exec…`) so the Amiga rejects it as "Invalid link". TODO: implement the
  `'L'` interactive path — server `'L'` header format + a live bidirectional channel over
  TCP (relates to the parked partyline-over-TCP item in diagnostics/transport).
- Editor edit behaviour and the opcode-5 frame-count wiring (from the "Editor frames" Setup
  value). NOTE: the `Next/Last/All/Send/Done` frame-button actions, the `Back` (`B`) command,
  and the client↔editor colour match are now DONE (commits `c3cef8e`, `8d1fee5`); text and
  program uploads work end-to-end.

The readability/reconstruction goals above are **done**. The client is fully
reconstructed as readable C (`client/amiga/src/`), builds with the vbcc KS1.3 toolchain,
and **boots to a working idle state** in the emulator with the offline UI functional:
menus, About, Settings (config load/save + toggle), Editor launch, and Quit (clean exit)
all verified on real emulated hardware.

Verification standard: every function is checked BYTE-EXACT against the relocated
disassembly of the original binary (tool: `client/amiga/vintage/tools/re/disasm_fn.py`;
rule in [CLAUDE.md](../CLAUDE.md): NEVER infer — verify against the machine code). The
running audit log is
[re/audit-findings.md](../client/amiga/vintage/tools/re/audit-findings.md).

**Audited + verified faithful so far:**
- **Transport primitives** — `serial_write`/`serial_read`/`serial_io_c`/`send_dat_packet`
  /`serial_io_variant` (byte-exact; fixed a swapped-out-param bug in serial_read).
- **Connect/login path** — `open_transport`, `do_connect`, `wait_connect_handshake`,
  `send_login_record`, `validate_login` (five real wire-protocol fidelity bugs found and
  fixed: the login-record terminal id, the connect-handshake bytes, the modem-name
  pointer, and a full rewrite of the handshake scanner).
- **Application layer** — directory, frames (PETSCII renderer), mail, put_frame, the full
  download subsystem incl. the IFF/ILBM image viewer, and the resource tracker (rebuilt
  faithfully to the original's exec-List design, fixing a Quit double-free).

**Frame encoding — CORRECTED:** the Amiga uses **PETSCII** (converted in the renderer),
NOT a separate "ESC-code" format — see goal 3 above and the note under Next steps. Any
lingering "ESC-code" phrasing elsewhere in this doc is superseded.

### Next steps

The remaining work is the transport swap (the last architectural piece) plus finishing
the audit. In priority order:

1. **bsdsocket TCP transport (the milestone, "2b").** Replace the `cnet.device`
   OpenDevice + `io_Command` read/write/dial calls with native
   `bsdsocket.library` TCP sockets connecting to the Reborn server (raw TCP on port
   **6400**, the same transport the C64 client uses), keeping the X.25 framing and the
   command/ack protocol above it byte-identical. Keep the 1.3 build for the offline UI;
   only the new socket code needs 2.04+, so it can runtime-detect bsdsocket and degrade
   gracefully. Decisions to settle first: which stack (Roadshow is the easiest modern
   choice; also AmiTCP/Miami — all expose the standard BSD-socket API), and the
   **host:port config surface** (repurpose existing config fields — e.g. modem-name →
   hostname — to avoid inventing UI the original lacked).
2. **Environment prerequisites for 2b (not code):**
   - **Kickstart 2.04** minimum — every Amiga TCP/IP stack requires it. The current
     binary is expected to run unchanged on 2.04 (RELOC32 + minstart.o + old-style
     Intuition are all backward-compatible); verify by booting on KS2.04.
   - **Emulator with guest networking** — FS-UAE cannot pass TCP from the emulated
     environment to the host, so the network dev loop needs **WinUAE or Amiberry** with
     an emulated Ethernet NIC (e.g. `a2065.device`) bridged to the host, pointed at the
     server on the Mac/LAN. Keep FS-UAE/vAmiga for the (faster) offline-UI checks.
   - A **2.04 Workbench** boot disk for the network tests (the current self-boot disk
     cherry-picks 1.3 Workbench pieces, which may misbehave on a 2.04 ROM).
3. **Finish the fidelity audit.** Remaining unaudited: the pure-UI layer
   (`ui.c`/`ui_state.c`/`ui_dialogs.c`/`menu.c`/`event_loop.c`) — not on the network
   path, so it doesn't block 2b. Also: faithfully re-trace `file_download_xfer`
   (FUN_0010b174, only approximately reconstructed); fix the LONG-vs-UWORD width of
   `g_state`/`g_online`/`g_frame_hdr_more`; and reconstruct `apply_serial_params`
   correctly (it is bound to FUN_00114050, which is actually an editor command).
4. **Reproducibility:** make `make_boot_adf.sh` deterministic (pin datestamps) so a
   built ADF is byte-identical and checksummable — a non-deterministic build caused a
   long false-trail chasing a "stale disk" as if it were a code bug.

**Protocol match (reference):** transport framing (X.25 in `cnet.device`) and application
commands both CONFIRMED matching the C64/server — single-letter commands + numeric arg in
COM frames, ack `@`: `P<nn>`=SHOW, `D<nn>`=DIR, plus `A`/`B`/`E`/`M`/`N`/`O`. The
identification handshake differs (`C CNET\r`×2 + 14-zero+CR field) but is detectable, so
the server can recognise an Amiga client at connect. See
[re/protocol-analysis.md](../client/amiga/vintage/tools/re/protocol-analysis.md) and
[re/identification-and-commands.md](../client/amiga/vintage/tools/re/identification-and-commands.md).

- **Unpack `CNETTTY`** — DONE (decrunched; shipped as `CnetTty` and driven by the link
  download path).

## Extraction notes

- Extracted with `amitools` (`xdftool`). The ADF has one filesystem error: the
  `ReadMe` and `future.txt` files have a bad data-block sequence number and did not
  extract; everything else extracted cleanly.
- The Compunet client files (original, still-crunched where applicable),
  `cnet.device`, the full `cnet_modems` set, and the sample `Frames/test.frame`
  are under [client/amiga/vintage/](../client/amiga/vintage/). The source disk
  image [historical/Comms_Disc_III_1989_17-Bit_Software.adf](../historical/Comms_Disc_III_1989_17-Bit_Software.adf)
  retains everything else (the other five programs).
- Decrunched executables and text are under
  [client/amiga/vintage/decrunched/](../client/amiga/vintage/decrunched/); the
  decruncher is [client/amiga/vintage/tools/ppdecrunch.py](../client/amiga/vintage/tools/ppdecrunch.py).
