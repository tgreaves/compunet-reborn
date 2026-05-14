# TODO

## Bugs

- ~~**Frame upload sends wrong data when Editor empty**~~: FIXED — `$8019/$801A` correctly points to Editor buffer at $E000 when user has edited a frame. ACIA_UPLOAD_BYTE preserves X register so frame data transmits correctly.

## Features

- ~~**Server-generated mail header frame**~~: DONE — envelope frame generated from template at `server/content/templates/courier-envelope.seq`. Prepended as frame 0 on delivery. Global message sequence tracked in `server/mail/sequence.json`.
- ~~**LEAVE command**~~: DONE.
- ~~**UPLOAD (UPLD) command**~~: DONE — Pages uploaded to current directory, persisted to root.json.
- **Upload permissions**: Users should only be allowed to upload to directories they own (author matches) or to designated "Jungle" areas. Admins bypass this check. Server can reject with an error token response — client aborts cleanly via BCS at $B60E. Stray frame DAT packet discarded since pending_send won't be set.
- **Sub-directory creation**: Users should be able to create sub-directories under entries they own (DIR on owned non-directory entries). Note: sub-directories with no content do not persist — they only remain if the user subsequently uploads content into them.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
