# 0.3-beta (2026-05-20)

* Client:
	* Fixed backspace not working on login password field.
* Server:
	* Type 'L' (link) directory entries: BUY triggers MODEM_INIT_DOWNLOAD to stream executable code to client.
	* Partyline directory with "JOIN PARTYLINE" L-type entry added.
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
	* PARTYLINE_WS_URL env var for configuring browser WebSocket endpoint.
	* partyline.py added to server Dockerfile.
	* Partyline design documented in docs/partyline.md.
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
