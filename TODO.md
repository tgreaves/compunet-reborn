# TODO

## Bugs

- ~~**Frame upload sends wrong data when Editor empty**~~: FIXED — `$8019/$801A` correctly points to Editor buffer at $E000 when user has edited a frame. ACIA_UPLOAD_BYTE preserves X register so frame data transmits correctly.
- **Login freeze on incorrect credentials**: Client freezes on "PLEASE WAIT" if wrong user ID or password entered. Server sends error response but client doesn't handle it.
- ~~**Program upload data corruption (bit-7 stripping)**~~: FIXED — caused by VICE's ip232 protocol layer corrupting TX bytes, which triggered tcpser's parity auto-detection to strip bit 7. Eliminated tcpser entirely: server now handles Hayes AT commands directly. Direct raw socket from VICE to server preserves all 8 bits. See `docs/UPLOAD-BIT7-INVESTIGATION.md`.
- ~~**Directory display corruption after upload**~~: FIXED — was caused by tcpser's parity stripping mangling the server's ACK response, desynchronising the client's stream parser. Resolved by eliminating tcpser.

## Features

- ~~**Server-generated mail header frame**~~: DONE — envelope frame generated from template at `server/content/templates/courier-envelope.seq`. Prepended as frame 0 on delivery. Global message sequence tracked in `server/mail/sequence.json`.
- ~~**LEAVE command**~~: DONE.
- ~~**UPLOAD (UPLD) command**~~: DONE — Pages uploaded to current directory, persisted to root.json.
- **Welcome screen PAGES/NEAR DEATH calculation**: Count pages owned by the user in root.json, and how many have life ≤ 3. Currently hardcoded as 0/0.
- **Welcome screen FREE STORAGE calculation**: Based on account type (GOLD/BASIC/ADMIN), calculate remaining upload slots. Currently hardcoded as 2000.
- **Welcome screen mail pillarbox graphic**: Replace the `{MAIL_IND}` placeholder with actual PETSCII pillarbox art (currently shows reversed "MAIL" text as a placeholder).
- ~~**Upload permissions**~~: DONE — Admins can upload anywhere. Normal users can upload/create DIRs only where author is JUNGLE or their own user ID. Denied uploads are silently discarded (client doesn't crash). Client has no permission check — only checks directory capacity (max 11 entries).
- ~~**Sub-directory creation**~~: DONE — DIR on a page without children enters an empty sub-directory. Permission check applies (same rules as upload). Empty directories show (EMPTY) placeholder entry. Content persists to root.json on upload; entry gains "+" suffix.
- ~~**VOTE system**~~: DONE — Users vote 1-9 on pages from directory listing. Votes stored per-user in `server/votes.json`, average (rounded) shown in VOTE column. Users can change their vote; self-voting allowed.
- ~~**Advert area**~~: DONE — Two lines above duckshoot populated from Part 2 of directory response. Per-directory adverts in `directory.json`, global fallback in `server/content/adverts.json`. Random selection from array on each render.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
- **Web administration interface**: Browser-based admin panel for managing the system. Features: create/edit/delete users, move/reorganise pages in the directory tree, view mail queues, monitor active sessions, edit system configuration.
- **Project website + sign-up system**: Public-facing website with project information, user registration (create account with email verification), password reminder/reset functionality. Required because the C64 client cannot handle account creation or password recovery — these must be done out-of-band via the web.
- ~~**Automated testing via VICE remote monitor**~~: DONE — `vice_test.sh` launches VICE with remote monitor, injects keystrokes via `keybuf` to automate login. Kills stray VICE processes on start. Password sent char-by-char to accommodate the client's input routine.
- **UCAT duckshoot command**: Shows a summary of the user's uploaded content.
