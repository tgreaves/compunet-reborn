/*
 * transfer.c — file download / upload (reconstructed).
 *
 *   download_check    (FUN_0010b730) — the D command entry: validate the selected
 *                     row's type via a jump table, dispatch to the right download
 *                     handler, or "Can't download this".
 *   file_download_xfer(FUN_0010b174) — negotiate a program download: send the "D"
 *                     command, read the 8-byte header (machine type), confirm the
 *                     machine type with the user, open the local file, and reply
 *                     with a control token (0x40 proceed / 0x41 abort).
 *   download_receive  (FUN_0010b2e6) — stream 4000-byte DAT blocks to disk until
 *                     the end flag; "No room for file" on write failure.
 *   upload_file       (FUN_0010c0ee) — send the "U" command, then stream the local
 *                     file back as DAT blocks (0x22), 4000 bytes at a time.
 *
 * The download control bytes (0x40/0x41) are single-char COM replies telling the
 * host to proceed or abort — a small sub-protocol on top of the command/ack model.
 */
#include <exec/types.h>
#include <string.h>

#include "compunet.h"

#define STATE_GOTO 2

/* File I/O + prompt helpers into the not-yet-reconstructed I/O and UI layers. */
extern APTR  file_open_write(const char *name, ULONG mode);  /* thunk FUN_0011a3c6 */
extern void  file_close(APTR fh);                            /* thunk FUN_0011a3fe */
extern APTR  file_open_read(const char *name);               /* thunk FUN_0011a344 */
extern LONG  file_write(APTR fh, APTR buf, ULONG len);       /* thunk FUN_0012804c */
extern LONG  file_read(APTR fh, APTR buf, ULONG len);        /* thunk FUN_00128030 */
extern LONG  download_filename_prompt(void);                 /* FUN_0010b06e */
extern LONG  download_machine_prompt(char type);             /* FUN_0010b0ea */
extern LONG  retry_dialog(const char *title, const char *body); /* thunk FUN_001104a6 */
extern LONG  upload_filename_prompt(void);                   /* upload() FUN_0010c000 */
extern ULONG upload_read_file(const char *name);             /* FUN_0010c0b4 -> size */
extern void  dir_action_cleanup(void);                       /* thunk FUN_0010d0d0 */
/* resource_mark / cleanup_resources declared in compunet.h. */

extern short g_sel_row;      /* DAT_001215c4 — selected directory row       */
extern char  g_dl_filename[];/* DAT_001215c6 — download filename buffer     */
extern char  g_dl_header[];  /* DAT_001215e8 — 8-byte download header        */
extern APTR  g_dl_file;      /* DAT_001215f0 — open local file handle        */
extern char  g_ul_name[];    /* DAT_0012161e — upload filename               */
extern char  g_xfer_buf[];   /* DAT_001220fc — 4000-byte transfer buffer     */
extern char  g_ul_hdr[];     /* DAT_00121640 — 8-byte upload size header     */

#define ROW_TYPE(p,r) (*(char *)((UBYTE *)(p) + (r) * 0x66 + 0x828))

/*
 * download_check — recon FUN_0010b730. The D command: build "D%02d" for the
 * selected row, then dispatch on the row's type byte. Types that aren't
 * downloadable fall through to "Can't download this". (The original uses a jump
 * table on the type char; the concrete per-type handlers are download_receive /
 * action_download, selected by type — expressed here via a small switch.)
 */
extern LONG download_receive(void);   /* FUN_0010b2e6 — program to disk */
extern LONG action_download(void);    /* FUN_0010b380 — executable "action" */

LONG download_check(void)
{
    char type;

    g_state = STATE_GOTO;
    g_sel_row = *(short *)((UBYTE *)g_dir_page + 0xc78);
    type = ROW_TYPE(g_dir_page, g_sel_row);
    sprintf(g_cmd_buf, "D%02d", (int)g_sel_row);

    switch (type) {
    case 'C':   /* C64 / program */
    case 'S':   /* ST / program  */
        return download_receive();
    case 'A':   /* action / executable */
        return action_download();
    default:
        show_status_message(1, "Can't download this");
        return 0;
    }
}

/*
 * file_download_xfer — recon FUN_0010b174. Send the D command, read the 8-byte
 * header (byte 0 = machine type: 0=C64, 1=Amiga, 2=ST), confirm the machine type,
 * open the destination file, and reply with a control token:
 *   0x40 ('@')  proceed — file opened OK
 *   0x41 ('A')  abort   — wrong machine / user cancelled / open failed
 */
LONG file_download_xfer(void)
{
    UBYTE ser_flags, status_hi;
    ULONG actual;

    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK)
        return 0;

    serial_read(g_dl_header, 8, &ser_flags, &status_hi, &actual);

    if (g_dl_header[0] == 2) {                       /* ST file */
        if (download_machine_prompt(2) == 0) {
            serial_write("A", 1, 1, 0x41);           /* abort */
            return 0;
        }
    } else if (g_dl_header[0] == 0) {                /* C64 file */
        if (download_machine_prompt(0) == 0) {
            serial_write("A", 1, 1, 0x41);
            return 0;
        }
    }
    /* machine type 1 (Amiga) needs no confirmation */

    for (;;) {
        g_dl_file = file_open_write(g_dl_filename, 0x3ee);
        if (g_dl_file != NULL) {
            serial_write("@", 1, 1, 0x40);           /* proceed */
            return 1;
        }
        if (retry_dialog("File download", "Can't open file - try again?") == 0)
            break;
    }
    serial_write("A", 1, 1, 0x41);                   /* give up */
    return 0;
}

/*
 * download_receive — recon FUN_0010b2e6. After a successful negotiation, stream
 * 4000-byte DAT blocks to disk until the end-of-transfer flag (ser_flags != 0).
 */
LONG download_receive(void)
{
    UBYTE ser_flags, status_hi;
    ULONG actual;

    if (file_download_xfer() == 0)
        return 0;

    do {
        serial_read(g_xfer_buf, 4000, &ser_flags, &status_hi, &actual);
        if (g_dl_file != NULL) {
            if (file_write(g_dl_file, g_xfer_buf, actual) != (LONG)actual) {
                file_close(g_dl_file);   /* write failed (disk full) */
                g_dl_file = NULL;
            }
        }
    } while (ser_flags == '\0');

    if (g_dl_file == NULL) {
        show_status_message(1, "No room for file");
        return 0;
    }
    file_close(g_dl_file);
    return 1;
}

/*
 * upload_file — recon FUN_0010c0ee. Prompt for a filename, read it into memory,
 * send the "U" command, then stream the file back as DAT blocks (token 0x22) in
 * 4000-byte chunks. The last block sets the "last" flag (ser_flags arg = 1).
 */
LONG upload_file(void)
{
    ULONG size, chunk;
    UBYTE last;
    APTR  fh;
    UBYTE ser_flags, status_hi;
    ULONG actual;

    if (upload_filename_prompt() == 0) {
        dir_action_cleanup();
        return 0;
    }

    size = upload_read_file(g_ul_name);
    if (size == 0) {
        dir_action_cleanup();
        show_status_message(1, "Empty file");
        return 0;
    }

    resource_mark();
    fh = file_open_read(g_ul_name);
    if (fh == NULL) {
        cleanup_resources();
        dir_action_cleanup();
        return 0;
    }

    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        dir_action_cleanup();
        cleanup_resources();
        return 0;
    }

    /* 8-byte size header, then the file itself as DAT blocks. */
    *(ULONG *)g_ul_hdr       = 0x1000000;   /* recon literal */
    *(ULONG *)(g_ul_hdr + 4) = size;
    serial_write(g_ul_hdr, 8, 0, TOKEN_DAT);

    do {
        if (size > 4000) {
            size -= 4000;
            chunk = 4000;
            last  = 0;
        } else {
            chunk = size;
            last  = 1;
        }
        file_read(fh, g_xfer_buf, chunk);
        serial_write(g_xfer_buf, chunk, last, TOKEN_DAT);
    } while (!last);

    cleanup_resources();
    if (serial_io_c(g_ack_text) == ACK_OK) {
        dir_action_cleanup();
        return 1;
    }
    dir_action_cleanup();
    return 0;
}

/*
 * action_download — recon FUN_0010b380. Download an "action" (executable) to a temp
 * file, verify it's an Amiga file (header byte 1), then Execute() it in a CON window.
 * "Not for Amiga!" if the machine type is wrong; "No room for temp file" on disk full.
 */
extern LONG dos_execute(const char *cmd, APTR in, APTR out);  /* thunk FUN_00128120 */

LONG action_download(void)
{
    UBYTE ser_flags, status_hi;
    ULONG actual;
    APTR  con;

    strcpy(g_dl_filename, "RAM:temp");
    if (download_filename_prompt() == 0)
        return 0;

    for (;;) {
        g_dl_file = file_open_write(g_dl_filename, 0x3ee);
        if (g_dl_file != NULL)
            break;
        if (retry_dialog("Action download", "Can't open file - try again?") == 0)
            return 0;
    }

    serial_write(g_cmd_buf, strlen(g_cmd_buf), 1, TOKEN_COM);
    if (serial_io_c(g_ack_text) != ACK_OK) {
        file_close(g_dl_file);
        return 0;
    }

    serial_read(g_dl_header, 8, &ser_flags, &status_hi, &actual);
    do {
        serial_read(g_xfer_buf, 4000, &ser_flags, &status_hi, &actual);
        if (g_dl_file != NULL &&
            file_write(g_dl_file, g_xfer_buf, actual) != (LONG)actual) {
            file_close(g_dl_file);
            g_dl_file = NULL;
        }
    } while (ser_flags == '\0');

    if (g_dl_file == NULL) {
        show_status_message(1, "No room for temp file");
        return 0;
    }
    file_close(g_dl_file);

    if (g_dl_header[0] != 1) {          /* machine type must be Amiga */
        show_status_message(1, "Not for Amiga!");
        return 0;
    }

    con = file_open_write("CON:20/10/300/100/Action Window", 0x3ee);
    if (con != NULL) {
        dos_execute(g_dl_filename, NULL, con);
        file_close(con);
        return 1;
    }
    return 0;
}
