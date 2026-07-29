# Terminal support // v0.8-beta

Hi everyone,

Firstly, a reminder that our very first PARTYLINE PARTY will be held on Sunday at 7:30pm UK time.
Looking forward to seeing as many there as possible.

## Terminal access launched!

We now support TERMINAL CONNECTIONS to Compunet. This means you can fire up your favourite
PETSCII client on Windows / Mac / Linux (e.g. SyncTerm), or on an actual Commodore 64 (CCGMS,
Ultimate Term). I have recreated the Compunet user experience in a classic terminal environment,
including the use of XMODEM for file transfers.

The native C64 clients remain the Gold Standard [TM]. Mainly due to the terminal clients not
supporting changing the background colour on the fly which is essential for some of the cool
frame graphics we know and love.

FULL DETAILS: https://compunet.live/connect

## Feedback welcome

Please continue to send your feedback and suggestions. You can Courier ADMIN or use the 'Contact'
page on the website.

Bugs and feature requests can also be raised on the GitHub page:
https://github.com/tgreaves/compunet-reborn/issues

## v0.8-beta

Here's everything new with the latest releases of Compunet Reborn:

### 0.8.1-BETA (2026-05-30)

- Terminal:
    - Fixed: charset inconsistency on C64 terminal clients (#56). DIR and MAIL screens no longer
      switch charset during rendering — eliminates flickering and graphical corruption when
      scrolling.
    - Terminal type selection on connection: C64 clients get full charset switching, PC terminals
      (SyncTerm) suppress $8E/$0E to avoid conflicts with fixed-font rendering.
    - Fixed: frame charset detection now properly parses RLE codes instead of naively scanning
      for $0E bytes (was misidentifying RLE counts as charset switches).
    - ID command implemented in MAIL duckshoot (user ID lookup with real name display).
    - Partyline: shared command handler (process_input) for both protocol and terminal clients —
      all commands available (dice, kick, ban, call etc). Proper PETSCII-to-ASCII conversion
      preserves mixed case. Name displayed on separate line from message (matches C64 client
      format).
    - Partyline: scrollable chat history (100 lines, cursor up/down).
    - Partyline: double-RETURN to send (first RETURN = line break).
    - Font recommendation changed to "Commodore 64 (LOWER)" for SyncTerm.

### 0.8-BETA (2026-05-29)

- PETSCII Terminal Mode (port 6401):
    - Server-rendered BBS interface for any PETSCII terminal (SyncTerm, CCGMS, StrikeTerm,
      UltimateTerm). No custom client required.
    - C64-accurate directory display with borders, duckshoot, welcome screen.
    - Full command set: DIR, SHOW, BACK, GOTO, MAIL, ACCNT, LIFE, VOTE, BUY, UPLD, EDITR, UCAT,
      HELP, LEAVE, WHO.
    - XMODEM-CRC/1K file transfers (upload and download).
    - Frame editor with 20-frame memory, free cursor editing, GET/PUT/STORE.
    - Mail: inbox browsing, read, compose with COURIER envelope and delivery.
    - Partyline: bordered chat UI, integrated with protocol client users.
    - Auto-detect Raw/Telnet connections.
- Client:
    - Page numbers right-aligned in directory listings.
    - Column headers indented one space from separator.
- Server:
    - Port 6401 listener added to main server event loop.
    - Dockerfile updated: terminal.py included, port 6401 exposed.
    - docker-compose.yml: port 6401 mapped.
- Website:
    - Connect page: PETSCII terminal setup instructions (SyncTerm), registration step, C64
      terminal client recommendations.

### 0.7.2-BETA (2026-05-29)

- Client:
    - Fixed: CPU JAM ($0008) on MAIL command and other multi-packet directory responses. NMI
      handler now saves/restores $01 and ensures I/O is visible (ORA #$06) before accessing ACIA
      registers. Previously, if NMI fired while the directory parser had KERNAL banked out
      ($01=$34) to read RAM under I/O, the hardware NMI vector at $FFFA/$FFFB read $0000 from RAM
      causing a jump to zero page.
    - Hardware NMI vector at $FFFA/$FFFB in RAM now set to $CF00 (NMI handler address) during
      ACIA_INIT, ensuring correct NMI vectoring regardless of current bank configuration.
- Server:
    - Fixed: WHO IS ONLINE missing users. When a user reconnected (new TCP connection before old
      session timed out), the old session's disconnect handler removed the user from
      `_online_users` even though the new session was still active. Now uses reference-counted
      tracking — user is only removed from the online set when their last session disconnects.

Thanks everyone for your continued support!

Kind regards,

Tris // ADMIN.
