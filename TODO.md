# TODO

## Bugs

- **Login freeze on incorrect credentials**: Server sends error frame and closes, but client enters terminal duckshoot with dead connection (no disconnect detection). Full fix requires client-side disconnect detection.

## Features

- **NETWHO page**: Virtual page (GOTO NETWHO) showing currently connected users. Currently renders as a directory response with user list in header frame. Investigate whether original rendered differently. Client always parses GOTO response as 6-part directory format.
- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE, F3=PARTYLINE). Expand to other directories and consider server-defined defaults.
- **Client API (modern clients)**: The broken `client/web/` experiment has been removed (recoverable from git history). A fresh, structured client API is being scoped — see [docs/spec/API-RESEARCH.md](docs/spec/API-RESEARCH.md). The goal is a clean application-layer binding (JSON over WebSocket/HTTP) so web/mobile/desktop clients need not reimplement X.25 framing or PETSCII decoding. Must not disturb the website's admin API (aiohttp, port 6403).

