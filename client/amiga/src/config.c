/*
 * config.c — configuration load/save (reconstructed).
 *
 *   load_config       (FUN_00102000) — read the 0x36-byte "cnet-configuration"
 *                     file into the config block; if absent, seed defaults
 *                     (empty phone, 1275 split baud 75/1200, 8 data bits).
 *   save_config_file  (FUN_00112250) — write the current config block back out.
 *
 * The config block starting at g_config (recon &DAT_00120108) holds, in order:
 *   +0x00 phone number / dial string (g_phone_number)
 *   +0x10 baud setting (LONG)         (g_baud_setting == recon DAT_00120118)
 *   +0x24 baud_up   (UWORD 75)        (DAT_0012012c)
 *   +0x26 baud_down (UWORD 1200)      (DAT_0012012e)
 *   +0x28 open flags                  (DAT_00120130)
 *   +0x2a data bits                   (DAT_00120132)
 * Content files are re-read on demand (no restart), matching the server model.
 */
#include <exec/types.h>
#include <string.h>

#include "compunet.h"

/* File helpers (into the DOS/IO layer; the config file is a plain 0x36-byte blob). */
extern APTR  config_open_read(const char *name);   /* thunk FUN_0011a41e */
extern void  config_free(APTR buf);                 /* thunk FUN_0011a238 */
extern APTR  config_open_write(const char *name);   /* thunk FUN_0011a534 */
extern void  apply_serial_params(UWORD bits);       /* thunk FUN_00114050 */

/* The whole config block, addressed as bytes (recon &DAT_00120108). */
extern UBYTE g_config[];        /* 0x36 bytes */
extern char  g_login_userid[];  /* DAT_00120244 — derived userid string */

#define CFG_BAUD_UP    (*(UWORD *)(g_config + 0x24))
#define CFG_BAUD_DN    (*(UWORD *)(g_config + 0x26))
#define CFG_OPENFLAGS  (*(UWORD *)(g_config + 0x28))
#define CFG_DATABITS   (*(UWORD *)(g_config + 0x2a))

LONG load_config(void)
{
    APTR buf;
    short i;

    g_config[0x2c] = 0;   /* recon 0x102004: clr.b config+0x2c (g_cfg_userid), NOT g_login_userid */

    buf = config_open_read("cnet-configuration");
    if (buf == NULL) {
        /* No config file: seed defaults. */
        g_phone_number[0] = '\0';           /* recon copies DAT_0011d46a "" */
        g_baud_setting = 400000;
        strcpy((char *)(g_config + 0x14), "");   /* modem name default (recon DAT_0011d46c) */
        CFG_BAUD_UP   = 0x4b;               /* 75   */
        CFG_BAUD_DN   = 0x4b0;              /* 1200 */
        CFG_OPENFLAGS = 4;
        CFG_DATABITS  = 8;
    } else {
        /* Copy the 0x36-byte saved block verbatim. */
        for (i = 0; i < 0x36; i++)
            g_config[i] = ((UBYTE *)buf)[i];
        config_free(buf);
    }

    apply_serial_params(CFG_DATABITS);
    strcpy(g_login_userid, (char *)(g_config + 0x2c)); /* recon DAT_00120134 */
    return 1;
}

/*
 * save_config_file — recon FUN_00112250. Open "cnet-configuration" (MODE_NEWFILE),
 * Write the 0x36-byte g_config block, Close. On open failure, pop the yes/no requester
 * "Can't open file - try again?" (title "Save configuration") and retry if the user
 * says yes; otherwise give up. (recon: retry_dialog at $112276, Write 0x36 bytes from
 * 0x120108 at $112290, Close at $11229c.)
 */
extern LONG retry_dialog(const char *title, const char *body);   /* FUN_001104a6 */
extern LONG file_write(APTR fh, APTR buf, ULONG len);
extern void config_close_write(APTR fh);   /* tracked Close + unregister (dosio.c) */

LONG save_config_file(void)
{
    APTR fh;
    for (;;) {
        fh = config_open_write("cnet-configuration");
        if (fh != NULL)
            break;
        /* open failed — offer retry (recon FUN_001104a6). */
        if (retry_dialog("Save configuration", "Can't open file - try again?") == 0)
            return 0;
    }
    file_write(fh, g_config, 0x36);   /* Write the whole config block (recon 0x36 @0x120108) */
    config_close_write(fh);           /* tracked close: Close + unregister (recon 0x11a3fe) */
    return 1;
}
