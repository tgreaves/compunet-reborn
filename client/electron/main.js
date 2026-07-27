// Electron shell for the Compunet Reborn web client.
//
// The desktop app IS the web client (client/web) — one codebase, two targets.
//
// ⚠ The client is served from a CUSTOM SCHEME, not a localhost HTTP server, and
// the reason is persistence. `localStorage` is keyed by ORIGIN. This shell used
// to serve the client over http://127.0.0.1 on an EPHEMERAL port (`listen(0)`),
// so every launch had a different origin and therefore its own empty storage:
// the editor buffer and remembered settings vanished on restart while working
// perfectly within a session. `compunet://app` is constant, so what §8.4
// requires to survive a restart actually does.
//
// file:// is not the alternative — it blocks fetch() of assets.json, which is
// why the HTTP server existed at all. A privileged custom scheme gives a stable
// origin AND a working fetch, and removes the server entirely.

const { app, BrowserWindow, shell, protocol, net } = require('electron');
const path = require('path');
const { pathToFileURL } = require('url');

// In development the client lives beside this shell; when packaged it is copied
// into the app's resources (see "extraResources" in package.json).
const WEB_DIR = app.isPackaged
  ? path.join(process.resourcesPath, 'app', 'web')
  : path.join(__dirname, '..', 'web');

// Must be declared before the app is ready. `standard` gives the scheme a real
// origin (so localStorage and relative URLs behave), `secure` keeps it out of
// Chrome's insecure-origin restrictions, and `supportFetchAPI` is what loading
// assets.json needs.
protocol.registerSchemesAsPrivileged([{
  scheme: 'compunet',
  privileges: { standard: true, secure: true, supportFetchAPI: true },
}]);

function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 900,
    backgroundColor: '#101014',
    title: 'Compunet Reborn',
    webPreferences: {
      // The renderer only talks to the Compunet API over the network; it needs
      // no Node access, so keep the sandbox intact.
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  win.setMenuBarVisibility(false);
  // External links open in the user's browser, not inside the app shell.
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; });
  win.loadURL('compunet://app/index.html');
}

app.whenReady().then(() => {
  protocol.handle('compunet', (request) => {
    const url = new URL(request.url);
    const rel = url.pathname === '/' ? 'index.html' : url.pathname.replace(/^\/+/, '');
    const full = path.join(WEB_DIR, decodeURIComponent(rel));
    // Contain within WEB_DIR — no traversal outside the bundled client.
    if (!full.startsWith(path.resolve(WEB_DIR))) return new Response('forbidden', { status: 403 });
    return net.fetch(pathToFileURL(full).toString());
  });
  createWindow();
});

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
