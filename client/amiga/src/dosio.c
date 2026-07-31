/*
 * dosio.c — AmigaDOS file I/O + config file helpers (reconstructed).
 *
 * The original wraps the AmigaDOS library vectors in thin resource-tracked helpers
 * (recon FUN_00128000.. = Open/Close/Read/Write/Lock/LoadSeg/CreateProc/Delay, and
 * FUN_0011a3xx = the tracked variants). This file provides the file-transfer and
 * config-file seams the application modules call.
 *
 *   file_open_read/write  — Open() a file (tracked so cleanup closes it).
 *   file_close            — Close().
 *   file_read/file_write  — Read()/Write() a buffer.
 *   config_open_read      — Open + slurp the 0x36-byte config into a temp buffer.
 *   config_open_write     — Open the config for writing.
 *   load_seg_tracked      — LoadSeg() (tracked with UnLoadSeg).
 *   create_proc           — CreateProc() a child (CnetEditor).
 *
 * File modes: MODE_OLDFILE (1005) read, MODE_NEWFILE (1006) write — recon passes
 * 0x3ed/0x3ee/0x3ee which are these AmigaDOS mode constants.
 */
#include <exec/types.h>
#include <clib/exec_protos.h>
#include <clib/dos_protos.h>
#include <libraries/dos.h>

#include "compunet.h"

/* resource_mark / cleanup_resources declared in compunet.h. */

/* Tracked-resource registration reused from resources.c. */
extern APTR alloc_tracked(ULONG size, ULONG flags);

/*
 * file_open_read / file_open_write — recon FUN_0011a344 / FUN_0011a3c6: Open() the
 * named file (mode already an AmigaDOS constant) and register an auto-close.
 * BPTR/BCPL handles are returned as APTR to keep the callers untyped.
 */
/*
 * The TRACKED DOS primitives. ⚠ file_open_read used to claim `recon FUN_0011a344`, but
 * that original is `lock_tracked` — a Lock, not an Open. The original's "open a file for
 * reading" is FUN_0011a3c6 with mode 0x3ed, and it REGISTERS a Close, which is why an
 * aborted upload in the original does not leave the file locked. Ours opened untracked,
 * so it did.
 */
extern void resource_unregister(void (*fn)(), APTR arg1);

static void close_bptr_fn(BPTR fh) { Close(fh); }
static void unlock_bptr_fn(BPTR l) { UnLock(l); }

APTR lock_tracked(const char *name, LONG mode)          /* recon FUN_0011a344 */
{
    BPTR l = Lock((STRPTR)name, mode);
    if (l)
        resource_register_free((void (*)())unlock_bptr_fn, (APTR)l, 0);
    return (APTR)l;
}

void unlock_tracked(APTR lock)                          /* recon FUN_0011a3a6 */
{
    if (lock == NULL) return;
    UnLock((BPTR)lock);
    resource_unregister((void (*)())unlock_bptr_fn, lock);
}

APTR open_tracked(const char *name, ULONG mode)         /* recon FUN_0011a3c6 */
{
    BPTR fh = Open((STRPTR)name, (LONG)mode);
    if (fh)
        resource_register_free((void (*)())close_bptr_fn, (APTR)fh, 0);
    return (APTR)fh;
}

void close_tracked(APTR fh)                             /* recon FUN_0011a3fe */
{
    if (fh == NULL) return;
    Close((BPTR)fh);
    resource_unregister((void (*)())close_bptr_fn, fh);
}

/* file_open_read / file_open_write — the application-facing opens. Now tracked, so a
 * transfer abandoned by the abort chord or a failure path does not strand the handle. */
APTR file_open_read(const char *name)
{
    return open_tracked(name, MODE_OLDFILE);
}

/* file_open_append — NOT part of the reconstruction (#129 diagnostic support).
 * Opens for writing positioned at end, creating the file if absent. The trace it
 * serves must survive a crash and be readable from the HOST while the emulator is
 * still running, so each line is opened, written and closed: a handle held open
 * leaves the writes buffered, the host sees a stale file, and the file stays locked.
 * Remove with the rest of the #129 instrumentation. */
APTR file_open_append(const char *name)
{
    BPTR fh = Open((STRPTR)name, MODE_OLDFILE);
    if (fh)
        Seek(fh, 0, OFFSET_END);
    else
        fh = Open((STRPTR)name, MODE_NEWFILE);
    return (APTR)fh;
}

/* ⚠ THE CALLER'S MODE IS HONOURED (11a3ca move.l $c(a5),-(a7)) — it was discarded and
 * MODE_NEWFILE hardcoded, so every caller got a truncating open whatever it asked for. */
APTR file_open_write(const char *name, ULONG mode)
{
    return open_tracked(name, mode ? mode : MODE_NEWFILE);
}

void file_close(APTR fh)
{
    close_tracked(fh);
}

LONG file_read(APTR fh, APTR buf, ULONG len)
{
    return Read((BPTR)fh, buf, (LONG)len);
}

LONG file_write(APTR fh, APTR buf, ULONG len)
{
    return Write((BPTR)fh, buf, (LONG)len);
}

/*
 * config_open_read — recon FUN_0011a41e. Open "cnet-configuration" (OLDFILE), read
 * its bytes into a tracked buffer, and return the buffer (or NULL if absent).
 * Callers copy the 0x36-byte block and then config_free() the buffer.
 */
APTR config_open_read(const char *name)
{
    BPTR fh;
    APTR buf;

    fh = Open((STRPTR)name, MODE_OLDFILE);
    if (fh == 0)
        return NULL;

    buf = alloc_tracked(0x36, 0);
    if (buf != NULL)
        Read(fh, buf, 0x36);
    Close(fh);
    return buf;
}

void config_free(APTR buf)
{
    extern void free_tracked(APTR ptr);
    if (buf)
        free_tracked(buf);
}

/* config_open_write / config_close_write — the SAME originals as open_tracked /
 * close_tracked (FUN_0011a3c6 / FUN_0011a3fe), so they delegate rather than reimplement.
 *
 * ⚠ They used to be a second copy with their OWN static close function, which meant one
 * original function had two identities in this tree: a handle opened by one and closed by
 * the other would fail to unregister (resource_unregister matches on the function
 * POINTER as well as the argument), leaving a node that closes an already-closed handle
 * at exit. Two copies of one function is how the download dispatcher drifted too. */
APTR config_open_write(const char *name)
{
    return open_tracked(name, MODE_NEWFILE);
}

void config_close_write(APTR fh)
{
    close_tracked(fh);
}

/*
 * load_seg_tracked — recon FUN_0011a868. LoadSeg() the named executable and register
 * an UnLoadSeg cleanup. Returns the seg (BPTR) as APTR.
 */
/* ⚠ THE "tracked" IN THE NAME WAS A LIE — it registered nothing.
 *
 * Original FUN_0011a868: LoadSeg, and on success
 *   pea $11a928(pc)          ; -> 0x1280e4 -> dos -$9c = UnLoadSeg
 *   bsr $11a16c              ; resource_register_free(UnLoadSeg, seg, 0)
 * so the segment is released by the exit unwind. Ours did a bare LoadSeg, and nothing in
 * the tree called UnLoadSeg anywhere. AmigaDOS does NOT reclaim LoadSeg'd segments when a
 * process exits, so both users — CnetEditor (launch.c) and CnetTty (launch.c) — leaked
 * their whole code image on every run. */
APTR load_seg_tracked(const char *name)
{
    extern void resource_register_free(void (*fn)(), APTR arg1, APTR arg2);
    BPTR seg = LoadSeg((STRPTR)name);
    if (seg)
        resource_register_free((void (*)())UnLoadSeg, (APTR)seg, 0);
    return (APTR)seg;
}

/*
 * create_proc — recon FUN_001280b4 = AmigaDOS CreateProc(). Spawns the loaded seg as
 * a child process with the given stack size.
 */
APTR create_proc(const char *name, LONG pri, APTR seg, ULONG stack)
{
    return (APTR)CreateProc((STRPTR)name, pri, (BPTR)seg, (LONG)stack);
}

/*
 * upload_read_file — recon FUN_0010c0b4. Return the size of the named file (bytes)
 * by opening it and seeking to the end, or 0 on failure. Used by upload_file to size
 * the transfer before streaming it.
 */
/* file_size_examine — recon FUN_0010c030: the actual size routine, via Lock+Examine
 * inside a resource mark so a failure unwinds cleanly. (Seek round-tripping the file
 * worked, but Examine is what the original does and it does not need write access.) */
static ULONG file_size_examine(const char *name)
{
    extern APTR lock_tracked(const char *name, LONG mode);
    extern void unlock_tracked(APTR lock);
    APTR  lock;
    UBYTE *fib;
    ULONG size = 0;

    resource_mark();
    lock = lock_tracked(name, -2);              /* SHARED_LOCK */
    if (lock != NULL) {
        fib = (UBYTE *)alloc_tracked(0x104, 0);  /* FileInfoBlock, TRACKED */
        if (fib != NULL) {
            if (Examine((BPTR)lock, (struct FileInfoBlock *)fib))
                size = *(ULONG *)(fib + 0x7c);   /* fib_Size */
            free_tracked(fib);
        }
        unlock_tracked(lock);
    }
    cleanup_resources();
    return size;
}

/* ⚠ upload_read_file IS THE RETRY WRAPPER, not the size routine (recon FUN_0010c0b4).
 * Reconstructed as a bare size query, so a file the client could not read reported size
 * 0 and the upload silently did nothing — where the original offers
 * "File upload / Can't read file - try again?" and loops until the user gives up. */
ULONG upload_read_file(const char *name)
{
    ULONG size;
    for (;;) {
        size = file_size_examine(name);
        if (size != 0)
            return size;                                     /* 10c0c8 */
        if (retry_dialog("File upload", "Can't read file - try again?") == 0)
            return 0;                                        /* 10c0e2 */
    }
}

/* dos_execute — recon thunk FUN_00128120 = AmigaDOS Execute(). Runs a command with
 * the given input/output streams (used by action_download to launch the file). */
LONG dos_execute(const char *cmd, APTR in, APTR out)
{
    return Execute((STRPTR)cmd, (BPTR)in, (BPTR)out);
}

/*
 * load_file_to_mem — recon FUN_0011a41e. Lock the named file, Examine it for its size
 * (fib_Size at FileInfoBlock+0x7c), UnLock, allocate a tracked block of that size (so
 * cleanup frees it), Open + Read the whole file into it, and return the buffer. Returns
 * NULL on any failure. The returned pointer is an alloc_tracked block, so its size is
 * recoverable via mem_block_size and it is released by free_tracked. Used by
 * iff_view_file to decode an IFF picture already saved to disk.
 */
/* ⚠ THE WHOLE FUNCTION IS A RESOURCE-MARK SCOPE. Reconstructed with raw Lock/AllocMem/
 * Open and no mark/commit/cleanup, every failure path AFTER the buffer was allocated
 * returned NULL while leaving that tracked buffer allocated — a leak on every failed IFF
 * view — and a longjmp out of here (the abort chord now works) would strand the lock and
 * the file handle too. resource_mark/commit is exactly the mechanism that prevents both:
 * everything acquired inside the mark is released by cleanup_resources unless commit
 * keeps it. Ground truth FUN_0011a41e: mark, lock_tracked, alloc_tracked(fib),
 * Examine, unlock_tracked, free_tracked(fib), alloc_tracked(size), open_tracked(0x3ed),
 * Read, close_tracked, commit — with a single shared failure exit to cleanup+return 0. */
APTR load_file_to_mem(const char *name)
{
    extern APTR lock_tracked(const char *name, LONG mode);
    extern void unlock_tracked(APTR lock);
    extern APTR open_tracked(const char *name, ULONG mode);
    extern void close_tracked(APTR fh);
    APTR   lock, fh;
    UBYTE *fib;
    ULONG  size;
    UBYTE *buf;

    resource_mark();
    lock = lock_tracked(name, -2);                  /* SHARED_LOCK */
    if (lock == NULL) goto fail;
    fib = (UBYTE *)alloc_tracked(0x104, 0);
    if (fib == NULL) goto fail;
    if (!Examine((BPTR)lock, (struct FileInfoBlock *)fib)) goto fail;
    unlock_tracked(lock);
    size = *(ULONG *)(fib + 0x7c);                  /* fib_Size */
    free_tracked(fib);

    buf = (UBYTE *)alloc_tracked(size, 0);
    if (buf == NULL) goto fail;
    fh = open_tracked(name, 0x3ed);                 /* MODE_OLDFILE */
    if (fh == NULL) goto fail;
    if ((ULONG)Read((BPTR)fh, buf, (LONG)size) != size) goto fail;
    close_tracked(fh);

    resource_commit();                              /* keep buf; release the rest */
    return (APTR)buf;

fail:
    cleanup_resources();                            /* frees lock/fib/buf/handle */
    return NULL;
}

/* mem_block_size — recon FUN_0011a26c. Recover the payload size of an alloc_tracked
 * block: the total (incl. the 0x20 header) is stored at (p-0x20)+0x12, so the payload
 * is that minus 0x20. */
ULONG mem_block_size(APTR p)
{
    UBYTE *base = (UBYTE *)p - 0x20;
    return *(ULONG *)(base + 0x12) - 0x20;
}
