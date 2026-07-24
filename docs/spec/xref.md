# Implementation cross-reference

> Part of the [Compunet Client Specification](README.md). This maps each spec section to
> where its behaviour is implemented in the server — the protocol authority. Keep it beside
> the spec: when server code here changes, check the linked spec section; when a spec claim
> is doubted, jump to the code.
>
> Paths are relative to the repo root. Line numbers drift as code changes — treat the
> function/symbol name as authoritative and the line as a hint.

## §2 — Transport

| Spec | Claim | Server location |
|---|---|---|
| §2.2 | `$01…$02` framing | `server/x25_protocol.py` `PKT_START`/`PKT_END`, `feed_data` |
| §2.3 | Byte stuffing (`$01–$03` → `$03`+`b+$20`) | `x25_protocol.py` `_byte_stuff`, de-stuff loop in `feed_data` |
| §2.4 | Content layout `[len][token][seq][payload][crc×2]` | `x25_protocol.py` `make_data_packet`, `feed_data` parse |
| §2.5 | Tokens `ACK=$20`, `DAT=$22`, `COM=$43` | `x25_protocol.py` `TOKEN_*`; **COM acted on as `$43`** `compunet_server.py` (`token == 0x43`) |
| §2.6 | CRC-CCITT `$1021`, init `$0000`, zero-residual | `x25_protocol.py` `crc_ccitt` (call sites pass `0x00,0x00`) |
| §2.8 | Sequence `$20–$5F`, wrap, window 4 | `x25_protocol.py` `SEQ_MIN`/`SEQ_MAX`/`WINDOW_SIZE`, `_advance_seq` |
| §2.9 | ACK pacing; EOS not ACKed; 5 s timeout | `compunet_server.py` `wait_for_ack`, `send_pkt_with_ack` |
| §2.10 | Handshake byte `$20` | `x25_protocol.py` `make_handshake`, `check_handshake` |

## §3 — Session lifecycle

| Spec | Claim | Server location |
|---|---|---|
| §3.2 | 12×`$20` handshake; Hayes auto-detect | `compunet_server.py` `tcp_handler` (handshake loop; `& 0x7F == 0x41` Hayes branch) |
| §3.3 | Identification; native vs hash-gated detection | `compunet_server.py` `tcp_handler` (`b'CNET'` parse; `has_slash`/`is_amiga`) |
| §3.3 | Hash gate + `*PLEASE DOWNLOAD LATEST CLIENT` | `compunet_server.py` (`client_version.txt` compare) |
| §3.4 | MOTD (PETSCII-lowercased) + `*CON\r` | `compunet_server.py` `tcp_handler` (motd.txt loop; `\x2a\x43\x4f\x4e\x0d`) |
| §3.5 | Login packet `Z` + creds; auth; welcome/error frame | `compunet_server.py` (`cmd_byte == 0x5A`), `handle_login` |
| §3.6 | LINKING stream (ROM only); skipped for native | `compunet_server.py` (`linking_header`; `is_amiga` skip) |
| §3.7 | Command loop; native `@` ack prefix | `compunet_server.py` `handle_command` dispatch; `tcp_ack_prefix` |
| §3.8 | LEAVE close; 20-min idle timeout | `compunet_server.py` `tcp_handler` (`_leaving` close; `reader.read` timeout=1200) |

## §4 — Command protocol

| Spec | Claim | Server location |
|---|---|---|
| §4.1 | Command = `cmd byte` + ASCII-decimal arg | `compunet_server.py` `handle_command` (`data[0]`, `data[1:]`) |
| §4.2 | DAT stream + EOS; ACK single-packet no EOS | `compunet_server.py` command-response chunk loop (`last_response_type != RESP_ACK` EOS gate) |
| §4.3 | Response types ACK/DIR/FRAME/ERROR/LINKING | `compunet_server.py` `RESP_*` + EOS gate (`last_response_type != RESP_ACK`) |
| §4.5 | Parser selection by command/mode | `compunet_server.py` `handle_command` / `_cmd_dir` (entry-type branch); `docs/PROTOCOL.md` (GOTO always DIR) |
| §4.3 | `@` (`$40`) ack prefix for ID / mail-send | `compunet_server.py` (`tcp_ack_prefix` + `is_amiga`) |
| §4.4 | Command dispatch table | `compunet_server.py` `handle_command`; `CMD_*` constants |
| §4.4 | `E` = LEAVE (not editor); `CMD_EDITR` vestigial | `compunet_server.py` (`cmd == ord('E')` → `_cmd_leave`) |

## §5 — Display contract

| Spec | Claim | Source |
|---|---|---|
| §5.1 | 40×24 content grid | `client/amiga/src/frame_control.c` (cursor bounds `0x28`/`0x17`, `clear_screen`) |
| §5.2 | Charset select `$0E`/`$8E` | `frame.c` `frame_display`; `frame_control.c` `charset_upper` |
| §5.3 | PETSCII→screen-code conversion | `client/amiga/src/frame.c` `render_char` (`byte >> 5`) |
| §5.4 | Font = C64 char ROM | Amiga embedded ROM (`0x11d9c0`/`0x11ddc0`), `build_font` |
| §5.5 | 16-colour palette; index→pen remap | Amiga `LoadRGB4` table (`0x11d0c2`); `client/amiga/src/globals.c` `g_palette` |
| §5.6 | Control-code tables | `client/amiga/src/frame_control.c` `g_ctrl_lo`/`g_ctrl_hi` |
| §5.7 | Reverse video (inverted glyph) | `frame_control.c` `reverse_on`/`reverse_off`; `frame.c` font build |

## §6 — Frame format

| Spec | Claim | Server location |
|---|---|---|
| §6.2 | 4-byte header `[flags][border][bg][charset]` | `compunet_server.py` `_make_info_frame`, `_send_current_frame`; `client/amiga/src/frame.c` `frame_display` |
| §6.3 | PETSCII body, `$00` terminator | `client/amiga/src/frame.c` `frame_display` (`while … != '\0'`) |
| §6.4 | RLE `$06`/`$07`, `1+N` count | `client/amiga/src/frame.c` `frame_rle_getchar` (recon `FUN_00108086`) |
| §6.5 | Multi-page flags bit 7 | `compunet_server.py` `_send_current_frame` (flags byte); `docs/PROTOCOL.md` |

## §7 — Directory format

| Spec | Claim | Server location |
|---|---|---|
| §7.2 | Six-part directory stream | `compunet_server.py` `_make_page_response` |
| §7.3 | Entry layout; dual comma/fixed-width constraint | `compunet_server.py` `_make_page_response` Part 6; `client/amiga/src/directory_parse.c`; `docs/PROTOCOL.md` L_A5F3 |
| §7.4 | Entry types | `compunet_server.py` `type_string`; `docs/PROTOCOL.md` §Directory Entry Types |
| §7.5 | Built-in template (Part 1 empty) | `client/c64/src/compunet.s` `$BCE1` (loaded at L_A385); `directory_parse.c` (Amiga) |
| §7.6 | 11 entries/page paging | `compunet_server.py` `_cmd_dir`/`_make_page_response` (`dir_page_offset`, `[:11]`) |

## §8 — Subsystems

| Spec | Claim | Server location |
|---|---|---|
| §8.2 | Mail = 6-part directory | `compunet_server.py` `_cmd_mail`, `_cmd_mail_show` |
| §8.3.1 | Program download header; `$40`/`$41` tokens | `compunet_server.py` `_send_current_frame` (type `P`); `token == 0x40`/`0x41` branches |
| §8.3.2 | Upload / mail-send; validation stream | `compunet_server.py` `_cmd_upload`, `_cmd_upload_content`, `_cmd_mail_send` |
| §8.5 | Partyline; link entry; raw session | `compunet_server.py` `_cmd_dir` (type `L`, `is_amiga` branch); `server/partyline.py` `handle_session`/`handle_amiga_session` |
| §8.6 | UCAT / VOTE / BUY | `compunet_server.py` `_cmd_ucat`, `_cmd_vote`, `_cmd_buy` |

## §A — Appendices (data provenance)

| Appendix | Source |
|---|---|
| §A.3 palette RGB | Amiga `LoadRGB4` table `0x11d0c2` (via `g_palette` remap) |
| §A.5 font | Amiga embedded C64 char ROM `0x11d9c0` / `0x11ddc0` |
| §A.6 directory template | `client/c64/src/compunet.s` `$BCE1`–`$BD77` |
