# Amiga client — UI / rendering / navigation layer audit (handoff)

**Purpose:** a byte-exact audit of the client's UI/rendering/navigation layer against
the relocated disassembly of the original — the same rigor the protocol path already
received (see [audit-findings.md](audit-findings.md)), applied to the half that was
deliberately deferred.

## Why this audit exists

The reconstruction was verified in two very different degrees:

- **Protocol / network path — AUDITED byte-exact** (audit-findings.md): transport
  (`transport.c`, `modem.c`, `net.c`), connect/login (`connect.c`, `login.c`),
  framing, and the application commands (directory/mail/download command senders).
  This is why login over TCP, framing, MAIL, ACCOUNT, and the wire protocol all work.

- **UI / rendering / navigation — NOT audited.** This layer (`ui.c`, `ui_state.c`,
  `ui_dialogs.c`, `menu.c`, `event_loop.c`, `directory_parse.c`, `directory_select.c`,
  `directory.c`, `frame.c`, `frame_gfx.c`, `frame_control.c`, `dispatch.c`,
  `navigate.c`, `launch.c`, `partyline.c`) was reconstructed only to **compile and
  link**. It contains **stubs** (`return 1`), **"deferred"** bodies, **omitted calls**,
  **empty globals**, and **no-op** functions — none of which mattered until the client
  could run online, which was impossible until the TCP transport existed.

Now that the client logs in and renders frames over TCP, this layer is exercised for
the first time and its gaps surface one interaction at a time. **This audit finds and
fixes them as a batch, in priority order.**

## Methodology (same as audit-findings.md)

1. Regenerate the relocated flat image: `python flatten.py ../../decrunched/Compunet
   compunet_flat` → `compunet_flat.bin` (BASE `0x100000`, blob DATA_BASE `0x11d000`).
2. For each UI function, disassemble the **original** (`disasm_fn.py <name|0xADDR>` or
   capstone: `CS_ARCH_M68K, CS_MODE_M68K_000|CS_MODE_BIG_ENDIAN`) and compare the
   reconstruction call-by-call. Verify EVERY OS call, struct offset, argument, and
   branch. Fix any stub/omission/mis-decode. Rebuild (`emulation/make_hdd.sh`) and have
   the user runtime-test in WinUAE against docker.lan.
3. Ground every claim in the machine code — never infer (CLAUDE.md rule).

## PRIORITY 1 — directory population (BLOCKS navigation; do first)

Symptom: after login the "Current Directory" window is blank and there is no way to
navigate ("stuck on the welcome frame"). Verified navigation model:
- `dir_select` (directory_select.c) mode 1 → `goto_page()` → `P<nn>` (first call `P00`
  = top directory); mode 2 → `validate_login()` → `D<nn>`.
- directory link rows → `link_follow()` → `L<code>` (codes at `page + row*7 + 0x790`).
- All require the directory window to already have clickable content — which it lacks.

Concrete gaps to fix (all verified this session):
1. **Page-buffer sizing (do this first).** `ui.c` sets `g_frame_page = (APTR)&g_frame_win`
   and `g_dir_page = (APTR)&g_dir_win`, but `g_frame_win`/`g_dir_win` are single
   `struct Window *` globals (4 bytes). The page struct is large — `PAGE_CELLS(p) =
   p+0x10`, 40x24 cells × 2 bytes = `0x780`, so a page is ~`0x790` bytes. Rendering a
   frame into `&g_frame_win` overruns adjacent globals. It "works" for the welcome
   frame only because the corruption happens to be benign; this likely also causes the
   welcome-frame rendering imperfections. Find the original page structures (the recon
   uses `DAT_0011d078`/`DAT_0011d07c` as the page pointers whose first field is the
   window) and give `g_frame_page`/`g_dir_page` a real backing buffer of the correct
   size, matching how the original lays them out.
2. **`init_directory` (FUN_001099c0) omits `frame_display_mem`.** The original ends with
   `frame_display_mem(DATA(0x11e226), page)` — it draws an initial directory template
   into the window. The reconstruction skipped it. (The menu-strip/share-port calls were
   added in commit `7c84a0d`; the `frame_display_mem` call still needs adding, AFTER the
   page-buffer fix so it renders into real storage.) Full original layout: preinit
   `bsr 0x109000`; open window; `share_user_port`; `ModifyIDCMP(0x520)`;
   `set_menu_strip_tracked(win, g_menu_pair[0])`; `frame_display_mem(DATA(0x11e226),
   page)`; set `g_dir_page`.
3. **`directory_parse.c` / `directory_select.c`** — verify `parse_directory_frame`
   (FUN_00109a5e) fully populates the row link codes (`+0x790`) and installs the
   `link_follow` handlers (`gadget+0x2c`), and that `dir_select` (FUN_0010935a) drives
   the mode-1/mode-2 dispatch correctly, so a click actually issues `P00` and loads the
   top directory. This is the interaction that unblocks everything.

## PRIORITY 2 — dispatch hook stubs

`dispatch.c` has hooks bound to blob gadgets/menu items that are `return 1` no-ops:
- `hook_render_entry` (0x?), `hook_ed_172f4`/`1733a`/`17380`/`173c6`/`1740c`/`17470`
  (editor gadget hooks, FUN_00117xxx), `hook_16000`/`16200`/`16400` ("editor render
  entry points"). Disassemble each original and implement its real behaviour (most are
  the frame editor — confirm whether the editor is in scope, and if not, document that
  these are intentionally inert).

## PRIORITY 3 — frame rendering fidelity

The welcome frame renders but is "not perfect" (user). After the page-buffer fix (P1.1),
re-audit `frame.c` `frame_display`/`render_char`/`frame_rle_getchar`, `frame_control.c`
(the control-code jump tables — colours, cursor, RVS, charset), and `frame_gfx.c`
(offscreen begin/end, `frame_border`, the direct-draw `blt_font_to_rastport` added this
session) against the originals. Confirm the palette (`g_palette`), the charset-mode
handling, and cell/colour attribute logic match.

## SYSTEMIC issue to sweep — blob→globals stale pointers

Several bugs this session were the SAME root cause: structures in the extracted data
blob (`g_data_blob.asm`) that point INTO the globals region (addresses > `0x1200e8`,
past the blob's end) hold the **original absolute address**, because `extract_data.py`
relocated blob-internal (data→data) and blob→code pointers but NOT blob→global-data
pointers. Instances already found + fixed:
- credentials gadget `StringInfo.Buffer` (0x120244/0x12024d) — commit `1a27133`
- busy-pointer sprite pointer (`*0x11d068` → 0x116400, data in a code hunk) — `7c84a0d`
- C64 charset `c64_charset_upper`/`_lower` (empty globals vs blob 0x11d9c0/0x11ddc0) —
  `7c84a0d` (this one was in-blob but read from an empty global — related class)

**Audit `extract_data.py` and enumerate EVERY blob relocation whose target is > the
blob end (`0x1200e8`).** Each is a latent stale-pointer bug. Fix them at the source
(relocate to the reconstruction's globals) or document each. This likely covers menu/
window/gadget structures not yet exercised.

## Current runtime state (2026-07-22)

Verified live (docker.lan, WinUAE KS3.x), all on commit `7c84a0d`:
- **Works:** TCP login end to end; welcome frame renders (imperfect); MAIL → Courier
  page; ACCOUNT → credit popup; menus restored on all windows; LEAVE goes offline.
- **Broken / incomplete:** navigation (directory window blank, no way to reach the
  directory — Priority 1); welcome-frame rendering imperfections (Priority 3); dispatch
  editor stubs (Priority 2).

## Fixes already landed (for context — these WERE UI-layer gaps)

`7c84a0d` (frame render + online session): direct-draw cell blit (was no-op), charset
from blob (was empty), TCP drain-loop skip, logon TAB, busy sprite, LEAVE always-
disconnect + socket close, frame/dir window menu strip.
`1a27133` (login): case-insensitive `*CON`, credentials gadget buffer re-point,
NextGadget tab fix, password field width.
`699cd42`: transport seams + server Amiga branch. `f4c2e94`: net.c foundation.

The transport/protocol design and RE ground truth are in
[../../src/TCP-TRANSPORT.md](../../src/TCP-TRANSPORT.md) and
[cnet-device-re.md](cnet-device-re.md); the wider analysis in
[docs/amiga-client.md](../../../../docs/amiga-client.md).
