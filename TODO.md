# TODO

## Bugs

- **Frame upload sends wrong data when Editor empty**: `$B175` reads from `$8019/$801A`. If the user hasn't entered the Editor and composed content, the pointer may reference uninitialised RAM. Works correctly when user has edited a frame in the Editor before sending.

## Features

- ~~**Server-generated mail header frame**~~: DONE — envelope frame generated from template at `server/content/templates/courier-envelope.seq`. Prepended as frame 0 on delivery. Global message sequence tracked in `server/mail/sequence.json`.
- ~~**LEAVE command**~~: DONE — Server responds with goodbye.seq frame, waits for delivery, closes connection.
- **UPLOAD (UPLD) command**: Allow users to upload text frames to the next available slot in a directory. Should be similar to MAIL SEND — same 'U' command, same frame upload via ACIA_UPLOAD_BYTE. Server creates a new page entry in root.json with the uploaded frames. Need to handle: finding next free page number, setting title/type/author/life from upload metadata.
- **Sub-directory creation**: Users should be able to create sub-directories under entries they own (DIR on owned non-directory entries). Note: sub-directories with no content do not persist — they only remain if the user subsequently uploads content into them.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
