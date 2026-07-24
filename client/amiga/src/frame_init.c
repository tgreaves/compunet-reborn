/*
 * frame_init.c — frame-window button bar: build the 6 gadgets + highlight lock.
 *
 * frame_preinit  (recon FUN_00117000) builds the 6 frame-window button gadgets
 *     (Next/Last/More/All/Send/Done) into the frame page buffer at frame+0x790, stride
 *     0x34 — the reader/editor control bar. Parallels dir_preinit.
 * frame_lock     (recon FUN_001170be) toggles the COMPLEMENT highlight box around one
 *     button (like link_lock for the directory bar), for pressed-button feedback.
 *
 * Verified against the relocated disassembly of FUN_00117000 / FUN_001170be, with
 * a4 = DATA_BASE (0x11d000): GadgetRender 0x11fa6e, labels 0x11faa4 (stride 0x14),
 * handler table 0x11fb1c (we bind our C hooks instead of the original code addresses).
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/graphics_protos.h>

#include "compunet.h"

extern APTR GfxBase;
extern UBYTE g_data[];
#define DATA_BASE 0x11d000
#define DATA(off) ((APTR)(g_data + ((off) - DATA_BASE)))

/* The 6 frame-button handlers. Original: static blob table 0x2b1c(a4)=0x11fb1c holding
 * FUN_001172f4.. ; we bind our reconstructed C hooks. */
extern LONG hook_ed_172f4(APTR);   /* Next */
extern LONG hook_ed_1733a(APTR);   /* Last */
extern LONG hook_ed_17380(APTR);   /* More */
extern LONG hook_ed_173c6(APTR);   /* All  */
extern LONG hook_ed_1740c(APTR);   /* Send */
extern LONG hook_ed_17470(APTR);   /* Done */

static APTR const g_frame_handlers[6] = {
    (APTR)hook_ed_172f4, (APTR)hook_ed_1733a, (APTR)hook_ed_17380,
    (APTR)hook_ed_173c6, (APTR)hook_ed_1740c, (APTR)hook_ed_17470
};

/*
 * frame_preinit — recon FUN_00117000. Build the 6 frame button gadgets into the frame
 * page buffer. NextGadget links backward so the chain head is the row-5 gadget
 * (page + 0x894), which open_frame_window writes into the NewWindow FirstGadget field.
 */
void frame_preinit(APTR page_v)
{
    UBYTE *page = (UBYTE *)page_v;
    UBYTE *g, *prev = NULL;
    int i;
    for (i = 0; i < 6; i++) {
        g = page + 0x790 + i * 0x34;
        *(APTR  *)(g + 0x00) = (APTR)prev;            /* NextGadget = prev             */
        *(UWORD *)(g + 0x04) = (UWORD)(i * 0x36 + 7); /* LeftEdge = i*54 + 7           */
        *(UWORD *)(g + 0x06) = 0x00cb;                /* TopEdge = 203                 */
        *(UWORD *)(g + 0x08) = 0x0032;                /* Width = 50                    */
        *(UWORD *)(g + 0x0a) = 0x0010;                /* Height = 16                   */
        *(UWORD *)(g + 0x0c) = 0x0107;                /* Flags = GADGIMAGE|HNONE|DISABLED */
        *(UWORD *)(g + 0x0e) = 0x0102;                /* Activation = GADGIMMEDIATE|TOGGLE */
        *(UWORD *)(g + 0x10) = 0x0001;                /* GadgetType = BOOLGADGET       */
        *(APTR  *)(g + 0x12) = DATA(0x11fa6e);        /* GadgetRender (shared image)   */
        *(APTR  *)(g + 0x16) = NULL;                  /* SelectRender                  */
        *(APTR  *)(g + 0x1a) = (APTR)((UBYTE *)DATA(0x11faa4) + i * 0x14); /* GadgetText */
        *(APTR  *)(g + 0x1e) = NULL;                  /* MutualExclude                 */
        *(APTR  *)(g + 0x22) = NULL;                  /* SpecialInfo                   */
        *(UWORD *)(g + 0x26) = (UWORD)i;              /* GadgetID = button index       */
        *(APTR  *)(g + 0x28) = NULL;                  /* UserData                      */
        *(APTR  *)(g + 0x2c) = g_frame_handlers[i];   /* handler (recon *(0x11fb1c+i*4)) */
        *(APTR  *)(g + 0x30) = page_v;                /* page pointer                  */
        prev = g;
    }
}

/*
 * frame_lock — recon FUN_001170be. COMPLEMENT highlight box around frame button 'row'
 * (x = row*0x36+7 .. row*0x36+0x38, y = 203..218), toggled before/after the action.
 */
void frame_lock(APTR frame_page, int row)
{
    struct Window   *win = *(struct Window **)frame_page;
    struct RastPort *rp  = win->RPort;
    LONG x0 = row * 0x36 + 7;
    LONG x1 = row * 0x36 + 0x38;
    SetDrMd(rp, COMPLEMENT);                 /* recon $117634(rp, 2)                 */
    RectFill(rp, x0, 0xcb, x1, 0xda);        /* recon $11761c(rp, x0, 203, x1, 218)  */
}
