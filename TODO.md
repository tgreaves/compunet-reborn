# TODO

## Bugs

- **Login freeze on incorrect credentials**: Server sends error frame and closes, but client enters terminal duckshoot with dead connection (no disconnect detection). Full fix requires client-side disconnect detection.

## Features

- **WHO page**: Virtual page (GOTO WHO) showing currently connected users. Currently renders as a directory response with user list in header frame. Investigate whether original rendered differently. Client always parses GOTO response as 6-part directory format.
- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE). Expand to other directories and consider server-defined defaults.
- **Partyline (multi-user chat)**: Implement Compunet's scrolling chat system.
  - **Mechanism**: Directory entry with type 'L' (link). User selects it with BUY command.
  - **Client flow**: BUY on type 'L' → server responds → client calls MODEM_INIT_DOWNLOAD ($810F) which downloads arbitrary code into RAM and executes it via JMP ($001F).
  - **Implementation**: Server sends a small 6502 chat program that gets loaded and run. The chat program handles scrolling text display, keyboard input, and communication with the server.
  - **Key findings**:
    - SHOW on type 'L' displays "PLEASE USE BUY" (type table at $A983: TCALPS, X>=3 triggers this)
    - BUY handler checks type at $C019; when 'L' ($4C), jumps to L_AABE which calls ROMCALL_05 (MODEM_INIT_DOWNLOAD)
    - MODEM_INIT_DOWNLOAD reads: 3 header bytes (discarded), dest address hi/lo ($1F/$20), load address lo/hi ($1D/$1E), 2 bytes (discarded), then streams code into ($1D),Y until end-of-stream, then JMP ($001F)
    - The downloaded program has full access to the C64 and can use ACIA for server communication
  - **TODO**: Write 6502 chat client program, implement server-side chat room routing, create 'L' type directory entries
- **Web client update**: Bring the web client (`client/web/`) up to date with current server architecture, protocol changes, and all features implemented in the C64 TCP path.
- **Deployment**: Set up Cloudflare in front of home network for testing. Cloudflare proxied (orange cloud) for website HTTPS on port 6464. Separate subdomain (e.g. `server.compunet.live`) with Cloudflare DNS only (grey cloud) for C64 TCP on port 6400. Port-forward both on router. Later migrate to DigitalOcean Droplet (just update A records).
