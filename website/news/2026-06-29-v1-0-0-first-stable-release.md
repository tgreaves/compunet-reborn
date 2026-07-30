# Compunet Reborn: v1.0.0 (First stable release)

After months of intensive development and testing with the community, I'm pleased to announce
that **Compunet Reborn has reached v1.0.0** — our first stable release.

## The Community

We now have **93 registered users** and a growing library of user-contributed content:

- **269 pages** across **57 directories**
- **385 text frames** (graphics, articles, news)
- **146 programs** available for download
- Active Partyline chat sessions most evenings

## What's New Since My Last Email

### Performance

- **ACK-based flow control** — page loads and downloads are dramatically faster. The server
  adapts to your connection speed with zero fixed delays.
- **LINKING** — the terminal code is now downloaded on-demand from the server in ~3 seconds.
  Client PRG reduced from 12K to 5.5K. Server-side updates deploy instantly to all users on next
  connect.
- **8K CRT cartridge** — plug in and go. Works on VICE and C64 Ultimate.
- **CNLOAD/CNSAVE** — cache the terminal to disk for instant reconnects (skips the 3-second
  download).

### Partyline

- Multi-room chat with `*enter`, `*who`, `*where`, `*alias`, `*call`, `*dice`
- Scrollable chat history (255 lines, cursor up/down)
- `*save` — save your chat log to disk as a SEQ file
- Room names and aliases match original Compunet conventions (8 char max)

### PETSCII Terminal Mode (port 6401)

- Full server-rendered BBS interface — **no custom client required**
- Works with SyncTerm, CCGMS, StrikeTerm, UltimateTerm, or any PETSCII terminal
- Complete command set, XMODEM file transfers, frame editor, mail, partyline

### Content &amp; Features

- **"WHAT'S NEW?"** dynamic page — see the latest uploads at a glance
- **Upload replace** — update your own content without creating duplicates
- **VOTE/NUM** column matching original Compunet format
- **Courier mail** with proper header logo (thanks JS7!)
- Upload date column, directory paging, UCAT improvements

### Stability

- Dozens of crash fixes (NMI/banking conflicts, memory corruption, protocol edge cases)
- TCP keepalives prevent idle disconnects through NAT/firewalls

## How to Connect

- **Website:** https://compunet.live
- **C64 Ultimate / SwiftLink:** `vme.compunet.live:6400`
- **PETSCII Terminal (SyncTerm):** `vme.compunet.live:6401`
- **Downloads:** https://compunet.live/connect (CRT, PRG, D64)

## What's Next

We're continuing to add content, improve historical accuracy, and work on a modern cross-platform
client. If you have original Compunet content (SEQ files, programs, screenshots), we'd love to
hear from you.

Thanks to everyone who has tested, reported bugs, contributed content, and kept the spirit of
Compunet alive.

Kind regards,

Tris // ADMIN

**THE LIVE ONE LIVES ON — 2026**
