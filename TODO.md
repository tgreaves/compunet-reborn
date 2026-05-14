# TODO

## Bugs

- **Duckshoot corruption after MAIL SEND**: After sending a frame in the MAIL SEND sub-duckshoot, the duckshoot text is corrupted (shows `@@@@?????` etc). The duckshoot still functions but text is unreadable. Likely caused by "SENDING" status text or ACK response interfering with screen memory.
- **Frame upload content wrong**: `$B175` reads frame data from pointer at `$8019/$801A` which currently points to `$E004` (Kernal ROM area / uninitialised RAM). Needs Editor integration so that viewed/composed frames are stored where `$8019/$801A` points. Sent data is garbage instead of actual frame content.

## Features

- **Editor integration for MAIL SEND**: The upload pointer (`$8019/$801A`) must be set to the Editor's current page buffer when sending. Need to understand how the original Editor stores frame data and ensure SHOW'd frames are available for sending.
- **Sub-directory creation**: Users should be able to create sub-directories under entries they own (DIR on owned non-directory entries).
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
