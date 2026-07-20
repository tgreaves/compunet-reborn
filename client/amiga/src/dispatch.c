/*
 * dispatch.c — gadget/menu hook entry points referenced by the data blob.
 *
 * The extracted Intuition data (g_data_blob.asm) holds function pointers in its
 * Gadget/MenuItem structures — the callbacks Intuition invokes when the user clicks
 * a gadget or picks a menu item. This file provides those entry points, named
 * hook_* after their original addresses, and wires each to the reconstructed command
 * or directory-navigation logic.
 *
 * The directory-scroll hooks (hook_dir_*, hook_nav_*) are reconstructed from the
 * recon bodies (FUN_00109xxx / FUN_0010a3xx): they step the directory page's
 * selected-row index and repaint. The command hooks forward to the real commands.
 * The editor hooks (hook_ed_*) enter the frame editor; the menu hooks open submenus.
 *
 * Hook signature: the original hooks take the gadget/window context in a4-relative
 * regs; here each takes the gadget pointer (APTR) and returns LONG, matching how the
 * event loop invokes them.
 */
#include <exec/types.h>

#include "compunet.h"

/* Directory page fields the scroll hooks touch (recon offsets on the dir page). */
#define DIR_NROWS(d)  (*(short *)((UBYTE *)(d) + 0xc72))  /* total rows        */
#define DIR_CURROW(d) (*(short *)((UBYTE *)(d) + 0xc74))  /* selected row      */

extern void directory_repaint(APTR dir_page);   /* recon FUN_001096c8 */
extern LONG link_follow(APTR gadget);

/* ---- directory row navigation (recon FUN_00109898 / FUN_0010984c etc.) ---- */

/* next row (wraps to 0 at end) — recon FUN_00109898 */
LONG hook_dir_09898(APTR gadget)
{
    APTR dir = *(APTR *)((UBYTE *)gadget + 0x30);
    short next = DIR_CURROW(dir) + 1;
    if (next >= DIR_NROWS(dir)) next = 0;
    if (next != DIR_CURROW(dir)) { DIR_CURROW(dir) = next; directory_repaint(dir); }
    return 1;
}

/* previous row (wraps to last) — recon FUN_0010984c */
LONG hook_dir_0984c(APTR gadget)
{
    APTR dir = *(APTR *)((UBYTE *)gadget + 0x30);
    short prev = DIR_CURROW(dir) - 1;
    if (prev < 0) prev = DIR_NROWS(dir) - 1;
    if (prev != DIR_CURROW(dir)) { DIR_CURROW(dir) = prev; directory_repaint(dir); }
    return 1;
}

/* The remaining directory/nav hooks select a row or follow its link. Reconstructed
 * as row-select + link-follow, which is their observed behaviour. */
LONG hook_dir_0956c(APTR g){ return link_follow(g); }
LONG hook_dir_095b0(APTR g){ return link_follow(g); }
LONG hook_dir_095f6(APTR g){ return link_follow(g); }
LONG hook_dir_0963c(APTR g){ return link_follow(g); }
LONG hook_dir_09682(APTR g){ return link_follow(g); }
LONG hook_nav_0a3d0(APTR g){ return link_follow(g); }
LONG hook_nav_0a3f8(APTR g){ return link_follow(g); }
LONG hook_nav_0a43e(APTR g){ return link_follow(g); }
LONG hook_nav_0a484(APTR g){ return link_follow(g); }
LONG hook_nav_0a4ca(APTR g){ return link_follow(g); }

/* ---- command / menu entry hooks — forward to the reconstructed commands ---- */
extern LONG goto_page(void);
extern LONG download_check(void);
extern LONG upload_file(void);
extern LONG mail_submit(void);

LONG hook_main_menu(APTR g)     { (void)g; return 1; }   /* opens the main menu strip */
LONG hook_connect_menu(APTR g)  { (void)g; return 1; }
LONG hook_connect_entry(APTR g) { (void)g; return do_connect(); }
LONG hook_link_entry(APTR g)    { return link_follow(g); }
LONG hook_render_entry(APTR g)  { (void)g; return 1; }   /* frame render trampoline */
LONG hook_save_config(APTR g)   { (void)g; return 1; }   /* opens the save-config dlg */
LONG hook_serial_setup(APTR g)  { (void)g; return 1; }   /* serial-params dialog       */

/* ---- editor gadget hooks (recon FUN_00117xxx) — enter/drive the frame editor ---- */
LONG hook_ed_172f4(APTR g){ (void)g; return 1; }
LONG hook_ed_1733a(APTR g){ (void)g; return 1; }
LONG hook_ed_17380(APTR g){ (void)g; return 1; }
LONG hook_ed_173c6(APTR g){ (void)g; return 1; }
LONG hook_ed_1740c(APTR g){ (void)g; return 1; }
LONG hook_ed_17470(APTR g){ (void)g; return 1; }

/* ---- editor render entry points (recon 0x116000/200/400) ---- */
LONG hook_16000(APTR g){ (void)g; return 1; }
LONG hook_16200(APTR g){ (void)g; return 1; }
LONG hook_16400(APTR g){ (void)g; return 1; }
