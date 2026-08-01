/*
 * osglue.c — small OS-glue wrappers (reconstructed).
 *
 * Thin wrappers the original kept as amiga.lib-style stubs, plus a couple of tiny
 * UI helpers. Each maps to a single library vector or a short sequence.
 *
 *   open_dos_library    (FUN_001001c4) — OpenLibrary("dos.library"); fatal if absent.
 *   open_library_checked(FUN_0011a290) — OpenLibrary + resource-track the close.
 *   put_msg             — PutMsg() to a port (editor startup message).
 *   link_lock           (FUN_00109520) — highlight/unhighlight a directory row box.
 *   fatal_exit          (FUN_0011a11e) — free resources and exit with a code.
 *   handle_extra_signal / handle_device_message / mail_state_enter — small hooks.
 */
#include <exec/types.h>
#include <stdlib.h>
#include <clib/exec_protos.h>
#include <clib/dos_protos.h>
#include <clib/graphics_protos.h>
#include <clib/intuition_protos.h>
#include <intuition/intuition.h>
#include <stdio.h>

#include "compunet.h"

/* The extracted data section, addressed by original address (see download.c/ui.c). */
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

extern APTR DOSBase;                 /* set by runtime; opened here if needed */
extern BYTE cleanup_resources(void);
extern APTR alloc_tracked(ULONG, ULONG);
extern void free_tracked(APTR);

/* open_dos_library — recon FUN_001001c4. */
APTR open_dos_library(void)
{
    if (DOSBase == NULL)
        DOSBase = (APTR)OpenLibrary((STRPTR)"dos.library", 0);
    return DOSBase;
}

/* open_library_checked — recon FUN_0011a290: OpenLibrary, and on success register a
 * tracked CloseLibrary so cleanup_resources unwinds it (recon 0x11a2b4: register
 * CloseLibrary(lib)). The bare OpenLibrary left opened libraries untracked. */
extern void resource_register_free(void (*fn)(), APTR arg1, APTR arg2);
APTR open_library_checked(const char *name, ULONG ver)
{
    APTR lib = (APTR)OpenLibrary((STRPTR)name, ver);
    if (lib != NULL)
        resource_register_free((void (*)())CloseLibrary, lib, 0);
    return lib;
}

/* put_msg — send the editor startup message (recon thunk_FUN_001290f4 = PutMsg). */
void put_msg(APTR port, APTR msg)
{
    PutMsg((struct MsgPort *)port, (struct Message *)msg);
}

/*
 * link_lock — recon FUN_00109520. Draw (or undraw) the busy highlight over a directory
 * action button. Called TWICE per action, before and after, and the pair must cancel.
 *
 * ⚠ SetDrMd(COMPLEMENT), NOT SetAPen. That is the whole mechanism: complement mode XORs
 * the rectangle, so the second call erases exactly what the first drew. Reconstructed as
 * `SetAPen(rp, 2)`, the first call painted a SOLID pen-2 block over the button and the
 * second painted it again — the highlight never came off, so the first use of Dir, Back,
 * Goto, Dnld or Upld blanked that button for the rest of the session. It also left the
 * directory RastPort's APen at 2, which the original never touches here.
 *
 * Ground truth FUN_00109520 (the entire function):
 *   10952a  pea.l  $2.w              ; 2 = JAM1|COMPLEMENT -> COMPLEMENT
 *   10952e  move.l $32(a0), -(a7)    ; Window->RPort
 *   109532  jsr    $10a5b8(pc)       ; -> $12a0b8 -> GfxBase LVO -$162 = SetDrMd
 *   109560  jsr    $10a594(pc)       ; RectFill(rp, row*64+7, $cb, row*64+$42, $da)
 *
 * ⚠ TOOLING TRAP: disasm_fn.py's built-in LVO table labels -$162 as SetBPen. It is not.
 * Per fd1.3/graphics_lib.fd, -354 = SetDrMd; SetBPen is -348 and SetAPen -342. Confirm
 * graphics LVOs against the .fd file, not the disassembler's annotation.
 */
void link_lock(APTR dir_page, int row)
{
    struct Window *w = *(struct Window **)dir_page;
    if (w == NULL) return;
    SetDrMd(w->RPort, COMPLEMENT);
    RectFill(w->RPort, row * 0x40 + 7, 0xcb, row * 0x40 + 0x42, 0xda);
}

/* fatal_exit — recon FUN_0011a11e: unwind all tracked resources and terminate. */
void fatal_exit(ULONG code)
{
    /* Free ALL tracked resources in one pass (recon FUN_0011a0f0), then terminate.
     * The original tail-calls the SAS/C exit epilogue; with vbcc's minstart.o, exit()
     * restores the entry stack pointer and returns to DOS. (An earlier version looped
     * on cleanup_resources() level-by-level, which was the wrong unwind primitive.) */
    extern void cleanup_all_resources(void);
    wb_startup_end();          /* if launched from Workbench: restore cwd + reply the WBStartup
                                * message (while DOSBase is still open) so WB can unload us */
    cleanup_all_resources();   /* frees the whole list — incl. CloseWindow/CloseScreen */
    exit((int)code);
}

/*
 * handle_extra_signal — recon FUN_00119506 (100 bytes). THE USER ABORT.
 *
 * ⚠ THIS WAS AN EMPTY STUB THAT CLAIMED TO BE A RECONSTRUCTION. The comment said the
 * original "drains the main window's IDCMP and sets the abort flag"; it does not set any
 * flag — it longjmps. Every blocking transport wait calls this when the extra signal
 * fires (serial_write 0x119600, serial_read 0x1196fe, serial_io_c 0x119816,
 * modem_send_delayed 0x11992e, serial_io_variant 0x1199d8, modem_read_status 0x119a9a),
 * so with an empty body TWO things were broken:
 *   - Left-Amiga+HELP could not abort a stuck download or a hung frame read — precisely
 *     when a user needs it. The idle event loop implements the chord correctly, which is
 *     why the feature looked present.
 *   - the IntuiMessages arriving on the shared UserPort during a transfer were never
 *     GetMsg'd or ReplyMsg'd, so they queued up for the duration.
 *
 * Ground truth:
 *   11950a  GetMsg(g_main_uport)          ; $3100(a4) = 0x120100
 *   11951e  Class     &lt;- msg+0x14 (LONG)
 *   119526  Code      &lt;- msg+0x18 (WORD, zero-extended)
 *   11952a  Qualifier &lt;- msg+0x1a (WORD)
 *   119536  ReplyMsg  — unconditional, before any test
 *   11953c  Class == $400            (IDCMP_RAWKEY)
 *   119546  Code  == $5f             (HELP)
 *   119550  btst #6 of the qualifier's LOW byte  (IEQUALIFIER_LCOMMAND = $0040)
 *   119560  longjmp(g_jmpbuf @0x120170, 1)
 * Exactly one message is taken per call — no loop.
 */
void handle_extra_signal(void)
{
    extern APTR g_main_uport;                  /* DAT_00120100 */
    struct IntuiMessage *msg;
    ULONG cls, code;
    UWORD qual;

    msg = (struct IntuiMessage *)GetMsg((struct MsgPort *)g_main_uport);
    if (msg == NULL)
        return;
    cls  = msg->Class;
    code = (ULONG)msg->Code;
    qual = msg->Qualifier;
    ReplyMsg((struct Message *)msg);

    if (cls == 0x400UL && code == 0x5fUL && (qual & 0x0040))
        set_connection_error(1);               /* longjmp(g_jmpbuf, 1) — does not return */
}

/*
 * handle_device_message — recon FUN_001190e8 (462 bytes; recon_functions.txt says 260,
 * which is wrong — the unlk/rts is at 0x1192b2). Renders one device record into the
 * Diagnostics window.
 *
 * ⚠ ALSO AN EMPTY STUB CLAIMING TO BE A RECONSTRUCTION. Together with the flag defect
 * (0x11fd74 declared twice, then declared too narrow) this is why the Diagnostics window
 * has never shown anything: even with the gate fixed, there was nothing to draw.
 *
 * Record layout: +0x16 kind (0 Sending, 1 Received, 2 error), +0x17 subcode, +0x18 value.
 */
void handle_device_message(struct Message *m)
{
    extern APTR g_diag_win;                    /* DAT_0011fd70 */
    UBYTE *msg = (UBYTE *)m;
    struct IntuiText *it = (struct IntuiText *)DATA(0x11fe16);
    struct RastPort  *rp;
    const char *type;
    char  buf[40];
    WORD  y = 0x0e;

    if (g_diag_win == NULL)
        return;
    rp = ((struct Window *)g_diag_win)->RPort;

    if (msg[0x16] == 2) {                      /* error record — jump table at 0x119112 */
        switch (msg[0x17]) {
        case 0x4f: it->IText = (UBYTE *)DATA(0x11fe72); break;  /* "Buffer overflow " */
        case 0x55: it->IText = (UBYTE *)DATA(0x11fe60); break;  /* "Spurious EOP    " */
        case 0x43: it->IText = (UBYTE *)DATA(0x11fe4e); break;  /* "CRC check failed" */
        case 0x4e: it->IText = (UBYTE *)DATA(0x11fe3c); break;  /* "Count incorrect " */
        case 0x53: it->IText = (UBYTE *)DATA(0x11fe2a); break;  /* "Unexpected SOP  " */
        default:   break;      /* faithful: IText left as-is, so the last one re-prints */
        }
        it->FrontPen = 2;
        PrintIText(rp, it, 8, 0x26);
        return;
    }

    /* Which label row the value goes on. ⚠ The original leaves this local UNINITIALISED
     * for any kind >= 3 and prints at a garbage Y; we default to the Sending row instead.
     * Deliberate, and the only deviation here — a wild TopEdge is not worth reproducing. */
    if (msg[0x16] == 1) y = 0x1a;              /* "Received" */
    else if (msg[0x16] == 0) y = 0x0e;         /* "Sending"  */

    switch (msg[0x17]) {                       /* jump table at 0x1191c8, 9 entries */
    case 0x20:            type = (const char *)DATA(0x11fe84); break;   /* "ACK" */
    case 0x21: case 0x61: type = (const char *)DATA(0x11fe88); break;   /* "DIR" */
    case 0x22: case 0x62: type = (const char *)DATA(0x11fe8c); break;   /* "DAT" */
    case 0x40:            type = (const char *)DATA(0x11fe90); break;   /* "OK " */
    case 0x41:            type = (const char *)DATA(0x11fe94); break;   /* "ERR" */
    case 0x42:            type = (const char *)DATA(0x11fe98); break;   /* "FTL" */
    case 0x43:            type = (const char *)DATA(0x11fe9c); break;   /* "COM" */
    default:              type = (const char *)DATA(0x11fea0); break;   /* "???" */
    }

    /* Image 0x11fdc8 is PlanePick=0 / PlaneOnOff=1 with no data — a solid pen-1 144x8
     * bar that ERASES the error line, which shares row 0x26. */
    DrawImage(rp, (struct Image *)DATA(0x11fdc8), 8, 0x26);
    sprintf(buf, (char *)DATA(0x11fea4), type, *(ULONG *)(msg + 0x18));   /* "%s %02lx" */
    it->IText    = (UBYTE *)buf;
    it->FrontPen = 6;
    PrintIText(rp, it, 0x58, y);
}

/* mail_state_enter (recon FUN_001091f2) is reconstructed faithfully in
 * directory_select.c — it re-labels the directory window's 5 action gadgets for
 * mail/courier mode and refreshes them. */
