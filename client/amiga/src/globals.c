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
 * SysBase and DOSBase are supplied by the C runtime startup (SAS/C's c.o or vbcc's
 * startup.o), so we only define the two the client opens itself. */
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

/* ---- Serial parameters loaded from config (recon 0x12012c-0x120130) ---- */
UWORD  g_baud_up     = 0x4b;    /* 75   */
UWORD  g_baud_down   = 0x4b0;   /* 1200 */
UWORD  g_dev_param2e = 0;
ULONG  g_open_flags  = 4;
struct Device *g_cnet_device = NULL;

/* ---- Connection / session state ---- */
char   g_phone_number[64];      /* DAT_00120108 */
LONG   g_baud_setting = 0;      /* DAT_00120118 */
UWORD  g_state        = 0;      /* DAT_0011d070 */
UWORD  g_online       = 0;      /* DAT_0011d074 */
UWORD  g_state_shadow = 0xffff; /* DAT_0011d46e */
UWORD  g_online_shadow= 0xffff; /* DAT_0011d472 */
APTR   g_dir_page     = NULL;   /* DAT_0011d07c */
APTR   g_frame_page   = NULL;   /* DAT_0011d078 */

/* ---- Command / ack scratch ---- */
char   g_cmd_buf[256];          /* DAT_00121588 — shared command buffer */
char   g_ack_text[64];          /* DAT_0012021a — status text passed to acks */

/* ---- Login record fields ---- */
char   g_login_userid[16];      /* DAT_00120244 */
char   g_login_scratch[16];     /* DAT_0012024d */
UBYTE  g_frame_indent = 0;      /* placeholder for DAT_0011d078 indent check */

/* ---- Config block (0x36 bytes, recon &DAT_00120108 aliases the head) ---- */
UBYTE  g_config[0x36];

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
static const char *mail_title_str = "Mail Upload";
const char **g_mail_title = &mail_title_str; /* PTR_s_Mail_Upload_0011eae2 */

/* ---- Extra / abort signal + device-message logging ---- */
ULONG  g_extra_sig = 0;         /* DAT_00120104 */
BOOL   g_log_device_messages = 0;/* DAT_0011fd74 */
