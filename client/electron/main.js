// Electron shell for the Compunet Reborn web client.
//
// The desktop app IS the web client (client/web) — one codebase, two targets.
// Rather than loading it over file://, where fetch() of assets.json is blocked,
// the main process serves client/web from an ephemeral localhost port and points
// the window at that. Keeps the renderer identical to the browser build.

const { app, BrowserWindow, shell } = require('electron');
const http = require('http');
const fs = require('fs');
const path = require('path');

// In development the client lives beside this shell; when packaged it is copied
// into the app's resources (see "extraResources" in package.json).
const WEB_DIR = app.isPackaged
  ? path.join(process.resourcesPath, 'app', 'web')
  : path.join(__dirname, '..', 'web');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
};

function startStaticServer() {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(req.url.split('?')[0]);
      const rel = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
      // Contain within WEB_DIR — no traversal outside the bundled client.
      const full = path.join(WEB_DIR, rel);
      if (!full.startsWith(path.resolve(WEB_DIR))) { res.writeHead(403).end(); return; }
      fs.readFile(full, (err, data) => {
        if (err) { res.writeHead(404).end('not found'); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(full)] || 'application/octet-stream' });
        res.end(data);
      });
    });
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

async function createWindow() {
  const server = await startStaticServer();
  const { port } = server.address();

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
  win.loadURL(`http://127.0.0.1:${port}/`);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
