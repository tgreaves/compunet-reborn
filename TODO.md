# TODO

## Bugs

- **Login freeze on incorrect credentials**: Server sends error frame and closes, but client enters terminal duckshoot with dead connection (no disconnect detection). Full fix requires client-side disconnect detection.

- **Program upload guesses the machine type from the filename**: the web client
  ([client/web/src/main.ts](client/web/src/main.ts), `sendProgram`) decides C64 vs Amiga by
  testing the file name against `/\.prg$/i` — anything else is treated as an Amiga HUNK
  executable. That value becomes byte 0 of the §8.3.2 header and is stored as the page's
  `machine_type`, which the **download** path then uses to decide whether to restore a load
  address. A wrong guess therefore corrupts the file on the way back out, not merely the
  listing, and the user is never shown or asked for it.

  Deriving a load-bearing field from an extension is the same class of mistake §8.3.2 calls out
  when it makes the *type* byte mandatory: it cannot be derived from the content, so it must be
  collected. Proposed fix: when Type is `P`, offer an explicit **machine** choice in the upload
  dialog (default from the extension, overridable), and have `SEND` report which machine it
  used so a wrong choice is visible before `FINISH` rather than after the entry exists.

  Left deliberately for a decision rather than patched — a picker is one option, sniffing the
  content (Amiga HUNK magic `00 00 03 F3`, a plausible C64 load address) is another, and the
  two combine.

  Test residue: page **910 "FOO"** in JUNGLE/MUSIC is a junk upload from testing, labelled
  `machine_type: amiga`. Delete it when convenient.

## Features

- **F-key shortcuts**: Implemented for root directory (F1=JUNGLE, F3=PARTYLINE). Expand to other directories and consider server-defined defaults.
- **Client API (Binding B)**: In progress on branch `client-api`. Phase 1 (Tier 1) is complete end-to-end: token auth + WebSocket gateway ([server/api_binding.py](server/api_binding.py), port 6404), the directory + frame-cell-grid serializers, and a canvas reference client ([client/web/](client/web/)). Design in [docs/spec/api/README.md](docs/spec/api/README.md); rationale in [docs/spec/api/RATIONALE.md](docs/spec/api/RATIONALE.md). Next: Tier 2 (account/mail/download/vote/life), Tier 3 (upload/editor/Partyline), then the REST read path (hybrid). Does not disturb the website's admin API (aiohttp, port 6403).

