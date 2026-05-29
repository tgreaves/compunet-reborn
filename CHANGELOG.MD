# 0.8-beta (2026-05-29)

* PETSCII Terminal Mode (port 6401):
	* New server-rendered terminal interface: any PETSCII terminal program
	  (SyncTerm, CCGMS, StrikeTerm, etc.) can connect without the custom client.
	* Full welcome screen with template rendering (user info, pages, storage,
	  pillarbox mail indicator) — pixel-accurate match to the C64 client.
	* Directory browsing with C64-accurate bordered layout: thick/thin box
	  drawing, column separator at col 30, status line, breadcrumb, F7/F8
	  column toggle (PRICE/LIFE/AUTHOR/VOTE).
	* Duckshoot command bar: revolving display with selected item in centre,
	  full C64 command set (17 commands: HELP, DIR, SHOW, BACK, GOTO, UCAT,
	  MAIL, ACCNT, SAVE, EDITR, LEAVE, PRINT, LIFE, BUY, LOAD, UPLD, VOTE).
	* Frame display with RLE expansion ($06/$07 codes) — correct count+1
	  semantics matching C64 ROM behaviour. Single-frame pages show
	  "PRESS ANY KEY" instead of duckshoot.
	* CR suppression after full 40-char lines (prevents blank line on terminal
	  auto-wrap, matching C64 KERNAL CHROUT behaviour).
	* Charset mode management: uppercase/graphics ($8E) for PETSCII artwork,
	  lowercase/uppercase ($0E) for text rendering.
	* Auto-detect Telnet vs Raw connections (IAC negotiation for Telnet clients,
	  $FF byte escaping).
	* PETSCII test indicator on login screen (block character).
	* GOTO (page numbers, keywords, WHO), VOTE, MAIL, LIFE, WHO IS ONLINE,
	  LEAVE, HELP, ACCNT, BUY, UPLD commands implemented.
	* MAIL: full bordered inbox with cursor navigation, F7/F8 column toggle
	  (SENDER/DATE/STATUS), SHOW to read, SEND to compose+deliver with
	  COURIER envelope. Email notifications on send.
	* BUY: XMODEM-CRC file download for 'P' pages, partyline entry for 'L'
	  pages, credit deduction for paid content.
	* UPLD: XMODEM-CRC upload for 'P' pages, editor-based compose for 'T'
	  pages. Progressive preview in directory during entry.
	* EDITR: frame viewer/editor with 20-frame rolling memory. Commands:
	  EDIT (free cursor), NEW, COPY, ERASE, LAST, NEXT, GET (XMODEM upload
	  frames), PUT (XMODEM download frame), STORE (XMODEM download all),
	  FREE (show memory remaining). Dedicated editor HELP screen.
	* Partyline: full terminal UI with bordered chat area, input area,
	  scrolling messages, commands (*help, *who, *alias, *enter, *quit).
	  Integrated with partyline module (cross-client chat).
	* DIR on non-directory pages creates empty subdirectory (with upload
	  permission check). Directory persists only if content uploaded.
	* LEAVE uses goodbye.seq template (same artwork as protocol client).
	* HELP screen loaded from `server/cfg/help.pet`.
	* SHOW on type L pages shows "PLEASE USE BUY".
	* Login: generic "INVALID USERNAME / PASSWORD" error (security).
	* Shared state: terminal users appear in WHO IS ONLINE, same auth/audit system.
	* Efficient redraw: cursor up/down only repaints two entry lines, F7/F8
	  only repaints column values, duckshoot movement only repaints row 24.
	* Duckshoot position preserved across commands and frame view/return.
	* Version number displayed dynamically on login screen.
* Server:
	* Port 6401 listener added to main server event loop.
	* Dockerfile updated: terminal.py included, port 6401 exposed.
	* docker-compose.yml: port 6401 mapped.

# 0.7.2-beta (2026-05-29)

* Client:
	* Fixed: CPU JAM ($0008) on MAIL command and other multi-packet directory
	  responses. NMI handler now saves/restores $01 and ensures I/O is visible
	  (ORA #$06) before accessing ACIA registers. Previously, if NMI fired while
	  the directory parser had KERNAL banked out ($01=$34) to read RAM under I/O,
	  the hardware NMI vector at $FFFA/$FFFB read $0000 from RAM causing a jump
	  to zero page.
	* Hardware NMI vector at $FFFA/$FFFB in RAM now set to $CF00 (NMI handler
	  address) during ACIA_INIT, ensuring correct NMI vectoring regardless of
	  current bank configuration.
* Server:
	* Fixed: WHO IS ONLINE missing users. When a user reconnected (new TCP
	  connection before old session timed out), the old session's disconnect
	  handler removed the user from `_online_users` even though the new session
	  was still active. Now uses reference-counted tracking — user is only
	  removed from the online set when their last session disconnects.

# 0.7.1-beta (2026-05-28)

* Partyline:
	* Fixed: client not displaying any received text. NMI ring buffer was moved
	  to $C500 in the main client but the partyline client still read from $CE00.
	* Restored PETSCII conversion on send (with raw ASCII for protocol sentinels).

# 0.7-beta (2026-05-28)

* Server:
	* New EDITOR user role: can upload to any directory and modify any content
	  (same privileges as ADMIN for content management).
	* EXTEND permissions relaxed: any user can positively extend anyone's content
	  (costs their own storage/credit). Only owner, admin, or editor can reduce life.
	* `open_upload` flag in directory JSON: marks a subtree as open for uploads by
	  any user (replaces hardcoded "JUNGLE" author check). Set in the Jungle's
	  directory.json.
	* Audit/event log: key events (signup, connect, upload, extend, mail send/read,
	  partyline, page read, download, vote, password reset) logged to
	  `server/data/audit.jsonl`. All events include client IP address.
	* Email from address now shows "Compunet Reborn" as friendly name.
	* Fixed UCAT: SHOW now works on entries (price field must be first column
	  for client's free/paid check). LIFE reloads UCAT instead of previous DIR.
	* Pre-response delay reduced from 500ms to 250ms.
	* WHO IS ONLINE? (page 800): dynamic page showing connected users with
	  partyline indicator (*). Regenerated on each view.
	* `dynamic` flag in directory JSON for server-generated pages.
	* Page title slugs now strip filesystem-unsafe characters (?, !, etc.).
* Partyline:
	* Fixed case handling: uppercase/lowercase now preserved correctly in messages.
	* Fixed *QUIT: *EXIT sentinel was being PETSCII-converted, client couldn't match.
	* Blank line after "has left partyline" message.
	* Max idle ping limit (20): disconnects ghost sessions instead of pinging forever.
	* Admin/editor commands: *kick, *ban, *unban. Bans persisted to
	  `cfg/partyline-bans.json`. Banned users rejected on entry.
	* ADMIN user cannot be kicked or banned.
* Website:
	* Admin panel: EDITOR checkbox on user edit page.
	* Admin panel: Audit Log page with pagination (50 events/page), now shows IP.
	* Admin notification email when a new user completes registration
	  (templated via `server/cfg/new-user-notification.md`).
	* Contact page: form sends email to admin@compunet.live, links to
	  Courier mail on Compunet and Compunet Corner on Facebook.
	* Password reset via email: user enters email address, receives a 24-hour
	  tokenised reset link (template at `server/cfg/password-reset.md`).
	* "Forgot password?" link on login page.
	* All audit events now include client IP address.
	* Connect page: two-column VICE/Ultimate setup, step-by-step screenshots,
	  Windows VICE workaround callout, SFX manual client download added.
* Content:
	* New PETSCII COMPUNET logo header for root directory (extracted from
	  welcome frame artwork).
* Dev:
	* `vice_test.sh` updated for SFX auto-connect client (no SYS or IP needed).
	  Usage: `./vice_test.sh <username> <password> [--restart-server]`
	* Website templates, static files, and app.py volume-mounted in Docker.
	  Template/CSS changes deploy with just `git pull` + container restart (no rebuild).

# 0.6.4-beta (2026-05-28)

* Client:
	* Moved NMI ring buffer from $CE00 to $C500: eliminates overlap with
	  CRT_ENTRY and auto_connect_addr which grow toward end of ACIA segment.
	  Fixes Ultimate reconnect crash (hostname corruption) permanently.
	* ACIA_INIT now forces $00=$2F/$01=$37 (correct DDR/port) before
	  configuring ACIA. Fixes intermittent I/O invisibility on some VICE
	  configurations where processor port was left in wrong state.
	* Makefile: live PRG now uses its own entry point detection
	  (LIVE_CRT_ENTRY_ADDR) — was using wrong address from non-live binary,
	  causing jump into hostname data instead of CRT_ENTRY.
	* @wait_resp timeout increased from ~0.5s to ~8s (was racing with
	  server's 500ms response delay).
* Known limitation:
	* Windows VICE auto-connect intermittently fails to receive server
	  response. VICE's SwiftLink emulation doesn't deliver TCP data to
	  the ACIA under certain timing conditions. Workaround: use SFX manual
	  client (compunet-reborn-sfx.prg) and enter vme.compunet.live:6400.

# 0.6.3-beta (2026-05-27)

* Client:
	* Fixed auto-connect reconnect failure on C64 Ultimate: `auto_connect_addr`
	  data was placed after CRT_ENTRY, overlapping into the NMI ring buffer at
	  $CE00. After the first connection, received data corrupted the hostname
	  for subsequent dials. Moved data before CRT_ENTRY.
	* Fixed intermittent CPU JAM ($0008) on Windows VICE: SFX decompressor left
	  dirty zero-page locations ($9E,$9F,$A7,$A8,$AE,$AF) and residue on the stack
	  page. CRT_ENTRY now clears both zero-page decompressor state and the full
	  stack page ($0100-$01FF).
	* Fixed "stuck on Dialling" on reconnect: ACIA_DIAL @wait_resp now has an ~8
	  second timeout. Returns to prompt on failure instead of hanging forever.
	* ACIA_WAIT_READY TDRE poll has ~4 second timeout for Windows VICE where the
	  socket may not be established immediately.

# 0.6.2-beta (2026-05-27)

* Client:
	* Fixed intermittent "stuck on Dialling" in VICE auto-connect client: removed
	  NMI disable during TX (was setting RTS high which blocked VICE socket),
	  added TDRE poll + 200ms settle delay before dialling to wait for socket
	  readiness.
* Dev:
	* Build hash override: `make HASH=xxxxxx` for testing against a specific server.

# 0.6.1-beta (2026-05-24)

* Client:
	* Fixed intermittent byte loss during ATDT on C64 Ultimate: RX NMI now
	  disabled during transmission to prevent NMI handler interfering with TX.
* Dev:
	* Makefile auto-detects CRT_ENTRY address (no longer hardcoded).

# 0.6-beta (2026-05-24)

* Client:
	* New self-extracting PRG: `LOAD "COMPUNET",8` then `RUN` — no SYS command
	  needed. Decompresses and starts automatically via exomizer.
	* Auto-connect "live" variant: connects to vme.compunet.live:6400 without
	  prompting for a phone number. Available as PRG and D64.
	* D64 now contains SFX version as primary file ("COMPUNET"), live auto-connect
	  ("COMPUNET-LIVE"), and raw PRG ("COMPUNET-RAW").
* Website:
	* Refreshed design: dark theme with modern retro aesthetic. Clean body font,
	  pixel font for headings, C64 colour palette accents.
	* Connect page: download links for live PRG/D64, instructions for VICE and
	  C64 Ultimate, simplified connect flow (no phone number needed).
	* New Guide page: full user guide covering navigation, mail, uploads,
	  partyline, editor, and all duckshoot commands.
	* Trailer video embedded on home page.
* Dev:
	* `server/data/content/` no longer tracked by git. Prevents `git pull` from
	  overwriting live content on production. Use `server/data.example/` as template
	  for fresh installs.
	* Build system generates SFX PRG via exomizer alongside raw PRG/D64.
	* Auto-connect build variant (`-D AUTO_CONNECT`) skips phone number prompt.
	* CRT_ENTRY trampoline added for SFX/cartridge entry (resets CPU state).

# 0.5-beta (2026-05-23)

* Client:
	* Fixed C64 Ultimate compatibility: AT commands were sent in PETSCII ($C1$D4)
	  instead of ASCII ($41$54). The Ultimate's SwiftLink bridge requires ASCII.
	* ACIA initialization no longer de-asserts RTS during setup (broke bridge
	  handshake on hardware with RTS flow control enabled).
	* NMI ring buffer pointers now correctly initialized to zero.
	* TX routine polls TDRE before writing (was blind-writing with fixed delay).
	* NMI handler simplified: no IRQ toggling (prevents nested NMI on real hardware).
* Partyline:
	* Fixed long messages being truncated: server now splits messages longer than
	  35 chars into multiple display lines.
	* Fixed *PING keepalive appearing on screen (check was unreachable dead code).
	* Fixed multi-line input: first RETURN pads to 35-char boundary so each
	  visual line displays separately under one name header.
* Dev:
	* Client version check now uses a hash of `compunet.s` source instead of git
	  commit hash. Server-only changes no longer force a client rebuild.
* Server:
	* Fixed upload field parsing: server was reading 8-byte price field but client
	  sends 6 bytes (NNN.NN) + 3-byte lifetime (NNN). The 2-byte overlap caused
	  lifetime digits to bleed into price (e.g. price 0 parsed as 0.01) and
	  lifetime to lose its leading digits (e.g. 999 parsed as 9).
	* Mail auto-expiry: read messages hidden from inbox after 2 days (soft delete,
	  files remain on disk).
	* Email notification: users receive a real email (via Postmark) when they get
	  new in-game mail. Template at `server/cfg/mail-notification.md`.

# 0.4.1-beta (2026-05-22)

* Client:
	* Put back disk drive check (was breaking UPLOADs)

# 0.4-beta (2026-05-22)

* Client:
	* Removed legacy disk drive check for voting on P/A type pages.
	* Partyline client: silent *PING keepalive handling.
	* Client version check: git commit hash sent in CNET identification field[1].
* Server:
	* Fixed GOTO crash when targeting frame pages (always returns directory response).
	* Invalid GOTO now reloads current directory instead of crashing.
	* Client idle timeout extended from 10 to 20 minutes.
	* Client version verification: rejects outdated clients with "PLEASE DOWNLOAD LATEST CLIENT".
* Website:
	* Admin broadcast page: compose in Markdown, sends as HTML via Postmark broadcast stream.
	* Test mode sends to admin users only; all mode sends to all subscribers.
	* Display name field on registration now allows mixed case.
	* Broadcast editor uses readable monospace font.
* Partyline:
	* Added *PING keepalive (every 60s idle) to prevent NAT/firewall drops.
	* Added logging for commands, messages, and keepalive activity.

# 0.3-beta (2026-05-20)

* Client:
	* Fixed backspace not working on login password field.
* Server:
	* Type 'L' (link) directory entries: BUY triggers MODEM_INIT_DOWNLOAD to stream executable code to client.
	* Partyline directory with "JOIN PARTYLINE" L-type entry added.
	* Fixed multi-frame upload corruption: packet chunks now accumulated properly.
	* Free storage tracking: 2000 units/quarter, EXTEND uses free storage first then credit.
	* EXTEND supports negative values to reduce LIFE (refunds storage). Life=0 deletes page.
	* Admins can EXTEND/reduce any content (not just their own).
	* Fixed EXTEND causing navigation into child directory on reload.
	* Fixed EXTEND not persisting updated life to directory JSON.
	* Fixed negative EXTEND not persisting reduced life.
	* Upload prices now rounded to 2 decimal places (prevents invalid fractional values).
* Partyline:
	* Full multi-user chat system implemented (server/partyline.py).
	* C64 client: draws UI frame, sends/receives messages via ACIA, scrolling chat.
	* Commands: *help, *alias, *who, *enter, *dice, *call, *quit.
	* Room system: users start in lobby, can create/join rooms with *enter.
	* Cursor up/down scrollback through 114 lines of chat history.
	* History buffer at $3000 (not included in download binary for speed).
	* Web admin partyline client at /admin/partyline (WebSocket-based).
	* PETSCII-to-ASCII conversion for C64 text input.
	* Loads at $2000 (safe RAM area, avoids terminal workspace).
* Dev:
	* Partyline demo disassembly (partyline_demo.s) added to client/c64/vintage/.
	* Partyline source in client/c64/src/partyline/ with build system.
	* server/data/ now tracked in git (except mail, votes, jungle subdirs).
	* Removed placeholder content (NEWS, CHAT, VIP, etc.) — clean slate.
	* Added DEMOS jump-off directory to Jungle.
	* D64 download now hosted from website (copied during build, no GitHub link).
	* PARTYLINE_WS_URL env var for configuring browser WebSocket endpoint.
	* partyline.py added to server Dockerfile.
	* Partyline design documented in docs/partyline.md.

# 0.2-beta (2026-05-19)

* Client:
	* Phone number input now accepts up to 24 characters (was 16).
	* Phone number input now accepts letters, allowing domain name entry.
	* Domain names are automatically lowercased when sent over the wire.
	* MOTD display: server-sent text shown during connection handshake.
	* Fixed duplicate character bug in connection handshake (NMI double-read).
	* Increased connection handshake timeout to ~30 seconds.
* Website:
	* Admin panel: View all registered users and pending registrations.
	* Admin panel: Edit user password, credit, name, email, and account type.
	* Admin panel: Approve or delete pending registrations.
	* Login now properly verifies passwords via server API.
	* Config now finds .env in project root when running locally (not just Docker).
	* Added animated walkthrough GIF to home page.
	* Connect page: added D64 download link, updated server address.
* Server:
	* New /api/auth endpoint for credential verification.
	* New /api/pending list endpoint for admin use.
	* /api/users update endpoint now supports credit and email changes.
	* Email address now stored when user accounts are created.
	* Fixed unhandled exception on client disconnect (connection reset).
	* Removed plaintext passwords from log output.
	* Mail pagination: mailbox now shows max 11 messages per page with MORE/BACK.
	* Fixed mail frame flags (last frame bit 7 now correctly cleared).
	* Fixed mixed-case real names displaying as graphics characters on C64.
	* Unread mail indicator: "MAIL" shown in red on directory breadcrumb line.
	* Welcome screen: recreated original PETSCII artwork from historical template.
	* Welcome screen: pillarbox mail indicator (shown when unread mail exists).
	* Welcome screen: live PAGES/NEAR DEATH, FREE STORAGE, NEXT QUARTER fields.
	* Welcome screen: last login date/time now persisted between sessions.
	* Fixed welcome frame packet timing (50ms → 250ms to prevent buffer overflow).
	* F-key navigation shortcuts: F1-F6 trigger GOTO via Part 3 field definitions.
	* WHO page: GOTO WHO shows currently connected users (WIP).
	* MOTD: pre-login message of the day displayed during connection handshake.
* Dev:
	* server/data/ removed from git tracking (use server/data.example/ for dev setup).
	* users.json removed from git tracking (use users.json.example for dev setup).
	* README: added Live Service section linking to https://compunet.live/
	* Docs: clarified that any number can be entered at the phone number prompt.

# 0.1-beta (2026-05-19)

First release.
