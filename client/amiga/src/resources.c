/*
 * resources.c — SAS/C-style resource tracking (reconstructed).
 *
 * The original is compiled with SAS/Lattice C's auto-cleanup resource tracker: each
 * allocation (memory, MsgPort, IORequest, library, file) is registered on a global
 * unwind list tagged with the current nesting level, so a single cleanup call at an
 * error point (or program exit) frees everything opened since the matching mark.
 *
 *   resource_mark        (FUN_0011a000) — enter a new nesting level.
 *   resource_commit      (FUN_0011a00a) — leave the level, KEEPING its resources
 *                        (promote them to the parent level).
 *   cleanup_resources    (FUN_0011a0b0) — leave the level, FREEING its resources.
 *   create_port_tracked  (FUN_0011a75c) — CreatePort + register.
 *   create_extio_tracked (FUN_0011a80e) — CreateExtIO + register.
 *   open_device_tracked  (FUN_0011a2e8) — OpenDevice + register (frees req on fail).
 *
 * The list node layout (recon): +0x00 next, +0x08 tag(0x2a), +0x09 level,
 * +0x0e free-fn, +0x12 arg1, +0x16 arg2. We keep that layout so behaviour matches;
 * the tracker is runtime plumbing, not application logic.
 */
#include <exec/types.h>
#include <exec/memory.h>
#include <clib/exec_protos.h>

#include "compunet.h"

/* amiga.lib-style helpers the original calls (CreatePort/CreateExtIO/etc). We use
 * the same names; a real SAS/C or vbcc build links these from amiga.lib. */
extern struct MsgPort *CreatePort(char *name, LONG pri);
extern void            DeletePort(struct MsgPort *port);
extern APTR            CreateExtIO(struct MsgPort *port, ULONG size);
extern void            DeleteExtIO(APTR ioReq);

struct ResNode {
    struct ResNode *next;    /* +0x00 */
    UBYTE           pad[4];  /* +0x04 */
    UBYTE           tag;     /* +0x08 (0x2a) */
    UBYTE           level;   /* +0x09 */
    UBYTE           pad2[4]; /* +0x0a */
    void          (*freefn)();/* +0x0e */
    APTR            arg1;    /* +0x12 */
    APTR            arg2;    /* +0x16 */
};

extern struct ResNode *g_res_list;   /* PTR_DAT_0011ff1c — head of unwind list */
extern BYTE            g_res_level;   /* DAT_0011ff2a — current nesting level    */

APTR alloc_tracked(ULONG size, ULONG flags);   /* recon FUN_0011a1ee */
void free_tracked(APTR ptr);                    /* recon FUN_0011a238 */

/* Register 'ptr' with free function 'fn' at the current level (recon FUN_0011a16c
 * -> FUN_0011a132). */
static void res_register(void (*fn)(), APTR arg1, APTR arg2)
{
    struct ResNode *n = (struct ResNode *)AllocMem(0x1a, 0);
    if (n == NULL)
        return;
    n->tag    = 0x2a;
    n->level  = g_res_level;
    n->freefn = fn;
    n->arg1   = arg1;
    n->arg2   = arg2;
    /* push onto the list head (recon thunk_FUN_00129050 = AddHead-style) */
    n->next   = g_res_list;
    g_res_list = n;
}

/* Public register: attach an arbitrary free-fn(arg1) to the current level. Used by
 * set_menu_strip_tracked (register ClearMenuStrip) etc. (recon FUN_0011a16c). */
void resource_register_free(void (*fn)(), APTR arg1, APTR arg2)
{
    res_register(fn, arg1, arg2);
}

/* Enter a new nesting level; returns it (recon FUN_0011a000 returns DAT_0011ff2a).
 * The top level saves this so a longjmp'd disconnect can unwind back to it. */
BYTE resource_mark(void)
{
    g_res_level++;
    return g_res_level;
}

/* Leave the level, keeping its resources: demote each node at this level to the
 * parent so cleanup_resources() at an outer scope still frees them. */
void resource_commit(void)
{
    struct ResNode *n = g_res_list;
    while (n != NULL && n->level == g_res_level && n->next != NULL) {
        n->level--;
        n = n->next;
    }
    g_res_level--;
}

/* Leave the level, freeing every resource registered at it. Returns the new
 * (decremented) level — the disconnect handler loops on this to unwind several
 * levels back to a saved mark (recon thunk_FUN_0011a0b0 returns DAT_0011ff2a). */
BYTE cleanup_resources(void)
{
    struct ResNode *n = g_res_list;
    while (n != NULL && n->level == g_res_level && n->next != NULL) {
        struct ResNode *nxt = n->next;
        if (n->freefn)
            n->freefn(n->arg1, n->arg2);
        FreeMem(n, 0x1a);
        n = nxt;
    }
    g_res_list = n;
    g_res_level--;
    return g_res_level;
}

/* Remove (without calling) the tracker node matching (freefn, arg1) and free it —
 * recon FUN_0011a19c. Used by close_window_tracked after it closes the window itself,
 * so the exit-time cleanup doesn't double-close it. */
void resource_unregister(void (*fn)(), APTR arg1)
{
    struct ResNode **pp = &g_res_list;
    struct ResNode *n;
    while ((n = *pp) != NULL) {
        if (n->freefn == fn && n->arg1 == arg1) {
            *pp = n->next;
            FreeMem(n, 0x1a);
            return;
        }
        pp = &n->next;
    }
}

/* Free the ENTIRE resource list regardless of level (recon FUN_0011a0f0). Used by
 * fatal_exit at program termination — walks every node to NULL, not just one level. */
void cleanup_all_resources(void)
{
    struct ResNode *n = g_res_list;
    while (n != NULL) {
        struct ResNode *nxt = n->next;
        if (n->freefn)
            n->freefn(n->arg1, n->arg2);
        FreeMem(n, 0x1a);
        n = nxt;
    }
    g_res_list = NULL;
}

struct MsgPort *create_port_tracked(char *name, LONG pri)
{
    struct MsgPort *p = CreatePort(name, pri);
    if (p != NULL)
        res_register((void(*)())DeletePort, p, 0);
    return p;
}

struct CnetRequest *create_extio_tracked(struct MsgPort *port, ULONG size)
{
    APTR req = CreateExtIO(port, size);
    if (req != NULL)
        res_register((void(*)())DeleteExtIO, req, (APTR)size);
    return (struct CnetRequest *)req;
}

BOOL open_device_tracked(const char *name, ULONG unit,
                         struct IORequest *req, ULONG flags)
{
    LONG err = OpenDevice((STRPTR)name, unit, req, flags);
    if (err == 0)
        res_register((void(*)())CloseDevice, req, 0);
    return err;   /* recon returns the OpenDevice error (0 == success) */
}

/*
 * alloc_tracked — recon FUN_0011a1ee. AllocMem(size + 0x20), clear it, register a
 * matching free, and hand back a pointer past the 0x20-byte bookkeeping header
 * (which stores the size so free_tracked can recover it).
 */
APTR alloc_tracked(ULONG size, ULONG flags)
{
    UBYTE *p = (UBYTE *)AllocMem(size + 0x20, flags);
    if (p == NULL)
        return NULL;
    /* stash the total size in the header (recon writes it near -0xe) so the tracked
     * free can call FreeMem with the right length. */
    *(ULONG *)(p + 0x12) = size + 0x20;
    res_register((void(*)())free_tracked, p + 0x20, 0);
    return p + 0x20;
}

/*
 * free_tracked — recon FUN_0011a238. Recover the header (ptr - 0x20) and its stored
 * size, then FreeMem the whole block.
 */
void free_tracked(APTR ptr)
{
    UBYTE *base = (UBYTE *)ptr - 0x20;
    ULONG  total = *(ULONG *)(base + 0x12);
    FreeMem(base, total);
}
