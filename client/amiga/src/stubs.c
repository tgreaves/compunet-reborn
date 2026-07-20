/*
 * stubs.c — placeholder bodies for not-yet-reconstructed helpers.
 *
 * These are the UI (Intuition window/gadget/menu), DOS file I/O, and modem-
 * script functions that the reconstructed application modules call into but
 * which have not themselves been reconstructed yet. Each is a linkable no-op so
 * the whole program links into a HUNK executable and the reconstructed logic can
 * be exercised. They are NOT faithful — replacing each with its real
 * reconstruction (from the recon_annotated.c address noted where known) is the
 * remaining work. Grouped by subsystem.
 *
 * See coverage-census.md: the 53 census functions are reconstructed in the other
 * modules; these stubs are the supporting UI/IO glue below the application layer.
 */
#include <exec/types.h>
#include "compunet.h"

/* ---- data globals referenced across modules ---- */
/* g_ctrl_lo / g_ctrl_hi are now real (frame_control.c) */
APTR  g_editor_port = 0;
APTR  g_editor_seg  = 0;
UBYTE g_editor_status = 0;
APTR  g_screen = 0;
APTR  g_window = 0;
APTR  g_res_list = 0;    /* PTR_DAT_0011ff1c */
BYTE  g_res_level = 0;   /* DAT_0011ff2a */

/* ---- function stubs ---- */
LONG  action_download() { return 0; }
void  apply_serial_params() { }
void  clear_wait_pointer() { }
void  close_connection_window() { }
void  close_logon_window() { }
void  config_free() { }
void  config_open_read() { }
void  config_open_write() { }
APTR  create_proc() { return 0; }
LONG  dial_modem() { return 0; }
void  dir_action_cleanup() { }
LONG  directory_refresh() { return 0; }
LONG  download_machine_prompt() { return 0; }
LONG  extend_by_prompt() { return 0; }
void  fatal_exit() { }
void  file_close() { }
APTR  file_open_read() { return 0; }
APTR  file_open_write() { return 0; }
void  file_read() { }
void  file_write() { }
APTR  frame_display() { return 0; }
APTR  frame_display_done() { return 0; }
APTR  frame_display_mem() { return 0; }
LONG  goto_page_prompt() { return 0; }
void  handle_device_message() { }
void  handle_extra_signal() { }
LONG  init_directory() { return 0; }
void  link_lock() { }
APTR  load_seg_tracked() { return 0; }
LONG  logon_poll() { return 0; }
void  logon_window_ready() { }
void  mail_append() { }
void  mail_close_window() { }
LONG  mail_open_window() { return 0; }
LONG  mail_run_id_dialog() { return 0; }
LONG  mail_run_upload_dialog() { return 0; }
void  main_event_loop() { }
void  modem_delay() { }
LONG  modem_read_status() { return 0; }
void  modem_send() { }
void  modem_send_delayed() { }
APTR  open_dos_library() { return 0; }
APTR  open_frame_window() { return 0; }
APTR  open_library_checked() { return 0; }
APTR  open_logon_window() { return 0; }
APTR  open_screen_tracked() { return 0; }
APTR  open_window_tracked() { return 0; }
LONG  put_frame_type_ok() { return 0; }
LONG  put_frame_xfer() { return 0; }
void  put_msg() { }
void  retry_dialog() { }
void  set_connection_error() { }
void  set_wait_pointer() { }
void  show_status_message() { }
void  status_ok_dialog() { }
void  ui_set_title() { }
LONG  upload_filename_prompt() { return 0; }
LONG  upload_read_file() { return 0; }
LONG  vote_choice_prompt() { return 0; }
