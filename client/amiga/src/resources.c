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
#include <exec/lists.h>
#include <exec/nodes.h>
#include <clib/exec_protos.h>

#include "compunet.h"

/* amiga.lib-style helpers the original calls (CreatePort/CreateExtIO/etc). We use
 * the same names; a real SAS/C or vbcc build links these from amiga.lib. */
extern struct MsgPort *CreatePort(char *name, LONG pri);
extern void            DeletePort(struct MsgPort *port);
extern APTR            CreateExtIO(struct MsgPort *port, ULONG size);
extern void            DeleteExtIO(APTR ioReq);

/*
 * ResNode — the unwind-list node, laid out EXACTLY as the original (verified against
 * FUN_0011a132 / FUN_0011a054). It begins with an exec Node so the list is a real
 * exec List driven by AddHead/Remove:
 *   +0x00 ln_Succ, +0x04 ln_Pred, +0x08 ln_Type(=tag 0x2a), +0x09 ln_Pri(=level),
 *   +0x0a ln_Name (cleared), +0x0e freefn, +0x12 arg1, +0x16 arg2.  sizeof = 0x1a.
 *
 * TWO node modes, matching the original:
 *   (A) freefn == 0: the node IS the front of a tracked memory block (alloc_tracked's
 *       0x20 header). arg1 holds the block's total size. Freed by Remove + FreeMem(node,
 *       arg1) — one block, so the tracker can never outlive its payload.
 *   (B) freefn != 0: a standalone 0x1a node (AllocMem'd) tracking some other resource
 *       (window/library/port/file). Freed by freefn(arg1,arg2) + Remove + FreeMem(node,
 *       0x1a).
 */
struct ResNode {
    struct Node node;        /* +0x00 exec Node (ln_Succ/Pred/Type/Pri/Name) */
    void      (*freefn)();    /* +0x0e */
    APTR        arg1;         /* +0x12 */
    APTR        arg2;         /* +0x16 */
};                            /* sizeof = 0x1a */

/* The unwind list head (recon DAT_0011ff1c) is an exec List; the current nesting level
 * (recon DAT_0011ff2a) is an ln_Pri-style byte. Both live in stubs.c. */
extern struct List g_res_list;   /* PTR_DAT_0011ff1c — the exec List head */
extern BYTE        g_res_level;  /* DAT_0011ff2a — current nesting level  */

#define RES_LIST  (&g_res_list)

APTR alloc_tracked(ULONG size, ULONG flags);   /* recon FUN_0011a1ee */
void free_tracked(APTR ptr);                    /* recon FUN_0011a238 */

/* Lazily NewList() the head the first time anything registers (the original inits it at
 * startup; doing it on first use is equivalent and avoids a separate init hook). An
 * empty exec List has lh_TailPred == &lh_Head, which g_res_list==NULL (fresh BSS) is
 * not — so we detect the uninitialised state by lh_Head == NULL. */
static void res_list_init(void)
{
    struct List *l = RES_LIST;
    if (l->lh_Head == NULL && l->lh_TailPred == NULL)
        NewList(l);
}

/* res_node_init — recon FUN_0011a132: fill a caller-supplied block's node fields and
 * AddHead it to the list. */
static void res_node_init(struct ResNode *n, void (*fn)(), APTR arg1, APTR arg2)
{
    n->node.ln_Type = 0x2a;
    n->node.ln_Pri  = (BYTE)g_res_level;
    n->node.ln_Name = NULL;      /* recon clr.l +0x0a */
    n->freefn = fn;
    n->arg1   = arg1;
    n->arg2   = arg2;
    res_list_init();
    AddHead(RES_LIST, &n->node);
}

/* res_free_node — recon FUN_0011a054. Free one node per its mode (see ResNode above). */
static void res_free_node(struct ResNode *n)
{
    if (n->freefn == 0) {                     /* mode A: node == tracked block */
        ULONG size = (ULONG)n->arg1;
        Remove(&n->node);
        FreeMem(n, size);
    } else {                                  /* mode B: standalone 0x1a node */
        n->freefn(n->arg1, n->arg2);
        Remove(&n->node);
        FreeMem(n, 0x1a);
    }
}

/* Public register: attach an arbitrary free-fn(arg1,arg2) to the current level via a
 * standalone node (recon FUN_0011a16c: AllocMem(0x1a) then FUN_0011a132). Used for
 * windows/screens/libraries/ports/files — anything whose storage isn't ours to embed. */
void resource_register_free(void (*fn)(), APTR arg1, APTR arg2)
{
    struct ResNode *n = (struct ResNode *)AllocMem(0x1a, 0);
    if (n == NULL)
        return;
    res_node_init(n, fn, arg1, arg2);
}

/* Enter a new nesting level; returns it (recon FUN_0011a000 returns DAT_0011ff2a).
 * The top level saves this so a longjmp'd disconnect can unwind back to it. */
BYTE resource_mark(void)
{
    g_res_level++;
    return g_res_level;
}

/* Leave the level, keeping its resources: demote each node at this level to the parent
 * so cleanup_resources() at an outer scope still frees them (recon FUN_0011a00a: walk
 * from lh_Head while node->ln_Pri == current level, decrement each, then level--). */
void resource_commit(void)
{
    struct Node *n;
    res_list_init();
    for (n = RES_LIST->lh_Head; n->ln_Succ != NULL; n = n->ln_Succ) {
        if ((UBYTE)n->ln_Pri != g_res_level)
            break;
        n->ln_Pri--;
    }
    g_res_level--;
}

/* Leave the level, freeing every resource registered at it (recon FUN_0011a0b0). Returns
 * the new (decremented) level — disconnect loops on this to unwind several levels back to
 * a saved mark. Frees from the head while the node's level matches. res_free_node Removes
 * each node before freeing, so the list stays consistent even if a freefn re-enters. */
BYTE cleanup_resources(void)
{
    res_list_init();
    for (;;) {
        struct Node *n = RES_LIST->lh_Head;
        if (n->ln_Succ == NULL)                /* empty list (head == tail sentinel) */
            break;
        if ((UBYTE)n->ln_Pri != g_res_level)
            break;
        res_free_node((struct ResNode *)n);
    }
    g_res_level--;
    return g_res_level;
}

/* Remove (without calling its freefn) the standalone tracker node matching (freefn,
 * arg1) and free it — recon FUN_0011a19c. Used by close_window_tracked etc. after they
 * close the resource themselves, so exit-time cleanup doesn't double-close it. Only
 * mode-B (freefn != 0) nodes are ever unregistered this way. */
void resource_unregister(void (*fn)(), APTR arg1)
{
    struct Node *n;
    res_list_init();
    for (n = RES_LIST->lh_Head; n->ln_Succ != NULL; n = n->ln_Succ) {
        struct ResNode *r = (struct ResNode *)n;
        if (r->freefn == fn && r->arg1 == arg1) {
            Remove(n);
            FreeMem(r, 0x1a);
            return;
        }
    }
}

/* Free the ENTIRE resource list regardless of level (recon FUN_0011a0f0). Used by
 * fatal_exit at program termination — frees from the head until the list is empty. */
void cleanup_all_resources(void)
{
    res_list_init();
    for (;;) {
        struct Node *n = RES_LIST->lh_Head;
        if (n->ln_Succ == NULL)                /* empty (head == tail sentinel) */
            break;
        res_free_node((struct ResNode *)n);
    }
}

struct MsgPort *create_port_tracked(char *name, LONG pri)
{
    struct MsgPort *p = CreatePort(name, pri);
    if (p != NULL)
        resource_register_free((void(*)())DeletePort, p, 0);
    return p;
}

struct CnetRequest *create_extio_tracked(struct MsgPort *port, ULONG size)
{
    APTR req = CreateExtIO(port, size);
    if (req != NULL)
        resource_register_free((void(*)())DeleteExtIO, req, (APTR)size);
    return (struct CnetRequest *)req;
}

BOOL open_device_tracked(const char *name, ULONG unit,
                         struct IORequest *req, ULONG flags)
{
    LONG err = OpenDevice((STRPTR)name, unit, req, flags);
    if (err == 0)
        resource_register_free((void(*)())CloseDevice, req, 0);
    return err;   /* recon returns the OpenDevice error (0 == success) */
}

/*
 * alloc_tracked — recon FUN_0011a1ee. AllocMem(size + 0x20) and register the block AS
 * ITS OWN node (mode A: freefn = 0, arg1 = total size), the node living in the first
 * 0x1a bytes of the 0x20 header. The payload starts at +0x20 and is what we return.
 * Because the node and payload are one block, freeing it (free_tracked, or res_free_node
 * at cleanup) Removes the node in the same step — a tracker can never outlive its
 * payload, so there is no orphan/double-free.
 */
APTR alloc_tracked(ULONG size, ULONG flags)
{
    struct ResNode *n = (struct ResNode *)AllocMem(size + 0x20, flags);
    if (n == NULL)
        return NULL;
    res_node_init(n, 0, (APTR)(size + 0x20), 0);   /* freefn=0, arg1=total size */
    return (UBYTE *)n + 0x20;
}

/*
 * free_tracked — recon FUN_0011a238. Free an alloc_tracked block early (before cleanup):
 * recover the node at (ptr - 0x20), Remove it from the list, and FreeMem the whole block
 * with its stored size. This is exactly res_free_node's mode-A path done directly.
 */
void free_tracked(APTR ptr)
{
    struct ResNode *n = (struct ResNode *)((UBYTE *)ptr - 0x20);
    ULONG total = (ULONG)n->arg1;
    Remove(&n->node);
    FreeMem(n, total);
}
