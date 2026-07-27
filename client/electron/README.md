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
npm run pack:win     # fast: dist/win-unpacked/ only, for testing
npm run dist:win     # installer + portable exe
npm run dist:mac     # dmg  (must run ON macOS — the dmg target needs hdiutil)
npm run dist         # every target configured for the current platform
```

Every script rebuilds the web client first. The shell only *copies*
`../web/dist/app.bundle.js` into its resources, so without that it packages whatever
bundle happens to be on disk: it builds cleanly, launches cleanly, and runs stale code.

### The two Windows artifacts

| File | What it does |
|---|---|
| `Compunet Reborn <version> Setup.exe` | **Installer.** Asks where to install, makes shortcuts, registers an uninstaller |
| `Compunet Reborn <version> (portable).exe` | **No install.** Unpacks to a temp folder and runs; delete the file to remove it |

⚠ **The installer is deliberately not `oneClick`.** electron-builder's NSIS default installs
silently to a fixed per-user path with no pages at all — so re-running it reinstalls, which
reads as the app announcing "Installing…" every time you launch it. `oneClick: false` plus
`allowToChangeInstallationDirectory` gives the wizard people expect, including putting it on
another drive.

⚠ **"Portable" means no install, NOT self-contained.** Both builds keep user data —
settings and the editor buffer — in `%APPDATA%\Compunet Reborn`, because the app does not
relocate `userData`. A portable copy therefore leaves data behind on any machine it runs on,
and shares it with an installed copy. Making it travel with the exe means pointing
`userData` at `PORTABLE_EXECUTABLE_DIR` when electron-builder sets it.

### Other platforms

macOS **must** be built on macOS. Linux can be built from any host via electron-builder's
Docker image:

```bash
docker run --rm -it -v ${PWD}/../..:/project electronuserland/builder   /bin/bash -c "cd /project/client/electron && npm install && npm run dist -- --linux"
```

Neither is signed. macOS Gatekeeper will refuse an unsigned app until the user right-clicks
→ Open; notarising needs an Apple Developer account.

## How it works

`main.js` serves `../web` from an ephemeral `127.0.0.1` port and loads that URL, rather than
using `file://`, where `fetch()` of `assets.json` is blocked. The renderer runs with
`nodeIntegration: false` and `contextIsolation: true` — it only speaks to the Compunet API
over the network and needs no Node access. External links open in the system browser.
