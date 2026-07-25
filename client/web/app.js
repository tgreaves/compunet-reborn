// Compunet Reborn — reference web client for Binding B (the JSON API).
// Runnable ES-module JavaScript (no build step) so it works directly in a
// browser and, in an Electron shell, as the desktop app. Structured to port
// to strict TypeScript with no restructuring. See docs/spec/api/README.md.

const COLS = 40, ROWS = 24, CELL = 8, SCALE = 2;
const RED = 2, BLUE = 6, WHITE = 1;

let assets;              // { palette:[16], font:[256][8], template:{cells} }
let ws = null;
let httpBase = '';       // http(s) origin for /v1/session
let account = null;

// view state
let mode = 'idle';       // 'directory' | 'frame'
let dir = null;          // last directory message
let sel = 0;             // highlighted entry index (client-local)
let colIdx = 0;          // which Part-5 column shows in the right pane (F7/F8)
let frame = null;        // last frame message

const $ = (id) => document.getElementById(id);
const canvas = $('screen');
const ctx = canvas.getContext('2d');

// --- glyph mapping ---------------------------------------------------------
function petsciiToScreencode(b) {           // mirrors spec §5.3 / server
  if (b >= 0x20 && b <= 0x3F) return b;
  if (b >= 0x40 && b <= 0x5F) return b & 0x1F;
  if (b >= 0x60 && b <= 0x7F) return (b & 0x1F) | 0x40;
  if (b >= 0xA0 && b <= 0xBF) return (b & 0x1F) | 0x60;
  if (b >= 0xC0 && b <= 0xDE) return b & 0x7F;
  if (b === 0xFF) return 0x5E;
  return b & 0x7F;
}
// directory text is unshifted uppercase ASCII (§7.2) -> uppercase/graphics set
function asciiGlyph(ch) { return petsciiToScreencode(ch.charCodeAt(0) & 0xFF); }

// --- canvas rendering ------------------------------------------------------
function sizeCanvas() {
  canvas.width = COLS * CELL * SCALE;
  canvas.height = ROWS * CELL * SCALE;
}
function drawGlyph(g, col, row, fg, bg, rv) {
  const bmp = assets.font[g] || assets.font[0x20];
  const px = col * CELL * SCALE, py = row * CELL * SCALE, s = SCALE;
  ctx.fillStyle = assets.palette[bg]; ctx.fillRect(px, py, CELL * s, CELL * s);
  ctx.fillStyle = assets.palette[fg];
  for (let y = 0; y < 8; y++) {
    const byte = bmp[y];
    for (let x = 0; x < 8; x++) {
      let on = (byte >> (7 - x)) & 1;
      if (rv) on = on ^ 1;
      if (on) ctx.fillRect(px + x * s, py + y * s, s, s);
    }
  }
}
function renderGrid(cells, background) {
  ctx.fillStyle = assets.palette[background & 0x0F]; ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (let r = 0; r < ROWS; r++)
    for (let c = 0; c < COLS; c++) {
      const cell = cells[r * COLS + c];
      drawGlyph(cell.g, c, r, cell.fg, cell.bg, cell.rv);
    }
}
function setBorder(idx) { $('screenWrap').style.background = assets.palette[idx & 0x0F]; }

// --- directory composition (client owns layout — §7.5–§7.7) ----------------
function cloneTemplate() { return assets.template.cells.map(x => ({ ...x })); }
function put(grid, row, col, text, fg, bg, rv) {
  const t = (text || '').toUpperCase();
  for (let i = 0; i < t.length && col + i < COLS; i++) {
    const idx = row * COLS + (col + i);
    if (col + i < 0) continue;
    grid[idx] = { g: asciiGlyph(t[i]), fg, bg, rv: rv ? 1 : 0 };
  }
}
function composeDirectory() {
  const g = cloneTemplate();
  const tbg = 15;                          // template background (light grey)
  // breadcrumb (Part 4) — blue, from base column 2
  if (dir.breadcrumb[0]) put(g, 7, 2, dir.breadcrumb[0], BLUE, tbg);
  if (dir.breadcrumb[1]) put(g, 8, 2, dir.breadcrumb[1], BLUE, tbg);
  if (dir.mailWaiting) put(g, 8, 22, 'MAIL', RED, tbg);
  // selected column header (right pane, row 8, one in from the ~col-30 divider)
  put(g, 8, 31, dir.columns[colIdx] || '', BLUE, tbg);
  // entries rows 10..20
  dir.entries.forEach((e, i) => {
    const row = 10 + i;
    const colour = (i === 0) ? RED : BLUE;           // first entry always red (§7.7)
    const selected = (i === sel);
    const fg = selected ? WHITE : colour;
    const bg = selected ? colour : tbg;
    if (selected) for (let c = 1; c <= 38; c++) g[row * COLS + c] = { g: 0x20, fg: WHITE, bg: colour, rv: 0 };
    if (selected) {                                   // page number only on selected row (§7.7)
      const ps = String(e.page);
      put(g, row, 8 - ps.length, ps, fg, bg);
    }
    put(g, row, 9, e.title, fg, bg);
    const type = e.type + (e.size ? String(e.size) : '') + (e.hasSubdir ? '+' : '');
    put(g, row, 26, type, fg, bg);
    const val = (e.values && e.values[dir.columns[colIdx]]) || '';
    if (val) put(g, row, 31, val, fg, bg);
  });
  // advert (Part 2) rows 22–23, centred, blue
  (dir.advert || []).slice(0, 2).forEach((line, i) => {
    const col = Math.max(0, Math.floor((COLS - line.length) / 2));
    put(g, 22 + i, col, line, BLUE, tbg);
  });
  renderGrid(g, tbg);
  setBorder(assets.template.border);
}

function render() {
  if (mode === 'directory' && dir) composeDirectory();
  else if (mode === 'frame' && frame) { renderGrid(frame.cells, frame.background); setBorder(frame.border); }
}

// --- gateway ---------------------------------------------------------------
function status(s) { $('status').textContent = s; }

async function connect() {
  const wsBase = $('host').value.trim().replace(/\/$/, '');
  httpBase = wsBase.replace(/^ws/, 'http');
  try {
    const r = await fetch(httpBase + '/v1/session', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user: $('user').value, pass: $('pass').value }),
    });
    if (!r.ok) { status('Login failed (' + r.status + ')'); return; }
    const s = await r.json();
    account = s.account;
    ws = new WebSocket(wsBase + '/v1/gateway');
    ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token: s.token }));
    ws.onmessage = (ev) => onMessage(JSON.parse(ev.data));
    ws.onclose = () => status('Disconnected.');
    ws.onerror = () => status('WebSocket error.');
    $('connect').disabled = true;
  } catch (e) { status('Connect error: ' + e.message); }
}

function onMessage(m) {
  switch (m.type) {
    case 'ready':
      account = m.account;
      if (m.welcome) { mode = 'frame'; frame = m.welcome; render(); }
      status('Logged in as ' + account.user + ' — credit ' + account.credit);
      break;
    case 'directory': mode = 'directory'; dir = m; sel = 0; colIdx = 0; render();
      status(m.title + ' — ' + m.entries.length + ' entries'); break;
    case 'frame': mode = 'frame'; frame = m; render();
      status('Reading page' + (m.morePages ? ' — MORE follows' : '')); break;
    case 'download': status('Download: ' + m.title + ' (' + (m.note || '') + ')'); break;
    case 'account': status('You are ' + m.creditText + ' in credit'); break;
    case 'error': status('⚠ ' + m.code + (m.message ? ': ' + m.message : '')); break;
    default: status('· ' + m.type);
  }
}

function send(msg) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg)); }
function curEntry() { return dir && dir.entries[sel]; }

const actions = {
  SHOW: () => curEntry() && send({ type: 'open', page: curEntry().page }),
  DIR:  () => curEntry() && send({ type: 'enter', page: curEntry().page }),
  BACK: () => send({ type: 'back' }),
  MORE: () => send({ type: 'more' }),
  FINISH: () => send({ type: 'finish' }),
  GOTO: () => { const t = prompt('GOTO page number or keyword:'); if (t) send({ type: 'goto', target: t }); },
  COL:  () => { if (dir) { colIdx = (colIdx + 1) % dir.columns.length; render(); status('Column: ' + dir.columns[colIdx]); } },
  LEAVE: () => { send({ type: 'leave' }); if (ws) ws.close(); },
};

function buildBar() {
  const bar = $('bar'); bar.innerHTML = '';
  for (const name of Object.keys(actions)) {
    const b = document.createElement('button');
    b.textContent = name; b.onclick = actions[name]; bar.appendChild(b);
  }
}

window.addEventListener('keydown', (e) => {
  if (mode === 'directory' && dir) {
    if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, dir.entries.length - 1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowUp')   { sel = Math.max(sel - 1, 0); render(); e.preventDefault(); return; }
    if (e.key === 'Enter')      { actions.SHOW(); return; }
    if (e.key === 'ArrowRight') { actions.DIR(); return; }
  }
  if (e.key === 'ArrowLeft') actions.BACK();
  else if (e.key.toLowerCase() === 'n') actions.MORE();
  else if (e.key.toLowerCase() === 'f') actions.FINISH();
  else if (e.key.toLowerCase() === 'c') actions.COL();
});

// --- boot ------------------------------------------------------------------
(async function boot() {
  sizeCanvas(); buildBar();
  assets = await (await fetch('./assets.json')).json();
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  $('connect').onclick = connect;
  status('Ready. Enter credentials and Connect.');
})();
