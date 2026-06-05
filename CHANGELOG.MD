# 0.13.2-beta (2026-06-05)

* Server:
	* Upload replace: uploading with the same title as an existing page now
	  replaces it instead of creating a duplicate (#78). Only the original
	  author (or admin/editor) can replace. Other users are rejected.
	  All metadata (price, life, type) and timestamp updated on replace.
	* Archive on replace/expire: old content is archived to
	  `server/data/archive/` with metadata before removal. Nothing is
	  ever permanently deleted.
	* Directory column justification (#80): PRICE right-justified with
	  leading space, LIFE right-justified with 2-space indent, VOTE
	  indented by one space. No leading zeros.
	* Column order changed to: PRICE, AUTHOR, VOTE, UPLDDATE, LIFE.
	  LIFE moved to last position to fix ROM upload preview showing
	  wrong column at "NEW ENTRY OK?" prompt (ROM uses last column
	  for LIFE preview via $C001).
* Dev:
	* `vice_test.sh` updated to use CRT cartridge instead of D64.

# 0.13.1-beta (2026-06-04)

* Server:
	* Fixed: UCAT now pages results (#76). Shows 10 entries + "MORE >>>>"
	  indicator when more exist. DIR on MORE advances, BACK returns to
	  previous page. Breadcrumb shows range (e.g. "UPLOADS 1-10").
	  Added UPLDDATE column.
* Terminal:
	* Directory paging: all directories now show "MORE >>>>" when entries
	  exceed 11. DIR on MORE advances to next page, BACK returns to
	  previous page. Matches C64 client behaviour.

# 0.13-beta (2026-06-03)

* Protocol:
	* LINKING: terminal code now downloaded from server on connect (#73).
	  Server sends 8-byte header (jump/load addresses) followed by terminal
	  binary (~7.7K) via ACK-paced packets. Download takes ~3 seconds.
	  "LINKING" status displayed during transfer.
	* Client SFX reduced from 12K to 5.5K. Terminal no longer bundled —
	  downloaded on demand. Raw PRG is 7.3K.
	* Server stores terminal at `server/cfg/terminal.bin`, sent to all
	  connecting clients after welcome frame.
	* CNLOAD/CNSAVE: terminal end address stored after LINKING, enabling
	  disk caching of the downloaded terminal for instant reconnects.
	  CNSAVE saves from $A000 to terminal end (~31 blocks). CNLOAD
	  restores it.
	* Version-aware LINKING: server computes 2-byte hash of terminal.bin.
	  Hash sent in LINKING header; client stores at $A000/$A001. On
	  reconnect after CNLOAD, matching hash skips LINKING (~100ms vs
	  ~3 seconds). Terminal updates automatically re-download.
	* 8K CRT cartridge build: standard format (EXROM=0, GAME=1), boots to
	  Compunet BASIC prompt. Works on VICE and C64 Ultimate.
* Client:
	* Stripped dead X.25 protocol engine (~2.3K removed). All protocol
	  handling done by ACIA driver. Only RTS stubs + string constants
	  remain for ROM jump table compatibility.
	* ACIA segment now follows CODE directly (no $C900 gap). Combined
	  CODE+ACIA is 7.2K — fits within 8K for future CRT build.
* Server:
	* DIR response: prepend $8E charset byte to Part 1 header. Fixes
	  lowercase rendering on C64 Ultimate after LINKING.
	* Fixed: terminal client crash on SHOW (render_frame missing
	  `_get_server()` call for audit logging).
* Build:
	* Exomizer removed. PRG files now use a lightweight BASIC stub +
	  machine language relocator (gen_sfx.py). No external dependencies.
	* Simplified outputs: `compunet-reborn.prg` (manual, LOAD+RUN),
	  `compunet-reborn-live.prg` (auto-connect, LOAD+RUN),
	  `compunet-reborn.crt` (8K cartridge), `compunet-reborn-live.crt`
	  (8K auto-connect cartridge), `compunet-reborn.d64` (both PRGs),
	  `terminal.bin` (server LINKING).
	* Removed: `compunet-reborn-sfx.prg`, `compunet-reborn-live.d64`,
	  raw 20K PRG.
	* Terminal binary extracted from main build and copied to server/cfg/.
	* Linker config keeps all segments in one MEMORY region for correct
	  cross-segment label resolution, then splits terminal post-build.
	* AUTO_CONNECT code path padded to match standard path byte count,
	  ensuring one terminal.bin works for all client variants.

# 0.12-beta (2026-06-01)

* Partyline:
	* Room names now preserve mixed case (#66). Previously forced to lowercase.
	  Default room renamed from "lobby" to "Lobby".
	* Auto-run `*who` on join so user immediately sees who is online.
	* New command: `*where <user>` — shows which room a user is in, or
	  reports they are not on Partyline.
	* C64 client: PETSCII graphics characters blocked from input. Only allows
	  alphanumeric, punctuation, and space. Prevents garbled text in chat.
* Server:
	* WHO IS ONLINE: format now matches original Compunet (#69). Red header
	  with "CNETTERS ON THE SYSTEM AT HH:MM", partyline indicator note,
	  cyan user list.
	* Directory listings: new UPLDDATE column (#70). F7/F8 cycles through
	  PRICE, LIFE, AUTHOR, VOTE, UPLDDATE. Shows upload date in DD-MMM
	  format with hyphen-aligned. Works on both protocol and terminal clients.
	* Directory listings: single-frame text pages now show `T` instead of
	  `T1` (matches original Compunet). Multi-frame and other types unchanged.
	* Directory listings: dynamic directory pages (e.g. WHAT'S NEW?) now
	  correctly show `D+` to indicate they contain entries.
	* Fixed: `_save_directory` no longer persists children of dynamic pages.
	  Previously, saving after an upload would write a stale `whats-new/`
	  directory to disk, causing "FRAME NOT FOUND" when viewing entries from
	  the WHAT'S NEW? listing.
	* Fixed: page `_dir_path` now derived from the `directory` JSON field
	  when present, not from the title slug. Fixes "FRAME NOT FOUND" when
	  a page is renamed (e.g. JUNGLE → THE JUNGLE).
	* Audit: frame reads now logged for terminal clients (was protocol-only).
	* Audit: credit purchases (`buy` event) now logged for protocol clients
	  (was terminal-only).
* Docker:
	* Set `TZ=Europe/London` on both containers. Fixes Docker log timestamps,
	  audit log times, and WHO IS ONLINE clock showing UTC instead of local.
* Website:
	* Fixed: partyline log admin page not showing content in Docker. Path
	  resolution used `..` which escaped the container's `/app` directory.
	* docker-compose.yml: mount `server/data` into website container (read-only)
	  for partyline log access.

# 0.11.1-beta (2026-06-01)

* Client:
	* Fixed: downloads broken by EOS_RECEIVED flag persisting across stream
	  boundaries. After receiving the program header + EOS, the flag remained
	  set, causing ACIA_PROCESS_CMD to immediately return "no data" when the
	  ROM called it for the actual download bytes. Removed EOS_RECEIVED check
	  from @need_new_packet — ACIA_FLOW_CONTROL's timeout handles end-of-stream.
	* Hardening: NMI handler forces $00=$2F (DDR) before banking in I/O,
	  preventing failure if ROM has zeroed the DDR during processing.
	* Hardening: ACIA_FLOW_CONTROL restores $00=$2F and re-arms the NMI
	  vector ($FFFA/$FFFB=$CF00) on entry, after ROM directory buffer
	  operations may have overwritten them.

# 0.11-beta (2026-06-01)

* Client:
	* Fixed: ACK CRC init changed from $40/$E6 to $00/$00, matching server
	  receive-path validation. CRC check re-enabled for all packets.
	* Fixed: ~2.7 second delay before duckshoot appeared after viewing frames.
	  EOS packet was consumed during pre-fetch but subsequent ACIA_PROCESS_CMD
	  calls would wait for the full timeout. New EOS_RECEIVED flag ($C3FB)
	  causes immediate stream termination on re-entry.
	* Carrier detect: ACIA_REG_READ now checks real DCD bit ($DE01 bit 5)
	  instead of hardcoding carrier present. On C64 Ultimate, TCP disconnect
	  triggers the ROM's "CARRIER LOST" handler and returns to dial prompt
	  for easy reconnection. Partyline also checks DCD in its main loop.
	* Fixed: crash after browsing several directories. ROM directory parser
	  temporarily zeroes $00 (DDR), making $01 writes no-ops. With ACK-paced
	  flow control, NMIs fire during ROM processing — if NMI arrives while
	  DDR is zero, I/O becomes permanently invisible and the client hangs.
	  NMI handler now forces $00=$2F before touching $01. ACIA_FLOW_CONTROL
	  also restores $00=$2F on entry as a recovery point (without changing
	  $01, which must remain in the ROM's chosen bank state).
* Server:
	* Disconnect events now logged to audit trail (protocol + terminal).

# 0.10-beta (2026-05-31)

* Server:
	* Fixed: `_save_directory` now preserves the `dynamic` field in directory
	  JSON. Previously, any upload or directory modification would drop this
	  flag, causing dynamic pages (e.g. WHO IS ONLINE?) to serve stale cached
	  content instead of regenerating on each view.
	* Fixed: `_save_directory` now preserves the `open_upload` field in
	  directory JSON. Previously, any upload into an open directory would drop
	  the flag, blocking subsequent uploads by non-owners. (terminal.py already
	  preserved this correctly.)
	* Missing frame files now serve an error frame ("FRAME NOT FOUND") instead
	  of sending uninitialised data. Event logged to audit.
	* Fixed: partyline *quit KeyError when user disconnects simultaneously
	  with sending the quit command (race condition).
	* Fixed: commands sent by client during ACK wait were being consumed and
	  lost. Now stashed in pending_packets buffer and processed by main loop.
	* Dedicated partyline log (`server/data/partyline.jsonl`): records all
	  messages, commands, joins, leaves, disconnects, kicks, and bans from
	  both protocol and terminal clients.
* Partyline:
	* `*save` command (#61): saves chat scrollback. C64 client prompts for
	  filename and saves to disk drive as PETSCII SEQ file (matching original
	  Compunet historical format). Terminal clients save via XMODEM.
	* Chat history buffer increased: C64 client 114 → 255 lines (~9KB),
	  terminal 100 → 500 lines.
* Website:
	* Admin panel: Partyline Log page (`/admin/partyline-log`) with paginated
	  view of partyline activity (50 per page, newest first).
* Content:
	* Upload date/time now stored in directory JSON (`uploaded` field, ISO format).
	  Preserved during directory saves.
	* "WHAT'S NEW?" dynamic directory (page 199, GOTO NEW): shows the 11 most
	  recent uploads across all directories, sorted newest first. Regenerated
	  on each view.
* Deployment notes:
	* Backfill `uploaded` field for existing content based on filesystem dates.
	* Re-add `"dynamic": "who"` to WHO IS ONLINE? entry in root.json if missing.
	* Add "WHAT'S NEW?" entry to root.json: `{"page_num": 199, "title":
	  "WHAT'S NEW?", "type": "D", "author": "SYSTEM", "price": 0, "life": 0,
	  "keyword": "NEW", "dynamic": "new"}`.
	* Verify `"open_upload": true` is present in community directories
	  (e.g. jungle/graphics/directory.json). If missing, re-add it — previous
	  server versions did not preserve the field on save.

# 0.9.1-beta (2026-05-31)

* Server:
	* Simplified online user tracking: removed reference counting. User marked
	  online on any activity (login, command received). Marked offline on LEAVE,
	  TCP disconnect, or idle timeout. Fixes ghost users in WHO IS ONLINE.

# 0.9-beta (2026-05-31)

* Protocol:
	* ACK-based flow control: client now sends X.25 ACK packets after receiving
	  each data packet. Server waits for ACK before sending next packet.
	* Removed all fixed inter-packet delays (500ms command, 250ms pre-response,
	  50ms download). Transfer speed now adapts to client processing speed.
	* Result: dramatically faster page loads, directory browsing, and program
	  downloads. Server never outpaces client regardless of baud rate setting.
	* EOS (end-of-stream) packets sent fire-and-forget (client treats zero-length
	  as terminator without ACK).
	* Breaking change: requires updated client. Old clients will not work.
	* TCP keepalives enabled on both ports (60s idle, 15s interval, 4 retries).
	  Prevents NAT/firewall connection drops during idle sessions.
* Client:
	* ACIA_SEND_ACK routine added: sends ACK packet ($01 [06] [$20] [$20] [seq]
	  [CRC] $02) after receiving each DAT packet in ACIA_FLOW_CONTROL.
	* CRC init $40/$E6 matching original ROM ACK behaviour at L9ABC.
	* Only DAT token ($22) triggers ACK — COM echoes and error tokens do not.

# 0.8.1-beta (2026-05-30)

* Terminal:
	* Fixed: charset inconsistency on C64 terminal clients (#56). DIR and MAIL
	  screens no longer switch charset during rendering — eliminates flickering
	  and graphical corruption when scrolling.
	* Terminal type selection on connection: C64 clients get full charset
	  switching, PC terminals (SyncTerm) suppress $8E/$0E to avoid conflicts
	  with fixed-font rendering.
	* Fixed: frame charset detection now properly parses RLE codes instead of
	  naively scanning for $0E bytes (was misidentifying RLE counts as charset
	  switches).
	* ID command implemented in MAIL duckshoot (user ID lookup with real name
	  display).
	* Partyline: shared command handler (process_input) for both protocol and
	  terminal clients — all commands available (*dice, *kick, *ban, *call etc).
	  Proper PETSCII-to-ASCII conversion preserves mixed case. Name displayed
	  on separate line from message (matches C64 client format).
	* Partyline: scrollable chat history (100 lines, cursor up/down).
	* Partyline: double-RETURN to send (first RETURN = line break).
	* Font recommendation changed to "Commodore 64 (LOWER)" for SyncTerm.

# 0.8-beta (2026-05-29)

* PETSCII Terminal Mode (port 6401):
	* Server-rendered BBS interface for any PETSCII terminal (SyncTerm, CCGMS,
	  StrikeTerm, UltimateTerm). No custom client required.
	* C64-accurate directory display with borders, duckshoot, welcome screen.
	* Full command set: DIR, SHOW, BACK, GOTO, MAIL, ACCNT, LIFE, VOTE, BUY,
	  UPLD, EDITR, UCAT, HELP, LEAVE, WHO.
	* XMODEM-CRC/1K file transfers (upload and download).
	* Frame editor with 20-frame memory, free cursor editing, GET/PUT/STORE.
	* Mail: inbox browsing, read, compose with COURIER envelope and delivery.
	* Partyline: bordered chat UI, integrated with protocol client users.
	* Auto-detect Raw/Telnet connections.
* Client:
	* Page numbers right-aligned in directory listings.
	* Column headers indented one space from separator.
* Server:
	* Port 6401 listener added to main server event loop.
	* Dockerfile updated: terminal.py included, port 6401 exposed.
	* docker-compose.yml: port 6401 mapped.
* Website:
	* Connect page: PETSCII terminal setup instructions (SyncTerm),
	  registration step, C64 terminal client recommendations.

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
