# TODO

## Bugs

- ~~**Frame upload sends wrong data when Editor empty**~~: FIXED — `$8019/$801A` correctly points to Editor buffer at $E000 when user has edited a frame. ACIA_UPLOAD_BYTE preserves X register so frame data transmits correctly.
- ~~**Login freeze on incorrect credentials**~~: PARTIALLY FIXED — Server now sends a proper error frame ("INVALID ID OR PASSWORD") before closing. Client displays the message but then enters the terminal duckshoot with a dead connection (no disconnect detection). Full fix requires client-side disconnect detection (see below).
- ~~**Program upload data corruption (bit-7 stripping)**~~: FIXED — caused by VICE's ip232 protocol layer corrupting TX bytes, which triggered tcpser's parity auto-detection to strip bit 7. Eliminated tcpser entirely: server now handles Hayes AT commands directly. Direct raw socket from VICE to server preserves all 8 bits. See `docs/UPLOAD-BIT7-INVESTIGATION.md`.
- ~~**Directory display corruption after upload**~~: FIXED — was caused by tcpser's parity stripping mangling the server's ACK response, desynchronising the client's stream parser. Resolved by eliminating tcpser.

## Features

- ~~**Server-generated mail header frame**~~: DONE — envelope frame generated from template at `server/content/templates/courier-envelope.seq`. Prepended as frame 0 on delivery. Global message sequence tracked in `server/mail/sequence.json`.
- ~~**LEAVE command**~~: DONE.
- ~~**UPLOAD (UPLD) command**~~: DONE — Pages uploaded to current directory, persisted to root.json.
- ~~**Welcome screen PAGES/NEAR DEATH calculation**~~: DONE — counts user's uploads and pages with life < 5.
- ~~**Welcome screen FREE STORAGE calculation**~~: DONE — 2000 - sum(frames × life) per quarter.
- ~~**Welcome screen mail pillarbox graphic**~~: DONE — original PETSCII pillarbox art, conditionally shown when unread mail exists.
- ~~**Upload permissions**~~: DONE — Admins can upload anywhere. Normal users can upload/create DIRs only where author is JUNGLE or their own user ID. Denied uploads are silently discarded (client doesn't crash). Client has no permission check — only checks directory capacity (max 11 entries).
- ~~**Sub-directory creation**~~: DONE — DIR on a page without children enters an empty sub-directory. Permission check applies (same rules as upload). Empty directories show (EMPTY) placeholder entry. Content persists to root.json on upload; entry gains "+" suffix.
- ~~**VOTE system**~~: DONE — Users vote 1-9 on pages from directory listing. Votes stored per-user in `server/votes.json`, average (rounded) shown in VOTE column. Users can change their vote; self-voting allowed.
- ~~**Advert area**~~: DONE — Two lines above duckshoot populated from Part 2 of directory response. Per-directory adverts in `directory.json`, global fallback in `server/content/adverts.json`. Random selection from array on each render.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
- ~~**Web administration interface**~~: DONE — admin panel at /admin for user management (edit, approve/delete pending registrations).
- ~~**Project website + sign-up system**~~: DONE — registration with email verification, login, account management.
- **WHO page**: Virtual page (GOTO WHO) showing currently connected users. Currently renders as a directory response with user list in header frame. Investigate whether original rendered differently (e.g. as a standalone frame). Client always parses GOTO response as 6-part directory format.
- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE). Expand to other directories and consider server-defined defaults.
- ~~**Automated testing via VICE remote monitor**~~: DONE — `vice_test.sh` launches VICE with remote monitor, injects keystrokes via `keybuf` to automate login. Kills stray VICE processes on start. Password sent char-by-char to accommodate the client's input routine.
- ~~**UCAT duckshoot command**~~: DONE — Lists all pages owned by the current user with LIFE, PRICE, VOTE, PAGE columns. Standard DIR duckshoot available for interaction.
- **Deployment**: Set up Cloudflare in front of home network for testing. Cloudflare proxied (orange cloud) for website HTTPS on port 6464. Separate subdomain (e.g. `server.compunet.live`) with Cloudflare DNS only (grey cloud) for C64 TCP on port 6400. Port-forward both on router. Later migrate to DigitalOcean Droplet (just update A records).
