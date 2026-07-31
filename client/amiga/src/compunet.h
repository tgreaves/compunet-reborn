/*
 * compunet.h — shared declarations for the reconstructed Amiga Compunet client.
 *
 * This is a from-scratch, idiomatic reconstruction of the original 1989 SAS/Lattice C
 * client (see client/amiga/vintage/), verified per-function against the decompiled
 * reference in client/amiga/vintage/tools/re/recon_annotated.c.
 *
 * Goal: readable and compilable with SAS/C (and vbcc m68k-amigaos as a proxy on
 * modern hosts). Uses standard Amiga system includes and real struct types instead
 * of the decompiler's raw offset arithmetic.
 *
 * Kickstart 1.3 target (the era of the original binary).
 *
 * The set of functions reconstructed here is not hand-picked: it is the auditable
 * application-function census in
 * client/amiga/vintage/tools/re/coverage-census.md (regenerate with
 * coverage_census.py). Every function that references a string or touches the
 * transport is covered.
 */
#ifndef COMPUNET_H
#define COMPUNET_H

#include <exec/types.h>
#include <exec/ports.h>
#include <exec/io.h>
#include <exec/nodes.h>

/*
 * CnetRequest — the request block the client uses with cnet.device.
 *
 * The original allocates 0x36 (54) bytes via CreateExtIO: a standard IOStdReq
 * (48 bytes) plus a 6-byte custom tail. It is NOT a stock IOExtSer (which is
 * larger). cnet.device defines its own compact request. We model it exactly so
 * the field offsets match the decompiled reference byte-for-byte.
 *
 * The client reuses the (serial-unused) io_Offset bytes as scratch:
 *   io_Offset byte 0 (+0x2c): serial flags / read: out_ser_flags / ack byte
 *   io_Offset byte 1 (+0x2d): status hi     / write: token
 *   io_Offset byte 2 (+0x2e): set to a config value at open (UWORD @ +0x2e)
 * Custom tail:
 *   +0x32 baud_up   (UWORD)  — 75   for Compunet's 1275 split-baud
 *   +0x34 baud_down (UWORD)  — 1200
 */
struct CnetRequest {
    struct IOStdReq io;         /* 0x00..0x2f — standard IO request (io_Offset @0x2c) */
    UWORD           baud_up;    /* 0x30/0x32 region — see accessor note below */
    UWORD           baud_down;  /* Compunet 1275 split baud: 75 up / 1200 down */
};
/*
 * The original touches sub-fields the stock structs don't name:
 *   +0x2c/+0x2d : two scratch bytes in io_Offset (serial flags/ack + status/token)
 *   +0x2e       : a UWORD in the high half of io_Offset (a config param at open)
 *   +0x32,+0x34 : the baud_up / baud_down UWORDs in the custom tail
 * Because these straddle io_Offset and the tail, the modules use the byte/word
 * accessor macros below (indexed from the request base) rather than relying on
 * struct padding.
 */
#define CNET_REQ_SIZE   0x36    /* size passed to CreateExtIO by the original */
#define REQ_SERFLAGS(r) (((UBYTE *)(r))[0x2c])   /* read: ack byte / ser flags */
#define REQ_STATUS(r)   (((UBYTE *)(r))[0x2d])   /* write: protocol token       */
/* req+0x2e holds a LONG POINTER to the modem-name string (recon open_transport 0x119398:
 * move.l a0,0x2e(a1), a0 = &g_config[0x14] = g_modem_name). It is NOT a 2-byte scalar. */
#define REQ_MODEMNAME(r) (*(char **)((UBYTE *)(r) + 0x2e))
#define REQ_BAUD_UP(r)  (*(UWORD *)((UBYTE *)(r) + 0x32))
#define REQ_BAUD_DN(r)  (*(UWORD *)((UBYTE *)(r) + 0x34))

/* cnet.device command codes (the io_Command values the client writes). */
#define CNET_CMD_READ    2      /* recon: io_Command = 2 (also 0xb via serial_io_c) */
#define CNET_CMD_WRITE   3      /* recon: io_Command = 3 */

/* ------------------------------------------------------------------ *
 *  Application-layer protocol (matches docs/PROTOCOL.md)
 * ------------------------------------------------------------------ *
 * The client sends single-letter commands in COM frames (token 0x43) and raw
 * data in DAT frames (token 0x22), then waits for the ack byte '@' (0x40).
 * These are the same commands and ack the C64 client uses.
 */
#define TOKEN_DAT   0x22       /* raw data block            */
#define TOKEN_COM   0x43       /* 'C' — command frame        */
#define ACK_OK      '@'        /* 0x40 — command accepted    */
#define ACK_MSG     'A'        /* 0x41 — accepted with message */
#define ACK_ERR     'B'        /* 0x42 — error with message  */

/* ------------------------------------------------------------------ *
 *  Transport layer — cnet.device serial I/O
 * ------------------------------------------------------------------ *
 * io_Error values on the request (read at +0x1f). VERIFIED against the relocated
 * disasm of serial_read (0x119744) and serial_io_c (0x119834):
 *   0  = SUCCESS (raw I/O completes; serial_io_c then classifies the ack byte)
 *   9  = carrier lost           -> "Carrier lost",  set_connection_error(9)
 *   7  = comms error            -> "Comms problem", set_connection_error(7)
 *   any other non-zero          -> also "Comms problem"
 * (An earlier reconstruction wrongly documented 7 as "expected/normal" and treated
 * it as success — the disassembly shows 7 is the error path.)
 */
#define CNET_ERR_OK        0   /* success */
#define CNET_ERR_CARRIER   9   /* carrier lost */
#define CNET_ERR_COMMS     7   /* comms error */

/* Transport request/port state (was g_read_req/g_write_req/g_device_port etc). */
extern struct CnetRequest *g_read_req;   /* read  request (CMD_READ)  */
extern struct CnetRequest *g_write_req;  /* write request (CMD_WRITE) */
extern struct MsgPort     *g_device_port;/* shared device reply port     */
extern struct MsgPort     *g_read_port;  /* read-completion reply port   */
extern struct MsgPort     *g_write_port; /* write-completion reply port  */
extern ULONG               g_device_sig; /* 1 << device_port mp_SigBit   */
extern ULONG               g_read_sig;   /* 1 << read_port   mp_SigBit   */
extern ULONG               g_write_sig;  /* 1 << write_port  mp_SigBit   */

/* serial_write / serial_read: submit one request and wait for completion,
 * servicing the other ports' signals meanwhile. serial_io_c additionally
 * classifies the '@'/'A'/'B' ack and returns it. */
LONG serial_write(APTR data, ULONG length, UBYTE status_hi, UBYTE ser_flags);
LONG serial_read(APTR data, ULONG length,
                 UBYTE *out_ser_flags, UBYTE *out_status_hi, ULONG *out_actual);
UBYTE serial_io_c(const char *status_text);   /* was FUN_0011979e — command ack */
void  send_dat_packet(APTR frame);            /* was FUN_00108254 */

/* Result codes from open_transport() (was do_connect's status switch):
 *   0 = success
 *   1 = resource allocation / OpenDevice failure ("Can't open cnet.device")
 *   3 = device opened but reported a bad version/unit (io_Device check) */
#define XPORT_OK        0
#define XPORT_FAIL      1
#define XPORT_BADVER    3

char open_transport(void);   /* was FUN_001192b6 */
LONG do_connect(void);       /* was FUN_0010343c — dial + login sequence */

/* ------------------------------------------------------------------ *
 *  Resource-tracked allocation wrappers (SAS/C-style auto-cleanup).
 *  The original registers each created resource with an unwind list so a
 *  single cleanup_resources() frees everything on error/exit.
 * ------------------------------------------------------------------ */
struct MsgPort  *create_port_tracked(char *name, LONG pri);      /* was thunk_FUN_0011a75c */
struct CnetRequest *create_extio_tracked(struct MsgPort *port, ULONG size); /* was thunk_FUN_0011a80e */
BOOL             open_device_tracked(const char *name, ULONG unit,
                                     struct IORequest *req, ULONG flags); /* was thunk_FUN_0011a2e8 */
BYTE             cleanup_resources(void);                        /* was thunk_FUN_0011a0b0 (returns new level) */
void             cleanup_all_resources(void);                   /* FUN_0011a0f0 — free entire list */
void             resource_unregister(void (*fn)(), APTR arg1);   /* FUN_0011a19c */
BYTE             resource_mark(void);                            /* was thunk_FUN_0011a000 (returns new level) */
void             resource_commit(void);                          /* was thunk_FUN_0011a00a */
void             resource_register_free(void (*fn)(), APTR arg1, APTR arg2); /* FUN_0011a16c */

/* ------------------------------------------------------------------ *
 *  Status / UI helpers
 * ------------------------------------------------------------------ *
 * show_status_message(code, text): the original takes a status code (1 = info,
 * 0x41/0x42 = message/error line) and a text string, and dispatches to the
 * matching status-line renderer via a jump table.
 */
void show_status_message(UBYTE code, const char *text);
void set_connection_error(int code);   /* was thunk_FUN_00101638(&DAT_00120170,n) */

/* ------------------------------------------------------------------ *
 *  Frame display (PETSCII) — frame.c
 * ------------------------------------------------------------------ *
 * A "frame page" is an 40x24 cell buffer with a small header; see FramePage.
 * render_char converts a PETSCII byte to a screen cell (byte>>5 dispatch, the
 * canonical PETSCII->C64 screencode mapping); blit_char_cell draws one cell from
 * the C64 font; build_font builds the 8x8 font (normal + reverse, upper + lower)
 * from the embedded C64 charset. Frame bytes arrive RLE-compressed (0x06 = space
 * run, 0x07 = char run), the same scheme as the server SEQ frames.
 */
void  render_char(UBYTE ch, APTR page);              /* was FUN_001054f8 */
void  blit_char_cell(WORD row, WORD col, APTR page); /* was FUN_00107000 */
LONG  build_font(void);                              /* was FUN_00106000 */
UBYTE read_frame_byte(void);                         /* was FUN_0010800c */
char  frame_rle_getchar(void);                       /* was FUN_00108086 */

extern UBYTE *g_font_base;         /* was g_font_base (0x120258)          */

/* ------------------------------------------------------------------ *
 *  Navigation / directory commands — navigate.c, directory.c
 * ------------------------------------------------------------------ */
LONG goto_page(void);        /* P — was FUN_0010a1e2 */
LONG link_follow(APTR gadget);/* L — was FUN_001098e8 */
LONG link_goto(void);        /* L — was FUN_0010a310 */
void parse_directory_frame(APTR page); /* was FUN_00109a5e — parse a directory frame */
void directory_repaint(APTR page);     /* was FUN_001096c8 — repaint selected row     */
LONG dir_select(APTR gadget, LONG mode);/* was FUN_0010935a — selection gadget handler*/
LONG vote(void);             /* V — was FUN_0010c510 */
LONG extend_life(void);      /* X — was FUN_0010c428 */
LONG account(void);          /* ACCOUNT — was FUN_0010c582 */
LONG put_frame(void);        /* U (publish) — was FUN_0010c2f8 */
void set_connection_state(void); /* was FUN_001023ec */

/* ------------------------------------------------------------------ *
 *  File transfer — transfer.c
 * ------------------------------------------------------------------ */
LONG download_check(void);   /* D — was FUN_0010b730 */
LONG upload_file(void);      /* U + DAT blocks — was FUN_0010c0ee */

/* ------------------------------------------------------------------ *
 *  Mail — mail.c
 * ------------------------------------------------------------------ */
LONG mail_submit(void);      /* was FUN_0010e188 */
LONG mail_read(void);        /* was FUN_0010e468 */
LONG mail_upload_mode(void); /* was FUN_0010f09e */
LONG id_check_mode(void);    /* was FUN_0010f116 */

/* ------------------------------------------------------------------ *
 *  Config / launch — config.c, launch.c
 * ------------------------------------------------------------------ */
LONG load_config(void);      /* was FUN_00102000 */
LONG launch_editor(void);    /* was FUN_001025de */
void launch_tty(void);       /* was FUN_001026ae */

/* Workbench-launch handling (wbstartup.c): wb_startup_begin() at program start (cwd = the
 * icon's drawer + take the WBStartup msg), wb_startup_end() at exit (restore + reply). */
void wb_startup_begin(void);
void wb_startup_end(void);
extern APTR g_wb_startup;    /* struct WBStartup * if launched from Workbench, else NULL */
void client_main(void);      /* was FUN_001029e6 — top-level: launch + setjmp + loop */
void event_loop(void);       /* was FUN_00102814 — Intuition IDCMP dispatch loop     */
void disconnect(void);       /* was FUN_00102968 — abort/disconnect teardown         */
LONG menu_dispatch(APTR menu_pair, UWORD number); /* was FUN_0011b478 */
APTR build_menu_strip(APTR spec);                 /* was FUN_0011b000 */

/* ------------------------------------------------------------------ *
 *  Client global state (the DAT_* the modules share). Defined in globals.c.
 *  Names reflect their observed role; see recon_annotated.c for raw addresses.
 * ------------------------------------------------------------------ */
/* The single config block (globals.c). The original keeps phone/baud/flags/userid in
 * ONE 0x36-byte record at 0x120108; these accessors alias into it at the verified
 * field offsets so config-file load/save, the device baud, and the Settings dialog all
 * share the same memory (recon: save writes 0x36 bytes from 0x120108; open_transport
 * reads baud from block+0x24). */
extern UBYTE  g_config[];        /* DAT_00120108 — the 0x36-byte config block */
#define g_phone_number  ((char  *)(g_config + 0x00)) /* DAT_00120108 dial string   */
#define g_baud_setting  (*(LONG  *)(g_config + 0x10)) /* DAT_00120118 link rate     */
#define g_modem_name    ((char  *)(g_config + 0x14)) /* DAT_0012011c modem name    */
#define g_baud_up       (*(UWORD *)(g_config + 0x24)) /* DAT_0012012c 75            */
#define g_baud_down     (*(UWORD *)(g_config + 0x26)) /* DAT_0012012e 1200          */
#define g_open_flags    (*(UWORD *)(g_config + 0x28)) /* DAT_00120130 OpenDevice fl */
#define g_editor_frames (*(UWORD *)(g_config + 0x2a)) /* DAT_00120132 "Editor frames" ring size
                                                        * (the Setup field; NOT serial data bits) */
#define g_cfg_userid    ((char  *)(g_config + 0x2c)) /* DAT_00120134 userid        */

/* editor_set_frame_count — recon FUN_00114050 (see dispatch.c). Sends editor opcode 5. */
extern LONG editor_set_frame_count(UWORD count);
extern LONG  g_state;           /* DAT_0011d070 — connection state enum    */
extern LONG  g_online;          /* DAT_0011d074 — online flag              */
extern APTR   g_dir_page;        /* DAT_0011d07c — current directory page   */
extern APTR   g_frame_page;      /* DAT_0011d078 — current frame page       */
extern char   g_cmd_buf[];       /* DAT_00121588 — shared command scratch   */
extern char   g_ack_text[];      /* DAT_0012021a — status text for acks     */

#endif /* COMPUNET_H */
