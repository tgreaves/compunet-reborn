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

Commands are presented as a **duckshoot** (spec §4.9), drawn as a real extra row below the
40×24 screen: the *row* scrolls and the **centre** word is the selection, white-on-black with the
centred command inverse.

Keys: `↑`/`↓` highlight a directory entry · `←`/`→` scroll the duckshoot (it wraps) · `Enter`
runs the centred command. The row's contents change with context (§4.8).

## Editor

The frame editor (spec §8.4/§8.4.1) is a real context with its own fourteen-command row and a
**multi-page buffer** — `LAST`/`NEXT` move between pages, `NEW` adds a blank one, `COPY`
duplicates, `ERASE` removes. `EDIT` starts typing on the page (`ESC` stops, `F3`/`F4`
insert/delete a line). `PUT` saves the current page, `STORE` the whole buffer, `GET` reloads
one — all as local JSON files. `DOS` is present but disabled: a sandboxed browser has no
local filesystem, and §8.4.1 permits disabling a command it cannot provide but not removing it.

**It works offline.** `EDITR` is available before you connect at all, and the buffer survives
disconnection — compose now, connect later, then `UPLD` (into a directory) or `SEND` (in mail)
submits the buffer. Those two are the only parts that need a session.

In production the client API (`server/api_binding.py`) runs on its own; this launcher's static
file serving is a dev convenience only.
