# TODO

## Bugs

- **Login freeze on incorrect credentials**: Server sends error frame and closes, but client enters terminal duckshoot with dead connection (no disconnect detection). Full fix requires client-side disconnect detection.

## Features

- **WHO page**: Virtual page (GOTO WHO) showing currently connected users. Currently renders as a directory response with user list in header frame. Investigate whether original rendered differently. Client always parses GOTO response as 6-part directory format.
- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE, F3=PARTYLINE). Expand to other directories and consider server-defined defaults.
- **Partyline enhancements**: Core system working. Potential improvements:
  - C64 client: scrollback with cursor up/down
  - C64 client: verify scrolling at edge cases (full chat area)
  - Private messaging between users
  - Room listing command
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
- **Deployment**: Set up Cloudflare in front of home network for testing. Cloudflare proxied (orange cloud) for website HTTPS on port 6464. Separate subdomain (e.g. `server.compunet.live`) with Cloudflare DNS only (grey cloud) for C64 TCP on port 6400. Port-forward both on router. Later migrate to DigitalOcean Droplet (just update A records).
