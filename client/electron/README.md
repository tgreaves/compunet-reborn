# Compunet Reborn — desktop client (Electron)

A thin Electron shell around the **web client** (`../web`). The desktop app *is* the web
client — one codebase, two targets — so anything fixed in the renderer ships to both.

## Run (development)

The client must be built first, then start the shell:

```bash
cd ../web && npm install && npm run build
cd ../electron && npm install && npm start
```

`npm install` here downloads Electron (~100 MB the first time).

Point the app at a server with the address field in the client (default
`ws://localhost:6404`); for the live service use `wss://<host>` once the client API is
deployed.

## Package

```bash
npm run dist:win     # NSIS installer
npm run dist:mac     # dmg
```

`electron-builder` copies `index.html`, `assets.json`, and `dist/app.bundle.js` from
`../web` into the app's resources — so **build the web client before packaging**.

## How it works

`main.js` serves `../web` from an ephemeral `127.0.0.1` port and loads that URL, rather than
using `file://`, where `fetch()` of `assets.json` is blocked. The renderer runs with
`nodeIntegration: false` and `contextIsolation: true` — it only speaks to the Compunet API
over the network and needs no Node access. External links open in the system browser.
