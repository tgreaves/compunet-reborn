/*
 * globals.c — definitions of the shared client state.
 *
 * In the original SAS/C build these live in the a4-relative small-data section
 * (recon addresses 0x11d000-0x123xxx). Here they are ordinary C globals so the
 * modules link into one program. Names and roles follow coverage-census.md /
 * function-map.md; the raw recon address is noted for each.
 *
 * The frame-display working set is CHIP-memory-backed at runtime (build_font
 * AllocMem's the font); the buffers here are the BSS-resident state the modules
 * read and write.
 */
#include <exec/types.h>
#include <exec/ports.h>

#include "compunet.h"

/* ---- Library bases (recon 0x11d040 / 0x1200d8 / 0x1200e8 / 0x1200ec) ----
 * We link with vbcc's MINIMAL startup (minstart.o), because the full startup.o's
 * CLI/DOS init crashes on Kickstart 1.3 (verified: a do-nothing flasher gurus with
 * startup.o but runs with minstart.o). minstart.o sets _SysBase and calls main(),
 * but does NOT open dos.library — so unlike with startup.o we must define DOSBase
 * ourselves; open_dos_library() (called first thing in main) fills it in.
 * IntuitionBase/GfxBase are opened by launch_tty as before. */
APTR DOSBase       = NULL;   /* opened by open_dos_library() at startup */
APTR IntuitionBase = NULL;
APTR GfxBase       = NULL;

/* ---- Transport request / port state (recon 0x1230a8-0x1230b8) ---- */
struct CnetRequest *g_read_req    = NULL;
struct CnetRequest *g_write_req   = NULL;
struct MsgPort     *g_device_port = NULL;
struct MsgPort     *g_read_port   = NULL;
struct MsgPort     *g_write_port  = NULL;
ULONG               g_device_sig  = 0;
ULONG               g_read_sig    = 0;
ULONG               g_write_sig   = 0;

struct Device *g_cnet_device = NULL;
UWORD  g_dev_param2e = 0;        /* DAT_0012012e-ish device param scratch (not in block) */

/* ---- THE config block — the single 0x36-byte record at recon 0x120108 ----
 * In the original this ONE block is: loaded from / saved to cnet-configuration
 * verbatim (0x36 bytes), read by open_transport for the device baud (block+0x24),
 * and edited by the Settings dialog. The reconstruction previously split it into
 * separate g_phone_number / g_baud_up / g_baud_down / g_baud_setting / g_open_flags
 * globals that nothing kept in sync (so config-file baud never reached the device).
 * They are now ACCESSOR MACROS into g_config (see compunet.h), so all consumers
 * share this one memory exactly as the original does. Field layout (block+offset):
 *   +0x00 char[16] phone   +0x10 LONG baud_setting  +0x14 char[16] modem
 *   +0x24 UWORD baud_up     +0x26 UWORD baud_down    +0x28 UWORD open_flags
 *   +0x2a UWORD data_bits   +0x2c char[..] userid */
UBYTE  g_config[0x36];

/* ---- Connection / session state ---- */
UWORD  g_state        = 0;      /* DAT_0011d070 */
UWORD  g_online       = 0;      /* DAT_0011d074 */
UWORD  g_state_shadow = 0xffff; /* DAT_0011d46e */
UWORD  g_online_shadow= 0xffff; /* DAT_0011d472 */
APTR   g_dir_page     = NULL;   /* DAT_0011d07c */
APTR   g_frame_page   = NULL;   /* DAT_0011d078 */

/* ---- Command / ack scratch ---- */
char   g_cmd_buf[256];          /* DAT_00121588 — shared command buffer */
char   g_ack_text[64];          /* DAT_0012021a — status text passed to acks */

/* ---- Login record fields (separate buffers at 0x120244, filled from config) ---- */
char   g_login_userid[16];      /* DAT_00120244 */
char   g_login_scratch[16];     /* DAT_0012024d */
UBYTE  g_frame_indent = 0;      /* placeholder for DAT_0011d078 indent check */

/* ---- Frame display state (recon 0x1203a0-0x1203bb, 0x120258, charset) ---- */
UBYTE *g_font_base = NULL;      /* 0x120258 */
UBYTE  c64_charset_upper[0x400];/* 0x11d9c0 — filled at build/link (font ROM) */
UBYTE  c64_charset_lower[0x400];/* 0x11ddc0 */

UBYTE (*g_frame_getbyte)(void) = NULL; /* DAT_001203b6 */
UWORD  g_frame_pos = 0;         /* DAT_001203a0 */
UWORD  g_frame_len = 0;         /* DAT_001203a4 */
UBYTE  g_frame_eof = 0;         /* DAT_001203ac */
UBYTE *g_frame_capture = NULL;  /* DAT_001203ae */
UBYTE  g_frame_buf[0x100];      /* DAT_00120310 (0x8f read window) */
UWORD  g_frame_hdr_more = 0;    /* DAT_001203b2 */
UBYTE  g_rle_char = 0;          /* DAT_001203ba */
UBYTE  g_rle_run  = 0;          /* DAT_001203bb */

UBYTE  g_offscreen = 0;         /* DAT_0011d9a8 */
UBYTE *g_plane_src[4];          /* DAT_00120264 */
UBYTE *g_plane_dst[4];          /* DAT_0012028c */

/* Frame output buffer shared by login/mail/validate. */
char   g_frame_out[4096];       /* DAT_001220fc */
APTR   g_frame_out_end = NULL;  /* DAT_0012309c */

/* ---- Navigation / directory scratch ---- */
short  g_goto_page_no = 0;      /* DAT_0012157e */
char   g_link_code[16];         /* DAT_00121580 */
char   g_vote_choice[8];        /* DAT_0012164c */
char   g_extend_days[8];        /* DAT_00121648 */

/* ---- put_frame (publish) fields ---- */
short  g_put_life = 0;          /* DAT_0012161a */
short  g_put_page = 0;          /* DAT_00121612 */
short  g_put_sub  = 0;          /* DAT_00121616 */
char   g_put_type = 0;          /* DAT_00121605 */
char   g_put_name[24];          /* DAT_001215f4 */

/* ---- File transfer scratch ---- */
short  g_sel_row = 0;           /* DAT_001215c4 */
char   g_dl_filename[128];      /* DAT_001215c6 */
char   g_dl_header[16];         /* DAT_001215e8 */
APTR   g_dl_file = NULL;        /* DAT_001215f0 */
char   g_ul_name[128];          /* DAT_0012161e */
char   g_xfer_buf[4096];        /* DAT_001220fc region (reuses frame_out area on HW) */
char   g_ul_hdr[8];             /* DAT_00121640 */

/* ---- Mail fields ---- */
char        g_mail_subject[24];      /* DAT_00121658 */
char        g_mail_names[5 * 9];     /* DAT_00121669 */
char        g_mail_cmd[8] = "M";     /* DAT_0011ea5e — mail-enter command */
static const char *mail_title_str = "Mail Upload";
const char **g_mail_title = &mail_title_str; /* PTR_s_Mail_Upload_0011eae2 */

/* ---- Extra / abort signal + device-message logging ---- */
ULONG  g_extra_sig = 0;         /* DAT_00120104 */
BOOL   g_log_device_messages = 0;/* DAT_0011fd74 */

/* ---- Top-level UI bring-up state (launch.c / ui.c) ---- */
APTR   g_main_uport      = NULL; /* DAT_00120100 — main window UserPort         */
APTR   g_proc            = NULL; /* DAT_001200f0 — our Process (FindTask(NULL))  */
APTR   g_saved_windowptr = NULL; /* DAT_001200f4 — saved pr_WindowPtr           */
ULONG  g_tty_seg_bptr    = 0;    /* DAT_0012016c — CnetTty seg (BPTR*4+4)        */
BYTE   g_res_saved_level = 0;    /* DAT_001201ac — resource level saved for abort*/

/* The built menu strip + its command map. These MUST be contiguous: the event
 * loop dispatches a MENUPICK by calling menu_dispatch(&g_menu_pair, num), and
 * menu_dispatch reads the command map at (&g_menu_pair)[1]. In the original they
 * are the adjacent longs DAT_001201ae (menu list) and DAT_001201b2 (command map). */
APTR   g_menu_pair[2] = { NULL, NULL };

/* Last-click state for Intuition DoubleClick() detection in the event loop
 * (recon DAT_0011d548 secs / DAT_0011d54c micros / DAT_0011d550 window). */
ULONG  g_click_secs   = 0;      /* DAT_0011d548 */
ULONG  g_click_micros = 0;      /* DAT_0011d54c */
APTR   g_click_win    = NULL;   /* DAT_0011d550 */

/* Extra per-connection window/session handles cleared by disconnect()
 * (recon FUN_00102968). Named by their role in the pointer/title helpers
 * (FUN_001020ae / FUN_0010217a) and the session-alloc sites. */
APTR   g_edit_proc    = NULL;   /* DAT_00120168 — frame-editor semaphore owner */
APTR   g_edit_msgport = NULL;   /* DAT_0012013e — editor message port (PutMsg target) */

/*
 * Editor startup message (recon DAT_00120142/46). launch_editor PutMsg's this to the
 * CnetEditor child and waits for the reply. It is a Message header + payload; the
 * original lays it out as raw bytes in the small-data section, so we mirror that with
 * a byte buffer and offset accessors (avoids any C struct-padding mismatch):
 *   +0x00..0x0d  Message/Node header (mn_Node etc.)
 *   +0x0e  APTR  mn_ReplyPort   = g_editor_port
 *   +0x15  UBYTE status         (editor writes 0 = ready, non-zero = fail)
 *   +0x16  APTR  screen (in)    / editor's Process (out, -> g_edit_proc)
 *   +0x1a  APTR  font base (in) / semaphore owner (out, -> DAT_00120168 region)
 *   +0x1e  APTR  pr_CurrentDir  (our process's current dir)
 * mn_Length would normally be set too; the child only reads the fields above.
 */
UBYTE  g_editor_msg[0x24];      /* DAT_00120146 — CnetEditor startup message  */
APTR   g_logon_win_h  = NULL;   /* DAT_0011d570 — logon window handle        */
APTR   g_courier_win  = NULL;   /* DAT_00121650 — courier/mail window        */
APTR   g_dir2_win     = NULL;   /* DAT_00121698 — secondary directory window */
APTR   g_party_win    = NULL;   /* DAT_0011fd70 — partyline window           */
APTR   g_party_screen = NULL;   /* DAT_0011fda2 — screen ptr copy for party  */
UBYTE  g_party_active = 0;      /* DAT_0011fd74 — partyline active flag       */
APTR   g_sess_a       = NULL;   /* DAT_0011f120 — session buffer/handle A    */
APTR   g_sess_b       = NULL;   /* DAT_0011f124 — session buffer/handle B    */
APTR   g_sess_c       = NULL;   /* DAT_0011f128 — session buffer/handle C    */

/* ---- frame parser palette + misc ---- */
UBYTE  g_palette[16] = {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15}; /* DAT_0011e1c0 */
UBYTE *g_mem_src = 0;          /* DAT_001203a8 — in-memory frame read cursor */
/* DAT_00120170 is a setjmp/longjmp buffer (recon FUN_00101624=setjmp saves
 * d1-d7/a1-a7 + return PC here; FUN_00101638=longjmp restores them). The top level
 * (recon FUN_001029e6) does setjmp(g_jmpbuf); a transport abort longjmps back with a
 * non-zero code to trigger disconnect(). Sized for PC + 14 saved regs (15 longs). */
ULONG  g_jmpbuf[16];           /* DAT_00120170 — abort jmp_buf */
APTR   g_edit_frame = 0;       /* DAT_0011d080 — frame being published */
APTR   g_frame_out_ptr = 0;    /* DAT_0012309c — mail output write cursor */
