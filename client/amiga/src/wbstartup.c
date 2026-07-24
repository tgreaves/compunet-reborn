/*
 * wbstartup.c — Workbench-launch handling.
 *
 * The original client shipped a WBTOOL icon and was launched by double-clicking it. Its
 * SAS/C startup (c.o) collected the Workbench startup message and set the current directory
 * to the icon's drawer, so the program's LoadSeg("CnetEditor" / "CnetTty") and its TCPHOST /
 * cnet-configuration reads resolved against that drawer. vbcc's minstart.o (which we link)
 * does neither — so from Workbench the current dir is wrong, those files are not found, the
 * startup LoadSegs fail, and the client dies (fatal_exit / guru). CLI launches were fine
 * because the Shell's current dir already is the drawer.
 *
 * These two helpers restore the original behaviour: wb_startup_begin() runs once at program
 * start (after DOS is open, before the UI/LoadSegs); wb_startup_end() runs once at exit (from
 * fatal_exit) to restore the directory and reply the message so Workbench can unload us.
 */
#include <exec/types.h>
#include <workbench/startup.h>
#include <proto/dos.h>          /* CurrentDir — uses the global DOSBase we open at startup */

#include "compunet.h"

/* exec.library entries, resolved via -lamiga as elsewhere in the client. */
extern APTR find_task(APTR name);        /* FindTask thunk (launch_helpers.c) */
extern void WaitPort(APTR port);
extern APTR GetMsg(APTR port);
extern void Forbid(void);
extern void ReplyMsg(APTR msg);

/* struct Process field offsets (dos/dosextens.h is absent from this NDK; the client already
 * accesses Process fields by offset — e.g. pr_CurrentDir +0x98, pr_WindowPtr +0xb8). */
#define PR_MSGPORT(p)  ((APTR)((UBYTE *)(p) + 0x5c))    /* &pr_MsgPort                       */
#define PR_CLI(p)      (*(LONG *)((UBYTE *)(p) + 0xac)) /* pr_CLI (BPTR; 0 => launched by WB) */

APTR         g_wb_startup = NULL;   /* struct WBStartup * when launched from Workbench */
static BPTR  s_wb_olddir  = 0;

void wb_startup_begin(void)
{
    APTR proc = find_task(NULL);
    struct WBStartup *wb;

    if (proc == NULL || PR_CLI(proc) != 0)      /* CLI/Shell launch — nothing to do */
        return;

    WaitPort(PR_MSGPORT(proc));                 /* the WBStartup message is waiting for us */
    wb = (struct WBStartup *)GetMsg(PR_MSGPORT(proc));
    g_wb_startup = (APTR)wb;
    if (wb != NULL && wb->sm_NumArgs > 0 && wb->sm_ArgList[0].wa_Lock != 0)
        s_wb_olddir = CurrentDir(wb->sm_ArgList[0].wa_Lock);   /* cwd = the icon's drawer */
}

void wb_startup_end(void)
{
    struct WBStartup *wb = (struct WBStartup *)g_wb_startup;
    if (wb == NULL)
        return;
    g_wb_startup = NULL;
    if (s_wb_olddir != 0)
        CurrentDir(s_wb_olddir);                /* restore before WB frees the drawer lock */
    Forbid();                                   /* WB must not unload us until we have replied */
    ReplyMsg((APTR)wb);
}
