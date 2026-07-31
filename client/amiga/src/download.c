/*
 * download.c — the "D" (download) command subsystem (reconstructed).
 *
 * download_check (FUN_0010b730) is the D-command entry reached from the directory
 * action dispatch. It builds "D%02d" for the selected row and dispatches on the row's
 * TYPE byte through a 6-way jump table (verified from the raw table at 0x10b780):
 *
 *   'T'  text/frame page   -> download_text     (FUN_00113000)
 *   'F'  IFF picture        -> action_download_run(FUN_0010b50e) -> IFF viewer
 *   'P','S' program         -> download_program (FUN_0010b36e) -> download_receive
 *   'A'  action/executable  -> action_download   (FUN_0010b380, in transfer.c)
 *   'L'  link/sub-program    -> download_link     (FUN_0010b66a)
 *   else                     -> "Can't download this"
 *
 * EVERY branch — including 'T' — is first gated by download_charged_prompt
 * (FUN_0010b000): a charged page shows "WARNING - CHARGED ITEM / Buy for £<price>?"
 * and only proceeds if the user confirms. (The earlier transfer.c reconstruction of
 * download_check was an invented 3-way 'C'/'S'/'A' switch with no charged gate —
 * replaced by this. This comment previously claimed 'T' was ungated, and the code
 * matched the comment rather than the binary: a charged text page billed silently.)
 *
 * The 'F' path decodes a streamed IFF/ILBM image live: action_download_run feeds each
 * downloaded byte to iff_feed_byte (FUN_00111024), a chunk state machine that parses
 * FORM/ILBM/BMHD/CMAP/BODY, opens a custom screen sized to the picture, and blits the
 * image row-by-row (uncompressed or ByteRun1) as it arrives.
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <intuition/screens.h>
#include <graphics/gfx.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>
#include <clib/graphics_protos.h>
#include <string.h>
#include <stdio.h>

#include "compunet.h"

#define STATE_GOTO 2

extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

extern APTR  g_screen;                   /* DAT_001200f8 */
extern APTR  g_dir_page;                 /* DAT_0011d07c */
extern APTR  g_frame_page;               /* DAT_0011d078 */
extern short g_sel_row;                  /* DAT_001215c4 */
extern APTR  g_dl_file;                  /* DAT_001215f0 */
extern char  g_dl_header[];              /* DAT_001215e8 */
extern BOOL  g_tcp_mode;                 /* net.h — TCP transport active */
extern char  g_xfer_buf[];               /* DAT_001220fc */
extern ULONG g_tty_seg_bptr;             /* DAT_0012016c — CnetTty viewer entry */
extern ULONG g_jmpbuf[];                 /* DAT_00120170 — abort jmp_buf         */

/* Transport-fed frame reader state (frame.c / globals.c). */
extern LONG  g_frame_pos;               /* DAT_001203a0 */
extern LONG  g_frame_len;               /* DAT_001203a4 */
extern UBYTE  g_frame_eof;               /* DAT_001203ac */
extern UBYTE *g_frame_capture;           /* DAT_001203ae */
extern UBYTE  read_frame_byte(void);     /* FUN_0010800c */

/* Helpers reconstructed elsewhere. */
extern APTR  load_file_to_mem(const char *name);           /* FUN_0011a41e (Lock+Examine+Read) */
extern ULONG mem_block_size(APTR p);                       /* FUN_0011a26c */
extern void  free_tracked(APTR p);                          /* FUN_0011a238 */
extern void  file_close(APTR fh);                           /* thunk FUN_0011a3fe */
extern LONG  file_write(APTR fh, APTR buf, ULONG len);      /* thunk FUN_0012804c */
extern LONG  download_filename_prompt(void);                /* FUN_0010b06e */
extern LONG  retry_dialog(const char *title, const char *body); /* FUN_001104a6 */
extern LONG  file_download_xfer(void);                      /* FUN_0010b174 (transfer.c) */
extern LONG  download_receive(void);                        /* FUN_0010b2e6 (transfer.c) */
extern LONG  action_download(void);                         /* FUN_0010b380 (transfer.c) */
extern APTR  frame_display(APTR page, APTR out);            /* FUN_0010818a */
extern void  frame_display_done(APTR out, APTR len);        /* FUN_0011754e */
extern APTR  alloc_tracked(ULONG size, ULONG flags);        /* FUN_0011a1ee */
extern APTR  open_screen_tracked(APTR ns);                  /* FUN_0011a4e0 */
extern APTR  open_window_tracked(APTR nw);                  /* FUN_0011a534 */
extern void  close_window_tracked(APTR win);                /* FUN_0011a568 (ui.c) */
extern void  close_screen_tracked(APTR scr);                /* FUN_0011a514 (ui.c) */
extern void  load_screen_palette(APTR vp, APTR ct, ULONG n);/* GfxBase.LoadRGB4 FUN_0012a01c */
extern void  set_connection_error(int code);               /* longjmp FUN_00101638 */

/* ================================================================= *
 *  IFF DIAGNOSTIC TRACE  (#129 — temporary instrumentation)
 * ================================================================= *
 * ⚠ NOT part of the reconstruction. The original has none of this, and it must
 * come out (or go behind a build flag) once the IFF display defect is found.
 *
 * Why it exists: on a real Amiga a type-`F` download completes perfectly — the
 * saved file is byte-for-byte correct — and no picture appears. iff_feed_byte
 * begins `if (g_iff_error) return;`, so any failure inside iff_setup silences the
 * decoder for the rest of the transfer while the file still writes. There is no
 * message and no console, so the failure is invisible from outside.
 *
 * The trace goes to "CompunetDebug.log" as a RELATIVE path, opened once at startup
 * (see main()). Relative is deliberate: wb_startup_begin() sets the current directory
 * to the icon's drawer, so the file lands beside the executable with no knowledge of
 * the Amiga's volume names. Opening it at startup rather than mid-download means a
 * run that never reaches the transfer still leaves evidence — the first version
 * logged nothing at all when the dispatch stopped early, which proved only that it
 * had stopped somewhere before the logging began.
 */
extern char  g_dl_filename[];                               /* DAT_001215c6 */
extern APTR  file_open_write(const char *name, ULONG mode); /* thunk */

extern APTR  file_open_append(const char *name);            /* dosio.c (#129) */

#define CNET_LOGFILE "CompunetDebug.log"
static char g_iff_logbuf[160];
static ULONG g_iff_bytes_fed;      /* how many BODY/chunk bytes reached the decoder */

/* ⚠ OPENED AND CLOSED PER LINE, deliberately. Holding the handle open for the session
 * left every write buffered inside the emulator: the host saw a stale file, could not
 * delete it ("device or resource busy"), and a whole test round was read against the
 * PREVIOUS run's trace. Slow is irrelevant here; visible and crash-proof is not. */
void cnet_log_open(void)
{
    APTR fh = file_open_write(CNET_LOGFILE, 0x3ee);   /* truncate once per run */
    if (fh) file_close(fh);
}

void cnet_log(const char *s)
{
    APTR fh = file_open_append(CNET_LOGFILE);
    if (!fh) return;
    file_write(fh, (APTR)s, (ULONG)strlen(s));
    file_write(fh, (APTR)"\n", 1);
    file_close(fh);
}

/* Row-type table: 0x66 bytes per row, type byte at +0x828 (recon), price at +0x82e. */
#define ROW_TYPE(p, r)  (*(char *)((UBYTE *)(p) + (r) * 0x66 + 0x828))
#define ROW_PRICE(p, r) ((char  *)((UBYTE *)(p) + (r) * 0x66 + 0x82e))

/* ================================================================= *
 *  download_charged_prompt — recon FUN_0010b000
 * ================================================================= *
 * Read the selected row's price string (dir + row*0x66 + 0x82e). Empty -> free, return 1.
 * A single leading space -> skip it (free). Otherwise sprintf "Buy for £%s?" and pop the
 * yes/no requester titled "WARNING - CHARGED ITEM"; return 1 only if the user confirms.
 */
LONG download_charged_prompt(void)
{
    char *price = ROW_PRICE(g_dir_page, g_sel_row);
    char  msg[0x1c];

    for (;;) {
        char c = *price;
        if (c == '\0')                       /* no price -> free */
            return 1;
        if (c == ' ') {                      /* skip leading spaces */
            price++;
            continue;
        }
        sprintf(msg, "Buy for \xa3%s?", price);   /* 0xa3 = '£' */
        return retry_dialog("WARNING - CHARGED ITEM", msg);
    }
}

/* ================================================================= *
 *  'T' text-frame download — recon FUN_00113000 / FUN_00113062 / FUN_001130ca
 * ================================================================= *
 * download_text sends "D%02d" (already in g_cmd_buf), on ack '@' displays the returned
 * frame into the frame window via frame_display + frame_display_done. If more frames
 * follow (g_frame_hdr_more via frame_display's return being non-empty) it sets state=3
 * so the top-level loop re-invokes download_text_continue for the next page.
 */
extern LONG g_frame_hdr_more;           /* DAT_001203b2 — more-frames flag */
extern APTR  g_frame_out_end;            /* DAT_0012309c — frame output cursor */
extern char  g_frame_out[];              /* DAT_001220fc region output buffer */
extern char  g_ack_text[];               /* DAT_0012021a */
extern char  g_cmd_buf[];                /* DAT_00121588 */

/* download_text — recon FUN_00113000: initial "D" page fetch + display. */
LONG download_text(void)
{
    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK)
        return 0;
    g_frame_out_end = frame_display(g_frame_page, g_frame_out);
    frame_display_done(g_frame_out, g_frame_out_end);
    if (g_frame_hdr_more != 0)
        g_state = 3;                         /* more pages: continue */
    return 1;
}

/* download_text_continue — recon FUN_00113062: fetch + display the NEXT page. Sends the
 * continue command in the blob at 0x11f7cc; on a non-'@' ack it drops back to state 2. */
LONG download_text_continue(void)
{
    serial_write(DATA(0x11f7cc), strlen((char *)DATA(0x11f7cc)), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        g_state = STATE_GOTO;
        return 0;
    }
    g_frame_out_end = frame_display(g_frame_page, g_frame_out);
    frame_display_done(g_frame_out, g_frame_out_end);
    if (g_frame_hdr_more == 0)
        g_state = STATE_GOTO;
    return 1;
}

/* download_text_loop — recon FUN_001130ca: pump download_text_continue while state==3. */
LONG download_text_loop(void)
{
    LONG r = 0;
    while (g_state == 3)
        r = download_text_continue();
    return r;
}

/* ================================================================= *
 *  IFF/ILBM decoder — recon FUN_00111000 family
 * ================================================================= */
extern LONG   g_iff_state, g_iff_error, g_iff_skip, g_iff_need;
extern UBYTE *g_iff_field, *g_iff_field_wr;
extern UBYTE  g_iff_chunk[];             /* 0x1216e4: [0..3]=id [4..7]=len; BMHD body @+8 */
extern UBYTE  g_cmap_raw[];              /* 0x121700 */
extern LONG   g_cmap_ncolors;
extern UWORD  g_cmap[];                  /* 0x121764 */
extern UBYTE  g_iff_compress;            /* 0x1217a4 */
extern LONG   g_brun_state;              /* 0x1217a6 */
extern UWORD  g_iff_rowbytes, g_iff_nplanes, g_iff_lastmask;
extern UBYTE *g_iff_planeptr[];          /* 0x1217b0 */
extern UWORD  g_iff_row, g_iff_plane, g_iff_planeleft, g_brun_run;
extern UBYTE *g_iff_wr;                  /* 0x1217d4 */
extern UBYTE  g_iff_rowimg[];            /* 0x1217d8 — temp Image for per-row DrawImage */

/* BMHD gather fields land at g_iff_chunk+8 (0x1216ec) — a standard BitMapHeader. */
#define BMHD    ((UBYTE *)g_iff_chunk + 8)
#define BMHD_W      (*(UWORD *)(BMHD + 0x00))
#define BMHD_H      (*(UWORD *)(BMHD + 0x02))
#define BMHD_NPLANES (*(UBYTE *)(BMHD + 0x08))
#define BMHD_COMPRESS (*(UBYTE *)(BMHD + 0x0a))
#define BMHD_PAGEW  (*(UWORD *)(BMHD + 0x10))
#define BMHD_PAGEH  (*(UWORD *)(BMHD + 0x12))
/* chunk length is a big-endian LONG at g_iff_chunk+4. */
#define CHUNK_LEN   (*(LONG *)(g_iff_chunk + 4))
#define CHUNK_LEN_ODD (g_iff_chunk[7] & 1)

/* Screen/Window/BitMap handles + templates live in the blob. */
#define IFF_BITMAP  (*(APTR *)DATA(0x11f120))
#define IFF_SCREEN  (*(struct Screen **)DATA(0x11f124))
#define IFF_WINDOW  (*(struct Window **)DATA(0x11f128))

/* iff_free_all — recon FUN_00111270: tear down the decoder's Window, Screen, and the
 * BitMap-handle slot, in that order (each guarded). Called at the start of iff_setup so
 * a re-decode never leaks the previous image's screen. */
static void iff_free_all(void)
{
    /* ⚠ THE *TRACKED* CLOSES, and the bitmap is genuinely FREED. Ground truth,
     * FUN_00111270, is three calls through veneers that resolve to the tracked
     * helpers — not the raw Intuition functions:
     *   111276  $2128 (window) -> $1117aa -> $11a568  close_window_tracked
     *   11128a  $2124 (screen) -> $11179e -> $11a514  close_screen_tracked
     *   11129e  $2120 (bitmap) -> $1117b0 -> $11a238  free_tracked
     * We called raw CloseWindow/CloseScreen, which close the object but LEAVE the
     * node that open_*_tracked registered — so exit cleanup closed each a second
     * time (the "Recoverable Error" / crash on QUIT), and the chip row buffer was
     * merely forgotten rather than freed. */
    if (IFF_WINDOW)  { close_window_tracked(IFF_WINDOW);   IFF_WINDOW = NULL; }
    if (IFF_SCREEN)  { close_screen_tracked(IFF_SCREEN);   IFF_SCREEN = NULL; }
    if (IFF_BITMAP)  { free_tracked(IFF_BITMAP);           IFF_BITMAP = NULL; }
}

/* iff_free_bitmap — recon FUN_001116ee: free the decoder row buffer (the streamed
 * download path closes only the window; the screen/bitmap live in the tracked-resource
 * list and are released at connection teardown). */
static void iff_free_bitmap(void)
{
    /* ⚠ THIS FREES THE ROW BUFFER. IT DOES NOT CLOSE THE WINDOW.
     *
     * Reconstructed as "iff_free_window" (CloseWindow) — wrong, and it is why a
     * decoded picture vanished the instant it finished: the streamed path calls this
     * at the END of the download, so the viewer was torn down at the exact moment the
     * image was complete. Ground truth, FUN_001116ee:
     *   1116ee  tst.l  $2120(a4)     ; IFF_BITMAP  (NOT $2128 = IFF_WINDOW)
     *   1116f8  jsr    $1117b0(pc)   ; -> $11a238 = free_tracked
     *   1116fe  clr.l  $2120(a4)
     * $1117b0 is the same veneer iff_free_all uses for the bitmap, and a DIFFERENT one
     * from the window ($1117aa) and screen ($11179e) — so the operand and the callee
     * both say bitmap. The original leaves the picture's screen AND window open after
     * the transfer; they are released by iff_free_all on the next picture, or at
     * connection teardown. */
    if (IFF_BITMAP) {
        free_tracked(IFF_BITMAP);
        IFF_BITMAP = NULL;
    }
}

/* iff_init — recon FUN_00111000: reset the decoder to expect the 8-byte FORM header. */
void iff_init(void)
{
    g_iff_state    = 1;
    g_iff_need     = 8;
    g_iff_skip     = 0;
    g_iff_error    = 0;
    g_iff_field    = g_iff_chunk;
    g_iff_field_wr = g_iff_chunk;
}

/* iff_body_start — recon FUN_00111526: begin BODY. Point the plane write cursor at
 * plane 0's row buffer, arm the per-plane byte counter, pick uncompressed (state 8) or
 * ByteRun1 (state 9) row decoding. */
static void iff_body_start(void)
{
    g_iff_wr        = g_iff_planeptr[0];
    g_iff_planeleft = g_iff_rowbytes;
    g_iff_plane     = 0;
    g_iff_row       = 0;
    g_iff_state     = g_iff_compress ? 9 : 8;
    g_brun_state    = 0;
}

/* iff_draw_row — the per-row flush shared by both row decoders: DrawImage one screen
 * row (Height 1, all planes interleaved at the shared buffer) then advance. Matches
 * the recon's DrawImage(win->RPort, &rowImage, 0, row) call at 0x11155c / 0x1115e6. */
static void iff_draw_row(void)
{
    DrawImage(IFF_WINDOW->RPort, (struct Image *)g_iff_rowimg, 0, g_iff_row);
    g_iff_row++;
    g_iff_plane = 0;
    g_iff_wr    = g_iff_planeptr[0];
    g_iff_planeleft = g_iff_rowbytes;
}

/* iff_setup — recon FUN_001112ae: BMHD complete. Reject compression>1, size the blob
 * NewScreen from the picture, allocate the interleaved 1-row×nplanes bitmap buffer, set
 * up the per-plane pointers, the last-word mask, and the reusable per-row Image, then
 * open the screen + window. Sets g_iff_error on any failure. */
static void iff_setup(void)
{
    UWORD w, h;
    UWORD nplanes, i;
    ULONG rowwords, planebytes;
    UBYTE *base;
    struct Image *img = (struct Image *)g_iff_rowimg;
    struct NewScreen *ns = (struct NewScreen *)DATA(0x11f138);

    iff_free_all();                          /* recon FUN_00111270: full teardown first */

    sprintf(g_iff_logbuf, "BMHD w=%ld h=%ld planes=%ld compress=%ld pageW=%ld pageH=%ld",
            (long)BMHD_W, (long)BMHD_H, (long)BMHD_NPLANES,
            (long)BMHD_COMPRESS, (long)BMHD_PAGEW, (long)BMHD_PAGEH);
    cnet_log(g_iff_logbuf);

    g_iff_compress = BMHD_COMPRESS;
    if (g_iff_compress > 1) {                 /* only 0 / 1 (ByteRun1) supported */
        cnet_log("FAIL: compression > 1");
        g_iff_error = 1;
        return;
    }

    /* Screen dimensions from the BMHD page size (recon 0x1112d0..0x111318). */
    w = BMHD_PAGEW;
    if (w <= 0x140) {
        ns->ViewModes = 0;
        ns->Width = 0x140;
    } else {
        ns->ViewModes = 0x8000;               /* HIRES */
        ns->Width = 0x280;
    }
    h = BMHD_PAGEH;
    if (h <= 0x100) {
        ns->Height = 0x100;
    } else {
        ns->ViewModes |= 4;                   /* LACE */
        ns->Height = 0x200;
    }
    ns->Depth = BMHD_NPLANES;

    /* rowbytes = ceil(w/16) words * 2 bytes; allocate nplanes rows interleaved. */
    rowwords = ((ULONG)BMHD_W + 0xf) >> 4;
    g_iff_rowbytes = (UWORD)(rowwords * 2);
    nplanes = BMHD_NPLANES;
    planebytes = (ULONG)g_iff_rowbytes * nplanes;

    sprintf(g_iff_logbuf, "screen w=%ld h=%ld depth=%ld modes=$%lx rowbytes=%ld chip=%ld",
            (long)ns->Width, (long)ns->Height, (long)ns->Depth,
            (long)(UWORD)ns->ViewModes, (long)g_iff_rowbytes, (long)planebytes);
    cnet_log(g_iff_logbuf);

    base = alloc_tracked(planebytes, 2 /*MEMF_CHIP*/);
    IFF_BITMAP = (APTR)base;                  /* recon stores at 0x2120 */
    if (base == NULL) {
        cnet_log("FAIL: no chip RAM for the row buffer");
        g_iff_error = 1;
        return;
    }
    cnet_log("ok: chip row buffer");

    /* Reusable per-row Image (recon 0x11136e..0x1113b8). */
    img->LeftEdge = 0;
    img->TopEdge  = 0;
    img->Width    = BMHD_W;
    img->Height   = 1;
    img->Depth    = nplanes;
    img->ImageData = (UWORD *)base;
    /* PlanePick / PlaneOnOff (recon 0x47e6/0x47e7): 0x3f >> (6 - nplanes), clamped. */
    img->PlanePick  = (nplanes == 6) ? 0x3f : (UBYTE)(0x3f >> (6 - nplanes));
    img->PlaneOnOff = 0;
    img->NextImage  = NULL;

    /* Last-word mask for the final partial word of each plane row (recon 0x1113bc:
     * move.l #$ffff0000,d2; asr.l (w&0xf),d2 — an ARITHMETIC shift so the sign bit
     * replicates. Use a signed long literal to guarantee asr, not lsr. */
    {
        LONG m = (LONG)0xffff0000 >> (BMHD_W & 0xf);
        g_iff_lastmask = (UWORD)m;
    }
    g_iff_nplanes = nplanes;

    /* Per-plane row-start pointers into the interleaved buffer (recon 0x1113d0 loop). */
    for (i = 0; i < nplanes; i++)
        g_iff_planeptr[i] = base + (ULONG)i * g_iff_rowbytes;

    /* Open the screen + window (recon 0x111408 / 0x111458). */
    IFF_SCREEN = (struct Screen *)open_screen_tracked(DATA(0x11f138));
    if (IFF_SCREEN == NULL) {
        cnet_log("FAIL: OpenScreen returned NULL");
        iff_free_all();
        g_iff_error = 1;
        return;
    }
    cnet_log("ok: screen opened");

    /* ⚠ THE PICTURE SCREEN OPENS *BEHIND*, ON PURPOSE — AND MUST BE PULLED FORWARD.
     *
     * The blob's NewScreen at 0x11f138 has Type = 0x008F = CUSTOMSCREEN | SCREENBEHIND,
     * and iff_setup overwrites only Width/Height/Depth/ViewModes — never Type. So
     * OpenScreen deliberately creates the screen at the BACK of the display, and the
     * original's explicit ScreenToFront is the only thing that ever makes it visible.
     *
     * Omitting these two calls is why a picture stayed invisible even once the decoder
     * ran to completion: the bitmap was allocated, the palette loaded and all 256 rows
     * DrawImage'd correctly onto a screen parked permanently behind the Compunet one.
     * Nothing errors, so there is no symptom to chase — the log said rows=256, error=0.
     *
     * Ground truth, FUN_001112ae, between the OpenScreen NULL check and the NewWindow
     * patch below:
     *   111426  pea $40.w / clr.l -(a7) / move.l $2124(a4),-(a7)
     *   111430  jsr $111798(pc)   -> $12b0bc -> IntuitionBase LVO -162 = MoveScreen(s,0,64)
     *   111438  move.l $2124(a4),-(a7)
     *   11143c  jsr $111786(pc)   -> $12b184 -> IntuitionBase LVO -252 = ScreenToFront(s)
     * (LVOs checked against fd1.3/intuition_lib.fd.)
     */
    MoveScreen(IFF_SCREEN, 0, 0x40);
    ScreenToFront(IFF_SCREEN);
    cnet_log("ok: screen moved down 64 and brought to front");

    /* Patch NewWindow.Screen (blob 0x11f158 + 0x1e) and open.
     *
     * ⚠ THE WINDOW IS SIZED FROM THE SCREEN JUST OPENED — and omitting that was a real
     * reconstruction bug (#129). The blob's NewWindow is a fixed 640x256, while the
     * screen above is 320 wide for any picture with pageWidth <= 320. A window cannot
     * be larger than its screen, so OpenWindow returned NULL for every lowres picture,
     * iff_setup flagged an error, and iff_feed_byte — which begins `if (g_iff_error)
     * return;` — silently discarded the entire image while the file still saved
     * perfectly. Only pictures wider than 320 (which force a 640 hires screen) worked.
     *
     * Ground truth, relocated disassembly of FUN_001112ae:
     *   111442  move.l  $2124(a4), $2176(a4)   ; NewWindow.Screen = IFF_SCREEN
     *   111448  movea.l $2124(a4), a0          ; a0 = the screen
     *   11144c  move.w  $c(a0), $215c(a4)      ; NewWindow.Width  = Screen.Width
     *   111452  move.w  $e(a0), $215e(a4)      ; NewWindow.Height = Screen.Height
     *   11145c  jsr     OpenWindow
     * $215c/$215e(a4) are NewWindow+4/+6; $c/$e(a0) are Screen.Width/Height.
     */
    {
        struct NewWindow *nw = (struct NewWindow *)DATA(0x11f158);
        nw->Screen = IFF_SCREEN;
        nw->Width  = IFF_SCREEN->Width;
        nw->Height = IFF_SCREEN->Height;
    }
    IFF_WINDOW = (struct Window *)open_window_tracked(DATA(0x11f158));
    if (IFF_WINDOW == NULL) {
        cnet_log("FAIL: OpenWindow returned NULL");
        iff_free_all();
        g_iff_error = 1;
        return;
    }
    sprintf(g_iff_logbuf, "ok: window opened w=%ld h=%ld",
            (long)IFF_WINDOW->Width, (long)IFF_WINDOW->Height);
    cnet_log(g_iff_logbuf);
}

/* iff_cmap — recon FUN_0011147e: convert the gathered CMAP RGB bytes (3 per colour) to
 * 4-bit RGB4 words and LoadRGB4 them into the screen's ViewPort. */
static void iff_cmap(void)
{
    LONG n, i;

    n = 1L << BMHD_NPLANES;
    if (n > 0x20)
        n = 0x10;
    g_cmap_ncolors = n;

    for (i = 0; i < n; i++) {
        UWORD r = g_iff_field[i * 3 + 0] >> 4;
        UWORD g = g_iff_field[i * 3 + 1] >> 4;
        UWORD b = g_iff_field[i * 3 + 2] >> 4;
        g_cmap[i] = (r << 8) | (g << 4) | b;
    }
    load_screen_palette(&IFF_SCREEN->ViewPort, g_cmap, g_cmap_ncolors);
}

/* iff_row_uncompressed — recon FUN_0011155c: store one BODY byte into the current plane
 * row; mask the last word; on plane completion advance plane, flush the row when all
 * planes are in. */
static void iff_row_uncompressed(UBYTE byte)
{
    g_iff_planeleft--;
    if (g_iff_planeleft != 0) {
        *g_iff_wr++ = byte;
        return;
    }
    /* last byte of this plane row: apply the partial-word mask (recon: byte & lastmask). */
    *g_iff_wr++ = (UBYTE)(byte & g_iff_lastmask);
    g_iff_plane++;
    if (g_iff_plane == g_iff_nplanes) {
        iff_draw_row();
        return;
    }
    g_iff_wr = g_iff_planeptr[g_iff_plane];
    g_iff_planeleft = g_iff_rowbytes;
}

/* iff_row_byterun1 — recon FUN_001115e6: ByteRun1 (PackBits) row depacker. State 0 reads
 * a control byte: 0..127 -> copy next N+1 literally (state 1); 129..255 -> repeat the next
 * byte 257-N times (state 2); 128 -> no-op. States 1/2 consume data bytes; a plane row is
 * complete when its byte counter reaches 0, flushing the screen row every nplanes. */
static void iff_row_byterun1(UBYTE byte)
{
    if (g_brun_state == 2) {                  /* run: fill with 'byte' */
        g_iff_planeleft -= g_brun_run;
        do {
            *g_iff_wr++ = byte;
            g_brun_run--;
        } while (g_brun_run != 0);
        g_brun_state = 0;
    } else if (g_brun_state == 1) {           /* literal copy */
        *g_iff_wr++ = byte;
        g_iff_planeleft--;
        g_brun_run--;
        if (g_brun_run == 0)
            g_brun_state = 0;
    } else {                                  /* control byte */
        if (byte < 0x80) {
            g_brun_state = 1;
            g_brun_run   = byte + 1;
        } else if (byte != 0x80) {
            g_brun_state = 2;
            g_brun_run   = (UWORD)(0x100 - byte + 1);
        }
        return;
    }

    if (g_iff_planeleft != 0)                 /* plane row not finished */
        return;
    g_iff_plane++;
    if (g_iff_plane == g_iff_nplanes) {
        iff_draw_row();
    } else {
        g_iff_wr = g_iff_planeptr[g_iff_plane];
        g_iff_planeleft = g_iff_rowbytes;
    }
    g_brun_state = 0;
}

/*
 * iff_feed_byte — recon FUN_00111024. The IFF chunk state machine, fed one byte at a
 * time. If an error was flagged it ignores input. It first honours a pending skip
 * (unknown-chunk padding), then gathers bytes into the current field until `need` is
 * satisfied, then dispatches on the current state.
 */
void iff_feed_byte(UBYTE byte)
{
    if (g_iff_error)
        return;
    if (g_iff_skip != 0) {
        g_iff_skip--;
        return;
    }
    if (g_iff_need != 0) {
        *g_iff_field_wr++ = byte;
        g_iff_need--;
        if (g_iff_need != 0)
            return;
    }

    switch (g_iff_state) {
    case 1:                                   /* FORM id */
        if (*(LONG *)g_iff_chunk != 0x464f524dL /* 'FORM' */) {
            g_iff_error = 1;
            return;
        }
        g_iff_state = 2;
        g_iff_need  = 4;                       /* FORM size (ignored) */
        g_iff_field = g_iff_field_wr = g_iff_chunk;
        return;
    case 2:                                   /* FORM type == ILBM */
        if (*(LONG *)g_iff_chunk != 0x494c424dL /* 'ILBM' */) {
            g_iff_error = 1;
            return;
        }
        g_iff_state = 3;
        g_iff_need  = 8;                       /* next chunk header */
        g_iff_field = g_iff_field_wr = g_iff_chunk;
        return;
    case 3:                                   /* expect BMHD; skip anything else (recon 0x111100) */
        if (*(LONG *)g_iff_chunk == 0x424d4844L /* 'BMHD' */) {
            g_iff_state = 4;
            g_iff_need  = CHUNK_LEN + (CHUNK_LEN_ODD ? 1 : 0);
            g_iff_field = g_iff_field_wr = g_iff_chunk + 8;   /* BMHD body @ +8 (0x46ec) */
        } else {                              /* not BMHD yet — skip this chunk, stay in state 3 */
            g_iff_skip  = CHUNK_LEN + (CHUNK_LEN_ODD ? 1 : 0);
            g_iff_need  = 8;
            g_iff_field = g_iff_field_wr = g_iff_chunk;
        }
        return;
    case 4:                                   /* BMHD gathered */
        cnet_log("BMHD gathered -> iff_setup");
        iff_setup();
        if (g_iff_error) cnet_log("iff_setup FAILED — decoder now silent");
        g_iff_state = 5;
        g_iff_need  = 8;                       /* next chunk header */
        g_iff_field = g_iff_field_wr = g_iff_chunk;
        return;
    case 5:                                   /* expect CMAP; skip anything else (recon 0x11118a) */
        if (*(LONG *)g_iff_chunk == 0x434d4150L /* 'CMAP' */) {
            g_iff_state = 6;
            g_iff_need  = CHUNK_LEN + (CHUNK_LEN_ODD ? 1 : 0);
            g_iff_field = g_iff_field_wr = g_cmap_raw;      /* CMAP RGB bytes (0x4700) */
        } else {                              /* not CMAP yet — skip this chunk, stay in state 5 */
            g_iff_skip  = CHUNK_LEN + (CHUNK_LEN_ODD ? 1 : 0);
            g_iff_need  = 8;
            g_iff_field = g_iff_field_wr = g_iff_chunk;
        }
        return;
    case 6:                                   /* CMAP gathered */
        cnet_log("CMAP gathered -> load palette");
        iff_cmap();
        g_iff_state = 7;
        g_iff_need  = 8;
        g_iff_field = g_iff_field_wr = g_iff_chunk;
        return;
    case 7:                                   /* expect BODY; skip anything else (recon 0x111210) */
        if (*(LONG *)g_iff_chunk == 0x424f4459L /* 'BODY' */) {
            sprintf(g_iff_logbuf, "BODY starts, len=%ld mode=%s",
                    (long)CHUNK_LEN, g_iff_compress ? "ByteRun1" : "uncompressed");
            cnet_log(g_iff_logbuf);
            iff_body_start();                 /* switch to per-byte row decode (state 8/9) */
        } else {                              /* not BODY yet (e.g. CAMG/ANNO) — skip, stay in state 7 */
            g_iff_skip  = CHUNK_LEN + (CHUNK_LEN_ODD ? 1 : 0);
            g_iff_need  = 8;
            g_iff_field = g_iff_field_wr = g_iff_chunk;
        }
        return;
    case 8:                                   /* uncompressed BODY row byte */
        iff_row_uncompressed(byte);
        return;
    case 9:                                   /* ByteRun1 BODY row byte */
        iff_row_byterun1(byte);
        return;
    default:
        return;
    }
}

/* iff_view_file — recon FUN_00111704: decode an IFF file already on disk. Loads the
 * whole file into a tracked block (load_file_to_mem), feeds every byte to the decoder,
 * frees the decoder window, and frees the file block. Returns 0 if the load failed. Not
 * on the streamed download path (that uses action_download_run) but part of the family;
 * used to re-view a saved picture. */
LONG iff_view_file(const char *name)
{
    UBYTE *buf;
    ULONG  size, i;

    buf = (UBYTE *)load_file_to_mem(name);    /* FUN_0011a41e */
    if (buf == NULL)
        return 0;
    size = mem_block_size(buf);               /* FUN_0011a26c */
    iff_init();
    for (i = 0; i < size; i++)
        iff_feed_byte(buf[i]);
    iff_free_bitmap();
    free_tracked(buf);                        /* FUN_0011a238 */
    return 1;
}

/* ================================================================= *
 *  'F' picture download — recon FUN_0010b50e (action_download_run)
 * ================================================================= *
 * Prompt for a save filename, negotiate the transfer (file_download_xfer), reset the
 * frame reader, then process the stream in <=4000-byte blocks: for each block, pull frame
 * bytes one at a time, stage them into g_xfer_buf AND feed each to the IFF decoder; when
 * the block fills (i==4000) or the transport signals end-of-frame with the buffer drained
 * (done = frame_eof && frame_pos>=frame_len), write the staged block to disk. Repeat until
 * done. On success frees the decoder window; "No room for file" if a write failed.
 *
 * NOTE the reader-state fields the recon clears at 0x10b532 alias the transport frame
 * reader: 0x33a0 = g_frame_pos, 0x33a4 = g_frame_len, 0x33ac = g_frame_eof (byte),
 * 0x33ae = g_frame_capture — so read_frame_byte streams fresh transport data here.
 */
LONG action_download_run(void)
{
    ULONG i;
    LONG  done;

    cnet_log("action_download_run: asking for a filename");
    if (download_filename_prompt() == 0) {
        cnet_log("  -> filename prompt cancelled/failed, nothing sent");
        return 0;
    }
    cnet_log("action_download_run: negotiating transfer");
    if (file_download_xfer() == 0) {
        cnet_log("  -> file_download_xfer refused (machine type / file open)");
        return 0;
    }

    g_frame_pos     = 0;
    g_frame_len     = 0;
    g_frame_capture = NULL;
    g_frame_eof     = 0;
    iff_init();
    cnet_log("--- F transfer negotiated, decoding begins ---");
    g_iff_bytes_fed = 0;

    do {
        i = 0;
        for (;;) {
            if (i >= 4000)                    /* recon cap 0xfa0 -> flush block */
                break;
            /* done when the device flagged end-of-frame and the read buffer is drained. */
            done = (g_frame_eof != 0 && g_frame_pos >= g_frame_len);
            if (done)
                break;
            {
                UBYTE b = read_frame_byte();
                g_xfer_buf[i] = b;            /* stage into the 0x50fc buffer */
                iff_feed_byte(b);
                g_iff_bytes_fed++;
            }
            i++;
        }

        if (g_dl_file != NULL) {              /* flush this block to disk */
            if (file_write(g_dl_file, g_xfer_buf, i) != (LONG)i) {
                file_close(g_dl_file);
                g_dl_file = NULL;
            }
        }
    } while (!done);

    /* #129 trace summary. `rows` is the number the decoder actually blitted: 0 with
     * no FAIL line above means the BODY never started; short of the picture height
     * means the stream ended early. */
    sprintf(g_iff_logbuf, "--- end: fed=%ld rows=%ld state=%ld error=%ld screen=%s window=%s",
            (long)g_iff_bytes_fed, (long)g_iff_row, (long)g_iff_state, (long)g_iff_error,
            IFF_SCREEN ? "open" : "NULL", IFF_WINDOW ? "open" : "NULL");
    cnet_log(g_iff_logbuf);

    iff_free_bitmap();
    if (g_dl_file == NULL) {
        show_status_message(1, "No room for file");
        return 0;
    }
    file_close(g_dl_file);
    return 1;
}

/* ================================================================= *
 *  'P'/'S' program download — recon FUN_0010b36e
 * ================================================================= */
LONG download_program(void)
{
    if (download_filename_prompt() == 0)
        return 0;
    return download_receive();
}

/* ================================================================= *
 *  'L' link download — recon FUN_0010b66a / FUN_0010b602 / FUN_0010b656
 * ================================================================= *
 * Send "D%02d", read the 8-byte link header, validate it (masking byte set AND magic
 * 0x01000001 AND a-word zero), drain the link preamble, then hand the connection to the
 * loaded CnetTty viewer (g_tty_seg_bptr) with read / io / send callbacks. On carrier
 * loss the viewer returns 0 -> "Carrier lost" (host-error) + longjmp to disconnect.
 */
extern LONG   modem_read_status(void);                  /* FUN_00119a60 */
extern void   serial_io_variant(APTR buf, UWORD len);   /* FUN_0011998a */
extern void   modem_send_delayed(const char *s, ULONG len); /* FUN_001198e0 */
extern UBYTE  g_link_char;                              /* DAT_001230bc */

/* link_read_char — recon FUN_00119a24: read a single byte via serial_io_variant into
 * the link scratch (g_link_char) and return it. */
static UBYTE link_read_char(void)        /* FUN_00119a24 */
{
    serial_io_variant(&g_link_char, 1);
    return g_link_char;
}

/* link_drain_preamble — recon FUN_0010b602: arm the link viewer, then read link-status
 * bytes, skipping type-1 markers and emitting a "\x01\x06  " sequence on a type-2 marker,
 * until 3 consecutive non-marker reads; then emit "\x01\x01\x01\x01\x01\x01". */
extern void link_viewer_arm(void);           /* FUN_001194e8 */
static void link_drain_preamble(void)
{
    int run = 0;
    link_viewer_arm();                       /* recon FUN_0010b826 -> FUN_001194e8: arm raw
                                              * mode; the mirror of link_viewer_exit. NOT a
                                              * byte read (the earlier recon read a spurious
                                              * byte here and never armed the session). */
    while (run < 3) {
        UBYTE c = (UBYTE)(link_read_char() & 0xff);
        if (c == 2) {
            modem_send_delayed(DATA(0x11e5a6), 8);   /* "\x01\x06  " */
            run = 0;
        } else if (c == 1) {
            run++;
        } else {
            run = 0;
        }
    }
    modem_send_delayed(DATA(0x11e5b0), 6);   /* "\x01\x01\x01\x01\x01\x01" */
}

/* link_end — recon FUN_0010b656: send "\x02\x02\x02\x02\x02\x02" then the viewer-exit. */
extern void link_viewer_exit(void);      /* FUN_001194c8 */
static void link_end(void)
{
    modem_send_delayed(DATA(0x11e5b8), 6);   /* "\x02..." */
    link_viewer_exit();
}

LONG download_link(void)
{
    UBYTE ser_flags, status_hi;
    ULONG actual;
    LONG  rc;

    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK)
        return 0;

    serial_read(g_dl_header, 8, &ser_flags, &status_hi, &actual);
    sprintf(g_iff_logbuf, "link header: eof=%ld hdr0=$%08lx hdr4=$%08lx",
            (long)ser_flags, (unsigned long)*(LONG *)g_dl_header,
            (unsigned long)*(LONG *)(g_dl_header + 4));
    cnet_log(g_iff_logbuf);
    /* The two CONTENT checks are the faithful ones, and both were wrong before:
     *   10b6c6  cmpi.l #$1000001, $45e8(a4)  ; g_dl_header[0..3]
     *   10b6d0  tst.l  $45ec(a4)             ; g_dl_header+4 — the SECOND longword
     * We used to test `g_dl_link_a`, which in this tree is a standalone LONG that is
     * initialised to 0 and never written — in the ORIGINAL that address IS
     * g_dl_header+4. So the header's second longword went unexamined and the clause was
     * constant-true. These now read the received bytes.
     *
     * ⚠ DELIBERATE DEVIATION — the end-of-message test is SKIPPED over TCP.
     *   10b6c0  tst.b -$2(a5)   ; ser_flags == 0 -> "Invalid link"
     * On the real modem the fixed 8-byte read reports end-of-message and this is a
     * genuine validity check. Over TCP the flag is not set until the EOS is consumed,
     * and the link stream does NOT have one to consume here: an attempt to drain it
     * (which is what file_download_xfer legitimately does for a program header) blocks
     * forever on a read that never returns — it HUNG the client the moment a Partyline
     * link was selected. The transport flag carries no meaning on this path, so it is
     * not tested there; the two content checks above still reject a malformed header. */
    if ((!g_tcp_mode && ser_flags == 0) ||
        *(LONG *)g_dl_header != 0x01000001L ||
        *(LONG *)(g_dl_header + 4) != 0) {
        show_status_message(1, "Invalid link");
        return 0;
    }

    link_drain_preamble();

    /* Hand off to the CnetTty viewer ("Scrollback v1.0", Zugger '89):
     *   entry(screen, read_cb, io_cb, send_cb)  — C stack call, returns a WORD in d0.
     * read_cb is POLLED: it must return the byte-available COUNT (0 = nothing waiting,
     * 0xffff = carrier lost -> viewer returns 0, >0 = N bytes ready). That is
     * modem_read_status, NOT link_read_char (which returns a byte value and could never
     * signal 0xffff — the earlier recon broke the viewer's read loop and carrier detect).
     * The viewer then bulk-reads min(count,35) bytes via io_cb, and sends typed keys via
     * send_cb. It returns 1 on a clean end (three consecutive 0x02 bytes from the host, or
     * the "Done" gadget) and 0 on carrier loss. (verified: original 0x10b6f4 pushes
     * FUN_00119a60 = modem_read_status.) */
    rc = ((LONG (*)(APTR, APTR, APTR, APTR))g_tty_seg_bptr)(
             g_screen,
             (APTR)modem_read_status,
             (APTR)serial_io_variant,
             (APTR)modem_send_delayed);
    /* ⚠ TESTED AS A WORD (original 0x10b706 `tst.w d0`), and CnetTty returns a WORD in
     * d0 (cnettty-re.md:52). Testing the full LONG means junk left in the high half by
     * any exit path that does not `moveq` would read as "not zero" and silently suppress
     * the carrier-loss report and its longjmp — the connection would appear alive. Every
     * documented exit does moveq, so this cannot bite today; it is free to be exact. */
    if ((WORD)rc == 0) {
        show_status_message(0x42, "Carrier lost");
        set_connection_error(1);
    }
    link_end();
    return 1;
}

/* ================================================================= *
 *  download_check — recon FUN_0010b730 (the D-command entry + dispatch)
 * ================================================================= */
LONG download_check(void)
{
    char type;

    g_state = STATE_GOTO;
    g_sel_row = *(short *)((UBYTE *)g_dir_page + 0xc78);
    type = ROW_TYPE(g_dir_page, g_sel_row);
    sprintf(g_cmd_buf, "D%02d", (int)g_sel_row);

    /* #129 trace: proves download_check was REACHED, and with which row/type. If the
     * log shows no line here after a double-click, the click never dispatched a row
     * action at all (dir_select only does so "while navigable") — which is a very
     * different problem from the type being wrong. */
    sprintf(g_iff_logbuf, "download_check: row=%ld type='%c' cmd=%s",
            (long)g_sel_row, (type >= 32 && type < 127) ? type : '?', g_cmd_buf);
    cnet_log(g_iff_logbuf);

    switch (type) {
    case 'T':
        /* ⚠ A CHARGED TEXT PAGE IS GATED TOO. Reconstructed without the prompt, which
         * meant a priced `T` entry was fetched — and the user BILLED — with no
         * "WARNING - CHARGED ITEM / Buy for £x?" confirmation. All six types are gated
         * in the original; this was the one that was not. Ground truth 0x10b7a4:
         *   10b7a4  bsr.w $10b000     ; download_charged_prompt
         *   10b7a8  tst.l d0
         *   10b7aa  beq.b $10b7b2     ; declined -> moveq #0,d0 ; rts
         *   10b7ac  jsr   $10b86e(pc) ; -> $113000 download_text
         * The header comment on this file asserted the opposite and has been corrected. */
        return download_charged_prompt() ? download_text() : 0;
    case 'F':                                 /* IFF picture */
        return download_charged_prompt() ? action_download_run() : 0;
    case 'P':
    case 'S':                                 /* program */
        return download_charged_prompt() ? download_program() : 0;
    case 'A':                                 /* action / executable */
        return download_charged_prompt() ? action_download() : 0;
    case 'L':                                 /* link / sub-program */
        return download_charged_prompt() ? download_link() : 0;
    default:
        cnet_log("  -> no handler for this type: \"Can't download this\"");
        show_status_message(1, "Can't download this");
        return 0;
    }
}
