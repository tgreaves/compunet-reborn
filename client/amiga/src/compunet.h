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
#define REQ_PARAM2E(r)  (*(UWORD *)((UBYTE *)(r) + 0x2e))
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
 * io_Error values observed on the request:
 *   7  = expected/normal completion       (recon: '\a')
 *   9  = carrier lost                      (recon: '\t')
 *   0  = ok / no error
 * anything else is treated as "Comms problem".
 */
#define CNET_ERR_OK        0
#define CNET_ERR_EXPECTED  7   /* normal completion */
#define CNET_ERR_CARRIER   9   /* carrier lost */

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
void             cleanup_resources(void);                        /* was thunk_FUN_0011a0b0 */
void             resource_mark(void);                            /* was thunk_FUN_0011a000 */
void             resource_commit(void);                          /* was thunk_FUN_0011a00a */

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
extern UBYTE  c64_charset_upper[]; /* was c64_charset_upper (0x11d9c0)    */
extern UBYTE  c64_charset_lower[]; /* was c64_charset_lower (0x11ddc0)    */

/* ------------------------------------------------------------------ *
 *  Navigation / directory commands — navigate.c, directory.c
 * ------------------------------------------------------------------ */
LONG goto_page(void);        /* P — was FUN_0010a1e2 */
LONG link_follow(APTR gadget);/* L — was FUN_001098e8 */
LONG link_goto(void);        /* L — was FUN_0010a310 */
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

/* ------------------------------------------------------------------ *
 *  Client global state (the DAT_* the modules share). Defined in globals.c.
 *  Names reflect their observed role; see recon_annotated.c for raw addresses.
 * ------------------------------------------------------------------ */
extern char   g_phone_number[];  /* DAT_00120108 — modem dial string       */
extern LONG   g_baud_setting;    /* DAT_00120118 — configured link rate     */
extern UWORD  g_state;           /* DAT_0011d070 — connection state enum    */
extern UWORD  g_online;          /* DAT_0011d074 — online flag              */
extern APTR   g_dir_page;        /* DAT_0011d07c — current directory page   */
extern APTR   g_frame_page;      /* DAT_0011d078 — current frame page       */
extern char   g_cmd_buf[];       /* DAT_00121588 — shared command scratch   */
extern char   g_ack_text[];      /* DAT_0012021a — status text for acks     */

#endif /* COMPUNET_H */
