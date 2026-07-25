# Compunet Reborn — web client (Binding B)

Reference client for the modern **JSON API** ([Binding B](../../docs/spec/api/README.md)). It
logs in, browses directories, and renders PETSCII pages on a `<canvas>` using the C64 font and
palette. Written in **TypeScript** (strict), bundled with esbuild; it runs in a browser and, in
an Electron shell, as a Windows/Mac desktop app.

Phase 1 (Tier 1): connect / login, directory navigation (SHOW, DIR, BACK, MORE, FINISH, GOTO),
faithful directory composition (red first entry, blue/red selection bar, column cycling), and
frame rendering (40×24 cell grid, colour, charset, RLE).

## Files

- `index.html` — page shell (login, canvas, command bar); loads `dist/app.bundle.js`.
- `src/` — TypeScript: `protocol.ts` (the Binding-B message types), `render.ts` (canvas
  renderer + directory composer), `gateway.ts` (transport), `main.ts` (app/input).
- `dist/app.bundle.js` — the built bundle (committed, so it runs without a build).
- `assets.json` — palette, 256-glyph C64 font, and the directory-template chrome, extracted
  from the spec appendix. Regenerate with `python gen_assets.py`.
- `gen_assets.py` — regenerates `assets.json` from `docs/spec/99-appendices.md`.

## Build

```bash
npm install        # once
npm run build      # esbuild -> dist/app.bundle.js   (npm run watch to rebuild on change)
npm run typecheck  # strict tsc, no emit
```

The committed bundle means you can skip the build to just run it.

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
