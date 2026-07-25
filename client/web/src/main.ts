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

function status(s: string): void { statusEl.textContent = s; }

function render(): void {
  if (mode === 'directory' && dir) renderer.renderDirectory(dir, sel, colIdx);
  else if (mode === 'frame' && frame) renderer.renderFrame(frame);
}

function onMessage(m: ServerMsg): void {
  switch (m.type) {
    case 'ready': {
      const r = m as { account: Account; welcome: FrameMsg | null };
      account = r.account;
      if (r.welcome) { mode = 'frame'; frame = r.welcome; render(); }
      status(`Welcome, ${account.user} — press DIR to enter the system`);
      break;
    }
    case 'directory':
      mode = 'directory'; dir = m as DirectoryMsg; sel = 0; colIdx = 0; render();
      status(`${(m as DirectoryMsg).title} — ${(m as DirectoryMsg).entries.length} entries`);
      break;
    case 'frame':
      mode = 'frame'; frame = m as FrameMsg; render();
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
      setChatVisible(true);
      chatLog('*** Partyline — room ' + (m as { room: string }).room + ' ***');
      status('In Partyline. *help for commands, *quit to leave.');
      break;
    case 'partyline':
      chatLog((m as { line: string }).line);
      break;
    case 'partyline.left':
      setChatVisible(false);
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
  SHOW: () => {
    const e = curEntry(); if (!e) return;
    if (dir?.context === 'mail') gw.send({ type: 'mail.read', index: e.index });
    else gw.send({ type: 'open', page: e.page });
  },
  // In a directory: enter the highlighted entry. On the welcome frame (no directory
  // context): DIR reaches the root — a bare `dir` (§4.7 / Binding-B schema).
  DIR: () => {
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
  PARTY: () => { if (inParty) gw.send({ type: 'partyline.leave' }); else gw.send({ type: 'partyline.enter' }); },
  LEAVE: () => { gw.send({ type: 'leave' }); gw.close(); },
};

function buildBar(): void {
  const bar = $('bar'); bar.innerHTML = '';
  for (const name of Object.keys(actions)) {
    const b = document.createElement('button');
    b.textContent = name;
    b.onclick = actions[name];
    bar.appendChild(b);
  }
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
  // Don't hijack keys while the user is typing (chat, login fields).
  const el = e.target as HTMLElement | null;
  if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return;
  if (inParty) return;
  if (mode === 'directory' && dir) {
    if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, dir.entries.length - 1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); render(); e.preventDefault(); return; }
    if (e.key === 'Enter') { actions.SHOW(); return; }
    if (e.key === 'ArrowRight') { actions.DIR(); return; }
  }
  if (e.key === 'ArrowLeft') actions.BACK();
  else if (e.key.toLowerCase() === 'n') actions.MORE();
  else if (e.key.toLowerCase() === 'f') actions.FINISH();
  else if (e.key.toLowerCase() === 'c') actions.COL();
});

async function boot(): Promise<void> {
  buildBar();
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
