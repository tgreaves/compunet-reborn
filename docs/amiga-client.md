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
| `cnet-configuration` | 54 B | binary | Saved config: user ID `019975422`, modem `linnet_1200`, `NEW-USER` |

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
`cnet-configuration` selects `linnet_1200` with a 9-digit Compunet user ID and the
`NEW-USER` account, matching the Compunet login model.

## Feasibility — paths to an Amiga Reborn client

Reborn's premise (per project rules) is "preserve the app-layer protocol, swap only
the transport — TCP instead of the phone line." The Amiga suite has the same seam,
so two paths exist:

1. **Reuse the original `Compunet` binary unchanged.** Provide it a transport to the
   Reborn server, either by:
   - a drop-in replacement `cnet.device` that speaks TCP to the Reborn server, or
   - running the binary under WinUAE/vAmiga with serial→TCP redirection (or a
     virtual/WiFi modem) pointed at the Reborn server.

   If the client's app-layer protocol matches [docs/PROTOCOL.md](PROTOCOL.md), this
   could work with little or no reverse-engineering of the client. **Highest-value,
   lowest-effort path.**

2. **Reimplement** the Amiga client, using a disassembly of `Compunet` as reference.
   The binary is now decrunched, so this is unblocked.

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
3. **PETSCII handling — how does the Amiga cope?** C64 Compunet content is PETSCII,
   but the Amiga has no native PETSCII support. **Open question:** does the `Compunet`
   client translate PETSCII ↔ its own display charset (a lookup table or conversion
   routine), render a custom C64-style font, or handle frames some other way? This
   directly affects how Reborn frames (authored as PETSCII) will render on the Amiga.
   Needs investigation in the decompiled display/frame-rendering code.

### Next steps

- **Name the Amiga LVOs** in the Ghidra project (fd-based) so OS calls in `recon.c`
  read as `OpenDevice`/`DoIO`/`Printf`/etc. — the last big readability step before
  systematic reconstruction. *(Current focus — goal 1.)*
- **Assign sensible function names** in the recon based on the strings each function
  references and its call graph, replacing `FUN_00xxxxxx` with meaningful names.
- **Locate PETSCII handling** (goal 3): search the decompiled code for character
  translation tables, `$40`/`$60`/`$C0` PETSCII-range remapping, or custom font
  loading in the frame-display path.
- **Map the transport touch-points** (goal 2): every `cnet.device` open / `DoIO` /
  `SendIO` / read / write / dial / carrier-check site, as the set of calls TCP will
  replace.
- **Assemble the KS1.3 NDK headers** into the vbcc tree so OS-calling modules
  compile (the base toolchain and pure-logic modules already build).
- **Reconstruct module-by-module**, starting with the transport (`cnet.device`
  open/IO around `0x1192b6` / `0x10343c`) and the protocol/framing code, verifying
  each against its original with the round-trip method.
- **Protocol match.** Does this Amiga client speak the *same* application-layer
  protocol (command bytes, frame format, linking/login sequence) that Reborn's
  server implements? Verify the reconstructed transport/framing against
  [docs/PROTOCOL.md](PROTOCOL.md) and the C64 linking sequence in
  [docs/LINKING.md](LINKING.md). This is the critical unknown.
- **Unpack `CNETTTY`** (cruncher #2) via 68k emulation of its stub, if the TTY
  viewer proves useful.

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
