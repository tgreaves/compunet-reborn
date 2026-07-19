# Compunet Amiga client — function map

Identified functions in `recon.c` (444 total), by string references (Ghidra +
`a4xref.py`), OS-call fingerprint (see `lvo_callsites.txt`), and call graph.
Names proposed here will be applied in the naming pass. Confidence noted.

## Application-level functions (high confidence — string-anchored)

| Address | Proposed name | Evidence |
|---------|---------------|----------|
| `FUN_00100000` | `_start` / C startup | argc/argv/a4 setup, FindTask, entry point |
| `FUN_001001c4` | `open_dos_library` | "dos.library", OpenLibrary |
| `FUN_00102000` | `load_config` | "cnet-configuration" (read) |
| `FUN_00112000` | `save_config` | "cnet-configuration" (write) |
| `FUN_001023ec` | `set_connection_state` | "Compunet - offline/logging on/online/courier", "Dir or Goto…", "Send to upload…" |
| `FUN_001025de` | `launch_editor` | "CnetEditor" |
| `FUN_001026ae` | `launch_tty` | "CnetTty", graphics/intuition.library |
| `FUN_0012a068` | `connection_setup` | "Modem error", "Can't open cnet.device", "Can't open logon window", "Can't open frame window" (via a4xref) |
| `FUN_0010a1e2` | `goto_page` | "Goto Page", "P%02d" |
| `FUN_0010b000` | `file_download` | "Download filename", "File download", "Action download", "Invalid link" |
| `FUN_0010b730` | `download_check` | "Can't download this", "D%02d" |
| `FUN_0010c000` | `upload` | "Upload filename" |
| `FUN_0010e0fc` | `validate_login` | "*** No Such User ***", "D%02d" |
| `FUN_0011956a` | `comms_error_a` | "Carrier lost", "Comms problem" |
| `FUN_0011967c` | `comms_error_b` | "Carrier lost", "Comms problem" |
| `FUN_0011979e` | `comms_error_c` | "Carrier lost", "Comms problem" |
| `FUN_0010b000`* | (charged item) | "WARNING - CHARGED ITEM" |

## Transport touch-points (goal 2 — TCP will replace these)

Device I/O runs through amiga.lib-style thunks on ExecBase:

| Thunk | OS call | recon.c line |
|-------|---------|--------------|
| `thunk_FUN_00129190` | `DoIO` (ExecBase -0x1c8) | 7641 |
| (send thunk) | `SendIO` (ExecBase -0x1ce) | 7770 |
| `thunk_FUN_00129120` | `ReplyMsg` (-0x17a) | 7630 |
| (msg thunks) | `GetMsg`/`PutMsg`/`WaitPort` | see lvo_callsites.txt |

`OpenDevice`/`CloseDevice` for `cnet.device` are invoked via register-base calls
(currently UNRESOLVED in the automated pass — need per-function dataflow). The
docs cite the device-open helper near `0x1192b6`.

### Transport globals (confirmed — named in `lvo.KNOWN_GLOBALS`)

Two serial IORequests + a shared reply port. IORequest offsets confirm the struct:
`0x1c` io_Command, `0x24` io_Length, `0x28` io_Data, `0x20` io_Actual,
`0x1f/0x2c/0x2d` IOExtSer status.

| Global | Name | Role |
|--------|------|------|
| `DAT_001230b4` | `g_write_req` | write IORequest (io_Command=3 CMD_WRITE) |
| `DAT_001230b8` | `g_read_req`  | read IORequest (io_Command=2 CMD_READ / 0xb) |
| `DAT_001230a8` | `g_device_port` | shared reply MsgPort (GetMsg/WaitPort) |

### Serial read/write routines (confirmed)

| Address | Proposed name | Evidence |
|---------|---------------|----------|
| `FUN_0011956a` | `serial_write` | sets `g_write_req` io_Command=3, SendIO, waits; "Carrier lost"/"Comms problem" on failure |
| `FUN_0011967c` | `serial_read`  | sets `g_read_req` io_Command=2, SendIO, waits; carrier-loss detection |
| `FUN_0011979e` | `serial_io_c`  | third carrier-aware IO routine (variant — confirm) |

These three routines + the two IORequests + reply port are the **complete transport
surface**. A TCP transport replaces exactly this: instead of `SendIO/DoIO` on
`cnet.device`, read/write a socket. Everything above (framing, frames, login) is
unchanged — the same seam as the C64 SwiftLink↔TCP swap.

## OpenLibrary wrapper chain (confirmed)

`FUN_0011a290` → `FUN_001291b8` → `(**(ExecBase -0x228))()` = **OpenLibrary**.

## Register-base (unresolved) calls — dataflow-proven so far

- startup `FUN_00100000` line 49: `iVar9 + -0x1e` where `iVar9 = DAT_001200d8`
  (DOSBase) → **DOSBase.Open()** (result stored as a file handle). `-0x24` on the
  same base → **DOSBase.Close()**.

## PETSCII handling (goal 3) — early findings

- `GfxBase.Text()` is called from **exactly one** thunk (`FUN_0012a000`), and that
  thunk has no statically-recovered caller (reached via an indirect/computed
  reference Ghidra did not wire up). So raw font text is *not* the main display path.
- `IntuitionBase.PrintIText()` is called **7×**, plus heavy use of `DrawImage`,
  `DrawBorder`, `AddGList`/`RefreshGList`, `RectFill`, `BltBitMapRastPort`. This is a
  **gadget/IntuiText + bitmap** display model, not a scrolling character TTY.
- Implication: Compunet *frames* are likely rendered as graphics/IntuiText rather
  than streamed as PETSCII characters to a font. **Where (and whether) PETSCII→Amiga
  translation happens is still unconfirmed** — candidates: a translation table
  applied when a frame arrives, or a custom C64-style font bound to the RastPort.
  Needs interactive tracing of the frame-receive → display path (the `CnetTty`
  viewer, still packed, may also be the character-stream renderer).

## Connect / login (traced by disassembly — see login-connect-flow.md)

| Address | Proposed name | Role |
|---------|---------------|------|
| `0x10343c` | `do_connect` | open transport → dispatch status → open logon window |
| `0x1192b6` | `open_transport` | create ports + IORequests, signal masks; returns status |
| `0x10e0fc` | `validate_login` | "*** No Such User ***" (server login rejection) |

`open_transport` status codes: 0=ok, 10=Modem error, 1=modem msg, else=can't open
cnet.device. Login packet uses token `0x43` (COM).

> **Pipeline gap found:** `SeedCode.java` seeds only hunk *starts*, so functions
> reached solely via indirect/computed calls (e.g. `do_connect` @0x10343c,
> `open_transport` @0x1192b6) were never created in `recon.c`. A future SeedCode
> improvement: also seed the targets of `jsr`/`jmp abs` and pointer tables so these
> appear in the decompiled output. For now they are disassembled directly.

## Still to identify

- **PETSCII translation** — confirm the mechanism (table / custom font / none).
- The frame/directory parser and X.25 framing/CRC (protocol match vs PROTOCOL.md).
- Wire up the indirectly-referenced thunks (jump table / function pointers) so the
  `Text()` caller and similar become visible.
