# TODO

## Bugs

- ~~**Frame upload sends wrong data when Editor empty**~~: FIXED — `$8019/$801A` correctly points to Editor buffer at $E000 when user has edited a frame. ACIA_UPLOAD_BYTE preserves X register so frame data transmits correctly.

## Features

- ~~**Server-generated mail header frame**~~: DONE — envelope frame generated from template at `server/content/templates/courier-envelope.seq`. Prepended as frame 0 on delivery. Global message sequence tracked in `server/mail/sequence.json`.
- ~~**LEAVE command**~~: DONE.
- ~~**UPLOAD (UPLD) command**~~: DONE — Pages uploaded to current directory, persisted to root.json.
- **Welcome screen PAGES/NEAR DEATH calculation**: Count pages owned by the user in root.json, and how many have life ≤ 3. Currently hardcoded as 0/0.
- **Welcome screen FREE STORAGE calculation**: Based on account type (GOLD/BASIC/ADMIN), calculate remaining upload slots. Currently hardcoded as 2000.
- **Welcome screen mail pillarbox graphic**: Replace the `{MAIL_IND}` placeholder with actual PETSCII pillarbox art (currently shows reversed "MAIL" text as a placeholder).
- **Upload permissions**: Users should only be allowed to upload to directories they own (author matches) or to designated "Jungle" areas. Admins bypass this check. Server can reject with an error token response — client aborts cleanly via BCS at $B60E. Stray frame DAT packet discarded since pending_send won't be set.
- **Sub-directory creation**: Users should be able to create sub-directories under entries they own (DIR on owned non-directory entries). Note: sub-directories with no content do not persist — they only remain if the user subsequently uploads content into them.
- ~~**VOTE system**~~: DONE — Users vote 1-9 on pages from directory listing. Votes stored per-user in `server/votes.json`, average (rounded) shown in VOTE column. Users can change their vote; self-voting allowed.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
- **Web administration interface**: Browser-based admin panel for managing the system. Features: create/edit/delete users, move/reorganise pages in the directory tree, view mail queues, monitor active sessions, edit system configuration.
- **Project website + sign-up system**: Public-facing website with project information, user registration (create account with email verification), password reminder/reset functionality. Required because the C64 client cannot handle account creation or password recovery — these must be done out-of-band via the web.
- ~~**Automated testing via VICE remote monitor**~~: DONE — `vice_test.sh` launches VICE with remote monitor, injects keystrokes via `keybuf` to automate login. Kills stray VICE processes on start. Password sent char-by-char to accommodate the client's input routine.
