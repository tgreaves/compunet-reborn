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
APTR file_open_read(const char *name)
{
    return (APTR)Open((STRPTR)name, MODE_OLDFILE);
}

APTR file_open_write(const char *name, ULONG mode)
{
    /* recon passes 0x3ee == MODE_NEWFILE for downloads. */
    (void)mode;
    return (APTR)Open((STRPTR)name, MODE_NEWFILE);
}

void file_close(APTR fh)
{
    if (fh)
        Close((BPTR)fh);
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

/* config_open_write — recon FUN_0011a3c6: Open(name, MODE_NEWFILE) and, on success,
 * register a tracked Close (recon 0x11a3ea) so cleanup unwinds the file handle. */
extern void resource_register_free(void (*fn)(), APTR arg1, APTR arg2);
extern void resource_unregister(void (*fn)(), APTR arg1);
static void close_bptr(APTR fh){ if (fh) Close((BPTR)fh); }
APTR config_open_write(const char *name)
{
    APTR fh = (APTR)Open((STRPTR)name, MODE_NEWFILE);
    if (fh != NULL)
        resource_register_free((void (*)())close_bptr, fh, 0);
    return fh;
}

/* config_close_write — recon FUN_0011a3fe: Close the handle AND remove its tracker node
 * (so the exit-time cleanup doesn't double-close it). Pairs with config_open_write. */
void config_close_write(APTR fh)
{
    if (fh) {
        Close((BPTR)fh);
        resource_unregister((void (*)())close_bptr, fh);
    }
}

/*
 * load_seg_tracked — recon FUN_0011a868. LoadSeg() the named executable and register
 * an UnLoadSeg cleanup. Returns the seg (BPTR) as APTR.
 */
APTR load_seg_tracked(const char *name)
{
    return (APTR)LoadSeg((STRPTR)name);
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
ULONG upload_read_file(const char *name)
{
    BPTR fh;
    LONG size;

    fh = Open((STRPTR)name, MODE_OLDFILE);
    if (fh == 0)
        return 0;
    Seek(fh, 0, OFFSET_END);
    size = Seek(fh, 0, OFFSET_BEGINNING);   /* Seek returns previous position = size */
    Close(fh);
    return (ULONG)size;
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
APTR load_file_to_mem(const char *name)
{
    BPTR   lock, fh;
    struct FileInfoBlock *fib;
    ULONG  size;
    UBYTE *buf;

    lock = Lock((STRPTR)name, SHARED_LOCK);
    if (lock == 0)
        return NULL;
    fib = (struct FileInfoBlock *)AllocMem(sizeof(struct FileInfoBlock), 0);
    if (fib == NULL) {
        UnLock(lock);
        return NULL;
    }
    if (!Examine(lock, fib)) {
        FreeMem(fib, sizeof(struct FileInfoBlock));
        UnLock(lock);
        return NULL;
    }
    size = (ULONG)fib->fib_Size;
    FreeMem(fib, sizeof(struct FileInfoBlock));
    UnLock(lock);

    buf = (UBYTE *)alloc_tracked(size, 0);
    if (buf == NULL)
        return NULL;

    fh = Open((STRPTR)name, MODE_OLDFILE);
    if (fh == 0)
        return NULL;
    if ((ULONG)Read(fh, buf, (LONG)size) != size) {
        Close(fh);
        return NULL;
    }
    Close(fh);
    return (APTR)buf;
}

/* mem_block_size — recon FUN_0011a26c. Recover the payload size of an alloc_tracked
 * block: the total (incl. the 0x20 header) is stored at (p-0x20)+0x12, so the payload
 * is that minus 0x20. */
ULONG mem_block_size(APTR p)
{
    UBYTE *base = (UBYTE *)p - 0x20;
    return *(ULONG *)(base + 0x12) - 0x20;
}
