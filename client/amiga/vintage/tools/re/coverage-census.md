# Application-function coverage census

**Purpose:** guarantee the C reconstruction in [`../../src/`](../../src/) covers the
*whole* client, not just a hand-picked subset. This census is **mechanical and
reproducible** — regenerate it any time with
[`coverage_census.py`](coverage_census.py) and diff against `../../src/`.

## The completeness argument

A function in `recon_annotated.c` is **application logic** (as opposed to SAS/C
runtime glue or an OS-call thunk) if and only if it does one of two *observable*
things:

1. **References a string literal** — a status message, a dialog title, or a
   `sprintf`/`serial_write` format string (Ghidra annotates these as
   `/* strings: ... */`).
2. **Calls the transport** — `serial_write` / `serial_io_c` / `send_dat_packet`.

Everything else (register shuffles, list walks, `AllocMem` wrappers, LVO thunks)
has *no* strings and *never* touches the wire. So the **union of those two sets is
the complete application surface**. Critically, **every command the client sends to
the server is built from a format-string literal**, so criterion (1) alone captures
100% of the wire-command vocabulary; criterion (2) additionally catches handlers
that build into the shared command buffer (`DAT_00121588`) and so carry no string of
their own.

Current census: **53 functions** (41 string-anchored ∪ 24 transport-calling).

> This document exists because the earlier hand-curated `symbols.json` (40 entries)
> **silently omitted whole subsystems** — VOTE, LIFE-extend, PUT/publish, MAIL,
> LINK, ACCOUNT and the download flow-control sub-protocol. The census caught them.
> Trust the census, not a curated list.

## The wire-command vocabulary (COM token 0x43 unless noted)

Every server command the client can issue, with the function that issues it. These
are the application-layer commands that a Reborn server must accept from an Amiga
client (compare [docs/PROTOCOL.md](../../../../docs/PROTOCOL.md)).

| Cmd | Format string | Meaning | Issuing function |
|-----|---------------|---------|------------------|
| `P` | `P%02d`      | SHOW page (select text frame) | `goto_page` `0x10a1e2` |
| `D` | `D%02d`      | DIR / open directory | `validate_login` `0x10e0fc`, `download_check` `0x10b730` |
| `L` | `L%.6s`      | LINK (go to 6-char link code) | `link_follow` `0x1098e8`, `link_goto` `0x10a310` |
| `V` | `V%02d%s`    | VOTE on a page | `vote` `0x10c510` |
| `X` | `X%02d%4.4s` | eXtend page LIFE | `extend_life` `0x10c428` |
| `U` | `U%-16s%c%03d.%02d%03d` | PUT / publish a frame (editor) | `put_frame` `0x10c2f8` |
| `U` | `U%-16sT`    | mail / ID record submit | `mail_submit` `0x10e188`, `mail_read` `0x10e468` |
| `I` | (buffer `0x49`…) | mail-in record | `mail_read` `0x10e468` |
| `Z` | (login rec) | login identity (`Z` + userid + password + `AM21`+ver) | `send_login_record` `0x1032fa` |
| `ACCOUNT` | literal | account balance query | `account` `0x10c582` |
| — (token 0x22 DAT) | raw data | file/frame data block | `send_dat_packet` `0x108254`, `upload_file` `0x10c0ee` |
| — (tokens 0x40/0x41) | control | download flow-control | `file_download_xfer` `0x10b174` |

After every command the client waits for the single-byte ack `@` (0x40) via
`serial_io_c` — identical to the C64 client's ack handling.

## Full census (53)

Grouped by reconstruction module. `sz` is the decompiled byte size.

### Transport / connect — `transport.c`, `connect.c`, `login.c`
| addr | recon name | sz | note |
|------|-----------|----|------|
| `0x1192b6` | `open_transport` | 410 | create ports+reqs, OpenDevice cnet.device |
| `0x11956a` | `serial_write` | 274 | CMD_WRITE, token+data |
| `0x11967c` | `serial_read` | 290 | CMD_READ |
| `0x11979e` | `serial_io_c` | 322 | command + `@`/`A`/`B` ack classify |
| `0x1011998a`| `serial_io_variant`| 154 | carrier-aware variant |
| `0x1190e8` | `log_device_message` | 260 | `%s %02lx` debug log |
| `0x10343c` | `do_connect` | 662 | dial → login → open frame window |
| `0x1032fa` | `send_login_record` | 322 | `Z`+userid+pw+`AM21`+version |
| `0x103162` | `wait_connect_handshake` | 408 | wait `@ okay`, detect `NO CARRI` |
| `0x10e0fc` | `validate_login` | 140 | `D%02d` after login |

### Frame display (PETSCII) — `frame.c`
| addr | recon name | sz |
|------|-----------|----|
| `0x10800c` | `read_frame_byte` | 122 |
| `0x108086` | `frame_rle_getchar` | 84 |
| `0x1054f8` | `render_char` | 358 |
| `0x106000` | `build_font` | 246 |
| `0x107000` | `blit_char_cell` | 342 |
| `0x108254` | `send_dat_packet` | 42 |

### Navigation — `navigate.c`
| addr | recon name | sz | cmd |
|------|-----------|----|-----|
| `0x1023ec` | `set_connection_state` | 498 | — |
| `0x10a1e2` | `goto_page` | 184 | P |
| `0x1098e8` | `link_follow` | 216 | L |
| `0x10a310` | `link_goto` | 116 | L |

### Directory actions — `directory.c`  (**census-recovered**)
| addr | recon name | sz | cmd |
|------|-----------|----|-----|
| `0x10c510` | `vote` | 114 | V |
| `0x10c428` | `extend_life` | 162 | X |
| `0x10c582` | `account` | 220 | ACCOUNT |
| `0x10c2f8` | `put_frame` | 226 | U |
| `0x10c270` | `put_frame_xfer` | 110 | U+DAT |

### File transfer — `transfer.c`
| addr | recon name | sz |
|------|-----------|----|
| `0x10b000` | `download_charged_prompt` | 110 |
| `0x10b06e` | `download_filename_prompt` | 124 |
| `0x10b0ea` | `download_machine_prompt` | 138 |
| `0x10b174` | `file_download_xfer` | 370 |
| `0x10b2e6` | `download_no_room` | 136 |
| `0x10b380` | `action_download` | 398 |
| `0x10b50e` | `action_download_run` | 244 |
| `0x10b66a` | `download_link` | 198 |
| `0x10b730` | `download_check` | 102 |
| `0x10c000` | `upload_filename_prompt` | 48 |
| `0x10c0b4` | `upload_read_file` | 58 |
| `0x10c0ee` | `upload_file` | 354 |

### Mail — `mail.c`  (**census-recovered**)
| addr | recon name | sz |
|------|-----------|----|
| `0x10e188` | `mail_submit` | 528 |
| `0x10e468` | `mail_read` | 558 |
| `0x10e000` | `mail_prepare` | 88 |
| `0x10e058` | `mail_finish` | 92 |
| `0x10e0b4` | `mail_send_record` | 72 |
| `0x10e398` | `mail_field_send` | 106 |
| `0x10e402` | `mail_field_next` | 46 |
| `0x10f000` | `mail_open_window` | 158 |
| `0x10f09e` | `mail_upload_mode` | 120 |
| `0x10f116` | `id_check_mode` | 120 |
| `0x10f23a` | `mail_event_loop` | 398 |

### Config / launch / startup — `config.c`, `launch.c`, `startup.c`
| addr | recon name | sz |
|------|-----------|----|
| `0x102000` | `load_config` | 174 |
| `0x112250` | `save_config_file` | 86 |
| `0x1001c4` | `open_dos_library` | 22 |
| `0x1025de` | `launch_editor` | 208 |
| `0x1026ae` | `launch_tty` | 358 |
| `0x100858` | `hex_format` | 102 |

### Misc helper
| addr | recon name | sz |
|------|-----------|----|
| `0x10c404` | `extend_by_prompt` | 36 |
| `0x10c4ca` | `vote_choice_prompt` | 70 |

> Not in the census (no strings, no sends) but reconstructed anyway because the
> frame parser calls them by pointer: the RLE/font helpers already listed under
> `frame.c`. Resource-tracking wrappers (`resource_mark` etc.) are SAS/C runtime —
> see `resources.c`.
