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
npm run dist:win     # win-unpacked + installer + portable exe  <- use this one
npm run dist:mac     # dmg  (must run ON macOS — the dmg target needs hdiutil)
npm run dist         # every target configured for the current platform
npm run pack:win     # dist/win-unpacked/ ONLY — see the warning below
```

**Use `dist:win` after any client change.** `pack:win` rebuilds only `dist/win-unpacked/` and
leaves `Compunet Reborn Setup <version>.exe` and `Compunet Reborn <version> (portable).exe` at
the previous build. Those two are exactly what a tester picks up, so packaging the "fast" way
is how someone runs old code while believing they are testing the fix.

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

⚠ **The portable build is self-contained.** It keeps settings and the editor buffer in a
`Compunet Reborn Data` folder **beside the exe**, so a copy on a USB stick carries the user's
pages with it and leaves nothing on the host — and an installed copy on the same machine keeps
its own data in `%APPDATA%\Compunet Reborn`, entirely separately. If the exe sits somewhere
unwritable (a read-only stick, a CD) it falls back to `%APPDATA%` rather than failing to
start.

### Other platforms

macOS **must** be built on macOS. Linux can be built from any host via electron-builder's
Docker image:

```bash
docker run --rm -it -v ${PWD}/../..:/project electronuserland/builder   /bin/bash -c "cd /project/client/electron && npm install && npm run dist -- --linux"
```

Neither is signed. macOS Gatekeeper will refuse an unsigned app until the user right-clicks
→ Open; notarising needs an Apple Developer account.

## How it works

`main.js` serves `../web` from a custom **`compunet://`** scheme, registered as `standard`,
`secure` and `supportFetchAPI`. `file://` is not an option — it blocks the `fetch()` of
`assets.json` — and the obvious alternative, an ephemeral `127.0.0.1` port, is a trap: browser
storage is keyed by **origin**, so a port that changes each launch gives every launch its own
empty storage. Settings and the editor buffer then work perfectly within a session and vanish
between them, which reads as broken persistence rather than a moved origin. A fixed scheme has
a constant origin, so §8.4's requirement that the buffer survive a restart actually holds.
The renderer runs with
`nodeIntegration: false` and `contextIsolation: true` — it only speaks to the Compunet API
over the network and needs no Node access. External links open in the system browser.
