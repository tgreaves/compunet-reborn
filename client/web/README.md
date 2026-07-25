# Compunet Reborn — web client (Binding B)

Reference client for the modern **JSON API** ([Binding B](../../docs/spec/api/README.md)). It
logs in, browses directories, and renders PETSCII pages on a `<canvas>` using the C64 font and
palette. Written as **runnable ES-module JavaScript** (no build step) so it works directly in a
browser and, in an Electron shell, as a Windows/Mac desktop app. It ports to strict TypeScript
with no restructuring.

Phase 1 (Tier 1): connect / login, directory navigation (SHOW, DIR, BACK, MORE, FINISH, GOTO),
faithful directory composition (red first entry, blue/red selection bar, column cycling), and
frame rendering (40×24 cell grid, colour, charset, RLE).

## Files

- `index.html` — page shell (login, canvas, command bar).
- `app.js` — the client (gateway, canvas renderer, directory composer, input).
- `assets.json` — palette, 256-glyph C64 font, and the directory-template chrome, extracted
  from the spec appendix. Regenerate with `python gen_assets.py`.
- `gen_assets.py` — regenerates `assets.json` from `docs/spec/99-appendices.md`.

## Run (development)

From the repo root, start the API + this client on one origin (needs `server/cfg/users.json`
and a staged content tree under `server/data/content` — see `server/data.example`):

```bash
python server/run_api_dev.py
```

Then open <http://localhost:6404/>, enter your credentials, and Connect.

Keys: `↑`/`↓` select · `Enter` = SHOW · `→` = DIR · `←` = BACK · `N` = MORE · `F` = FINISH ·
`C` = cycle the right-hand column. The same commands are on the button bar.

In production the client API (`server/api_binding.py`) runs on its own; this launcher's static
file serving is a dev convenience only.
