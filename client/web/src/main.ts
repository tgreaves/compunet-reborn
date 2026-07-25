// App orchestration: DOM, view state, input, and the command actions that map
// user intent to Binding-B messages.

import type { Account, Assets, DirectoryMsg, FrameMsg, ServerMsg } from './protocol';
import { Renderer } from './render';
import { Gateway } from './gateway';
import { EditorBuffer } from './editor';

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const canvas = $<HTMLCanvasElement>('screen');
const wrap = $<HTMLElement>('screenWrap');
const statusEl = $<HTMLElement>('status');

let assets: Assets;
let renderer: Renderer;
const gw = new Gateway();

// view state
type Mode = 'idle' | 'directory' | 'frame';
let mode: Mode = 'idle';
let dir: DirectoryMsg | null = null;
let frame: FrameMsg | null = null;
let sel = 0;          // highlighted entry (client-local)
let colIdx = 0;       // which Part-5 column shows in the right pane (F7/F8)
let account: Account | null = null;
// Context discriminators for §4.8 — the welcome frame is an entry point, not a
// "reading" context, and mail has its own command set.
let isWelcome = false;
let inMail = false;
let exitingMail = false;   // DONE in progress — keep unwinding until out of mail

function status(s: string): void { statusEl.textContent = s; }

function render(): void {
  if (inEditor) renderEditor();
  else if (mode === 'directory' && dir) renderer.renderDirectory(dir, sel, colIdx);
  else if (mode === 'frame' && frame) renderer.renderFrame(frame);
  updateBar();
}

function onMessage(m: ServerMsg): void {
  switch (m.type) {
    case 'ready': {
      const r = m as { account: Account; welcome: FrameMsg | null };
      account = r.account;
      if (r.welcome) { mode = 'frame'; frame = r.welcome; isWelcome = true; inMail = false; render(); }
      status(`Welcome, ${account.user} — press DIR to enter the system`);
      break;
    }
    case 'directory':
      mode = 'directory'; dir = m as DirectoryMsg; sel = 0; colIdx = 0;
      isWelcome = false; inMail = (m as DirectoryMsg).context === 'mail'; render();
      if (exitingMail) { if (inMail) gw.send({ type: 'back' }); else exitingMail = false; }
      status(`${(m as DirectoryMsg).title} — ${(m as DirectoryMsg).entries.length} entries`);
      break;
    case 'frame':
      mode = 'frame'; frame = m as FrameMsg; isWelcome = false; render();
      if ((m as { goodbye?: boolean }).goodbye) { status('Goodbye — disconnected.'); gw.close(); return; }
      if (exitingMail && inMail) gw.send({ type: 'back' });
      status('Reading page' + ((m as FrameMsg).morePages ? ' — MORE follows' : ''));
      break;
    case 'download': {
      const d = m as { title: string | null; size: number; machine: string };
      status(`Download: ${d.title} — ${d.size} bytes (${d.machine})`);
      if (confirm(`Download "${d.title}" (${d.size} bytes)?`)) gw.send({ type: 'download.fetch' });
      break;
    }
    case 'download.data': {
      const d = m as { title: string | null; bytes: string; size: number };
      saveBase64(d.bytes, (d.title || 'download').replace(/\s+/g, '_').toLowerCase() + '.prg');
      status(`Saved ${d.title} (${d.size} bytes)`);
      break;
    }
    case 'account':
      status(`You are ${(m as { creditText: string }).creditText} in credit`);
      break;
    case 'idlookup': {
      const u = (m as { users: { id: string; name: string | null }[] }).users;
      status(u.map((x) => `${x.id} = ${x.name ?? '(unknown)'}`).join(' · ') || 'No such user');
      break;
    }
    case 'ack':
      status(`${(m as { of?: string }).of ?? 'command'} accepted`);
      break;
    case 'partyline.entering':
      status('Joining Partyline…');
      break;
    case 'partyline.entered':
      setChatVisible(true); updateBar();
      chatLog('*** Partyline — room ' + (m as { room: string }).room + ' ***');
      status('In Partyline. *help for commands, *quit to leave.');
      break;
    case 'partyline':
      chatLog((m as { line: string }).line);
      break;
    case 'partyline.left':
      setChatVisible(false); updateBar();
      status('Left Partyline.');
      break;
    case 'error':
      status('⚠ ' + (m as { code: string }).code + ((m as { message?: string }).message ? ': ' + (m as { message?: string }).message : ''));
      break;
    default:
      status('· ' + m.type);
  }
}

function curEntry() { return dir ? dir.entries[sel] : undefined; }

/** The highlighted entry's price, or '' when free / already purchased (§8.6.4).
 *  PRICE is the first Part-5 column of a content listing and the server blanks it
 *  in both of those cases, so an empty value is the "no charge" signal. */
function curPrice(): string {
  const e = curEntry();
  if (!e || inMail) return '';
  return (e.values?.[0] ?? '').trim();
}

// --- Editor (§8.4 / §8.4.1 — a client feature; submits via the upload path §8.3.2) ---
//
// The editor is its OWN context with its own command row. It is not the upload
// form: the form below only collects the metadata (title/kind/price/life, or
// recipients) that accompanies whatever the editor buffer already holds.

const buf = new EditorBuffer();
let inEditor = false;
let editorReturn: (() => void) | null = null;   // how RETURN gets back
let submitMode: 'upload' | 'mail' | null = null;

function enterEditor(): void {
  inEditor = true;
  buf.editing = false;
  status('Editor — EDIT types on the page, RETURN leaves. Page ' + (buf.cur + 1) + ' of ' + buf.pages.length);
  render();
}

function leaveEditor(): void {
  inEditor = false;
  buf.editing = false;
  // ⚠ The buffer is NOT cleared — composing offline, connecting, then uploading
  // is a normal sequence (§8.4). It survives leaving the editor and disconnects.
  if (editorReturn) { const f = editorReturn; editorReturn = null; f(); }
  else render();
  status(mode === 'idle'
    ? 'Left the editor. Connect, then UPLD or SEND submits the buffer.'
    : 'Left the editor. UPLD or SEND submits the buffer.');
}

function renderEditor(): void {
  const p = buf.page();
  renderer.renderEditorPage(
    p.lines, p.colour, p.background, p.border,
    buf.cur, buf.pages.length, buf.row, buf.col, buf.editing,
  );
}

/** Open the metadata form. The BODY comes from the editor buffer (§8.4.1) —
 *  there is no text box here, because composing is the editor's job. */
function openSubmit(kind: 'upload' | 'mail'): void {
  if (buf.isEmpty()) {
    status('Nothing composed yet — use EDITR to write a page first');
    return;
  }
  submitMode = kind;
  $('editor').hidden = false;
  $('editorTitle').textContent = kind === 'upload'
    ? `Upload ${buf.pages.length} page(s) into "${dir?.title ?? 'this directory'}"`
    : `Send ${buf.pages.length} page(s) as mail`;
  $('edContentFields').hidden = kind !== 'upload';
  $<HTMLInputElement>('edTo').hidden = kind !== 'mail';
  $('edHint').textContent = kind === 'upload'
    ? 'Type and price are required (§8.3.2). Body comes from the editor buffer.'
    : 'Recipients: up to five user IDs, comma-separated.';
  $<HTMLInputElement>('edTitle').value = '';
  $<HTMLInputElement>('edTitle').focus();
}

function closeSubmit(): void { submitMode = null; $('editor').hidden = true; }

function doSubmit(): void {
  const title = $<HTMLInputElement>('edTitle').value.trim();
  if (!title) { status('A title is required'); return; }
  const frames = buf.toFrames();
  if (submitMode === 'mail') {
    const to = $<HTMLInputElement>('edTo').value.split(',').map((x) => x.trim()).filter(Boolean);
    if (!to.length) { status('At least one recipient is required'); return; }
    gw.send({ type: 'mail.send', to, subject: title, frames });
  } else {
    gw.send({
      type: 'upload', title,
      kind: $<HTMLSelectElement>('edKind').value,
      price: parseFloat($<HTMLInputElement>('edPrice').value) || 0,
      life: parseInt($<HTMLInputElement>('edLife').value, 10) || 0,
      frames,
    });
  }
  closeSubmit();
}

/** Save text as a file — the web equivalent of PUT / STORE to disk (§8.4.1). */
function saveText(text: string, filename: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

/** GET — the web equivalent of loading frames from disk (§8.4.1). */
function loadFile(): void {
  const inp = document.createElement('input');
  inp.type = 'file'; inp.accept = '.json,application/json';
  inp.onchange = () => {
    const f = inp.files?.[0]; if (!f) return;
    f.text().then((t) => {
      try { const n = buf.load(t); status(`GET — loaded ${n} page(s)`); render(); }
      catch (e) { status('GET failed: ' + (e as Error).message); }
    });
  };
  inp.click();
}

/** The editor's own command actions (§8.4.1). Names and order are NOT a UI
 *  choice — §4.7's closed vocabulary applies here too. */
const editorActions: Record<string, () => void> = {
  // ⚠ The EDITOR's help frame (§A.9) — a different asset from §A.8's.
  HELP: () => {
    if (!assets.editorHelp) { status('No editor help frame embedded'); return; }
    renderer.renderFrame(assets.editorHelp);
    renderer.renderDuckshoot(duck, duckIx);
    status('Editor help — any editor command returns');
  },
  EDIT: () => { buf.editing = !buf.editing; status(buf.editing ? 'EDIT — typing on the page; ESC stops' : 'Edit stopped'); render(); },
  LAST: () => { status(buf.last() ? `Page ${buf.cur + 1} of ${buf.pages.length}` : 'Already at the first page'); render(); },
  NEXT: () => { status(buf.next() ? `Page ${buf.cur + 1} of ${buf.pages.length}` : 'Already at the last page'); render(); },
  // ⚠ NEW is a BLANK page; COPY duplicates. Not the same command (§8.4.1).
  NEW: () => { buf.newPage(); status(`New blank page — ${buf.cur + 1} of ${buf.pages.length}`); render(); },
  COPY: () => { buf.copyPage(); status(`Copied — page ${buf.cur + 1} of ${buf.pages.length}`); render(); },
  ERASE: () => { buf.erasePage(); status(`Erased — page ${buf.cur + 1} of ${buf.pages.length}`); render(); },
  GET: () => loadFile(),
  // ⚠ PUT is ONE page, STORE is the WHOLE buffer — the editor's SHOW/BUY (§8.4.1).
  PUT: () => { saveText(buf.toJSON([buf.page()]), `page-${buf.cur + 1}.json`); status('PUT — current page saved'); },
  STORE: () => { saveText(buf.toJSON(), 'editor-buffer.json'); status(`STORE — all ${buf.pages.length} page(s) saved`); },
  PRINT: () => { window.print(); },
  FREE: () => status(`${buf.free()} CHARS FREE — ${buf.pages.length} page(s) in the buffer`),
  RETURN: () => leaveEditor(),
  // DOS names a local filesystem facility this environment does not have. §8.4.1
  // permits disabling it; it does NOT permit renaming or removing it.
  DOS: () => status('DOS is not available in a sandboxed browser client'),
};

// --- Partyline chat panel (§8.5) -------------------------------------------
let inParty = false;

function setChatVisible(on: boolean): void {
  inParty = on;
  $('chat').hidden = !on;
  if (on) { $<HTMLInputElement>('chatInput').value = ''; $<HTMLInputElement>('chatInput').focus(); }
  else { $('chatLog').textContent = ''; }
}

function chatLog(line: string): void {
  const log = $('chatLog');
  log.textContent += (log.textContent ? '\n' : '') + line;
  log.scrollTop = log.scrollHeight;
}

/** Trigger a browser save of base64 payload (program download, §8.3.1). */
function saveBase64(b64: string, filename: string): void {
  const bin = atob(b64);
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([buf], { type: 'application/octet-stream' }));
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

const actions: Record<string, () => void> = {
  // In the mailbox, SHOW reads the highlighted message (§8.2); otherwise it opens the entry.
  // SHOW refuses a paid page — the user must go through BUY (§8.6.4).
  SHOW: () => {
    const e = curEntry(); if (!e) return;
    if (dir?.context === 'mail') { gw.send({ type: 'mail.read', index: e.index }); return; }
    if (curPrice()) { status('PLEASE USE BUY'); return; }
    gw.send({ type: 'open', page: e.page });
  },
  // BUY is the same wire command as SHOW, plus the price confirmation (§8.6.4).
  // The server deducts the credit and allows overdraft; we never check locally.
  BUY: () => {
    const e = curEntry(); if (!e) return;
    const price = curPrice();
    if (price && !confirm(`BUY FOR ${price} - SURE?`)) return;
    gw.send({ type: 'open', page: e.page });
  },
  // In a directory: enter the highlighted entry. On the welcome frame (no directory
  // context): DIR reaches the root — a bare `dir` (§4.7 / Binding-B schema).
  DIR: () => {
    // In Courier, DIR means "leave mail" (§4.8) — the server exits mail mode on BACK.
    if (inMail) { gw.send({ type: 'back' }); return; }
    if (mode === 'directory' && curEntry()) gw.send({ type: 'enter', page: curEntry()!.page });
    else gw.send({ type: 'dir' });
  },
  BACK: () => gw.send({ type: 'back' }),
  // DONE returns the user where they were before Courier. `back` unwinds one
  // level at a time (message -> listing -> page -> out), so keep going until the
  // session is actually out of mail (§4.8).
  DONE: () => { exitingMail = true; gw.send({ type: 'back' }); },
  // HELP shows the embedded help frame (§A.8) — a client asset, nothing is sent.
  HELP: () => {
    if (!assets.help) { status('No help frame embedded'); return; }
    mode = 'frame'; frame = assets.help; isWelcome = false; render();
    status('Help — FINISH returns');
  },
  SAVE: () => status('SAVE is a client feature — not implemented in this reference client'),
  PRINT: () => status('PRINT is a client feature — not implemented in this reference client'),
  LOAD: () => status('LOAD is a client feature — not implemented in this reference client'),
  // EDITR enters the EDITOR context (§8.4.1) — it does not open an upload form.
  EDITR: () => { editorReturn = () => render(); enterEditor(); },
  ALL: () => gw.send({ type: 'more' }),           // page to the end
  MORE: () => gw.send({ type: 'more' }),
  FINISH: () => gw.send({ type: 'finish' }),
  GOTO: () => { const t = prompt('GOTO page number or keyword:'); if (t) gw.send({ type: 'goto', target: t }); },
  // (column cycling is F7/F8, §7.7 — not a command)
  ACCNT: () => gw.send({ type: 'account' }),
  MAIL: () => gw.send({ type: 'mail.list' }),
  UCAT: () => gw.send({ type: 'ucat' }),
  VOTE: () => {
    const e = curEntry(); if (!e) { status('Highlight an entry to vote on'); return; }
    const s = prompt(`Vote on "${e.title}" — score 1-9:`);
    if (s) gw.send({ type: 'vote', page: e.page, score: parseInt(s, 10) });
  },
  LIFE: () => {
    const e = curEntry(); if (!e) { status('Highlight an entry to extend'); return; }
    const d = prompt(`Extend life of "${e.title}" by how many days?`);
    if (d) gw.send({ type: 'life', page: e.page, days: parseInt(d, 10) });
  },
  ID: () => { const u = prompt('Look up user ID(s), comma-separated:'); if (u) gw.send({ type: 'idlookup', ids: u.split(',').map((x) => x.trim()).filter(Boolean) }); },
  UPLD: () => {
    if (mode !== 'directory' || !dir) { status('Navigate to a directory first'); return; }
    if (dir.entries.length >= 11) { status('This directory is full (11 entries max)'); return; }
    openSubmit('upload');
  },
  SEND: () => openSubmit('mail'),
  // §3.8: read and render the goodbye frame BEFORE handling the close — do not
  // close the socket here; the server closes after sending it.
  LEAVE: () => { gw.send({ type: 'leave' }); status('Leaving…'); },
};

// --- Command availability by context (spec §4.8) ----------------------------
//
// The command set MUST change with what is on screen; showing everything
// everywhere would offer MORE on a directory and VOTE in a chat window. The
// directory order below is the original's priority order (§4.8), so a client
// short of room drops from the end.

type Context = 'idle' | 'welcome' | 'directory' | 'frame' | 'mail' | 'mailFrame' | 'editor' | 'partyline';

const CONTEXT_COMMANDS: Record<Context, string[]> = {
  // ⚠ Not empty: the EDITOR works offline (§8.4), so it is reachable before any
  // login and after a disconnect. Nothing else is available with no session.
  idle:      ['EDITR'],
  // The welcome screen carries the DIRECTORY row, with HELP centred by default (§4.8).
  welcome:   ['HELP', 'DIR', 'SHOW', 'BACK', 'GOTO', 'UCAT', 'MAIL', 'ACCNT', 'SAVE', 'EDITR', 'LEAVE'],
  directory: ['HELP', 'DIR', 'SHOW', 'BACK', 'GOTO', 'UCAT', 'MAIL', 'ACCNT', 'SAVE', 'EDITR',
              'LEAVE', 'PRINT', 'LIFE', 'BUY', 'LOAD', 'UPLD', 'VOTE'],
  frame:     ['MORE', 'ALL', 'FINISH'],   // multi-frame only; single frame shows PRESS ANY KEY
  mail:      ['SEND', 'SHOW', 'MORE', 'ID', 'EDITR', 'DONE'],
  mailFrame: ['SEND', 'SHOW', 'MORE', 'ID', 'EDITR', 'DONE'],
  // ⚠ §8.4.1 order — it ends FREE, RETURN, DOS. Storage order (…FREE DOS RETURN)
  // is NOT display order: the C64 offset table is non-monotonic at the tail.
  editor:    ['HELP', 'EDIT', 'LAST', 'NEXT', 'NEW', 'COPY', 'ERASE', 'GET', 'PUT',
              'STORE', 'PRINT', 'FREE', 'RETURN', 'DOS'],
  partyline: [],
};

/** Commands that act on the highlighted entry — need a selection (§4.8). */
const NEEDS_SELECTION = new Set(['SHOW', 'DIR', 'VOTE', 'LIFE', 'BUY']);

function currentContext(): Context {
  if (inParty) return 'partyline';
  if (inEditor) return 'editor';
  if (mode === 'idle') return 'idle';
  if (mode === 'frame') return isWelcome ? 'welcome' : (inMail ? 'mailFrame' : 'frame');
  return inMail ? 'mail' : 'directory';
}

/** A real, selectable entry is highlighted (the (EMPTY) placeholder is not). */
function hasSelection(): boolean {
  const e = curEntry();
  return !!e && e.title.trim() !== '(EMPTY)' && e.title.trim() !== '(NO MAIL)';
}

let duck: string[] = [];   // the current context's command row
let duckIx = 0;            // index of the CENTRED (selected) command

/** Rebuild the row for the current context and redraw it (§4.9.4).
 *  Inapplicable commands are ABSENT, not disabled — the duckshoot is the
 *  documented exception to §4.8's disable-rather-than-hide (§4.9.5). */
function updateBar(): void {
  const ctx = currentContext();
  const prev = duck[duckIx];
  const table = ctx === 'editor' ? editorActions : actions;
  duck = CONTEXT_COMMANDS[ctx].filter((name) => {
    if (!table[name]) return false;
    // selection-dependent commands need a real highlighted entry (§4.9.5)
    if (NEEDS_SELECTION.has(name) && ctx === 'directory' && !hasSelection()) return false;
    return true;
  });
  // keep the user on the same command across a context change where possible
  const keep = duck.indexOf(prev);
  duckIx = duck.length ? (keep >= 0 ? keep : 0) : 0;
  // A single-frame page has NO duckshoot — just a prompt (§4.8/§4.9).
  if (ctx === 'frame' && frame && !frame.morePages && !inEditor) { renderer?.renderPrompt('PRESS ANY KEY'); }
  else renderer?.renderDuckshoot(duck, duckIx);
  $('ctx').textContent = ctx === 'idle' ? '' : `context: ${ctx}`;
}

/** Scroll the ROW; the selection stays in the centre. Wraps (§4.9.6). */
function duckScroll(delta: number): void {
  if (!duck.length) return;
  duckIx = ((duckIx + delta) % duck.length + duck.length) % duck.length;
  renderer.renderDuckshoot(duck, duckIx);
}

/** Commit the centred command — a distinct action from scrolling (§4.9.6). */
function duckCommit(): void {
  const name = duck[duckIx];
  const table = currentContext() === 'editor' ? editorActions : actions;
  if (name && table[name]) table[name]();
}

async function connect(): Promise<void> {
  const wsBase = $<HTMLInputElement>('host').value.trim().replace(/\/$/, '');
  const httpBase = wsBase.replace(/^ws/, 'http');
  try {
    const { token } = await gw.login(httpBase, $<HTMLInputElement>('user').value, $<HTMLInputElement>('pass').value);
    gw.connect(
      wsBase, token, onMessage,
      () => status('Disconnected.'),
      () => status('WebSocket error.'),
    );
    $<HTMLButtonElement>('connect').disabled = true;
  } catch (e) {
    status('Connect error: ' + (e as Error).message);
  }
}

window.addEventListener('keydown', (e) => {
  // Don't hijack keys while the user is typing (chat, login, editor).
  const el = e.target as HTMLElement | null;
  if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return;
  if (inParty) return;

  // --- Editor (§8.4.1) ---------------------------------------------------
  // While EDIT is active the keyboard belongs to the page, not the duckshoot;
  // ESC stops editing (the original's f1/f3 "STOP EDIT", §A.9).
  if (inEditor && buf.editing) {
    if (e.key === 'Escape')     { buf.editing = false; status('Edit stopped'); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowUp')    { buf.moveRow(-1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowDown')  { buf.moveRow(1);  render(); e.preventDefault(); return; }
    if (e.key === 'ArrowLeft')  { buf.moveCol(-1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowRight') { buf.moveCol(1);  render(); e.preventDefault(); return; }
    if (e.key === 'Enter')      { buf.newline();   render(); e.preventDefault(); return; }
    if (e.key === 'Backspace')  { buf.backspace(); render(); e.preventDefault(); return; }
    // f3/f4 — insert / delete a line above the cursor (§A.9)
    if (e.key === 'F3')         { buf.insertLine(); render(); e.preventDefault(); return; }
    if (e.key === 'F4')         { buf.deleteLine(); render(); e.preventDefault(); return; }
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      buf.typeChar(e.key); render(); e.preventDefault(); return;
    }
    return;
  }
  if (inEditor) {
    // Not editing: the duckshoot has the keyboard, as in any other context.
    if (e.key === 'ArrowLeft')  { duckScroll(-1); e.preventDefault(); return; }
    if (e.key === 'ArrowRight') { duckScroll(1);  e.preventDefault(); return; }
    if (e.key === 'Enter')      { duckCommit();   e.preventDefault(); return; }
    return;
  }

  // Up/Down move the highlighted directory entry; Left/Right scroll the
  // duckshoot; Enter commits the centred command (§4.9.6).
  if (mode === 'directory' && dir) {
    if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, dir.entries.length - 1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowUp')   { sel = Math.max(sel - 1, 0); render(); e.preventDefault(); return; }
  }
  // F7 / F8 cycle the right-hand column (§7.7) — the reference control.
  if (e.key === 'F7' || e.key === 'F8') {
    if (dir) {
      const n = dir.columns.length;
      colIdx = ((colIdx + (e.key === 'F8' ? 1 : -1)) % n + n) % n;
      render(); status('Column: ' + dir.columns[colIdx].trim());
    }
    e.preventDefault(); return;
  }
  if (e.key === 'ArrowLeft')  { duckScroll(-1); e.preventDefault(); return; }
  if (e.key === 'ArrowRight') { duckScroll(1);  e.preventDefault(); return; }
  if (e.key === 'Enter')      { duckCommit();   e.preventDefault(); return; }
});

async function boot(): Promise<void> {
  assets = await (await fetch('./assets.json')).json();
  renderer = new Renderer(canvas, assets, wrap);
  $<HTMLButtonElement>('connect').onclick = connect;
  // Partyline: one Enter sends (the originals used a double RETURN, §8.5).
  // The template draws <F7)(F8> at row 21, cols ~30-38 — make it clickable for
  // pointer users, same effect as the keys (§7.7).
  canvas.addEventListener('click', (ev) => {
    if (mode !== 'directory' || !dir) return;
    const r = canvas.getBoundingClientRect();
    const col = Math.floor(((ev.clientX - r.left) / r.width) * 40);
    const row = Math.floor(((ev.clientY - r.top) / r.height) * 25);
    // <F7)(F8> indicator: left half = F7 (back), right half = F8 (forward)
    if (row === 21 && col >= 30 && col <= 38) {
      const n = dir.columns.length;
      colIdx = ((colIdx + (col >= 34 ? 1 : -1)) % n + n) % n;
      render(); status('Column: ' + dir.columns[colIdx].trim());
      return;
    }
    // Entry rows 10..20: a single click only HIGHLIGHTS (§7.7) — nothing is sent.
    const i = row - 10;
    if (i < 0 || i >= dir.entries.length) return;
    sel = i; render();
  });

  // Double click on an entry = DIR, the only command a click may invoke (§7.7,
  // the Amiga client's behaviour). Never SHOW/BUY, so a click can't charge.
  canvas.addEventListener('dblclick', (ev) => {
    if (mode !== 'directory' || !dir) return;
    // No effect in Courier: DIR is not in the mail command set (§4.8/§7.7).
    if (inMail) return;
    const r = canvas.getBoundingClientRect();
    const row = Math.floor(((ev.clientY - r.top) / r.height) * 25);
    const i = row - 10;
    if (i < 0 || i >= dir.entries.length) return;
    sel = i; render();
    actions.DIR();
  });
  $<HTMLButtonElement>('edSubmit').onclick = doSubmit;
  $<HTMLButtonElement>('edCancel').onclick = closeSubmit;
  $<HTMLInputElement>('chatInput').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const input = $<HTMLInputElement>('chatInput');
    const text = input.value.trim();
    if (!text) return;
    gw.send({ type: text.startsWith('*') ? 'partyline.command' : 'partyline.send', text });
    input.value = '';
  });
  // Draw the idle row straight away: the editor is offline-capable (§8.4), so
  // EDITR must be reachable before the user connects at all.
  updateBar();
  status('Ready. Connect — or use EDITR now: the editor works offline.');
}

void boot();
