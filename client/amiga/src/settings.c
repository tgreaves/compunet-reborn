/*
 * settings.c — the "Setup" menu: the serial/login configuration dialog (reconstructed).
 *
 *   settings_open   (FUN_00112000) — open the settings window (blob NewWindow 0x11f188),
 *                   copy the current config fields into the window's string-gadget
 *                   buffers (all blob-resident), set the "auto-open Diagnostics" toggle
 *                   gadget imagery from the open-flags bit-2, add the gadget list, and
 *                   draw the window body.
 *   settings_dialog (FUN_001122a6) — the modal event loop: call settings_open, then
 *                   WaitPort/GetMsg on the window and dispatch by the clicked gadget's
 *                   GadgetID (0..6): Use / Save / Cancel / toggle option, redrawing the
 *                   toggle gadget when it changes. Use=apply, Save=apply+write file,
 *                   Cancel=discard; all close the window on exit.
 *   settings_apply  (FUN_00112182) — copy the edited gadget buffers back into the
 *                   config fields (phone, modem name, userid, baud up/down, data bits,
 *                   open-flags Diagnostics bit) and push the serial params to the device.
 *   settings_close  (FUN_0011216c) — close the settings window.
 *
 * The gadgets and their string buffers all live in the extracted data blob (the blob
 * spans 0x11d000..~0x1233xx incl. its BSS tail), so we drive them by blob offset via
 * DATA(). The config VALUES, however, live in our reconstructed C globals (g_config /
 * g_phone_number / g_login_userid / g_baud_* ), so settings_open/apply bridge between
 * those globals and the blob gadget buffers — exactly as the original bridges between
 * its config block and the same gadget buffers.
 *
 * TRANSCRIPTION: control flow + every blob offset and field are from the RELOCATED
 * disassembly of FUN_00112000 / 001122a6 / 00112182 / 0011216c (disasm_fn.py), not the
 * lossy decompile. a4 = 0x11d000, so $NNNN(a4) => DATA(0x11d000+NNNN).
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/exec_protos.h>
#include <clib/intuition_protos.h>
#include <clib/graphics_protos.h>
#include <string.h>
#include <stdio.h>

#include "compunet.h"

extern APTR  g_screen;
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))
#define DW(off)   (*(WORD  *)DATA(off))
#define DL(off)   (*(APTR  *)DATA(off))

extern APTR open_window_tracked(APTR nw);   /* FUN_0011a534 */
extern void close_window_tracked(APTR win); /* FUN_0011a568 */
extern void apply_serial_params(UWORD bits);/* FUN_00114050 */
extern LONG save_config_file(void);         /* FUN_00112250 */

/* Config values live in the single g_config block; access via the compunet.h
 * accessors (g_phone_number, g_modem_name, g_cfg_userid, g_baud_up/down, g_open_flags,
 * g_data_bits). g_login_userid is the separate derived-userid buffer. */
extern char  g_login_userid[];   /* DAT_00120244 */

/* Blob-resident settings-dialog state and gadget buffers (offsets are absolute
 * addresses the original uses; DATA() maps them into g_data). */
#define SET_WIN        DL(0x121828)   /* the settings Window handle (blob BSS)   */
#define SET_TOGGLE     DW(0x121826)   /* Diagnostics toggle state (0/1)            */
#define NEWWIN         DATA(0x11f188)  /* settings NewWindow                      */
#define NEWWIN_SCREEN  DL(0x11f1a6)    /* NewWindow.Screen field (0x11f188+0x1e)  */
#define GBUF_PHONE     ((char *)DATA(0x1217ec)) /* phone string gadget buffer      */
#define GBUF_MODEM     ((char *)DATA(0x1217fc)) /* modem-name gadget buffer         */
#define GBUF_USERID    ((char *)DATA(0x121805)) /* userid gadget buffer             */
#define GBUF_BAUDUP    ((char *)DATA(0x121815)) /* baud-up integer gadget buffer    */
#define GBUF_BAUDDN    ((char *)DATA(0x12181b)) /* baud-down integer gadget buffer  */
#define GBUF_DBITS     ((char *)DATA(0x121821)) /* data-bits integer gadget buffer  */
/* Integer gadgets' StringInfo.LongInt fields — Intuition parses the user's typed
 * number into these blob-resident longs; settings_apply reads the VALUE from here,
 * not by re-parsing the buffer. Addresses verified from the relocated disasm:
 * recon reads move.l $24aa(a4)=0x11f4aa, $2436(a4)=0x11f436, $23c2(a4)=0x11f3c2. */
#define LI_BAUDUP      (*(LONG *)DATA(0x11f4aa))
#define LI_BAUDDN      (*(LONG *)DATA(0x11f436))
#define LI_DBITS       (*(LONG *)DATA(0x11f3c2))

/* Gadget lists / render structs (blob). */
#define GLIST          DATA(0x11f60e)  /* the main gadget list added to the window */
#define IMG_BODY1      DATA(0x11f63a)  /* body image / border set 1                */
#define IMG_BODY2      DATA(0x11f766)
#define IMG_BODY3      DATA(0x11f662)
/* toggle-gadget imagery pairs (ON vs OFF): render + select structs */
#define TOG_ON_RENDER  DATA(0x11f328)
#define TOG_ON_SEL     DATA(0x11f2e2)
#define TOG_OFF_RENDER DATA(0x11f342)
#define TOG_OFF_SEL    DATA(0x11f2b0)
#define TOG_GADGET_R   0x11f370   /* toggle gadget.GadgetRender field (blob) */
#define TOG_GADGET_S   0x11f310   /* toggle gadget.SelectRender field (blob) */

/* uppercase in place — recon FUN_0011513a (a..z -> A..Z). */
static void str_upper(char *p)
{
    for (; *p; p++)
        if (*p >= 'a' && *p <= 'z')
            *p -= 0x20;
}

/* settings_close — recon FUN_0011216c. */
void settings_close(void)
{
    if (SET_WIN != NULL) {
        close_window_tracked(SET_WIN);
        SET_WIN = NULL;
    }
}

/*
 * settings_open — recon FUN_00112000. Open the window on our screen and populate the
 * gadget buffers from the config. Returns 1 on success, 0 if OpenWindow failed.
 */
static LONG settings_open(void)
{
    struct Window *w;

    NEWWIN_SCREEN = g_screen;                 /* patch NewWindow.Screen (0x11f1a6) */
    w = (struct Window *)open_window_tracked(NEWWIN);
    SET_WIN = (APTR)w;
    if (w == NULL)
        return 0;

    /* Copy config fields into the string-gadget buffers. The buffers are blob-resident
     * (the gadgets' StringInfo.Buffer point at them), so they are DATA(); the config
     * VALUES come from our single g_config block via the header accessors. The recon
     * src->dst addresses (0x1217ec<-0x120108 phone, 0x1217fc<-0x120134 userid,
     * 0x121805<-0x12011c modem) map directly to those accessors. */
    strcpy(GBUF_PHONE,  g_phone_number);   /* buffer 0x1217ec <- config 0x120108 */
    strcpy(GBUF_MODEM,  g_cfg_userid);     /* buffer 0x1217fc <- config 0x120134 */
    strcpy(GBUF_USERID, g_modem_name);     /* buffer 0x121805 <- config 0x12011c */
    /* Numeric gadgets: sprintf(buf, fmt, config-word). Formats are blob strings at
     * 0x11f77a/77e/82; buffers 0x121815/81b/821; values from the config block. */
    sprintf(GBUF_BAUDUP, (char *)DATA(0x11f77a), (int)g_baud_up);
    sprintf(GBUF_BAUDDN, (char *)DATA(0x11f77e), (int)g_baud_down);
    sprintf(GBUF_DBITS,  (char *)DATA(0x11f782), (int)g_data_bits);
    /* Seed each integer gadget's StringInfo.LongInt with the config value
     * (recon $112092..$1120aa: move.w cfg -> move.l -> 0x11f4aa/436/3c2). */
    LI_BAUDUP = (LONG)g_baud_up;
    LI_BAUDDN = (LONG)g_baud_down;
    LI_DBITS  = (LONG)g_data_bits;

    /* Toggle gadget imagery from open-flags bit 2 (Diagnostics auto-open). */
    if (g_open_flags & 4) {
        SET_TOGGLE = 1;
        DL(TOG_GADGET_R) = TOG_ON_RENDER;
        DL(TOG_GADGET_S) = TOG_ON_SEL;
    } else {
        SET_TOGGLE = 0;
        DL(TOG_GADGET_R) = TOG_OFF_RENDER;
        DL(TOG_GADGET_S) = TOG_OFF_SEL;
    }

    /* Draw the window body (recon DrawImage / PrintIText / DrawBorder at 4,2). */
    DrawImage(w->RPort, (struct Image *)IMG_BODY1, 4, 2);
    PrintIText(w->RPort, (struct IntuiText *)IMG_BODY2, 4, 2);
    DrawBorder(w->RPort, (struct Border *)IMG_BODY3, 4, 2);

    /* Attach the gadget list and refresh it. */
    AddGList(w, (struct Gadget *)GLIST, 0, ~0, NULL);   /* recon: position=0, numGad=-1 */
    RefreshGList((struct Gadget *)GLIST, w, NULL, ~0);
    return 1;
}

/*
 * settings_apply — recon FUN_00112182. Copy edited gadget buffers back to config and
 * push serial params. Numeric fields are range-checked before being accepted
 * (baud 75..9600, data bits 2..99), matching the original's guards.
 */
static void settings_apply(void)
{
    LONG v;
    /* Copy the edited buffers back to config. recon src->dst (strcpy $1124ba):
     *   0x1217ec -> 0x120108   phone   buffer -> g_phone_number
     *   0x121805 -> 0x12011c   modem   buffer -> g_modem_name
     *   0x1217fc -> 0x120134   userid  buffer -> g_cfg_userid (after uppercasing it)
     *   0x120134 -> 0x120244   config userid  -> g_login_userid
     * The modem buffer (0x1217fc) is uppercased in place first (recon $11246c ->
     * FUN_0011513a). */
    strcpy(g_phone_number, GBUF_PHONE);
    strcpy(g_modem_name,   GBUF_USERID);
    str_upper(GBUF_MODEM);
    strcpy(g_cfg_userid,   GBUF_MODEM);
    strcpy(g_login_userid, g_cfg_userid);

    /* Numeric fields: read the gadget's PARSED value (StringInfo.LongInt in the blob),
     * range-check, store as a WORD (recon reads move.l $24aa/$2436/$23c2(a4)). */
    v = LI_BAUDUP; if (v >= 0x4b && v <= 0x2580) g_baud_up   = (UWORD)v;  /* 75..9600 */
    v = LI_BAUDDN; if (v >= 0x4b && v <= 0x2580) g_baud_down = (UWORD)v;
    v = LI_DBITS;  if (v >= 2    && v <= 0x63)   g_data_bits = (UWORD)v;  /* 2..99    */

    if (SET_TOGGLE == 0) g_open_flags &= ~4;
    else                 g_open_flags |= 4;

    apply_serial_params(g_data_bits);
}

/* The Diagnostics toggle gadget (0x11f356) and where RemoveGList's returned position is
 * stashed (0x12182c). Verified from settings_dialog's toggle branches (0x112344 /
 * 0x1123b2 in the relocated disasm). */
#define TOG_GADGET     ((struct Gadget *)DATA(0x11f356))
#define TOG_POS        DW(0x12182c)

/*
 * settings_toggle — recon settings_dialog cases 4 (ON) and 6 (OFF). Flip the Diagnostics
 * toggle EXACTLY as the original: RemoveGList the single toggle gadget (saving its
 * position), swap its GadgetRender/SelectRender imagery, AddGList it back at that
 * position, then RefreshGList just that gadget. (No whole-list refresh — that was an
 * unverified simplification and has been removed.)
 */
static void settings_toggle(struct Window *w, int on)
{
    /* Operate on 2 gadgets (the ON/OFF toggle pair starting at 0x11f356) — verified
     * count 2 in the recon (RemoveGList/AddGList/RefreshGList all `pea $2.w`). */
    SET_TOGGLE = on ? 1 : 0;
    TOG_POS = RemoveGList(w, TOG_GADGET, 2);         /* $1124a8: remove 2, save pos  */
    if (on) {
        DL(TOG_GADGET_R) = TOG_ON_RENDER;            /* 0x11f370 = 0x11f328          */
        DL(TOG_GADGET_S) = TOG_ON_SEL;               /* 0x11f310 = 0x11f2e2          */
    } else {
        DL(TOG_GADGET_R) = TOG_OFF_RENDER;           /* 0x11f370 = 0x11f342          */
        DL(TOG_GADGET_S) = TOG_OFF_SEL;              /* 0x11f310 = 0x11f2b0          */
    }
    AddGList(w, TOG_GADGET, (ULONG)(UWORD)TOG_POS, 2, NULL);  /* $11245a: re-add 2   */
    RefreshGList(TOG_GADGET, w, NULL, 2);             /* $11244e: refresh 2 gadgets   */
}

/*
 * settings_dialog — recon FUN_001122a6. The "Setup" menu handler.
 */
LONG settings_dialog(void)
{
    struct Window *w;
    struct IntuiMessage *msg;
    struct Gadget *g;
    WORD id;

    if (!settings_open())
        return 0;
    w = (struct Window *)SET_WIN;

    for (;;) {
        WaitPort(w->UserPort);
        g = NULL;
        while ((msg = (struct IntuiMessage *)GetMsg(w->UserPort)) != NULL) {
            g = (struct Gadget *)msg->IAddress;   /* keep last (recon reads +0x1c) */
            ReplyMsg((struct Message *)msg);
        }
        if (g == NULL)
            continue;
        id = g->GadgetID;                          /* recon reads +0x26 */
        if (id >= 7)                               /* out of range -> keep looping */
            continue;

        /* GadgetID dispatch — VERIFIED against the recon jump table at 0x112310
         * (index = GadgetID). The IDs are NOT in button order:
         *   0 = Cancel, 1 = Use (apply only), 4 = Save (apply + write file),
         *   3 = ActivateGadget (Tab to next string field), 5 = toggle ON, 6 = toggle OFF. */
        switch (id) {
        case 0:  /* recon 0x11241e — Cancel: close, discard, return 0 */
            settings_close();
            return 0;
        case 1:  /* recon 0x112426 — Use: apply, close, return 1 (no file write) */
            settings_apply();
            settings_close();
            return 1;
        case 4:  /* recon 0x112432 — Save: apply, write file, close, return 1 */
            settings_apply();
            save_config_file();
            settings_close();
            return 1;
        case 3:  /* recon 0x11232c — ActivateGadget: move to the clicked string gadget */
            ActivateGadget(g, w, NULL);
            break;
        case 5:  /* recon 0x112344 — Diagnostics toggle ON (only if currently off) */
            if (SET_TOGGLE == 0) settings_toggle(w, 1);
            break;
        case 6:  /* recon 0x1123b2 — Diagnostics toggle OFF (only if currently on) */
            if (SET_TOGGLE != 0) settings_toggle(w, 0);
            break;
        default: /* 2 and any other — no action (recon loops back) */
            break;
        }
    }
}
