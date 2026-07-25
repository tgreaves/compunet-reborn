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
    case 'download':
      status(`Download: ${(m as { title: string }).title} (${(m as { note?: string }).note || ''})`);
      break;
    case 'account':
      status(`You are ${(m as { creditText: string }).creditText} in credit`);
      break;
    case 'error':
      status('⚠ ' + (m as { code: string }).code + ((m as { message?: string }).message ? ': ' + (m as { message?: string }).message : ''));
      break;
    default:
      status('· ' + m.type);
  }
}

function curEntry() { return dir ? dir.entries[sel] : undefined; }

const actions: Record<string, () => void> = {
  SHOW: () => { const e = curEntry(); if (e) gw.send({ type: 'open', page: e.page }); },
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
  COL: () => { if (dir) { colIdx = (colIdx + 1) % dir.columns.length; render(); status('Column: ' + dir.columns[colIdx]); } },
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
  status('Ready. Enter credentials and Connect.');
}

void boot();
