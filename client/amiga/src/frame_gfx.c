/*
 * frame_gfx.c — frame offscreen-bitmap graphics layer (reconstructed).
 *
 *   frame_offscreen_begin (FUN_001060f6) — init a 320x192 4-plane offscreen BitMap
 *                         (0x140 x 0xc0 bits), AllocMem the 4 planes (0x1e00 each),
 *                         and flag offscreen drawing on. On failure it falls back to
 *                         direct-to-window drawing (g_offscreen = 0).
 *   frame_offscreen_end   (FUN_0010617c) — BltBitMapRastPort the offscreen bitmap to
 *                         the window rastport and free the planes.
 *   frame_border          (FUN_001061e8) — draw the frame's border Image, sizing a
 *                         shared Image struct to the cell rectangle.
 *   blt_font_to_rastport  — the direct-draw path used by blit_char_cell when not
 *                         offscreen (GfxBase.BltBitMapRastPort of the assembled cell).
 *
 * These wrap graphics.library. The BitMap/RastPort/Image structures are the ones the
 * original kept in its data section; here they are real typed statics.
 */
#include <exec/types.h>
#include <exec/memory.h>
#include <graphics/gfx.h>
#include <graphics/rastport.h>
#include <intuition/intuition.h>
#include <clib/exec_protos.h>
#include <clib/graphics_protos.h>

#include "compunet.h"

#define FRAME_W   0x140   /* 320 px */
#define FRAME_H   0xc0    /* 192 px */
#define PLANE_SZ  0x1e00  /* bytes per bitplane (320/8 * 192) */
#define NPLANES   4

/* Offscreen bitmap + its own RastPort (recon DAT_00120284 / DAT_001202ac). */
static struct BitMap   g_offscreen_bm;   /* DAT_00120284 */
static struct RastPort g_offscreen_rp;   /* DAT_001202ac */

/* Shared Image used to stamp the border (recon DAT_0011d9ac + its size words). */
static struct Image    g_border_image;   /* DAT_0011d9ac */

extern UBYTE  g_offscreen;               /* DAT_0011d9a8 — 1 = offscreen active */
extern UBYTE *g_plane_dst[4];            /* DAT_0012028c — the 4 plane pointers  */

/* resource_mark / resource_commit / cleanup_resources declared in compunet.h. */
extern APTR alloc_tracked(ULONG size, ULONG flags);  /* thunk FUN_0011a1ee */
extern void free_tracked(APTR ptr);                  /* thunk FUN_0011a238 */

/*
 * frame_offscreen_begin — recon FUN_001060f6. Prepare the offscreen bitmap: init the
 * RastPort + BitMap, allocate 4 chip-mem planes (resource-tracked), and set the
 * offscreen flag. If any plane fails, unwind and draw straight to the window.
 */
void frame_offscreen_begin(void)
{
    int i;

    InitRastPort(&g_offscreen_rp);
    InitBitMap(&g_offscreen_bm, NPLANES, FRAME_W, FRAME_H);
    g_offscreen_rp.BitMap = &g_offscreen_bm;

    resource_mark();
    for (i = 0; i < NPLANES; i++) {
        g_plane_dst[i] = (UBYTE *)alloc_tracked(PLANE_SZ, MEMF_CHIP | MEMF_CLEAR);
        g_offscreen_bm.Planes[i] = (PLANEPTR)g_plane_dst[i];
        if (g_plane_dst[i] == NULL) {
            cleanup_resources();
            g_offscreen = 0;    /* fall back to direct draw */
            return;
        }
    }
    resource_commit();
    g_offscreen = 1;
}

/*
 * frame_offscreen_end — recon FUN_0010617c. Blit the assembled offscreen bitmap into
 * the frame window's rastport, then free the planes and clear the flag.
 */
void frame_offscreen_end(APTR page)
{
    struct Window *win = *(struct Window **)page;   /* page[0] -> window */
    int i;

    if (g_offscreen != 0) {
        BltBitMapRastPort(&g_offscreen_bm, 0, 0, win->RPort, 4, 10,
                          FRAME_W, FRAME_H, 0xc0);
        for (i = 0; i < NPLANES; i++)
            free_tracked(g_plane_dst[i]);
        g_offscreen = 0;
    }
}

/*
 * frame_border — recon FUN_001061e8. Size the shared border Image to the given cell
 * rectangle and DrawImage it, either into the window (direct) or the offscreen
 * bitmap. Cell coords are 8px each; the window path offsets by (4,10).
 */
void frame_border(int r0, int c0, int r1, int c1, APTR page)
{
    struct Window *win = *(struct Window **)page;

    g_border_image.Depth  = *(UBYTE *)((UBYTE *)page + 0x0f);  /* background colour */
    g_border_image.Height = (UWORD)(((r1 - r0) + 1) * 8);
    g_border_image.Width  = (UWORD)(((c1 - c0) + 1) * 8);

    if (g_offscreen == 0)
        DrawImage(win->RPort, &g_border_image, c0 * 8 + 4, r0 * 8 + 10);
    else
        DrawImage((struct RastPort *)&g_offscreen_rp, &g_border_image, c0 << 3, r0 << 3);
}

/*
 * blt_font_to_rastport — the direct-to-window cell draw used by blit_char_cell when the
 * offscreen bitmap is inactive (`g_offscreen == 0`). This is the path the login welcome
 * frame and every command frame take (frame_display does NOT set up the offscreen).
 *
 * Faithful to the original inline direct-draw (recon FUN_00107000 @0x10710e-0x10714a):
 *   BltBitMapRastPort(g_cell_bm, 0, 0, win->RPort, col*8+4, row*8+10, 8, 8, 0xc0)
 * where g_cell_bm is an 8x8 4-plane BitMap whose planes point at the assembled cell
 * (g_plane_src[], filled by blit_char_cell). The font stores each 8px row in 2 bytes,
 * so BytesPerRow = 2 (InitBitMap(width=8)).
 *
 * (An earlier reconstruction left this a no-op, so with the offscreen inactive nothing
 * was ever drawn — the frame window stayed blank.)
 */
extern UBYTE *g_plane_src[4];
struct BitMap g_cell_bm;   /* small 8x8 assembly bitmap the caller fills */

void blt_font_to_rastport(WORD row, WORD col, APTR page)
{
    struct Window *win = *(struct Window **)page;   /* page[0] -> window */
    int i;

    InitBitMap(&g_cell_bm, NPLANES, 8, 8);          /* BytesPerRow=2, Rows=8, Depth=4 */
    for (i = 0; i < NPLANES; i++)
        g_cell_bm.Planes[i] = (PLANEPTR)g_plane_src[i];

    BltBitMapRastPort(&g_cell_bm, 0, 0, win->RPort,
                      col * 8 + 4, row * 8 + 10, 8, 8, 0xc0);
}
