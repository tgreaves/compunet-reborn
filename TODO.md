# TODO

## Bugs

- **200-byte crash (CPU JAM)**: NMI ring buffer overflow + `@last_byte` peek race condition. See `docs/crash-investigation-200-byte.md` for full analysis and fix plan (Options A+C+D).

## Features

- **MAIL command**: Implement the Courier mail system (store/forward messages between users). Currently returns "NO MAIL WAITING" stub.
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
