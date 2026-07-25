# TODO

## Bugs

- **Login freeze on incorrect credentials**: Server sends error frame and closes, but client enters terminal duckshoot with dead connection (no disconnect detection). Full fix requires client-side disconnect detection.

## Features

- **NETWHO page**: Virtual page (GOTO NETWHO) showing currently connected users. Currently renders as a directory response with user list in header frame. Investigate whether original rendered differently. Client always parses GOTO response as 6-part directory format.
- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE, F3=PARTYLINE). Expand to other directories and consider server-defined defaults.
- **Client API (Binding B)**: In progress on branch `client-api`. Phase 1 (Tier 1) is complete end-to-end: token auth + WebSocket gateway ([server/api_binding.py](server/api_binding.py), port 6404), the directory + frame-cell-grid serializers, and a canvas reference client ([client/web/](client/web/)). Design in [docs/spec/api/README.md](docs/spec/api/README.md); rationale in [docs/spec/api/RATIONALE.md](docs/spec/api/RATIONALE.md). Next: Tier 2 (account/mail/download/vote/life), Tier 3 (upload/editor/Partyline), then the REST read path (hybrid). Does not disturb the website's admin API (aiohttp, port 6403).

