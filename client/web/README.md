# ⚠️ Web client — BROKEN / UNFINISHED / NON-COMPLIANT

**Do not use this client, and do not treat any file in this directory as a source of
truth.**

This web (browser) client was **never finished** and is **known to be broken**. It does not
correctly implement the Compunet protocol or display contract, and some of its embedded data
is wrong (for example, `charrom.js` contains a corrupted glyph, and `petscii.js` carries a
palette that does not match the reference clients).

## Why this note exists

The authoritative sources for how a Compunet client must behave are:

- **The specification** — [docs/spec/](../../docs/spec/README.md) (single source of truth).
- **The reference clients** — the C64 client (`client/c64/src/compunet.s`) and the Amiga
  client (`client/amiga/src/`), which the spec is verified against.

The font, palette, RLE, screen geometry, and protocol details in the spec are all extracted
from the C64/Amiga clients and the server — **not** from anything in this directory. If you
are building or checking a client, ignore this folder entirely.

## Status

Unmaintained and non-compliant. Retained only as an abandoned experiment. Rebuilding a web
client correctly would mean implementing it fresh against [docs/spec/](../../docs/spec/README.md)
(and would additionally need a WebSocket transport binding, which the spec does not yet
define — see the browser-transport discussion in the spec's scope, §1.3).
