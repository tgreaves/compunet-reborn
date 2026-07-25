// App orchestration: DOM, view state, input, and the command actions that map
// user intent to Binding-B messages.

import type { Account, Assets, DirectoryMsg, FrameMsg, ServerMsg } from './protocol';
import { Renderer } from './render';
import { Gateway } from './gateway';

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

function status(s: string): void { statusEl.textContent = s; }

function render(): void {
  if (mode === 'directory' && dir) renderer.renderDirectory(dir, sel, colIdx);
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
      status(`${(m as DirectoryMsg).title} — ${(m as DirectoryMsg).entries.length} entries`);
      break;
    case 'frame':
      mode = 'frame'; frame = m as FrameMsg; isWelcome = false; render();
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

// --- Editor (§8.4 — a client feature; submits via the upload path §8.3.2) ---
let editorMode: 'upload' | 'mail' | null = null;

function openEditor(kind: 'upload' | 'mail'): void {
  editorMode = kind;
  $('editor').hidden = false;
  $('editorTitle').textContent = kind === 'upload'
    ? `Upload a page into "${dir?.title ?? 'this directory'}"`
    : 'Compose mail';
  $('edContentFields').hidden = kind !== 'upload';
  $<HTMLInputElement>('edTo').hidden = kind !== 'mail';
  $('edHint').textContent = kind === 'upload'
    ? 'Type and price are required (§8.3.2).'
    : 'Recipients: up to five user IDs, comma-separated.';
  $<HTMLInputElement>('edTitle').value = '';
  $<HTMLTextAreaElement>('edBody').value = '';
  $<HTMLInputElement>('edTitle').focus();
}

function closeEditor(): void { editorMode = null; $('editor').hidden = true; }

function submitEditor(): void {
  const title = $<HTMLInputElement>('edTitle').value.trim();
  const lines = $<HTMLTextAreaElement>('edBody').value.split('\n');
  if (!title) { status('A title is required'); return; }
  if (editorMode === 'mail') {
    const to = $<HTMLInputElement>('edTo').value.split(',').map((x) => x.trim()).filter(Boolean);
    if (!to.length) { status('At least one recipient is required'); return; }
    gw.send({ type: 'mail.send', to, subject: title, frames: [{ lines, colour: 1 }] });
  } else {
    gw.send({
      type: 'upload', title,
      kind: $<HTMLSelectElement>('edKind').value,
      price: parseFloat($<HTMLInputElement>('edPrice').value) || 0,
      life: parseInt($<HTMLInputElement>('edLife').value, 10) || 0,
      frames: [{ lines, colour: 5, border: 6, background: 0 }],
    });
  }
  closeEditor();
}

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
  MORE: () => gw.send({ type: 'more' }),
  FINISH: () => gw.send({ type: 'finish' }),
  GOTO: () => { const t = prompt('GOTO page number or keyword:'); if (t) gw.send({ type: 'goto', target: t }); },
  COL: () => { if (dir) { colIdx = (colIdx + 1) % dir.columns.length; render(); status('Column: ' + dir.columns[colIdx].trim()); } },
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
  WHO: () => { const u = prompt('Look up user ID(s), comma-separated:'); if (u) gw.send({ type: 'idlookup', ids: u.split(',').map((x) => x.trim()).filter(Boolean) }); },
  UPLD: () => {
    if (mode !== 'directory' || !dir) { status('Navigate to a directory first'); return; }
    if (dir.entries.length >= 11) { status('This directory is full (11 entries max)'); return; }
    openEditor('upload');
  },
  SEND: () => openEditor('mail'),
  LEAVE: () => { gw.send({ type: 'leave' }); gw.close(); },
};

// --- Command availability by context (spec §4.8) ----------------------------
//
// The command set MUST change with what is on screen; showing everything
// everywhere would offer MORE on a directory and VOTE in a chat window. The
// directory order below is the original's priority order (§4.8), so a client
// short of room drops from the end.

type Context = 'idle' | 'welcome' | 'directory' | 'frame' | 'mail' | 'mailFrame' | 'partyline';

const CONTEXT_COMMANDS: Record<Context, string[]> = {
  idle:      [],
  welcome:   ['DIR', 'GOTO', 'ACCNT', 'MAIL', 'UCAT', 'LEAVE'],
  directory: ['DIR', 'SHOW', 'BACK', 'GOTO', 'UCAT', 'MAIL', 'ACCNT', 'LIFE', 'BUY',
              'UPLD', 'VOTE', 'WHO', 'COL', 'LEAVE'],
  frame:     ['MORE', 'FINISH', 'LEAVE'],
  mail:      ['DIR', 'SEND', 'SHOW', 'WHO', 'COL', 'LEAVE'],   // Courier set (§4.8)
  mailFrame: ['MORE', 'FINISH', 'SEND', 'LEAVE'],
  // Partyline has no bar commands: chat is driven by its own input, and you
  // leave with *quit — exactly as in the original (§8.5).
  partyline: [],
};

/** Commands that act on the highlighted entry — need a selection (§4.8). */
const NEEDS_SELECTION = new Set(['SHOW', 'DIR', 'VOTE', 'LIFE', 'BUY']);

function currentContext(): Context {
  if (inParty) return 'partyline';
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
  duck = CONTEXT_COMMANDS[ctx].filter((name) => {
    if (!actions[name]) return false;
    // selection-dependent commands need a real highlighted entry (§4.9.5)
    if (NEEDS_SELECTION.has(name) && ctx === 'directory' && !hasSelection()) return false;
    return true;
  });
  // keep the user on the same command across a context change where possible
  const keep = duck.indexOf(prev);
  duckIx = duck.length ? (keep >= 0 ? keep : 0) : 0;
  renderer?.renderDuckshoot(duck, duckIx);
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
  if (name && actions[name]) actions[name]();
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

  // Up/Down move the highlighted directory entry; Left/Right scroll the
  // duckshoot; Enter commits the centred command (§4.9.6).
  if (mode === 'directory' && dir) {
    if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, dir.entries.length - 1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowUp')   { sel = Math.max(sel - 1, 0); render(); e.preventDefault(); return; }
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
  $<HTMLButtonElement>('edSubmit').onclick = submitEditor;
  $<HTMLButtonElement>('edCancel').onclick = closeEditor;
  $<HTMLInputElement>('chatInput').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const input = $<HTMLInputElement>('chatInput');
    const text = input.value.trim();
    if (!text) return;
    gw.send({ type: text.startsWith('*') ? 'partyline.command' : 'partyline.send', text });
    input.value = '';
  });
  status('Ready. Enter credentials and Connect.');
}

void boot();
