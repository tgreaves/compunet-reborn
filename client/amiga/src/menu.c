/*
 * menu.c — Intuition menu-strip builder (reconstructed, faithful).
 *
 *   build_menu_strip (FUN_0011b000, 1144 bytes) — turn the client's compact menu
 *                    *spec* (a packed table in the data blob at 0x11d172) into a live
 *                    Intuition Menu / MenuItem / IntuiText tree, plus a parallel
 *                    "command map" that lets a MENUPICK number be dispatched straight
 *                    to its handler function.
 *   menu_dispatch    (FUN_0011b478, 52 bytes) — given a MENUPICK menu-number word,
 *                    walk the command map, find the matching entry, and call its
 *                    handler.
 *
 * TRANSCRIPTION NOTES (this is a faithful reconstruction, not an approximation):
 *   - Control flow is transcribed from the Ghidra decompile (recon FUN_0011b000).
 *   - Every value the decompiler dropped was recovered from the raw m68k
 *     disassembly of $11b000..$11b477: each thunk_FUN_00101604 call is the 16x16
 *     multiply helper ($11b4ac), so the coordinates are plain integer arithmetic
 *     (menu LeftEdge = menu*100+10, item TopEdge = item*10, subitem TopEdge =
 *     sub*10+5), and the alloc/mark/commit/cleanup thunks are the resource tracker.
 *   - The struct field offsets used by the original (Menu 0x1e, MenuItem 0x22,
 *     IntuiText 0x14) match the standard Intuition layouts exactly, so we set fields
 *     by name; the spec entry, however, is a packed 14-byte (0xe) record with no C
 *     alignment, so it is walked with a raw byte cursor.
 *
 * Spec layout (each record is 0xe = 14 bytes):
 *   +0x0  APTR  text     — MenuName (for a menu) / IText string (for an item)
 *   +0x4  LONG  count    — child count: items in a menu / subitems in an item
 *   +0x8  APTR  handler  — command handler fn (0 = none; only then a map entry)
 *   +0xc  UBYTE cmd      — command-key char (0 = none); also stored as Command
 *   +0xd  UBYTE pad
 * The first record is a header; only its +0x4 (menu count) is used, then the cursor
 * advances 0xe to the first menu record. Records are laid out depth-first:
 * menu, its items (each optionally followed by its subitems), next menu, ...
 *
 * Command map: 0x600 bytes = 256 entries of 6 bytes [UWORD number][ULONG handler],
 * terminated by a 0xffff number. The number word is the Intuition menu-number
 * encoding: bits 0-4 menu, bits 5-10 item, bits 11-15 subitem. Items with no
 * subitem set the subitem field to 0x1f (0xf800), matching NOSUB/MENUNULL.
 */
#include <exec/types.h>
#include <intuition/intuition.h>
#include <clib/exec_protos.h>

#include "compunet.h"

/* Resource tracker (resource_mark / resource_commit / cleanup_resources are
 * declared in compunet.h — recon FUN_0011a000 / a00a / a0b0). */
extern APTR  alloc_tracked(ULONG size, ULONG flags); /* FUN_0011a1ee */

/* Packed 14-byte spec record — walked with a byte cursor (no C alignment). */
#define SPEC_STRIDE     0x0e
#define SPEC_TEXT(p)    (*(APTR  *)((UBYTE *)(p) + 0x0))
#define SPEC_COUNT(p)   (*(LONG  *)((UBYTE *)(p) + 0x4))
#define SPEC_HANDLER(p) (*(APTR  *)((UBYTE *)(p) + 0x8))
#define SPEC_CMD(p)     (*(UBYTE *)((UBYTE *)(p) + 0xc))

/* The 2-word result the caller reads: [0] = Menu list, [1] = command map. */
static APTR g_menu_result[2];

/* Initialise one IntuiText for a (sub)item label: FrontPen 0, BackPen 1, JAM1,
 * origin 0,0, default font, IText = the spec's string. (recon: the 0x14-byte init
 * block written for each local_40 / local_44.) */
static void init_itext(struct IntuiText *it, APTR text)
{
    it->FrontPen  = 0;
    it->BackPen   = 1;
    it->DrawMode  = 0;
    it->LeftEdge  = 0;
    it->TopEdge   = 0;
    it->ITextFont = NULL;
    it->IText     = (UBYTE *)text;
    it->NextText  = NULL;
}

APTR build_menu_strip(APTR spec)
{
    struct Menu     *menus = NULL;   /* local_50 — Menu array / result[0] */
    UBYTE           *map   = NULL;   /* local_4c — command map / result[1] */
    UBYTE           *mp;             /* local_48 — write cursor into map   */
    UBYTE           *sp;             /* param_1  — spec record cursor      */
    LONG             nmenus;         /* local_8                            */
    struct Menu     *m;              /* local_24                           */
    LONG             mi;             /* local_c  — menu index              */

    /* Empty spec -> empty result. */
    nmenus = *(LONG *)((UBYTE *)spec + 0x4);
    if (nmenus == 0) {
        g_menu_result[0] = NULL;
        g_menu_result[1] = NULL;
        return g_menu_result;
    }

    sp = (UBYTE *)spec + SPEC_STRIDE;   /* skip header to first menu record */
    resource_mark();

    /* Command map (fixed 0x600 bytes). */
    map = (UBYTE *)alloc_tracked(0x600, 0);
    if (map == NULL) {
        cleanup_resources();
        g_menu_result[0] = NULL;
        g_menu_result[1] = NULL;
        return g_menu_result;
    }
    mp = map;

    /* Menu array (one struct Menu per menu). */
    menus = (struct Menu *)alloc_tracked((ULONG)nmenus * 0x1e, 0);
    if (menus == NULL) {
        cleanup_resources();
        g_menu_result[0] = NULL;
        g_menu_result[1] = map;
        return g_menu_result;
    }

    m = menus;
    for (mi = 0; mi < nmenus; mi++) {
        struct MenuItem *items;
        struct IntuiText *itexts;
        struct MenuItem *it;
        struct IntuiText *itx;
        LONG nitems, ii;

        m->NextMenu = (mi + 1 == nmenus) ? NULL : (struct Menu *)((UBYTE *)m + 0x1e);
        m->LeftEdge = (WORD)(mi * 100 + 10);
        m->TopEdge  = 0;
        m->Width    = 100;
        m->Height   = 10;
        m->Flags    = 1;                 /* MENUENABLED */
        m->MenuName = (BYTE *)SPEC_TEXT(sp);
        nitems      = SPEC_COUNT(sp);

        items  = (struct MenuItem  *)alloc_tracked((ULONG)nitems * 0x22, 0);
        itexts = (struct IntuiText *)alloc_tracked((ULONG)nitems * 0x14, 0);
        if (items == NULL || itexts == NULL) {
            cleanup_resources();
            g_menu_result[0] = NULL;
            g_menu_result[1] = map;
            return g_menu_result;
        }
        m->FirstItem = items;
        sp += SPEC_STRIDE;               /* advance to first item record */

        it  = items;
        itx = itexts;
        for (ii = 0; ii < nitems; ii++) {
            UWORD flags = (SPEC_CMD(sp) == 0) ? 0x52 : 0x56;  /* +COMMSEQ if a key */
            LONG  nsub;

            it->NextItem      = (ii + 1 == nitems) ? NULL
                                                   : (struct MenuItem *)((UBYTE *)it + 0x22);
            it->LeftEdge      = 0;
            it->TopEdge       = (WORD)(ii * 10);
            it->Width         = 100;
            it->Height        = 10;
            it->Flags         = flags;
            it->MutualExclude = 0;
            it->ItemFill      = (APTR)itx;
            it->SelectFill    = NULL;
            it->Command       = (BYTE)SPEC_CMD(sp);
            init_itext(itx, SPEC_TEXT(sp));

            /* If this item carries a handler, add a command-map entry. */
            if (SPEC_HANDLER(sp) != NULL) {
                *(UWORD *)(mp + 0) = (UWORD)(((ii & 0x3f) << 5) | (mi & 0x1f) | 0xf800);
                *(ULONG *)(mp + 2) = (ULONG)SPEC_HANDLER(sp);
                mp += 6;
            }

            nsub = SPEC_COUNT(sp);
            sp += SPEC_STRIDE;           /* advance past this item record */

            if (nsub == 0) {
                it->SubItem = NULL;
            } else {
                struct MenuItem  *sub;
                struct IntuiText *stx;
                struct MenuItem  *s;
                struct IntuiText *sx;
                LONG si;

                sub = (struct MenuItem  *)alloc_tracked((ULONG)nsub * 0x22, 0);
                stx = (struct IntuiText *)alloc_tracked((ULONG)nsub * 0x14, 0);
                if (sub == NULL || stx == NULL) {
                    cleanup_resources();
                    g_menu_result[0] = NULL;
                    g_menu_result[1] = map;
                    return g_menu_result;
                }
                it->SubItem = sub;

                s  = sub;
                sx = stx;
                for (si = 0; si < nsub; si++) {
                    UWORD sflags = (SPEC_CMD(sp) == 0) ? 0x52 : 0x56;

                    s->NextItem      = (si + 1 == nsub) ? NULL
                                                        : (struct MenuItem *)((UBYTE *)s + 0x22);
                    s->LeftEdge      = 70;               /* 0x46 — subitems inset right */
                    s->TopEdge       = (WORD)(si * 10 + 5);
                    s->Width         = 100;
                    s->Height        = 10;
                    s->Flags         = sflags;
                    s->MutualExclude = 0;
                    s->ItemFill      = (APTR)sx;
                    s->SelectFill    = NULL;
                    s->Command       = (BYTE)SPEC_CMD(sp);
                    s->SubItem       = NULL;
                    init_itext(sx, SPEC_TEXT(sp));

                    if (SPEC_HANDLER(sp) != NULL) {
                        *(UWORD *)(mp + 0) = (UWORD)(((si & 0x1f) << 11)
                                                     | ((ii & 0x3f) << 5)
                                                     | (mi & 0x1f));
                        *(ULONG *)(mp + 2) = (ULONG)SPEC_HANDLER(sp);
                        mp += 6;
                    }

                    sp += SPEC_STRIDE;
                    s  = (struct MenuItem  *)((UBYTE *)s  + 0x22);
                    sx = (struct IntuiText *)((UBYTE *)sx + 0x14);
                }
            }

            it  = (struct MenuItem  *)((UBYTE *)it  + 0x22);
            itx = (struct IntuiText *)((UBYTE *)itx + 0x14);
        }

        m = (struct Menu *)((UBYTE *)m + 0x1e);
    }

    *(UWORD *)mp = 0xffff;               /* terminate the command map */
    resource_commit();                   /* keep everything we built */

    g_menu_result[0] = menus;
    g_menu_result[1] = map;
    return g_menu_result;
}

/*
 * menu_dispatch — recon FUN_0011b478. Walk the command map looking for 'number'
 * (a MENUPICK menu-number word); on a match, call the stored handler and return its
 * result. Returns 0 if the number isn't in the map (e.g. an item with no handler).
 */
LONG menu_dispatch(APTR result, UWORD number)
{
    UBYTE *e = (UBYTE *)((APTR *)result)[1];   /* the command map */

    for (;;) {
        UWORD n = *(UWORD *)(e + 0);
        if (n == 0xffff)
            return 0;
        if (n == number) {
            LONG (*fn)(void) = (LONG (*)(void))(*(ULONG *)(e + 2));
            return fn();
        }
        e += 6;
    }
}
