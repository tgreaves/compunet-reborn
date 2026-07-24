# Compunet Reborn — pygame test client

A **Tier 1 (Browse)** client built as a *measuring instrument for the
specification* — not a product. It is written **clean-room from
[docs/spec/](../../docs/spec/README.md) only**, deliberately not referencing the
server or the C64/Amiga client source, so that every place the spec is
insufficient shows up as a forced guess (marked `SPEC-GAP:` in the code and
printed when the client exits).

It even loads its font, palette, and directory template by **parsing the spec's
Appendix A** (`docs/spec/99-appendices.md`), so it is a direct consumer of the
spec's own self-contained data.

## Scope

Implements spec §§2–7 for Tier 1: connect, identify (native handshake), log in,
navigate directories, and render frames into a pixel-accurate 40×24 grid using
the C64 font and 16-colour palette.

Not implemented (Tier 2/3): mail, downloads, uploads, editor, Partyline, VOTE.

## Install & run

```bash
pip install -r requirements.txt
python compunet_client.py docker.lan:6400 <userid> <password>
```

If you omit the userid/password it will prompt. Defaults to `docker.lan:6400`.

Keys: digits + **Enter** select a directory entry · **B** back · **Space** more ·
**P** show current directory · **Esc/Q** leave.

## Findings (spec suitability)

Building and running this clean-room against the live `docker.lan:6400` server
validated Tier 1 end-to-end (connect → login → welcome → directory → select →
render live content) and surfaced eight findings. The three substantive ones
were fixed in the spec:

- **§6.2** *(fixed)* — the server's `INVALID ID` frame has `$0D`, not a charset
  control, at byte 3; byte 3 is now specified as *consumed* as the charset
  selector (non-`$0E` = uppercase), tolerating any value.
- **§5.6.1** *(fixed, new)* — the auto-wrap/`CR` guard was under-explained and
  caused a blank line between every full-width row; the "just-wrapped" flag is
  now spelled out.
- **§7.7** *(fixed)* — entries must render first-field + one selected column,
  not the whole comma-separated line (which overflows 40 columns).

Clarified: **§2.8** (client sequence start), **§3.2** (initial handshake byte),
**§4.5** (read the entry type from the first field). Left non-normative by
design: **§6.3** (pre-colour default), **§4.2** (non-DAT mid-stream).
