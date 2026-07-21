# Amiga client — TCP transport design (milestone 2b)

Design for swapping the Amiga client's `cnet.device` modem transport for a native
TCP connection to the Reborn server. Grounded against the reconstructed client
(`connect.c`, `login.c`, `transport.c`) and the server (`server/x25_protocol.py`,
`server/compunet_server.py`). **Nothing here is inferred** — each claim cites the
code it came from.

## STATUS (2026-07-21) — logged in over TCP; frame rendering is next

Verified live against a Reborn server (docker.lan) from the reconstructed client in
WinUAE (KS3.x). **A full login now completes over native TCP:**

connect → server detects the Amiga (`*** Amiga client detected ***`) → `*CON`
handshake → credentials dialog (userid + password captured) → login record → server
`login OK!` → the 768-byte welcome frame streams as DAT frames, **each ACK'd by the
client** (X.25 flow control working) → EOS → `LINKING: skipped (Amiga native client)`.

### What works
- Native bsdsocket TCP transport, all seams wired (`net.c` + the `g_tcp_mode` branches).
- `net_read_stream`: DAT-payload accumulation, per-frame `$20` ACK, empty-DAT = EOF —
  confirmed by the server's `ACK received` after every frame.
- Server Amiga branch: identification detection (race-hardened) + LINKING skip.
- Credentials capture (see fixes below).

### Fixes made this session
Client (all in the `g_tcp_mode` path / UI, uncommitted → committed with this note):
- `login.c` — case-insensitive `*CON` match (server sends uppercase `*CON`; the
  original matched lowercase `*con`) — without this the handshake looped forever.
- `login.c` — skip the pre-login `serial_io_c` in TCP mode (Reborn waits for the login
  frame after `*CON`; reading first deadlocked).
- `ui.c` `logon_poll` — **re-point the credentials string-gadget `StringInfo.Buffer`
  fields at the real `g_login_userid`/`g_login_scratch`.** The blob's gadgets held the
  original absolute addresses `0x120244`/`0x12024d`, which are OUTSIDE the data blob
  (ends `0x1200e8`) and were never relocated, so typed input went to stray memory.
- `ui.c` `logon_poll` — `case 3` must `ActivateGadget(last->NextGadget, …)` (recon
  `FUN_00115168` @0x1151f6), not `last` — so ENTER on the userid field advances to the
  password field. (The earlier recon activated `last`, so the password came through empty.)
- `ui.c` — widen the password gadget (original `Width` was 8px = one char).
Server (`compunet_server.py`, additive): Amiga identification branch + LINKING skip.

### NEXT STEP — frame rendering does not display
The **"Current frame" window opens but stays blank** — the 768-byte welcome frame
arrives and is ACK'd, but nothing renders. The transport delivered the bytes; the
break is in the display path. Investigation starting points:
- `frame.c` `read_frame_byte` → `frame_rle_getchar` → `render_char`, and whoever drives
  the frame parse after login (`do_connect` calls `frame_display(g_frame_page, g_frame_out)`
  then the `serial_read` drain loop). Confirm `frame_display` (thunk `FUN_0010818a`) and
  `frame_display_done` actually parse+blit, or are stubs.
- `open_frame_window` sets `g_frame_page = (APTR)&g_frame_win` (ui.c) — verify the frame
  page/offscreen bitmap the renderer draws into is real and blitted to the window
  (`frame_gfx.c` offscreen begin/end).
- Verify `net_read_stream` hands the frame bytes to `read_frame_byte` correctly (the
  first `serial_io_c` peek + `net_unread_byte` pushback must not drop the first byte).
- The welcome-frame payload starts `01 05 22 …`? No — that's the wire frame; the DAT
  *payload* is the frame content (flags/border/bg + PETSCII). Capture the delivered
  payload bytes and walk them through `render_char` by hand to see where it stalls.

### Systemic risk uncovered
The credentials-gadget bug is a **class**: any blob structure whose pointer targets the
globals region (> `0x1200e8`) holds a stale absolute address, because `extract_data.py`
wired blob-internal and blob→code relocs but not blob→global-data ones. Other
windows/menus may have the same latent issue. Worth an audit of `extract_data.py` +
the blob's out-of-range relocs (could also relate to the blank frame if the frame
window's structures point out-of-blob).

## The corrected architecture (important)

An earlier note in `docs/amiga-client.md` said the swap was "replace `serial_read`/
`serial_write` with `recv`/`send`." **That is wrong** and would not work. The X.25
framing/CRC/sequencing does **not** live in the client — it lives in `cnet.device`
(confirmed: CRC-CCITT table + frame builder disassembled, see
`../vintage/tools/re/protocol-analysis.md`). The client hands the device `(token,
data)`; the device produces the `$01…$02` wire frame. So raw `send`/`recv` of the
client's buffers would put **unframed** bytes on the wire, and the Reborn server
speaks X.25-framing-over-TCP (it does so to the C64 today).

Therefore the TCP transport must **do the framing the device used to do**. The good
news: `server/x25_protocol.py` is a complete, authoritative implementation of that
exact framing, so the client side is written to match it (the same philosophy Reborn
already uses on the C64 — server implements the protocol the client expects).

### Approach: in-client sockets (not a TCP `cnet.device`)

Two packagings were possible: (A) a drop-in TCP `cnet.device`, or (B) do the sockets
+ framing inside the client's own transport layer. **Chosen: B.** Reason:
`bsdsocket.library` requires the *calling task to be a Process* (per-task `SocketBase`,
signal handling) — awkward inside a device task, natural in the client's own process.
B also keeps everything in the debuggable C we control. Cost: the client binary is
"modified" — but that is the whole point of the reconstruction (we are building a
Reborn client), and the original still runs unmodified against real `cnet.device`.

## The wire model (verified, both directions)

From `server/x25_protocol.py`:

- **Frame:** `$01 <byte-stuffed content> $02`.
- **Content (pre-stuffing):** `[len][token][seq][payload…][crc_hi][crc_lo]`.
  - `len` = total **unescaped** bytes between markers, incl. itself = `len(payload)+5`.
  - `token`: DAT `$22`, COM `$43` on the wire (the server's command loop keys on
    `token==0x43` for COM — line 2669; `$26` is only the logical name). ACK `$20`.
  - `seq`: range `$20–$5F`, wraps to `$20` (`_advance_seq`).
  - `crc`: **CRC-CCITT poly $1021, init $00/$00**, over `[len][token][seq][payload]`
    (`make_data_packet` / `make_ack`, both `crc_hi=0x00, crc_lo=0x00`).
- **Byte stuffing:** bytes `$01–$03` → `$03 (b+$20)`; applied after CRC, reversed on RX
  (`_byte_stuff` / de-stuff loop in `feed_data`).
- **Flow control:** the server sends each DAT frame via `send_pkt_with_ack` and then
  **waits (5 s) for the client to send a `$20` ACK frame** carrying the received seq
  (`wait_for_ack`, lines 2453-2481). So the client RX path **must generate an ACK
  frame per received DAT frame**. Non-ACK packets arriving during the wait are stashed
  server-side, so ordering is forgiving.

## The connect sequence (client ↔ server align)

Client side is `do_connect` (`login.c`); server side is the TCP handler
(`compunet_server.py` ~2484-2630). They already line up:

| Step | Client (`do_connect`) | Server |
|------|-----------------------|--------|
| handshake | (currently modem dial) | sends **12×`$20`** unprompted (line 2523) |
| turnaround | sends `_` ×2 raw, waits ≥10 status bytes | (absorbed as pre-ident bytes) |
| **identification** | `C CNET\r` ×2, delay, `00000000000000\r` — all **raw/unframed** via `modem_send_delayed` (lines 263-266) | scans raw bytes for `CNET` (line 2567) |
| server MOTD + go | `wait_connect_handshake` scans for `*con` (line 177) | sends MOTD then **`*CON\r`** (line 2625) |
| **login** | `send_login_record`: `Z`+user(8)+pass(6)+zeros+`AM21`+ver+rev, as a **COM frame** `serial_write(rec,0x1b,1,TOKEN_COM)` (line 106) | reads COM `$43`, `payload[0]=='Z'` → `handle_login` (line 2678) |
| ack | `serial_io_c` reads back the `@`/`A`/`B` ack (line 278) | login → sends welcome DAT frames + EOS; command acks are `RESP_ACK=0x41 'A'` (line 203) |

So identification/handshake bytes cross the wire **unframed** (plain text, both ways);
only from the login record onward is everything X.25-framed.

### The one required server change

The server checks identification **field[1] = `{hash}/100`** against
`client_version.txt` and rejects a mismatch with `*PLEASE DOWNLOAD LATEST CLIENT`
(lines 2578-2593). The Amiga's field[1] is `C CNET` (no hash) → it would be rejected.
**Mandatory, additive server change:** detect the Amiga identification (doubled
`C CNET\r`, or field[1]==`C CNET`) *before* the hash check, mark the session
Amiga/PETSCII, and skip the hash gate — mirroring the existing C64-vs-terminal split.
Harmless to C64 clients (their field[1] still has `/`).

## Transport-primitive mapping (what each seam becomes)

The client's transport calls and their TCP replacements:

| Client call (file) | Today (cnet.device) | TCP replacement |
|--------------------|---------------------|-----------------|
| `open_transport` (connect.c) | create ports + `OpenDevice("cnet.device")` | `OpenLibrary("bsdsocket.library")`, `socket()`; defer `connect()` to dial step |
| `dial_modem` (login.c call) | `io_Command 0xc` AT dial | `connect(fd, host:6400)`; success = connected |
| `modem_send_delayed` (raw send) | device raw write | `send(fd, buf, len)` — **no framing** (handshake/ident) |
| `modem_read_status` | bytes-waiting / −1 carrier | non-blocking `recv` peek → count; socket EOF/err → −1 |
| `serial_io_variant` (raw read) | device raw read | `recv(fd, buf, len)` — **no framing** (handshake) |
| `serial_write(data,len,st,token)` | device frames it | build X.25 frame(token,seq,payload) → `send`; (COM path) then await server response via `serial_io_c` |
| `serial_read(data,len,…)` | device de-frames | `recv`→de-stuff→CRC-check→**send `$20` ACK**→return payload + status |
| `serial_io_c(text)` | read back ack byte | read the server's response frame; return its first payload byte as `@`/`A`/`B` |

`modem_send` (the *other* one, `FUN_00103024`) is a **local logon-window echo**, not a
wire op — it stays unchanged.

The modem dial, `_`-turnaround probes, and carrier polling become no-ops/degenerate
under TCP (a socket has no dial); the identification + `*con` wait + framed login/command
protocol above the seam are unchanged.

## Config surface

Repurpose `g_phone_number` (`g_config+0x00`, the dial string that `do_connect`
already gates on and passes to "dial") as the **hostname**, optionally `host:port`;
default port **6400** (same as the C64 client). No new UI needed — the Settings
dialog already edits this field. `g_baud_*` / modem-name fields become irrelevant
under TCP but stay in the config block (unchanged layout, still 0x36 bytes).

## Build integration

- New module (e.g. `net.c`) providing the bsdsocket primitives; `transport.c` /
  `connect.c` / `login.c` call into it behind the existing seam names.
- `bsdsocket.library` needs KS2.04+ and a TCP/IP stack (Roadshow/AmiTCP/Miami — all
  expose the same BSD-socket API) in the emulated Amiga. The offline UI still targets
  1.3; runtime-detect bsdsocket and degrade gracefully so the same binary boots on 1.3
  without a stack. Confirmed the current binary already runs on KS3.x (WinUAE).
- vbcc: bsdsocket protos come from the NDK (`proto/socket.h`); link `-lamiga` covers
  the library-base stub. Verify the KS1.3 NDK we assembled has `clib/socket_protos.h`
  + `proto/socket.h`; if not, add them (they are OS-version-independent).

## Open items to pin during implementation (do NOT guess)

1. **`serial_io_c` exact semantics** — cnet.device's `io_Command 0xb`. The client
   treats the returned byte as `@`(0x40)/`A`(0x41)/`B`(0x42). The server's per-command
   ack is `RESP_ACK=0x41 'A'` wrapped how? Confirm whether the ack is a bare byte, a
   DAT frame whose first payload byte is read, or an `$23`/OK-token frame — by tracing
   the server's `handle_command` return path and matching it to what `serial_io_c`
   must return. Pin before writing the COM ack path.
2. **CRC init** — the server verifies RX with init `$00/$00` and masks bit 7 (SwiftLink
   artifact, lines 297-300). Over TCP there is no bit-7 stripping, so the client must
   produce an exact `$00/$00`-init CRC. (The `$40E6` init in x25_protocol's docstring
   is a specific ROM ACK-send path, not the data path — use `$00/$00`.)
3. **Sequence expectations** — server `feed_data` tracks `rx_seq` but does not reject
   on mismatch; client TX seq start value and whether the server cares. Verify the
   server tolerates the client's seq numbering before relying on a specific start.
4. **Handshake framing boundary** — confirm the exact first-framed-byte point (login
   record is the first framed thing; everything before is raw). Matches the table
   above but verify against a live capture once connected.
