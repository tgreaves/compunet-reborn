# 0.6.3-beta (2026-05-27)

* Client:
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
