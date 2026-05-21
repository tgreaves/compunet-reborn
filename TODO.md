# TODO

## Bugs

- **Login freeze on incorrect credentials**: Server sends error frame and closes, but client enters terminal duckshoot with dead connection (no disconnect detection). Full fix requires client-side disconnect detection.

## Features

- **NETWHO page**: Virtual page (GOTO NETWHO) showing currently connected users. Currently renders as a directory response with user list in header frame. Investigate whether original rendered differently. Client always parses GOTO response as 6-part directory format.
- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE, F3=PARTYLINE). Expand to other directories and consider server-defined defaults.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.

