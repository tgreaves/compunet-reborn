/*
 * directory_init.c — dir_preinit: build the directory page's clickable gadget array.
 *
 * Recon FUN_00109000 (498 bytes). Initialises three groups of Intuition Gadget structures
 * embedded in the directory page buffer (BSS at g_dir_page_buf):
 *   Group 1: 11 content-row gadgets at page+0xc7a, stride 0x34 — the clickable rows.
 *   Group 2:  5 action gadgets     at page+0xeb6, stride 0x34 — action buttons.
 *   Group 3:  2 navigation gadgets at page+0xfba, stride 0x34 — page up/down.
 *
 * Each gadget is 0x34 bytes (standard Intuition Gadget = 0x2e + a 6-byte tail holding
 * the handler pointer at +0x2c and the page pointer at +0x30). The handler is called by
 * the event loop when the gadget is clicked.
 *
 * Group 1's handler is dir_select (FUN_0010935a) — the directory-row click dispatcher.
 * Groups 2/3 handlers come from tables in the data blob; they're zero in the flat image
 * (filled at runtime by the server's directory response via parse_directory_frame).
 *
 * Verified byte-for-byte against the relocated disassembly of FUN_00109000.
 */
#include <exec/types.h>
#include "compunet.h"

extern LONG dir_select(APTR gadget, LONG mode); /* FUN_0010935a — row click handler */
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

/* Group 2 (action) and group 3 (nav) gadget handlers. In the original these come from
 * static blob pointer tables — action: 0x133e(a4)=0x11e33e (5 longs), nav:
 * 0x1352(a4)=0x11e352 (2 longs), with a4 = DATA_BASE (0x11d000) — holding the original
 * code addresses FUN_0010956c.. and FUN_0010984c.. We bind our reconstructed C
 * equivalents instead (the blob table's addresses point into the *original* binary,
 * not our code). Labels (0x11e2da) decode to "Dir/Back/Goto/Dnld/Upld", confirming the
 * base. NOTE: an earlier audit mis-set a4 to 0x11f000, landing these tables on empty
 * BSS at 0x12033e/0x120352 and the render/text on 0x11f212/0x11feda — so the action
 * buttons had null handlers and wrong labels. */
extern LONG hook_dir_0956c(APTR);   /* Dir  -> goto_page  (FUN_0010956c) */
extern LONG hook_dir_095b0(APTR);   /* Back -> back_dir   (FUN_001095b0) */
extern LONG hook_dir_095f6(APTR);   /* Goto -> link_goto  (FUN_001095f6) */
extern LONG hook_dir_0963c(APTR);   /* Dnld -> download   (FUN_0010963c) */
extern LONG hook_dir_09682(APTR);   /* Upld -> upload     (FUN_00109682) */
extern LONG hook_dir_0984c(APTR);   /* nav row prev       (FUN_0010984c) */
extern LONG hook_dir_09898(APTR);   /* nav row next       (FUN_00109898) */

static APTR const g_dir_action_handlers[5] = {
    (APTR)hook_dir_0956c, (APTR)hook_dir_095b0, (APTR)hook_dir_095f6,
    (APTR)hook_dir_0963c, (APTR)hook_dir_09682
};
static APTR const g_dir_nav_handlers[2] = {
    (APTR)hook_dir_0984c, (APTR)hook_dir_09898   /* [0]=prev, [1]=next (recon 0x11e352) */
};

/*
 * dir_preinit — recon FUN_00109000. Builds all directory gadgets into the page buffer.
 */
void dir_preinit(APTR page_v)
{
    UBYTE *page = (UBYTE *)page_v;
    UBYTE *g;
    UBYTE *prev;
    int i;

    /* ---- Group 1: 11 content-row gadgets (page+0xc7a, stride 0x34) ---- */
    prev = NULL;
    for (i = 0; i < 11; i++) {
        g = page + 0xc7a + i * 0x34;
        *(APTR *)(g + 0x00) = (APTR)prev;       /* NextGadget = previous (linked list) */
        *(UWORD *)(g + 0x04) = 0x0c;            /* LeftEdge = 12 */
        *(UWORD *)(g + 0x06) = (UWORD)(i * 8 + 0x5a); /* TopEdge = i*8 + 90 */
        *(UWORD *)(g + 0x08) = 0x0130;          /* Width = 304 */
        *(UWORD *)(g + 0x0a) = 0x08;            /* Height = 8 */
        *(UWORD *)(g + 0x0c) = 0x0003;          /* Flags = GADGHCOMP|GADGHNONE? (3) */
        *(UWORD *)(g + 0x0e) = 0x0102;          /* Activation = RELVERIFY|GADGIMMEDIATE */
        *(UWORD *)(g + 0x10) = 0x0001;          /* GadgetType = BOOLGADGET */
        *(APTR *)(g + 0x12) = NULL;             /* GadgetRender */
        *(APTR *)(g + 0x16) = NULL;             /* SelectRender */
        *(APTR *)(g + 0x1a) = NULL;             /* GadgetText */
        *(APTR *)(g + 0x1e) = NULL;             /* MutualExclude */
        *(APTR *)(g + 0x22) = NULL;             /* SpecialInfo */
        *(UWORD *)(g + 0x26) = (UWORD)i;       /* GadgetID = row index */
        *(APTR *)(g + 0x28) = NULL;             /* UserData */
        *(APTR *)(g + 0x2c) = (APTR)dir_select; /* handler (recon: lea $10935a,a1) */
        *(APTR *)(g + 0x30) = page_v;           /* page pointer (recon: move.l arg,+0x30) */
        prev = g;
    }

    /* ---- Group 2: 5 action gadgets (page+0xeb6, stride 0x34) ---- */
    for (i = 0; i < 5; i++) {
        g = page + 0xeb6 + i * 0x34;
        *(APTR *)(g + 0x00) = (APTR)prev;
        *(UWORD *)(g + 0x04) = (UWORD)(i * 0x40 + 7);  /* LeftEdge = i*64 + 7 */
        *(UWORD *)(g + 0x06) = 0x00cb;          /* TopEdge = 203 */
        *(UWORD *)(g + 0x08) = 0x003c;          /* Width = 60 */
        *(UWORD *)(g + 0x0a) = 0x0010;          /* Height = 16 */
        *(UWORD *)(g + 0x0c) = 0x0107;          /* Flags = GADGIMAGE|GADGHIMAGE|... */
        *(UWORD *)(g + 0x0e) = 0x0102;          /* Activation */
        *(UWORD *)(g + 0x10) = 0x0001;          /* GadgetType */
        *(APTR *)(g + 0x12) = DATA(0x11e212);   /* GadgetRender — shared button image (recon 0x1212(a4)) */
        *(APTR *)(g + 0x16) = NULL;             /* SelectRender */
        /* GadgetText: per-action IntuiText label (Dir/Back/Goto/Dnld/Upld) at
         * 0x11e2da, stride 0x14 (recon 0x12da(a4) + i*0x14). */
        *(APTR *)(g + 0x1a) = (APTR)((UBYTE *)DATA(0x11e2da) + i * 0x14);
        *(APTR *)(g + 0x1e) = NULL;
        *(APTR *)(g + 0x22) = NULL;
        *(UWORD *)(g + 0x26) = (UWORD)i;
        *(APTR *)(g + 0x28) = NULL;
        *(APTR *)(g + 0x2c) = g_dir_action_handlers[i]; /* Dir/Back/Goto/Dnld/Upld handler */
        *(APTR *)(g + 0x30) = page_v;
        prev = g;
    }

    /* ---- Group 3: 2 navigation gadgets (page+0xfba, stride 0x34) ---- */
    for (i = 0; i < 2; i++) {
        g = page + 0xfba + i * 0x34;
        *(APTR *)(g + 0x00) = (APTR)prev;
        *(UWORD *)(g + 0x04) = (UWORD)(i * 0x20 + 0xfc); /* LeftEdge = i*32 + 252 */
        *(UWORD *)(g + 0x06) = 0x00b2;          /* TopEdge = 178 */
        *(UWORD *)(g + 0x08) = 0x0020;          /* Width = 32 */
        *(UWORD *)(g + 0x0a) = 0x0008;          /* Height = 8 */
        *(UWORD *)(g + 0x0c) = 0x0003;          /* Flags */
        *(UWORD *)(g + 0x0e) = 0x0102;          /* Activation */
        *(UWORD *)(g + 0x10) = 0x0001;          /* GadgetType */
        *(APTR *)(g + 0x12) = NULL;
        *(APTR *)(g + 0x16) = NULL;
        *(APTR *)(g + 0x1a) = NULL;
        *(APTR *)(g + 0x1e) = NULL;
        *(APTR *)(g + 0x22) = NULL;
        *(UWORD *)(g + 0x26) = (UWORD)i;
        *(APTR *)(g + 0x28) = NULL;
        *(APTR *)(g + 0x2c) = g_dir_nav_handlers[i]; /* nav row prev/next handler */
        *(APTR *)(g + 0x30) = page_v;
        prev = g;
    }
}
