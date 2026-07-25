// App orchestration: DOM, view state, input, and the command actions that map
// user intent to Binding-B messages.

import type { Account, Assets, DirectoryMsg, FrameMsg, ServerMsg } from './protocol';
import { Renderer } from './render';
import { Gateway } from './gateway';
import { EditorBuffer, frameToPage } from './editor';

const $ = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;

const canvas = $<HTMLCanvasElement>('screen');
const wrap = $<HTMLElement>('screenWrap');
const edCanvas = $<HTMLCanvasElement>('edScreen');
const edWrap = $<HTMLElement>('edWrap');
const statusEl = $<HTMLElement>('status');

let assets: Assets;
/** The Compunet surface (directory / frame / mail) and the Editor surface are
 *  BOTH 40x24 grids, so each gets its own renderer and sits in its own pane.
 *  Showing them together is presentation only (§4.6) — no command changes
 *  meaning, and each pane carries the command row for ITS OWN context (§4.8). */
let renderer: Renderer;     // Compunet pane
let edRenderer: Renderer;   // Editor pane
const gw = new Gateway();

/** Which pane owns the keyboard. Two contexts are visible at once, so focus is
 *  what makes "which commands apply?" unambiguous (§4.8). */
type Pane = 'net' | 'editor';
let focusPane: Pane = 'net';

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

function status(s: string, bad = false): void {
  statusEl.textContent = s;
  statusEl.classList.toggle('bad', bad);
}

/** Move keyboard focus between panes and reflect it in the chrome. */
function setFocus(p: Pane): void {
  if (p === 'editor' && !inEditor) return;
  focusPane = p;
  $('paneNet').classList.toggle('focused', p === 'net');
  $('paneEditor').classList.toggle('focused', p === 'editor');
  updateBar();
}

function render(): void {
  // Both panes draw independently — neither can hide the other. This is what
  // fixes "connect while editing does nothing": the welcome frame lands in the
  // Compunet pane while the editor keeps its page.
  if (courierSlots) drawCourier();
  else if (mode === 'directory' && dir) renderer.renderDirectory(dir, sel, colIdx);
  else if (mode === 'frame' && frame) renderer.renderFrame(frame);
  else renderer.renderIdle();
  if (inEditor) renderEditor();
  updateBar();
}

function onMessage(m: ServerMsg): void {
  // Correlated replies go to whoever is awaiting them (see `request`).
  const rid = (m as { id?: number }).id;
  if (typeof rid === 'number' && pending.has(rid)) {
    pending.get(rid)!(m);
    pending.delete(rid);
    if (m.type === 'idlookup') return;      // consumed by the caller
  }
  switch (m.type) {
    case 'ready': {
      const r = m as { account: Account; welcome: FrameMsg | null };
      account = r.account;
      $('credit').textContent = `${account.user} · £${account.credit.toFixed(2)}`;
      if (r.welcome) { mode = 'frame'; frame = r.welcome; isWelcome = true; inMail = false; }
      // Always render: if the editor pane is open the Compunet pane still
      // updates beside it, so connecting is visibly successful.
      render();
      status(`Welcome, ${account.user} — press DIR to enter the system`);
      break;
    }
    case 'directory':
      mode = 'directory'; dir = m as DirectoryMsg; sel = 0; colIdx = 0;
      isWelcome = false; inMail = (m as DirectoryMsg).context === 'mail';
      courierSlots = null;                 // a real listing replaces the COURIER screen
      render();
      // An upload's result is the refreshed listing (§8.3.2) — the pages have
      // landed, so the Compunet pane takes focus back.
      if (submitting) { submitting = false; setFocus('net'); }
      if (exitingMail) { if (inMail) gw.send({ type: 'back' }); else exitingMail = false; }
      status(`${(m as DirectoryMsg).title} — ${(m as DirectoryMsg).entries.length} entries`);
      break;
    case 'frame': {
      mode = 'frame'; frame = m as FrameMsg; isWelcome = false; render();
      if ((m as { goodbye?: boolean }).goodbye) { status('Goodbye — disconnected.'); gw.close(); return; }
      // ⚠ Pages viewed on Compunet are automatically stored in the Editor
      // (§8.4). This is what makes the editor a reading tool as well as a
      // writing one — you can leave, and still have what you read.
      captureViewedFrame(m as FrameMsg);
      if (exitingMail && inMail) gw.send({ type: 'back' });
      status('Reading page' + ((m as FrameMsg).morePages ? ' — MORE follows' : ''));
      break;
    }
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
      // Mail sent: the result is an ack, not a listing — hand focus back here.
      if (submitting) { submitting = false; setFocus('net'); }
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
      status('⚠ ' + (m as { code: string }).code + ((m as { message?: string }).message ? ': ' + (m as { message?: string }).message : ''), true);
      // A refused upload leaves the buffer intact and the editor in front of the
      // user, so they can fix it and retry rather than hunt for their pages.
      submitting = false;
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
/** A submission is in flight; focus goes back to Compunet once it lands. */
let submitting = false;

function enterEditor(): void {
  inEditor = true;
  buf.editing = false;
  $('paneEditor').hidden = false;   // opened on demand — see the pane model
  setFocus('editor');
  render();
  status('Editor — EDIT types on the page, RETURN leaves. Page ' + (buf.cur + 1) + ' of ' + buf.pages.length);
}

function leaveEditor(): void {
  inEditor = false;
  buf.editing = false;
  $('paneEditor').hidden = true;
  setFocus('net');
  // ⚠ The buffer is NOT cleared — composing offline, connecting, then uploading
  // is a normal sequence (§8.4). It survives leaving the editor and disconnects.
  if (editorReturn) { const f = editorReturn; editorReturn = null; f(); }
  else render();
  status(mode === 'idle'
    ? 'Left the editor — the buffer is kept. Connect, then UPLD or SEND submits it.'
    : 'Left the editor. UPLD or SEND submits the buffer.');
}

/** Store a page the user has just viewed into the editor buffer, VERBATIM
 *  (§8.4.2) — the cells exactly as rendered, plus the bytes they came from.
 *  Silent on success — this happens on every page and must not chatter — but
 *  NOT silent when the buffer is full, because that is data not being kept. */
function captureViewedFrame(f: FrameMsg): void {
  const wasEmpty = buf.isEmpty();
  if (!buf.capture(frameToPage(f))) {
    status('Editor buffer full — this page was not stored (use STORE, then ERASE)', true);
    return;
  }
  // Redraw only if the editor is on screen; capture never steals focus or moves
  // the user's current page.
  if (inEditor) renderEditor();
  if (wasEmpty) $('edMeta').textContent = `page ${buf.cur + 1}/${buf.pages.length}`;
}

function renderEditor(): void {
  const p = buf.page();
  edRenderer.renderEditorPage(p.cells, p.background, p.border, buf.row, buf.col, buf.editing);
  // Buffer position lives in the pane furniture, never in a row taken from the
  // page: a page is the full 40x24 frame (§8.4.2).
  $('edMeta').textContent = `page ${buf.cur + 1}/${buf.pages.length}`
    + (buf.editing ? ` · EDIT ${buf.row + 1},${buf.col + 1}` : '')
    + (p.raw ? ' · captured' : '');
}

/** Open the metadata form. The BODY comes from the editor buffer (§8.4.1) —
 *  there is no text box here, because composing is the editor's job. */
/** Upload metadata, held if the user addresses a page before writing it. */
let pendingUpload: { title: string; kind: string; price: number; life: number } | null = null;

function openSubmit(kind: 'upload' | 'mail'): void {
  // ⚠ An empty buffer does NOT block this (see sendMail) — the metadata can be
  // filled in first and the page composed after.
  submitMode = kind;
  // The content being sent IS the editor buffer, so put the editor in front of
  // the user while they commit to it: open the pane if it is closed and give it
  // focus. Uploading blind — filling in a title for pages you cannot see — is
  // how the wrong buffer gets published.
  if (!inEditor) { editorReturn = () => render(); enterEditor(); }
  setFocus('editor');
  $('submit').hidden = false;
  $('submitTitle').textContent = kind === 'upload'
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

function closeSubmit(): void { submitMode = null; $('submit').hidden = true; }

function doSubmit(): void {
  const title = $<HTMLInputElement>('edTitle').value.trim();
  if (!title) { status('A title is required'); return; }
  const frames = buf.toFrames();
  if (submitMode === 'mail') {
    const to = $<HTMLInputElement>('edTo').value.split(',').map((x) => x.trim()).filter(Boolean);
    if (!to.length) { status('At least one recipient is required'); return; }
    gw.send({ type: 'mail.send', to, subject: title, frames });
  } else {
    const meta = {
      title,
      kind: $<HTMLSelectElement>('edKind').value,
      price: parseFloat($<HTMLInputElement>('edPrice').value) || 0,
      life: parseInt($<HTMLInputElement>('edLife').value, 10) || 0,
    };
    // Nothing written yet: keep the metadata and give them the editor.
    if (buf.isEmpty()) {
      pendingUpload = meta;
      closeSubmit();
      if (!inEditor) { editorReturn = () => render(); enterEditor(); }
      setFocus('editor');
      status(`"${title}" ready to upload — compose the page, then UPLD again`);
      return;
    }
    gw.send({ type: 'upload', ...meta, frames });
    pendingUpload = null;
  }
  // Focus returns to Compunet when the result lands (see `submitting`), not now:
  // the editor stays in view until the server has actually taken the pages.
  submitting = true;
  status(`Sending ${frames.length} page(s)…`);
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
    // Into the EDITOR pane — the Compunet pane keeps showing Compunet. Any
    // other editor command re-renders the page over it.
    edRenderer.renderFrame(assets.editorHelp);
    edRenderer.renderDuckshoot(rows.editor.words, rows.editor.ix);
    status('Editor help — any other editor command returns to the page');
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

/** Partyline TAKES OVER the Compunet pane rather than opening beside it (§4.10):
 *  on the C64 the link loads a chat program that occupies the screen, and the
 *  client restores the screen on exit (§8.5). It is also the one context with
 *  none of the normal commands, so a tiled Compunet pane would show an empty
 *  row anyway. The editor pane, if open, is unaffected — it is a separate
 *  context and Partyline never displaced it on the original either. */
function setChatVisible(on: boolean): void {
  inParty = on;
  $('chat').hidden = !on;
  $('screenWrap').hidden = on;
  $('netTitle').textContent = on ? 'Partyline' : 'Compunet';
  if (on) {
    setFocus('net');                       // the pane is live; the chat owns it
    $<HTMLInputElement>('chatInput').value = '';
    $<HTMLInputElement>('chatInput').focus();
  } else {
    $('chatLog').textContent = '';
    render();                              // restore the Compunet screen beneath
  }
}

function chatLog(line: string): void {
  const log = $('chatLog');
  log.textContent += (log.textContent ? '\n' : '') + line;
  log.scrollTop = log.scrollHeight;
}

// --- Input dialogs ----------------------------------------------------------
//
// ⚠ Electron does NOT implement window.prompt()/confirm() — they throw
// "prompt() is not supported". Every command that needs input therefore has to
// use these, or it silently does nothing in the desktop build while appearing
// to work in a browser. That is exactly how ID, GOTO, VOTE and LIFE were broken.

interface Field { label: string; value?: string; maxlength?: number; type?: string }

function ask(title: string, fields: Field[]): Promise<string[] | null> {
  return new Promise((resolve) => {
    $('askTitle').textContent = title;
    const host = $('askFields');
    host.textContent = '';
    const inputs = fields.map((f) => {
      const el = document.createElement('input');
      el.placeholder = f.label;
      el.value = f.value ?? '';
      if (f.maxlength) el.maxLength = f.maxlength;
      if (f.type) el.type = f.type;
      host.appendChild(el);
      return el;
    });
    $('ask').hidden = false;
    inputs[0]?.focus();
    const done = (v: string[] | null): void => {
      $('ask').hidden = true;
      $<HTMLButtonElement>('askOk').onclick = null;
      $<HTMLButtonElement>('askCancel').onclick = null;
      host.onkeydown = null;
      resolve(v);
    };
    $<HTMLButtonElement>('askOk').onclick = () => done(inputs.map((i) => i.value.trim()));
    $<HTMLButtonElement>('askCancel').onclick = () => done(null);
    host.onkeydown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') { e.preventDefault(); done(inputs.map((i) => i.value.trim())); }
      if (e.key === 'Escape') { e.preventDefault(); done(null); }
    };
  });
}

async function askConfirm(title: string): Promise<boolean> {
  return (await ask(title, [])) !== null;
}

/** Correlated request/response over the gateway, so a flow can await a reply
 *  (ID validation, §8.2) instead of firing and hoping. */
let nextId = 1;
const pending = new Map<number, (m: ServerMsg) => void>();

function request(msg: Record<string, unknown>): Promise<ServerMsg> {
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    gw.send({ ...msg, id } as never);
    setTimeout(() => { if (pending.delete(id)) resolve({ type: 'error', code: 'timeout' }); }, 10000);
  });
}

// --- Courier: ID check and SEND (§8.2) --------------------------------------
//
// Both open on the embedded COURIER frame (§A.10) — the C64 shows it before
// asking anything, so the user is in Courier before they start typing.

/** ⚠ The COURIER screen is a CLIENT-SIDE sub-state of Courier, not a place on
 *  the server: the lookup changes nothing and the frame is our own asset. So
 *  leaving it is a local redraw back to the mailbox — DONE here must NOT send
 *  `back`, which would unwind out of mail altogether (§8.2.1). */
let courierSlots: string[] | null = null;

function showCourier(slots: string[]): void {
  courierSlots = slots;
  drawCourier();
}

function drawCourier(): void {
  const slots = courierSlots ?? [];
  if (!assets.courier) return;
  const f = assets.courier;
  const cells = f.cells.map((c) => ({ ...c }));
  slots.slice(0, 5).forEach((text, i) => {
    const row = 6 + i;                       // the five ':' rows (§A.10)
    for (let j = 0; j < text.length && 3 + j < 40; j++) {
      const ch = text.toUpperCase().charCodeAt(j) & 0xFF;
      const sc = ch >= 0x40 && ch <= 0x5F ? ch & 0x1F : (ch >= 0x20 && ch <= 0x3F ? ch : 0x20);
      cells[row * 40 + 3 + j] = { g: sc, fg: 2, bg: f.background, rv: 0 };
    }
  });
  renderer.renderGrid(cells, f.background);
  renderer.setBorder(f.border);
}

/** ID — look up to five IDs and show each one's real name (§8.2). */
async function idCheck(): Promise<void> {
  showCourier([]);
  const r = await ask('ID TO CHECK?', Array.from({ length: 5 }, (_, i) => ({ label: `ID ${i + 1}`, maxlength: 8 })));
  if (!r) { render(); return; }
  const ids = r.filter(Boolean);
  if (!ids.length) { render(); return; }
  const reply = await request({ type: 'idlookup', ids });
  const users = (reply as { users?: { id: string; name: string | null }[] }).users ?? [];
  showCourier(users.map((u) => `${u.id.padEnd(8)} : ${u.name ?? 'NOT KNOWN'}`));
  status(`${users.filter((u) => u.name).length} of ${ids.length} ID(s) known`);
}

/** SEND — subject, then up to five destination IDs, each VALIDATED before the
 *  editor's frames go anywhere (§8.2). The original asks SUBJECT?, then
 *  DESTINATION ID? up to five times, then OKAY? to confirm. */
/** Recipients and subject, held between the two halves of the flow. */
let pendingMail: { subject: string; ids: string[] } | null = null;

async function sendMail(): Promise<void> {
  // ⚠ An empty buffer must NOT block the attempt. Addressing a message before
  // writing it is a normal order of work — the user can compose once focus
  // lands in the editor, then run SEND again to transmit (§8.2.1).
  if (!pendingMail) {
    showCourier([]);
    const subj = await ask('SUBJECT?', [{ label: 'subject', maxlength: 16 }]);
    if (!subj?.[0]) { courierSlots = null; render(); return; }

    const dest = await ask('DESTINATION ID?', Array.from({ length: 5 }, (_, i) => ({ label: `ID ${i + 1}`, maxlength: 8 })));
    if (!dest) { courierSlots = null; render(); return; }
    const ids = dest.filter(Boolean);
    if (!ids.length) { status('At least one recipient is required'); return; }

    // ⚠ Validate BEFORE sending: the server accepts unknown IDs silently, so an
    // unchecked typo becomes mail that is never delivered and never reported.
    const reply = await request({ type: 'idlookup', ids });
    const users = (reply as { users?: { id: string; name: string | null }[] }).users ?? [];
    const bad = ids.filter((id) => !users.find((u) => u.id.trim().toUpperCase() === id.toUpperCase() && u.name));
    showCourier(ids.map((id) => {
      const u = users.find((x) => x.id.trim().toUpperCase() === id.toUpperCase());
      return `${id.padEnd(8)} : ${u?.name ?? 'NOT KNOWN'}`;
    }));
    if (bad.length) { status(`Unknown ID(s): ${bad.join(', ')} — nothing sent`, true); return; }
    pendingMail = { subject: subj[0], ids };
  }

  // Addressed but not yet written: hand them the editor and keep the recipients.
  if (buf.isEmpty()) {
    if (!inEditor) { editorReturn = () => render(); enterEditor(); }
    setFocus('editor');
    status(`Addressed to ${pendingMail.ids.join(', ')} — compose your message, then SEND again`);
    return;
  }

  if (!await askConfirm(`OKAY? — send ${buf.pages.length} page(s) to ${pendingMail.ids.join(', ')}`)) return;
  submitMode = 'mail';
  setFocus('editor');
  gw.send({ type: 'mail.send', to: pendingMail.ids, subject: pendingMail.subject, frames: buf.toFrames() });
  submitting = true;
  pendingMail = null;
  status('SENDING…');
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
    if (!price) { gw.send({ type: 'open', page: e.page }); return; }
    void askConfirm(`BUY FOR ${price} - SURE?`).then((ok) => {
      if (ok) gw.send({ type: 'open', page: e.page });
    });
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
  // DONE from the COURIER screen (ID / SEND) returns to the MAILBOX — that
  // screen is client-side, so this is a redraw, not a wire command (§8.2.1).
  // Only from the mailbox itself does DONE leave Courier.
  DONE: () => {
    if (courierSlots) { courierSlots = null; pendingMail = null; render(); status('Back to the mailbox'); return; }
    exitingMail = true; gw.send({ type: 'back' });
  },
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
  GOTO: () => { void ask('GOTO', [{ label: 'page number or keyword' }]).then((r) => { if (r?.[0]) gw.send({ type: 'goto', target: r[0] }); }); },
  // (column cycling is F7/F8, §7.7 — not a command)
  ACCNT: () => gw.send({ type: 'account' }),
  MAIL: () => gw.send({ type: 'mail.list' }),
  UCAT: () => gw.send({ type: 'ucat' }),
  VOTE: () => {
    const e = curEntry(); if (!e) { status('Highlight an entry to vote on'); return; }
    void ask(`Vote on "${e.title}"`, [{ label: 'score 1-9', type: 'number' }]).then((r) => {
      if (r?.[0]) gw.send({ type: 'vote', page: e.page, score: parseInt(r[0], 10) });
    });
  },
  LIFE: () => {
    const e = curEntry(); if (!e) { status('Highlight an entry to extend'); return; }
    void ask(`Extend life of "${e.title}"`, [{ label: 'days', type: 'number' }]).then((r) => {
      if (r?.[0]) gw.send({ type: 'life', page: e.page, days: parseInt(r[0], 10) });
    });
  },
  // ID — "ID TO CHECK?" ($B0D9). Up to five, shown on the COURIER frame (§8.2).
  ID: () => { void idCheck(); },
  UPLD: () => {
    if (mode !== 'directory' || !dir) { status('Navigate to a directory first'); return; }
    if (dir.entries.length >= 11) { status('This directory is full (11 entries max)'); return; }
    // Metadata already given and the page now written: go straight to sending.
    if (pendingUpload && !buf.isEmpty()) {
      gw.send({ type: 'upload', ...pendingUpload, frames: buf.toFrames() });
      pendingUpload = null; submitMode = 'upload'; submitting = true;
      setFocus('editor'); status('Uploading…');
      return;
    }
    openSubmit('upload');
  },
  SEND: () => { void sendMail(); },
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
  // ⚠ Empty, and NOT because the editor is unavailable offline. With no session
  // there is no Compunet screen, so there is no duckshoot — the original sits at
  // the BASIC prompt, where EDITOR is a BASIC command ($8249), not a row entry.
  // Offline entry is a HOST-ENVIRONMENT affordance (our "Editor" button, beside
  // Connect); the duckshoot reappears inside the editor with its own row (§8.4).
  idle:      [],
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

/** The CONPUNET pane's context. The editor is a separate pane with its own
 *  context, so it never displaces this one — that is the whole point of the
 *  pane model, and it is why connecting while editing is now visible. */
function netContext(): Context {
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

/** ⚠ Each PANE carries the command row for its OWN context — not one shared row
 *  that changes meaning with focus. That is what keeps §4.8 unambiguous while
 *  two contexts are on screen: the Compunet row is always the Compunet row. */
interface Row { words: string[]; ix: number }
const rows: Record<Pane, Row> = { net: { words: [], ix: 0 }, editor: { words: [], ix: 0 } };

/** ⚠ Each context remembers where ITS row was left (§4.9.4). SHOW a page and
 *  come back, and the directory row is still on SHOW — not reset to HELP.
 *  Keyed by context and stored as the command NAME, not an index: the row's
 *  length changes as selection-dependent commands come and go (§4.9.5), so an
 *  index would drift onto a different command. */
const lastCommand: Partial<Record<Context, string>> = {};

function rememberRow(pane: Pane): void {
  const r = rows[pane];
  const ctx = pane === 'editor' ? 'editor' : netContext();
  if (r.words[r.ix]) lastCommand[ctx] = r.words[r.ix];
}

function buildRow(ctx: Context): string[] {
  const table = ctx === 'editor' ? editorActions : actions;
  return CONTEXT_COMMANDS[ctx].filter((name) => {
    if (!table[name]) return false;
    // selection-dependent commands need a real highlighted entry (§4.9.5)
    if (NEEDS_SELECTION.has(name) && ctx === 'directory' && !hasSelection()) return false;
    return true;
  });
}

/** Rebuild BOTH rows and redraw them (§4.9.4). Inapplicable commands are
 *  ABSENT, not disabled — the duckshoot is the documented exception to §4.8's
 *  disable-rather-than-hide (§4.9.5). */
function updateBar(): void {
  const nctx = netContext();
  rows.net.words = buildRow(nctx);
  // Restore this context's remembered position; the first command is the
  // default only the FIRST time a context is entered (§4.9.4).
  const keep = rows.net.words.indexOf(lastCommand[nctx] ?? '');
  rows.net.ix = rows.net.words.length ? (keep >= 0 ? keep : 0) : 0;

  // A single-frame page has NO duckshoot — just a prompt (§4.8/§4.9).
  if (nctx === 'frame' && frame && !frame.morePages) renderer?.renderPrompt('PRESS ANY KEY');
  else renderer?.renderDuckshoot(rows.net.words, rows.net.ix);

  if (inEditor) {
    rows.editor.words = buildRow('editor');
    const keepE = rows.editor.words.indexOf(lastCommand.editor ?? '');
    rows.editor.ix = keepE >= 0 ? keepE : rows.editor.ix;
    edRenderer?.renderDuckshoot(rows.editor.words, rows.editor.ix);
  }

  $('netMeta').textContent = mode === 'idle' ? 'not connected' : nctx;
  $('hint').textContent = focusPane === 'editor'
    ? 'Editor focused · ←/→ scroll the row · Enter runs it · EDIT then type · ESC stops editing'
    : '↑/↓ highlight an entry · ←/→ scroll the row · Enter runs it · F7/F8 cycle the right column';
}

/** Scroll the FOCUSED pane's row; the selection stays in the centre (§4.9.6). */
function duckScroll(delta: number): void {
  const r = rows[focusPane];
  if (!r.words.length) return;
  r.ix = ((r.ix + delta) % r.words.length + r.words.length) % r.words.length;
  rememberRow(focusPane);   // where the user leaves the row is where it returns
  (focusPane === 'editor' ? edRenderer : renderer).renderDuckshoot(r.words, r.ix);
}

/** Commit the centred command — a distinct action from scrolling (§4.9.6). */
function duckCommit(): void {
  const r = rows[focusPane];
  const name = r.words[r.ix];
  const table = focusPane === 'editor' ? editorActions : actions;
  // Record BEFORE running it: the command may change context (SHOW leaves the
  // directory), and this row's position must be captured against the context
  // the user was actually in.
  rememberRow(focusPane);
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
    $<HTMLInputElement>('pass').classList.remove('bad');
  } catch (e) {
    // Make failure land where the user is looking: the credentials, not just a
    // status line at the foot of the page.
    const msg = (e as Error).message;
    const bad = /401|403/.test(msg);
    $<HTMLInputElement>('pass').classList.toggle('bad', bad);
    if (bad) $<HTMLInputElement>('pass').focus();
    status(bad ? 'Login refused — check the user ID and password.' : 'Connect error: ' + msg, true);
  }
}

window.addEventListener('keydown', (e) => {
  // Don't hijack keys while the user is typing (chat, login, editor).
  const el = e.target as HTMLElement | null;
  if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return;
  if (inParty) return;

  // Tab moves focus between panes — the standard WIMP gesture, and the thing
  // that decides which context the keyboard drives (§4.8).
  if (e.key === 'Tab' && inEditor) {
    setFocus(focusPane === 'net' ? 'editor' : 'net');
    e.preventDefault(); return;
  }

  // --- Editor (§8.4.1) ---------------------------------------------------
  // Only when the EDITOR pane holds focus: with the Compunet pane focused the
  // editor is visible but inert, exactly as an unfocused window should be.
  if (focusPane === 'editor' && inEditor && buf.editing) {
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
  if (focusPane === 'editor' && inEditor) {
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
  edRenderer = new Renderer(edCanvas, assets, edWrap);
  $<HTMLButtonElement>('connect').onclick = connect;
  // Clicking a pane focuses it — the standard WIMP gesture (Tab also toggles).
  $('paneNet').addEventListener('mousedown', () => setFocus('net'));
  $('paneEditor').addEventListener('mousedown', () => setFocus('editor'));
  $<HTMLButtonElement>('edClose').onclick = () => leaveEditor();
  // Host-environment route into the editor — the only way in with no session,
  // and harmless with one (it returns wherever the user was).
  $<HTMLButtonElement>('openEditor').onclick = () => {
    if (inEditor) return;
    editorReturn = () => render();
    enterEditor();
  };
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
  render();
  status('Ready. Connect — or open the Editor now: it works offline.');
}

void boot();
