# Reconstruction audit findings (partial) — disasm-verified

Systematic per-function audit of the reconstructed Amiga client against the ORIGINAL
binary's relocated disassembly (`disasm_fn.py`). Method: for each function, compare our
compiled code / source to the original's relocated m68k disasm — offsets, constants,
LVO calls, arg order, table strides. Rule: NEVER infer (see CLAUDE.md).

Coverage: 3 of 5 module batches completed before the audit was halted (competing
session). Batches done: config/launch/mail/transfer/glue; directory/navigate;
frame/frame_gfx/frame_control. NOT yet audited: transport/connect/login, ui/menu/
event_loop/dialogs (agents were stopped mid-run).

Each item below marked **[VERIFIED]** was independently re-checked against the
disassembly. **[reported]** = found by audit, not yet re-verified. No fixes were
applied by the audit session — this is a findings list only. NOTE the competing
session has independently begun fixing some of these (e.g. goto_page "P00",
serial io_Error semantics in compunet.h).

## SEVERE (wire-protocol — server would reject)

- **[VERIFIED] account() — wrong command.** directory.c. Original (0x10c5a0) sends the
  string at 0x11e6d2 = `"A"` (length 1). Ours sends `"ACCOUNT"` (7 bytes). "ACCOUNT" is
  the dialog TITLE (0x11e6f6). PROTOCOL.md: `$41 'A' ACCNT`.
  FIX: `serial_write("A", 1, 1, TOKEN_COM);`
- **[VERIFIED] goto_page() offline branch — wrong buffer.** navigate.c. Original
  (0x10a206) sends literal `"P00"` (@0x11e3f4, len 3). Ours sent `g_link_code` (empty).
  FIX: `serial_write("P00", 3, 1, TOKEN_COM);`  (online "P%02d" branch was correct.)
  [The competing session appears to have already applied this.]

## HIGH

- **[VERIFIED] blit_char_cell — drops lowercase font bank.** frame.c (~line 268/270).
  Original (0x107032) reads page+0x0c (mode) and folds `(mode<<8)` into the screencode
  before `<<4`, selecting the +0x1000/+0x1800 lowercase banks build_font populates. Ours
  indexes by screencode only, so lowercase-mode frames render in the UPPERCASE bank.
  FIX: index = `code | (PAGE_MODE(page) << 8)`; normal `*0x10`, reverse `^0x80` then `*0x10`.
- **[VERIFIED] load_config — clears wrong global at entry.** config.c:43. Original
  (0x102004) `clr.b 0x120134` = g_config+0x2c (cfg userid). Ours clears g_login_userid
  (0x120244), a different global. FIX: clear `g_config+0x2c` (g_cfg_userid[0]).
- **[VERIFIED] launch_editor — pre-clears wrong message byte.** launch.c. Original
  (0x10264c) `clr.b 0x12015a` = editor msg **+0x14**. Ours clears +0x15 (EMSG_STATUS) and
  never clears +0x14, leaving it uninitialised for the child. Status read-back at +0x15
  is correct. FIX: clear msg+0x14; the original does not pre-clear +0x15.
- **[FIXED] put_frame() collapsed.** directory.c. Was missing the initial guard call
  FUN_0010d0e6 (0x10c6ae; `tst.l d0; beq return 0`), the two sscanf parses
  ("%d.%d"@0x11e654 -> g_put_page/g_put_sub; "%d"@0x11e65a -> g_put_life), and used the
  wrong widths + wrong dispatch. Now re-traced against the raw jump table at 0x10c3c2
  (stride 6 = [key.w][bra.w], verified from bytes): 'T'->put_frame_publish (FUN_0010c250),
  {A,S,P,F}->upload_file (FUN_0010c0ee), default->"Invalid page type"+dir_action_cleanup.
  g_put_page/sub/life widened to LONG; put_frame_type_ok (invented) removed. The gate
  FUN_0010d0e6 + opener FUN_0010d000 + string cleaner FUN_0010f1a4 are now fully
  reconstructed as put_frame_dialog/put_frame_dialog_open/str_clean_upper (ui_dialogs.c),
  all offsets verified vs disasm (`--our put_frame` matches; opener/OK-path field offsets
  Window+4/+6, RPort+50, UserPort+86, GadgetID+38 all confirmed).
  Two corrections this fix surfaced (both verified, both were latent bugs):
  * **FUN_0010c250 uses WindowToFront, not CloseWindow.** 0x12b1ec is a WindowToFront
    veneer (jsr -0x138(IntuitionBase)), not CloseWindow. put_frame_publish now brings the
    frame + courier windows to front and sets g_state=4.
  * **dir_action_cleanup (FUN_0010d0d0) closes the courier window, not the pointer.**
    Was wrongly reconstructed as clear_wait_pointer(); the disasm is
    `tst.l 0x121650(a4); beq; close_window_tracked(g_courier_win); clr.l 0x121650`.
    Fixed in ui_dialogs.c.
- **[FIXED] account() dialog arg count.** directory.c. status_ok_dialog is now the 5-arg
  form (line1, line2, p4, p5); account passes p4=1, p5=6 (the winptr arg is consumed by
  the requester core via the blob NewWindow.Screen patch). Verified.

## MEDIUM

- **[VERIFIED] g_ctrl_hi colours 0x97/98/99 permuted.** frame_control.c. Verified handler
  colours: 0x97->14 (lt_blue), 0x98->12 (grey2), 0x99->13 (lt_green). Ours binds
  0x97=grey2, 0x98=lt_grn, 0x99=lt_blu (rotated). FIX the three handler colour assignments.
  All other 32+32 control-table entries verified correct.
- **[reported] build_font — missing InitBitMap.** frame.c. Original (0x1060d6) ends with
  InitBitMap(&g_cell_bm=0x12025c, depth 4, w 8, h 8); ours returns without it. Also uses
  raw AllocMem(CHIP|CLEAR) vs original alloc_tracked(CHIP). Font math itself matches.
- **[reported] blt_font_to_rastport — empty stub.** frame_gfx.c. Original (0x10710e) does
  BltBitMapRastPort(g_cell_bm -> window RPort at col*8+4, row*8+10, 8x8, minterm 0xc0).
  Only reached when the offscreen alloc fails (fallback draws nothing).
- **[reported] mail_upload_mode / id_check_mode / mail_open_window incomplete.** mail.c.
  Missing SetWindowTitles + RemoveGList/AddGList/RefreshGList gadget-list swaps; mail_open_
  window missing dynamic NewWindow sizing + border/text draw. (census-recovered module.)
- **[reported] upload_read_file uses Open+Seek.** dosio.c. Original (0x10c030) uses
  Lock(SHARED)+Examine (fib_Size at fib+0x7c)+UnLock, wrapped in a retry dialog. Same size
  in the common case; different OS calls + missing retry.
- **[reported] dir_select action dispatch drops link_lock wrap.** directory_select.c:82.
  Original wraps each row action in link_lock via wrappers FUN_0010956c/963c/a484 (operate
  on the page action gadget +0xeb6/+0xf52); ours calls goto_page/download_check/
  validate_login bare, no highlight. State->action mapping itself is correct.
- **[reported] alloc_tracked structural difference.** resources.c. Original reuses the
  allocated block as its own ResNode (freefn=0, size at node+0x12); ours allocates a
  SEPARATE 0x1a node with freefn=free_tracked. Behaviour-equivalent (tracker is plumbing)
  but doubles allocations. Low priority.

## LOW

- **[reported] config_open_write / file_open_write don't register tracked Close.** dosio.c.
  Original (0x11a3c6) registers a tracked close after Open. Benign (explicit close on all
  paths) but not faithful; file_open_write also ignores its mode arg.
- **[reported] put_frame_xfer omits success-path `clr.b 0x121589`.** directory.c:183.
- **[reported] read_frame_byte g_frame_pos/len width.** globals.c:78. Declared UWORD;
  original treats DAT_001203a0/a4 as LONG. Values <0x100 so functionally identical.
- **[reported] link_goto zeroes g_goto_page_no as word not byte.** navigate.c. Harmless.
- **[note] config_open_read sequence differs.** dosio.c. Original (0x11a41e) Locks/
  Examines/reopens; ours Open+Read(0x36)+Close. Same 0x36 bytes; acceptable, not byte-faithful.

## VERIFIED CLEAN (match the original)

parse_directory_frame (1924B, byte-for-byte), render_char + all frame primitives
(frame_advance_cursor/home/set_cursor/pen_lower/pen_upper/row_newline/write_string/
clear_region/redraw/reset_page), all frame_control cursor/colour/charset/reverse handlers
(except the 0x97/98/99 colours), ctrl_nop, frame_offscreen_begin/end/border, frame_display_mem,
read_frame_byte, frame_rle_getchar, dir_select highlight path, hilite_row, directory_repaint,
mail_state_enter, hook_dir_09898/0984c, vote, extend_life, link_follow, link_goto,
settings_open/dialog/apply/close/toggle, save_config_file, all resource_* functions,
launch_tty, load_screen_palette, set_menu_strip_tracked, share/unshare_user_port,
open_dos_library, open_library_checked, fatal_exit, link_lock, partyline_open,
logon_window_ready, transfer.c (upload_file/action_download/download_receive).

## DOWNLOAD SUBSYSTEM — reconstructed this pass (download.c, verified vs disasm)

- **[FIXED] download_check (FUN_0010b730) dispatch was entirely invented.** The prior
  transfer.c version switched on 'C'/'S'/'A' and called handlers directly with NO
  charged-item gate. The real function (verified from the raw jump table at 0x10b780) is
  a 6-way dispatch on the row type: 'T'->download_text (FUN_00113000), 'F'->action_download_run
  (FUN_0010b50e), 'P'/'S'->download_program (FUN_0010b36e -> download_receive), 'A'->
  action_download (FUN_0010b380), 'L'->download_link (FUN_0010b66a), else "Can't download
  this". EVERY branch except 'T' is first gated by download_charged_prompt (FUN_0010b000):
  "WARNING - CHARGED ITEM / Buy for £<price>?". NB the competing audit wrongly listed
  download_check as VERIFIED CLEAN — an inference error; it never disassembled it.
- **[NEW] download_charged_prompt (FUN_0010b000)** reconstructed: reads the row price at
  dir+row*0x66+0x82e; empty/space -> free; else retry_dialog. Verified.
- **[NEW] download_text / _continue / _loop (FUN_00113000/113062/1130ca)** reconstructed:
  the 'T' text-page fetch+display via frame_display + frame_display_done, state=3 while more.
- **[NEW] action_download_run (FUN_0010b50e)** reconstructed: the 'F' picture path. Streams
  the download in <=4000-byte blocks, staging to disk AND feeding each byte to the IFF decoder.
- **[NEW] download_link (FUN_0010b66a) + link_drain_preamble (FUN_0010b602) + link_end
  (FUN_0010b656)** reconstructed: validate the 8-byte link header (0x01000001, link_a==0),
  drain the preamble, hand off to the CnetTty viewer (g_tty_seg_bptr) with read/io/send
  callbacks; "Carrier lost" (fatal) + longjmp on viewer return 0.
- **[NEW] IFF/ILBM decoder (FUN_00111000 family, ~1852 bytes)** reconstructed in download.c:
  iff_init (0x111000), iff_feed_byte state machine (0x111024: FORM/ILBM/BMHD/CMAP/BODY),
  iff_setup (0x1112ae: BMHD->screen, alloc interleaved 1-row×nplanes bitmap, per-plane
  pointers, last-word mask via asr.l #$ffff0000, open screen+window), iff_cmap (0x11147e:
  RGB4 palette + LoadRGB4), iff_body_start (0x111526), iff_row_uncompressed (0x11155c),
  iff_row_byterun1 (0x1115e6: PackBits), iff_free_all/window (0x111270/0x1116ee), and the
  standalone iff_view_file (0x111704). Each verified against `vc -S` vs the relocated disasm.
- **[NEW] serial_io_variant (FUN_0011998a) + link_viewer_exit (FUN_001194c8)** added to
  modem.c; **load_file_to_mem (FUN_0011a41e) + mem_block_size (FUN_0011a26c)** added to
  dosio.c (free_mem_block == existing free_tracked/FUN_0011a238).
- **[TODO] file_download_xfer (FUN_0010b174) is only approximately reconstructed** in
  transfer.c. The real function (370B) reads the 8-byte header, dispatches machine-type via
  download_machine_prompt with distinct abort strings (0x14b8/0x14bc, token 0x41) and
  extracts a transfer size from header+6 / 0x1215ec. Ours is a simplified retry-open loop.
  Needs a faithful re-trace (it feeds both download_receive and action_download_run).

## NOT YET AUDITED (agents stopped)

transport.c (serial_write/read/io_c, send_dat_packet, report_result), connect.c
(open_transport), login.c (do_connect, send_login_record, wait_connect_handshake,
validate_login), ui.c / ui_state.c / ui_dialogs.c / menu.c / event_loop.c.

Tooling: `disasm_fn.py <name|0xADDR> [--our]` (this dir) is the verified original-vs-ours
comparer used for this audit — the reliable, no-inference method for finishing it.
