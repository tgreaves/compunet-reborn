// App orchestration: DOM, view state, input, and the command actions that map
// user intent to Binding-B messages.

import type { Account, Assets, Cell, DirectoryMsg, FrameMsg, ServerMsg } from './protocol';
import { Renderer } from './render';
import { Gateway } from './gateway';
import { EditorBuffer, frameToPage, MIN_PAGES, DEFAULT_MAX_PAGES } from './editor';

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
/** The user's real name, for the SEND frame's FROM field (§A.11). Taken from
 *  the mailbox breadcrumb, which identifies the mailbox owner (§8.2). */
let accountName = '';
// Context discriminators for §4.8 — the welcome frame is an entry point, not a
// "reading" context, and mail has its own command set.
let isWelcome = false;
let inMail = false;
/** ⚠ A session exists. NOT the same as `mode !== 'idle'`: after LEAVE the
 *  goodbye frame stays on screen to be read (§3.8) while the session is over,
 *  and §8.4.2 is explicit that with no session there is no command row. */
let connected = false;

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
  // In message composition the Compunet surface shows the FRAME BEING SENT, not
  // the envelope: LAST/NEXT page through the editor's frames and SEND adds the
  // one on screen, so the user must be able to see which that is (§8.2.2).
  if (pendingMail && courier?.kind === 'send') {
    const p = buf.page();
    renderer.renderEditorPage(p.cells, p.background, p.border, 0, 0, null);
  } else if (courier) drawCourier();
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
      connected = true;
      if (r.welcome) { mode = 'frame'; frame = r.welcome; isWelcome = true; inMail = false; }
      // Always render: if the editor pane is open the Compunet pane still
      // updates beside it, so connecting is visibly successful.
      render();
      status(`Welcome, ${account.user} — press DIR to enter the system`);
      break;
    }
    case 'directory':
      // ⚠ A mail download ends by returning the mailbox (§8.2). Applying it here
      // would replace the message on screen with the listing before the user has
      // read a word of it; showMail holds it until they press a key.
      if (mailDownloading) { pendingMailListing = m; break; }
      mode = 'directory'; dir = m as DirectoryMsg; sel = 0; colIdx = 0;
      isWelcome = false;
      const wasMail = inMail;
      inMail = (m as DirectoryMsg).context === 'mail';
      // Left Courier: forget the mail row so re-entry starts on SEND (§4.9.4).
      if (wasMail && !inMail) { delete lastCommand.mail; delete lastCommand.mailFrame; }
      if (inMail) accountName = ((m as DirectoryMsg).breadcrumb[1] || '').trim();
      courier = null;                      // a real listing replaces the COURIER screen
      render();
      // An upload's result is the refreshed listing (§8.3.2) — the pages have
      // landed, so the Compunet pane takes focus back.
      if (submitting) { submitting = false; setFocus('net'); }
      status(`${(m as DirectoryMsg).title} — ${(m as DirectoryMsg).entries.length} entries`);
      break;
    case 'frame': {
      mode = 'frame'; frame = m as FrameMsg; isWelcome = false; render();
      if ((m as { goodbye?: boolean }).goodbye) { status('Goodbye — disconnected.'); gw.close(); return; }
      // ⚠ Pages viewed on Compunet are automatically stored in the Editor
      // (§8.4). This is what makes the editor a reading tool as well as a
      // writing one — you can leave, and still have what you read.
      captureViewedFrame(m as FrameMsg);
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
      if ((m as { of?: string }).of === 'mail.send' && sentTo) {
        status(`Message sent to ${sentTo} — it is in THEIR mailbox, not yours.`);
        sentTo = '';
      } else status(`${(m as { of?: string }).of ?? 'command'} accepted`);
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
 *  NOT silent when the buffer is full, because that is data not being kept.
 *  The editor follows along to the captured page (§8.4.2), unless an edit is in
 *  progress. */
function captureViewedFrame(f: FrameMsg): void {
  const wasEmpty = buf.isEmpty();
  // Always stored — the oldest page is evicted if the buffer is full, as on the
  // original ($849B/$8C40). `note` is set when that happened.
  const note = buf.capture(frameToPage(f));
  if (note) status(note, true);
  // ⚠ Redraw but do NOT take focus. The editor now MOVES to the captured page
  // (the original's allocator makes the new page current), so the pane must
  // repaint to show it — but focus stays with Compunet, where the user is
  // reading. Following the reading is the point; interrupting it is not.
  if (inEditor) renderEditor();
  if (wasEmpty) $('edMeta').textContent = `page ${buf.cur + 1}/${buf.pages.length}`;
}

/** ⚠ The cursor blinks, and blinking is not decoration — it is half of what
 *  makes it findable (§8.4.3). The original's period is a software delay loop
 *  around GETIN ($87B6-$87C5), so it has no exact millisecond value to copy;
 *  ~300 ms a phase matches the observed rate closely enough. */
const CURSOR_BLINK_MS = 300;

/** The C64's `CTRL`+1-8 colour bank, in key order (§8.4.3). */
const CTRL_COLOURS = [0, 1, 2, 3, 4, 5, 6, 7];
/** The second bank. On the C64 it is `C=`+1-8; `C=` maps to Tab here (§8.4.3),
 *  which cannot be chorded with a digit in a browser, so it takes SHIFT. */
const CTRL_COLOURS_ALT = [8, 9, 10, 11, 12, 13, 14, 15];

setInterval(() => {
  // Only while actually editing, and only when the editor is on screen: a
  // timer redrawing a hidden pane is wasted work, and capture (§8.4.2) must
  // not be disturbed by it.
  if (!inEditor || !buf.editing) return;
  buf.tickCursor();
  renderEditor();
}, CURSOR_BLINK_MS);

function renderEditor(): void {
  const p = buf.page();
  edRenderer.renderEditorPage(p.cells, p.background, p.border, buf.row, buf.col, buf.cursorState());
  // Buffer position lives in the pane furniture, never in a row taken from the
  // page: a page is the full 40x24 frame (§8.4.2).
  $('edMeta').textContent = `page ${buf.cur + 1}/${buf.pages.length}`
    + (buf.editing ? ` · EDIT ${buf.row + 1},${buf.col + 1}` : '')
    + (p.raw ? ' · captured' : '');
}

/** Open the metadata form. The BODY comes from the editor buffer (§8.4.1) —
 *  there is no text box here, because composing is the editor's job. */
/** ⚠ Upload is a two-part flow, exactly as mail send is (§8.3.2 steps 1-3): the
 *  metadata is validated first, and only then does the client transmit frames.
 *  `pendingUpload` holds the accepted metadata across that boundary, and its
 *  presence IS the upload sub-context (§4.8) — see netContext(). */
let pendingUpload: { title: string; kind: string; price: number; life: number } | null = null;
/** Frames the user has SENT into the upload, awaiting FINISH (§8.3.2 step 2). */
let outgoingUpload: ReturnType<EditorBuffer['toFrames']> = [];

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
    // ⚠ Accepting the metadata does NOT transmit anything. It enters the upload
    // sub-context (§4.8), where SEND adds frames and FINISH commits — the same
    // shape as mail composition, and for the same reason: on the wire these are
    // three separate steps (U, then the frames, then the finishing P).
    pendingUpload = meta;
    outgoingUpload = [];
    closeSubmit();
    if (!inEditor) { editorReturn = () => render(); enterEditor(); }
    setFocus('net');
    render();
    status('SEND each page of the upload, then FINISH. EDITR to compose.');
    return;
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
    edRenderer.renderDuckshoot(rows.editor.words, rows.editor.ix, buf.page().background);
    status('Editor help — any other editor command returns to the page');
  },
  EDIT: () => {
    if (buf.editing) { buf.stopEdit(); status('STOP — edit stopped, frame stored'); }
    else { buf.beginEdit(); status('EDIT — ESC stops & stores · SHIFT+ESC restores · SHIFT+TAB case · f3/f4 line · f6 colour · f7/f8 screen/border'); }
    render();
  },
  LAST: () => { status(buf.last() ? `Page ${buf.cur + 1} of ${buf.pages.length}` : 'Already at the first page'); render(); },
  NEXT: () => { status(buf.next() ? `Page ${buf.cur + 1} of ${buf.pages.length}` : 'Already at the last page'); render(); },
  // ⚠ NEW is a BLANK page; COPY duplicates. Not the same command (§8.4.1).
  NEW: () => {
    const note = buf.newPage();
    status(note ?? `New blank page — ${buf.cur + 1} of ${buf.pages.length}`, !!note);
    render();
  },
  COPY: () => {
    const note = buf.copyPage();
    status(note ?? `Copied — page ${buf.cur + 1} of ${buf.pages.length}`, !!note);
    render();
  },
  ERASE: () => { buf.erasePage(); status(`Erased — page ${buf.cur + 1} of ${buf.pages.length}`); render(); },
  GET: () => loadFile(),
  // ⚠ PUT is ONE page, STORE is the WHOLE buffer — the editor's SHOW/BUY (§8.4.1).
  PUT: () => { saveText(buf.toJSON([buf.page()]), `page-${buf.cur + 1}.json`); status('PUT — current page saved'); },
  STORE: () => { saveText(buf.toJSON(), 'editor-buffer.json'); status(`STORE — all ${buf.pages.length} page(s) saved`); },
  PRINT: () => { window.print(); },
  FREE: () => status(`${buf.free()} PAGES FREE — ${buf.pages.length} of ${buf.maxPages} used`),
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

/** ⚠ The COURIER screens are CLIENT-SIDE sub-states of Courier, not places on
 *  the server: the lookup changes nothing and the frames are our own assets. So
 *  leaving one is a local redraw back to the mailbox — DONE here must NOT send
 *  `back`, which would unwind out of mail altogether (§8.2.1).
 *
 *  There are TWO of them and they are different frames: the ID screen (§A.10)
 *  and the SEND screen (§A.11), which carries FROM/DATE/TIME/SUBJECT/TO. */
type Courier =
  | { kind: 'id'; lines: { text: string; colour: number }[] }
  | { kind: 'send'; subject: string; to: { id: string; name: string | null }[] };
let courier: Courier | null = null;

const C_BLUE = 6, C_BLACK = 0;

/** Write text into a copied grid at (row, col). */
function put(cells: Cell[], row: number, col: number, text: string, fg: number, bg: number): void {
  const t = text.toUpperCase();
  for (let i = 0; i < t.length && col + i < 40; i++) {
    const b = t.charCodeAt(i) & 0xFF;
    const sc = b >= 0x40 && b <= 0x5F ? b & 0x1F : (b >= 0x20 && b <= 0x3F ? b : 0x20);
    cells[row * 40 + col + i] = { g: sc, fg, bg, rv: 0 };
  }
}

function drawCourier(): void {
  if (!courier) return;
  const f = courier.kind === 'send' ? assets.courierSend : assets.courier;
  if (!f) return;
  const cells = f.cells.map((c) => ({ ...c }));

  if (courier.kind === 'id') {
    // Five result rows against the frame's ':' slots (§A.10): ID from column 3,
    // the frame's own colon at column 12, the name after it.
    courier.lines.slice(0, 5).forEach((l, i) => put(cells, 6 + i, 3, l.text, l.colour, f.background));
  } else {
    // §A.11 field positions: values sit one space past each label.
    put(cells, 6, 10, account?.user ?? '', C_BLUE, f.background);
    put(cells, 7, 10, accountName, C_BLUE, f.background);
    const now = new Date();
    const p2 = (n: number): string => String(n).padStart(2, '0');
    put(cells, 9, 10, `${p2(now.getDate())}-${p2(now.getMonth() + 1)}-${p2(now.getFullYear() % 100)}`, C_BLUE, f.background);
    put(cells, 10, 10, `${p2(now.getHours())}:${p2(now.getMinutes())}`, C_BLUE, f.background);
    put(cells, 12, 13, courier.subject, C_BLUE, f.background);
    // ⚠ Recipients show their looked-up NAME beside the ID, exactly as the ID
    // screen does (§8.2.1) — the name is how the sender confirms they have the
    // right person before committing. Same colours: blue found, black not.
    courier.to.slice(0, 5).forEach((r, i) => {
      put(cells, 16 + i, 3, r.id, C_BLUE, f.background);
      if (r.name === null) put(cells, 16 + i, 14, '*** NO SUCH USER ***', C_BLACK, f.background);
      else if (r.name) put(cells, 16 + i, 14, r.name, C_BLUE, f.background);
    });
  }
  renderer.renderGrid(cells, f.background);
  renderer.setBorder(f.border);
}

/** ID — look up to five IDs and show each one's real name (§8.2.1).
 *  Results are a PRESS ANY KEY screen, not a duckshoot: there is nothing to
 *  choose, only something to read. Any key returns to the mailbox. */
async function idCheck(): Promise<void> {
  courier = { kind: 'id', lines: [] };
  render();
  const r = await ask('ID TO CHECK?', Array.from({ length: 5 }, (_, i) => ({ label: `ID ${i + 1}`, maxlength: 8 })));
  if (!r) { courier = null; render(); return; }
  const ids = r.filter(Boolean);
  if (!ids.length) { courier = null; render(); return; }

  const reply = await request({ type: 'idlookup', ids });
  const users = (reply as { users?: { id: string; name: string | null }[] }).users ?? [];
  // ⚠ Colours are normative (§8.2.1): the ID and a found name are BLUE; the
  // not-found marker is BLACK, so a failed lookup reads differently at a glance.
  courier = {
    kind: 'id',
    lines: ids.map((id) => {
      const u = users.find((x) => x.id.trim().toUpperCase() === id.toUpperCase());
      return u?.name
        ? { text: `${id.padEnd(8)} : ${u.name}`, colour: C_BLUE }
        : { text: `${id.padEnd(8)} : *** NO SUCH USER ***`, colour: C_BLACK };
    }),
  };
  awaitingKey = true;
  render();
  status(`${users.filter((u) => u.name).length} of ${ids.length} ID(s) known — press any key`);
}

/** SEND — subject, then up to five destination IDs, each VALIDATED before the
 *  editor's frames go anywhere (§8.2). The original asks SUBJECT?, then
 *  DESTINATION ID? up to five times, then OKAY? to confirm. */
/** Recipients and subject, held between the two halves of the flow. */
let pendingMail: { subject: string; ids: string[] } | null = null;
/** Frames the user has SENT into the message, awaiting FINISH (§8.2.1). */
let outgoing: ReturnType<EditorBuffer['toFrames']> = [];
/** A PRESS ANY KEY screen is showing; the next key dismisses it (§4.8). */
let awaitingKey = false;
/** SHOW is pulling a message's frames (§8.2). While this is set, the mailbox
 *  listing that ends the download must NOT be rendered — see showMail. */
let mailDownloading = false;
/** The listing held back by that download, applied on the next keypress. */
let pendingMailListing: ServerMsg | null = null;
/** Recipients of the message in flight, for the delivery confirmation. */
let sentTo = '';

/** The message-composition commands (§8.2.1) — a distinct context reached once
 *  the subject and recipients are accepted. */
const courierActions: Record<string, () => void> = {
  // SEND transmits the frames one at a time, as the original does; FINISH ends
  // the message. Two commands, two jobs — not one "send it all" button.
  SEND: () => {
    outgoing.push(buf.toFrames()[buf.cur]);
    status(`Page ${buf.cur + 1} added — ${outgoing.length} frame(s) in the message. FINISH to send.`);
  },
  FINISH: () => {
    if (!pendingMail) return;
    if (!outgoing.length) { status('Nothing sent yet — SEND at least one frame first', true); return; }
    gw.send({ type: 'mail.send', to: pendingMail.ids, subject: pendingMail.subject, frames: outgoing });
    submitMode = 'mail'; submitting = true;
    // Name the recipients in the confirmation: mail lands in THEIR mailbox, not
    // the sender's, so "sent" with no addressee reads as "nothing happened".
    sentTo = pendingMail.ids.join(', ');
    status(`SENDING ${outgoing.length} frame(s) to ${sentTo}…`);
    pendingMail = null; outgoing = []; courier = null;
    gw.send({ type: 'mail.list' });          // back to the mailbox
  },
  LAST: () => { buf.last(); render(); status(`Frame ${buf.cur + 1} of ${buf.pages.length}`); },
  NEXT: () => { buf.next(); render(); status(`Frame ${buf.cur + 1} of ${buf.pages.length}`); },
  EDITR: () => {
    if (!inEditor) { editorReturn = () => render(); enterEditor(); }
    setFocus('editor');
  },
};

/** The upload sub-context (§4.8, §8.3.2) — `SEND`, `LOAD`, `GET`, `FINISH`.
 *
 *  ⚠ These are §4.7's commands with §4.7's meanings, not upload-specific
 *  inventions: `GET` loads editor frames from local storage (§8.4.1) and `LOAD`
 *  reads a saved page back into view (`SAVE`'s inverse). They are offered here
 *  because an upload is where a user reaches for stored material. */
const uploadActions: Record<string, () => void> = {
  // One page per SEND, as the original streams one frame at a time. Not a
  // "send everything" button — the buffer may hold pages this upload is not for.
  SEND: () => {
    outgoingUpload.push(buf.toFrames()[buf.cur]);
    status(`Page ${buf.cur + 1} added — ${outgoingUpload.length} page(s) in the upload. FINISH to commit.`);
  },
  FINISH: () => {
    if (!pendingUpload) return;
    if (!outgoingUpload.length) { status('Nothing sent yet — SEND at least one page first', true); return; }
    gw.send({ type: 'upload', ...pendingUpload, frames: outgoingUpload });
    submitMode = 'upload'; submitting = true;
    // ⚠ "The exchange completed" is not proof of success: a full directory
    // swallows the page silently (§8.3.2). The refreshed listing is the proof,
    // which is why the result of an upload is the directory, not an ack.
    status(`Uploading ${outgoingUpload.length} page(s) as "${pendingUpload.title}" — check the listing`);
    pendingUpload = null; outgoingUpload = [];
  },
  GET: () => loadFile(),
  LOAD: () => status('LOAD is a client feature — not implemented in this reference client'),
};

async function sendMail(): Promise<void> {
  // ⚠ An empty buffer must NOT block the attempt. Addressing a message before
  // writing it is a normal order of work — the user can compose once focus
  // lands in the editor, then run SEND again to transmit (§8.2.1).
  courier = { kind: 'send', subject: '', to: [] };
  render();
  const subj = await ask('SUBJECT?', [{ label: 'subject', maxlength: 16 }]);
  if (!subj?.[0]) { courier = null; render(); return; }
  courier = { kind: 'send', subject: subj[0], to: [] };
  render();   // subject appears on the envelope before the IDs are asked for

  const dest = await ask('DESTINATION ID?', Array.from({ length: 5 }, (_, i) => ({ label: `ID ${i + 1}`, maxlength: 8 })));
  if (!dest) { courier = null; render(); return; }
  const ids = dest.filter(Boolean);
  if (!ids.length) { status('At least one recipient is required'); return; }

  // ⚠ Validate BEFORE sending: the server accepts unknown IDs silently, so an
  // unchecked typo becomes mail that is never delivered and never reported.
  const reply = await request({ type: 'idlookup', ids });
  const users = (reply as { users?: { id: string; name: string | null }[] }).users ?? [];
  const resolved = ids.map((id) => ({
    id,
    name: users.find((u) => u.id.trim().toUpperCase() === id.toUpperCase())?.name ?? null,
  }));
  const bad = resolved.filter((r) => !r.name);
  courier = { kind: 'send', subject: subj[0], to: resolved };
  render();
  if (bad.length) { status(`Unknown ID(s): ${bad.map((b) => b.id).join(', ')} — nothing sent`, true); return; }

  // ⚠ "OKAY? " ($AFF7) — the original confirms the completed envelope before
  // going any further, with the names on screen so the user can check them.
  if (!await askConfirm('OKAY?')) { courier = null; render(); return; }

  // Accepted: this becomes the message-composition context (§8.2.2). The user
  // pages the editor with LAST/NEXT, SENDs each frame, and FINISHes.
  pendingMail = { subject: subj[0], ids };
  outgoing = [];
  if (!inEditor) { editorReturn = () => render(); enterEditor(); }
  setFocus('net');
  render();
  status('SEND each frame of the message, then FINISH. EDITR to compose.');
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

/** ⚠ How long each frame stays on screen during a multi-frame download.
 *
 *  This is DELIBERATE PACING, not a throttle. On the original, a 1200-baud line
 *  took seconds to paint a frame, so the user watched the message arrive one
 *  page at a time. Over TCP the whole thing lands in one flash and reads as
 *  "only the last frame was sent" — the frames really are all captured, but
 *  nothing on screen says so. Restoring the beat restores the meaning. */
const FRAME_DWELL_MS = 500;

const dwell = (): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, FRAME_DWELL_MS));

/** `ALL` (§4.7) — read the REST of a multi-frame page in one gesture: repeat
 *  the paging command until the reply stops being a frame. Paced like a mail
 *  download, and for the same reason.
 *
 *  Unlike a mail download this ends in the DIRECTORY, not `PRESS ANY KEY` —
 *  running past the last frame of content lands you back in the listing, which
 *  is what the original does (§6.5). So the terminating reply renders normally
 *  and nothing is held back. */
async function readAll(): Promise<void> {
  let reply = await request({ type: 'more' });
  let frames = 1;
  while (reply.type === 'frame') {
    frames++;
    status(`ALL — frame ${frames}…`);
    await dwell();
    reply = await request({ type: 'more' });
  }
}

/** ⚠ SHOW in Courier is not "open the message" — it behaves like `ALL` (§8.2):
 *  it pulls EVERY frame of the message as fast as it can, then stops on
 *  `PRESS ANY KEY`. There is no duckshoot while it runs and none at the end.
 *
 *  The point is the editor. Frames stream into the buffer as they arrive
 *  (§8.4.2), so the user can hang up and read their mail offline — which is
 *  what the whole download-it-all gesture was FOR on a metered phone line.
 *
 *  The wire is already this shape: `D`+index gives frame 0, bare `D` advances,
 *  and after the last frame the server clears the message and answers with the
 *  mailbox — so the loop terminates on "the reply stopped being a frame",
 *  exactly as §4.7 defines ALL. */
async function showMail(index: number): Promise<void> {
  // Each frame reply flows through onMessage on its way here, which renders it
  // and captures it — the download is visible, as it was on the C64.
  mailDownloading = true;
  let reply = await request({ type: 'mail.read', index });
  let frames = 0;
  while (reply.type === 'frame') {
    frames++;
    status(`Downloading frame ${frames}…`);
    await dwell();
    reply = await request({ type: 'more' });
  }
  mailDownloading = false;
  if (reply.type === 'error') {
    render();
    status(`Could not read the message: ${(reply as { message?: string }).message ?? ''}`, true);
    return;
  }
  // ⚠ The reply that ENDED the loop is the mailbox listing. Hold it back until
  // the user presses a key: rendering it here would wipe the last frame off the
  // screen the instant it arrived, leaving nothing to read.
  pendingMailListing = reply;
  awaitingKey = true;
  render();
  status(`${frames} frame(s) — now in the editor, readable offline. Press any key.`);
}

const actions: Record<string, () => void> = {
  // In the mailbox, SHOW reads the highlighted message (§8.2); otherwise it opens the entry.
  // SHOW refuses a paid page — the user must go through BUY (§8.6.4).
  SHOW: () => {
    const e = curEntry(); if (!e) return;
    if (dir?.context === 'mail') { void showMail(e.index); return; }
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
    if (courier) { courier = null; pendingMail = null; outgoing = []; render(); status('Back to the mailbox'); return; }
    // ⚠ Leaving Courier forgets the mail row's position, so re-entering starts
    // on SEND again (§4.9.4) — mail is entered to do something, not resumed.
    delete lastCommand.mail; delete lastCommand.mailFrame;
    // ⚠ ONE command, not a sequence. DONE is `N` on the wire (§4.8): the
    // server clears mail mode and returns the directory the user came from.
    // This used to fire `back` repeatedly and watch for mail mode to clear —
    // which reaches the same place, because `B` unwinds one level per press,
    // but it is a workaround for a command that already exists.
    gw.send({ type: 'mail.done' });
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
  // ⚠ ALL is NOT MORE. It reads the REST of a multi-frame page in one gesture
  // (§4.7) — repeat the paging command until the reply stops being a frame.
  // Sending a single `more` here made ALL a synonym for MORE: same bytes, same
  // one-frame advance, no way for the user to tell them apart. That is exactly
  // the collapse §4.7's closed vocabulary forbids, and it is invisible because
  // both "work".
  ALL: () => { void readAll(); },
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

type Context = 'idle' | 'welcome' | 'directory' | 'frame' | 'mail' | 'mailFrame'
  | 'courierSend' | 'upload' | 'editor' | 'partyline';

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
  // ⚠ Empty, and NOT an oversight. Reading a mail message has NO duckshoot: in
  // Courier, SHOW behaves like ALL — it pulls every frame of the message and
  // ends on PRESS ANY KEY (§8.2), so there is nothing to choose while it runs
  // and nothing to choose at the end. Any key returns to the mailbox. Offering
  // the mail row here would imply the message can be paged command-by-command,
  // which is not how Courier reads mail.
  mailFrame: [],
  // Message composition (§8.2.1), reached once subject and recipients are
  // accepted. SEND adds a frame, FINISH transmits — distinct commands.
  courierSend: ['SEND', 'FINISH', 'LAST', 'NEXT', 'EDITR'],
  // The upload sub-context (§8.3.2), entered once the title/type/price/life are
  // accepted. Same shape as composition: SEND adds a page, FINISH commits.
  upload:      ['SEND', 'LOAD', 'GET', 'FINISH'],
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
  if (!connected) return 'idle';      // no session, no row (§8.4.2)
  if (inParty) return 'partyline';
  if (courier?.kind === 'send' && pendingMail) return 'courierSend';
  if (pendingUpload) return 'upload';
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

/** ⚠ `welcome` and `directory` share one remembered position, because §4.8
 *  gives them the SAME row — the welcome frame "carries the directory row". A
 *  user who centres SHOW on the welcome screen and then enters a directory has
 *  not changed rows, so the row must not jump back to HELP under them. */
function rowMemoryKey(ctx: Context): Context {
  return ctx === 'welcome' ? 'directory' : ctx;
}

function rememberRow(pane: Pane): void {
  const r = rows[pane];
  const ctx = pane === 'editor' ? 'editor' : netContext();
  if (r.words[r.ix]) lastCommand[rowMemoryKey(ctx)] = r.words[r.ix];
}

function tableFor(ctx: Context): Record<string, () => void> {
  if (ctx === 'editor') return editorActions;
  if (ctx === 'courierSend') return courierActions;
  if (ctx === 'upload') return uploadActions;
  return actions;
}

function buildRow(ctx: Context): string[] {
  const table = tableFor(ctx);
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
/** The context the net row was last built for, so a REBUILD can be told apart
 *  from a context CHANGE. */
let lastNetCtx: Context | null = null;

function updateBar(): void {
  const nctx = netContext();
  // ⚠ The word the row is currently on, captured BEFORE the rebuild.
  //
  // updateBar runs on every render, and a command that leaves the context
  // unchanged — SHOW on a `D+` entry, which is inert and answers with the same
  // listing (§4.7) — still triggers one. Consulting only `lastCommand` was not
  // enough: any path that rebuilds without having gone through duckCommit lost
  // the position and snapped back to HELP. Within a context the row simply
  // stays where it is; `lastCommand` is for RETURNING to a context later
  // (§4.9.4), which is a different question.
  const current = rows.net.words[rows.net.ix];
  rows.net.words = buildRow(nctx);
  const remembered = lastCommand[rowMemoryKey(nctx)];
  const wanted = nctx === lastNetCtx ? (current ?? remembered) : remembered;
  const keep = rows.net.words.indexOf(wanted ?? '');
  rows.net.ix = rows.net.words.length ? (keep >= 0 ? keep : 0) : 0;
  lastNetCtx = nctx;

  // A single-frame page has NO duckshoot — just a prompt (§4.8/§4.9). The ID
  // results screen is the same shape: something to read, nothing to choose.
  if (awaitingKey || (nctx === 'frame' && frame && !frame.morePages))
    renderer?.renderPrompt('PRESS ANY KEY', netBackground());
  else renderer?.renderDuckshoot(rows.net.words, rows.net.ix, netBackground());

  if (inEditor) {
    rows.editor.words = buildRow('editor');
    const keepE = rows.editor.words.indexOf(lastCommand.editor ?? '');
    rows.editor.ix = keepE >= 0 ? keepE : rows.editor.ix;
    edRenderer?.renderDuckshoot(rows.editor.words, rows.editor.ix, buf.page().background);
  }

  $('netMeta').textContent = mode === 'idle' ? 'not connected' : nctx;
  $('hint').textContent = focusPane === 'editor'
    ? 'Editor focused · ←/→ scroll the row · Enter runs it · EDIT then type · ESC stops editing'
    : '↑/↓ highlight an entry · ←/→ scroll the row · Enter runs it · F7/F8 cycle the right column';
}

/** The background of whatever the pane is currently showing — the duckshoot and
 *  the PRESS ANY KEY prompt take their colours from it (§4.9.3): the row is the
 *  contrast colour with the text knocked out in the background, so it inverts
 *  over a dark page instead of staying a fixed black and white. */
function netBackground(): number {
  if (mode === 'frame' && frame) return frame.background;
  return 15;                       // the directory template's (§7.7/§A.6)
}

/** Scroll the FOCUSED pane's row; the selection stays in the centre (§4.9.6). */
function duckScroll(delta: number): void {
  const r = rows[focusPane];
  if (!r.words.length) return;
  r.ix = ((r.ix + delta) % r.words.length + r.words.length) % r.words.length;
  rememberRow(focusPane);   // where the user leaves the row is where it returns
  focusPane === 'editor'
    ? edRenderer.renderDuckshoot(r.words, r.ix, buf.page().background)
    : renderer.renderDuckshoot(r.words, r.ix, netBackground());
}

/** Commit the centred command — a distinct action from scrolling (§4.9.6). */
function duckCommit(): void {
  const r = rows[focusPane];
  const name = r.words[r.ix];
  const table = tableFor(focusPane === 'editor' ? 'editor' : netContext());
  // Record BEFORE running it: the command may change context (SHOW leaves the
  // directory), and this row's position must be captured against the context
  // the user was actually in.
  rememberRow(focusPane);
  if (name && table[name]) table[name]();
}

/** The session has ended — by LEAVE, by the server closing, or by a dropped
 *  socket. Put the client back in a state it can reconnect FROM.
 *
 *  ⚠ `connect` is disabled while connected and nothing used to re-enable it, so
 *  LEAVE left the user staring at the goodbye frame with a greyed-out button and
 *  no way back in short of reloading. The goodbye frame stays up — it is meant
 *  to be read — but the session is over, so the command row empties with it. */
function endSession(msg: string): void {
  connected = false;
  account = null;
  inMail = false;
  courier = null;
  pendingMail = null;
  pendingUpload = null;
  mailDownloading = false;
  pendingMailListing = null;
  setChatVisible(false);
  inParty = false;
  $<HTMLButtonElement>('connect').disabled = false;
  $('credit').textContent = '';
  render();
  status(msg + ' Press Connect to log in again.');
}

/** Turn whatever the user typed into the two base URLs the client needs.
 *
 *  ⚠ The field asks for a SERVER, not a URL. `ws://` is transport trivia the
 *  user has no reason to know, and a missing scheme or port is the obvious
 *  mistake — so accept the lot: `connect.compunet.live`, `docker.lan`,
 *  `localhost:6404`, `https://host/api`, `ws://host:6404`.
 *
 *  Three rules, in order:
 *
 *  1. EMPTY means "the server that served this page". A hosted client should
 *     need nothing typed at all — the URL you give someone is the whole
 *     instruction — and same-origin means no CORS and no mixed content. Only
 *     applies when the page came over http(s); the desktop build is served
 *     from `compunet://`, which is not a server, so it falls back to (3).
 *  2. An EXPLICIT scheme is honoured exactly, port and path included.
 *     `https`/`wss` stay secure: quietly downgrading a TLS request to a
 *     plaintext socket is the one place being lenient could do real harm.
 *  3. A BARE host is guessed from its shape. Anything local — `localhost`,
 *     an IP, `.lan`/`.local`, or a name with no dot — gets the direct port
 *     6404 over plaintext, because that is what a dev or LAN server is. A
 *     public name gets TLS on the default port, because it will be behind a
 *     proxy or tunnel (Cloudflare only proxies a fixed set of ports, and 6404
 *     is not among them). Typing a full URL overrides the guess. */
export function resolveServer(input: string, page?: { protocol: string; host: string }): { ws: string; http: string } {
  const loc = page ?? (typeof location !== 'undefined' ? location : { protocol: '', host: '' });
  const v = input.trim().replace(/\/+$/, '');

  if (!v) {
    if (loc.protocol === 'https:' || loc.protocol === 'http:') {
      const secure = loc.protocol === 'https:';
      return { ws: `${secure ? 'wss' : 'ws'}://${loc.host}`, http: `${secure ? 'https' : 'http'}://${loc.host}` };
    }
    return resolveServer('localhost', page);      // desktop build: no page origin to borrow
  }

  const m = /^([a-z][a-z0-9+.-]*):\/\//i.exec(v);
  if (m) {
    const scheme = m[1].toLowerCase();
    const rest = v.slice(m[0].length);
    const secure = scheme === 'wss' || scheme === 'https';
    return { ws: `${secure ? 'wss' : 'ws'}://${rest}`, http: `${secure ? 'https' : 'http'}://${rest}` };
  }

  const host = v.split('/')[0].split(':')[0];
  const local = host === 'localhost' || /^\d+\.\d+\.\d+\.\d+$/.test(host)
    || /\.(lan|local|internal|test)$/i.test(host) || !host.includes('.');
  if (local) {
    const withPort = /:\d+/.test(v) ? v : `${v}:6404`;
    return { ws: `ws://${withPort}`, http: `http://${withPort}` };
  }
  return { ws: `wss://${v}`, http: `https://${v}` };
}

async function connect(): Promise<void> {
  const { ws: wsBase, http: httpBase } = resolveServer($<HTMLInputElement>('host').value);
  try {
    const { token } = await gw.login(httpBase, $<HTMLInputElement>('user').value, $<HTMLInputElement>('pass').value);
    gw.connect(
      wsBase, token, onMessage,
      () => endSession('Disconnected.'),
      () => status('WebSocket error.'),
    );
    saveSettings();          // only once the host and id are known good
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

window.addEventListener('beforeunload', flushEditor);

window.addEventListener('keydown', (e) => {
  // Don't hijack keys while the user is typing (chat, login, editor).
  const el = e.target as HTMLElement | null;
  if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) return;
  if (inParty) return;

  // A PRESS ANY KEY screen (ID results §8.2.1, a read message §8.2): any key
  // returns to the mailbox. After SHOW that means applying the listing the
  // download held back; after an ID check there is nothing to apply and the
  // mailbox is already behind the COURIER frame.
  if (awaitingKey) {
    awaitingKey = false; courier = null;
    const held = pendingMailListing;
    pendingMailListing = null;
    if (held) onMessage(held); else render();
    e.preventDefault(); return;
  }

  // ABORT — abandon an upload in progress and return without sending (§4.7).
  // ⚠ Deliberately NOT a word in the upload row: §4.8 fixes that row at four
  // commands. Abandoning is a host-environment affordance here, the same
  // reasoning §8.4.2 applies to entering the editor offline.
  if (e.key === 'Escape' && pendingUpload && focusPane === 'net') {
    pendingUpload = null; outgoingUpload = [];
    render(); status('ABORT — upload abandoned, nothing was sent');
    e.preventDefault(); return;
  }

  // ⚠ Tab is the COMMODORE key (§8.4.3) — VICE's binding, and the editor needs
  // it for SHIFT-C=. Pane focus therefore moves to Ctrl+Tab; the C64 mapping
  // wins because it is fixed by the original, while pane focus is ours to place.
  if (e.key === 'Tab' && e.ctrlKey && inEditor) {
    setFocus(focusPane === 'net' ? 'editor' : 'net');
    e.preventDefault(); return;
  }

  // --- Editor (§8.4.1) ---------------------------------------------------
  // Only when the EDITOR pane holds focus: with the Compunet pane focused the
  // editor is visible but inert, exactly as an unfocused window should be.
  if (focusPane === 'editor' && inEditor && buf.editing) {
    // f5 "on/off auto-repeat": when off, a held key does not repeat (§A.9).
    if (e.repeat && !buf.autoRepeat) { e.preventDefault(); return; }
    // RUN/STOP maps to Escape: STOP alone stops the edit and stores the frame;
    // SHIFT+STOP is the C64's RUN, which restores the original (§8.4.3).
    if (e.key === 'Escape' && e.shiftKey) {
      status(buf.restoreOriginal() ? 'RUN — frame restored to its stored state' : 'Nothing stored to restore');
      render(); e.preventDefault(); return;
    }
    if (e.key === 'Escape')     { buf.stopEdit(); status('STOP — edit stopped, frame stored'); render(); e.preventDefault(); return; }
    // SHIFT-C= "change case overwrite" — Tab is the Commodore key (§8.4.3).
    if (e.key === 'Tab' && e.shiftKey) {
      buf.lowerCase = !buf.lowerCase;
      status(`Case: ${buf.lowerCase ? 'lower/mixed' : 'upper/graphics'}`);
      e.preventDefault(); return;
    }
    if (e.key === 'F5')         { buf.autoRepeat = !buf.autoRepeat; status(`Auto-repeat ${buf.autoRepeat ? 'on' : 'off'}`); e.preventDefault(); return; }
    if (e.key === 'F6')         { buf.colourOn = !buf.colourOn; status(`Colour ${buf.colourOn ? 'on' : 'off'}`); e.preventDefault(); return; }
    // f7 / f8 — screen and border colour (§A.9)
    if (e.key === 'F7')         { buf.cycleBackground(e.shiftKey ? -1 : 1); render(); status(`Screen colour ${buf.page().background}`); e.preventDefault(); return; }
    if (e.key === 'F8')         { buf.cycleBorder(e.shiftKey ? -1 : 1); render(); status(`Border colour ${buf.page().border}`); e.preventDefault(); return; }
    if (e.key === 'ArrowUp')    { buf.moveRow(-1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowDown')  { buf.moveRow(1);  render(); e.preventDefault(); return; }
    if (e.key === 'ArrowLeft')  { buf.moveCol(-1); render(); e.preventDefault(); return; }
    if (e.key === 'ArrowRight') { buf.moveCol(1);  render(); e.preventDefault(); return; }
    if (e.key === 'Enter')      { buf.newline();   render(); e.preventDefault(); return; }
    if (e.key === 'Backspace')  { buf.backspace(); render(); e.preventDefault(); return; }
    // f3 / f4 — delete / insert a line above the cursor (§A.9, in that order)
    if (e.key === 'F3')         { buf.deleteLine(); render(); e.preventDefault(); return; }
    if (e.key === 'F4')         { buf.insertLine(); render(); e.preventDefault(); return; }
    // ⚠ CTRL + 1-8 sets the PEN colour, as on the C64 (CTRL+4 is cyan). This is
    // not an editor command — it is the machine's own colour-key mechanism, which
    // is why it appears nowhere in the editor's help frame (§A.9): the KERNAL
    // handles it and the editor simply reads the current colour. Without it the
    // editor cannot author colour at all, on a page model that is per-cell
    // colour throughout.
    if (e.ctrlKey && !e.altKey && e.key >= '1' && e.key <= '8') {
      const bank = e.shiftKey ? CTRL_COLOURS_ALT : CTRL_COLOURS;
      buf.setColour(bank[Number(e.key) - 1]);
      render();
      status(`Pen colour ${bank[Number(e.key) - 1]}`);
      e.preventDefault(); return;
    }
    // ⚠ SHIFT + letter types a GRAPHICS character, as on the C64 — the keys are
    // the primary route and the picker is only an addition (§8.4.3). PETSCII
    // $C1-$DA (shifted letters) map to screen codes $41-$5A (§5.3), which is
    // the first graphics bank. The second bank ($61-$7A) is C=+letter on the
    // original; `C=` is Tab here and cannot be chorded with a letter, so that
    // bank is reachable only through the picker.
    if (e.shiftKey && !e.ctrlKey && !e.altKey && !buf.lowerCase && /^[A-Za-z]$/.test(e.key)) {
      buf.typeGlyph(0x40 + (e.key.toUpperCase().charCodeAt(0) - 0x40));
      render(); e.preventDefault(); return;
    }
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


// --- Persistence (§8.4.2) ---------------------------------------------------
//
// ⚠ The editor buffer MUST survive the client closing, not merely the
// connection. §8.4 requires the editor to work offline so a user can compose,
// hang up and upload later; if the buffer died with the window that would only
// hold WITHIN a session, which is not the feature. The original did not do this
// — a C64's RAM went with the power, which is what PUT and STORE were for — so
// this is a deliberate modern requirement, not reconstructed behaviour.
//
// Settings are a convenience by comparison: losing them costs retyping, not
// work, so they persist on a successful connect only. A host or user id that
// failed is not worth remembering.

const KEY_SETTINGS = 'compunet:settings';
const KEY_EDITOR = 'compunet:editor';
const KEY_LIMIT = 'compunet:pageLimit';

/** Never store the password. Plaintext in localStorage is readable by anything
 *  running in the renderer; "remember me" wants a server-issued token with an
 *  expiry, which is a different piece of work. */
interface Settings { host?: string; user?: string }

function loadSettings(): void {
  try {
    const raw = localStorage.getItem(KEY_SETTINGS);
    if (raw) {
      const st = JSON.parse(raw) as Settings;
      if (st.host) $<HTMLInputElement>('host').value = st.host;
      // ⚠ A BLANK host is meaningful — "the server that served this page" — so
      // a stored blank is honoured rather than treated as "nothing saved".
      else if ('host' in st) $<HTMLInputElement>('host').value = '';
      if (st.user) $<HTMLInputElement>('user').value = st.user;
    }
    const lim = parseInt(localStorage.getItem(KEY_LIMIT) ?? '', 10);
    if (lim > 0) buf.maxPages = lim;
  } catch { /* unreadable settings are not worth failing over */ }
}

function saveSettings(): void {
  try {
    localStorage.setItem(KEY_SETTINGS, JSON.stringify({
      host: $<HTMLInputElement>('host').value.trim(),
      user: $<HTMLInputElement>('user').value.trim(),
    }));
  } catch { /* quota or private mode — the session still works */ }
}

/** ⚠ Debounced, and also flushed on unload. Capture during a mail download can
 *  add pages faster than a user types, and a crash mid-read should not lose the
 *  message — the download exists precisely so mail survives hanging up. */
let saveTimer: number | undefined;
function persistEditor(): void {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(flushEditor, 1000) as unknown as number;
}

function flushEditor(): void {
  clearTimeout(saveTimer);
  try {
    localStorage.setItem(KEY_EDITOR, buf.toJSON());
  } catch {
    // ⚠ Do NOT fail silently. §8.4.2's point is that a user believing their
    // pages are kept when they are not is the failure worth preventing.
    status('Editor could not be saved — storage is full. STORE to a file.', true);
  }
}

function restoreEditor(): void {
  const raw = localStorage.getItem(KEY_EDITOR);
  if (!raw) return;
  try {
    const n = buf.load(raw);
    status(`Editor restored — ${n} page(s). STORE keeps a copy as a file.`);
  } catch {
    // Corrupt or from an incompatible build: start clean rather than refuse to
    // boot, but say so, because the pages are gone.
    localStorage.removeItem(KEY_EDITOR);
    status('Saved editor pages could not be read — starting with a blank page.', true);
  }
}

/** The colour and glyph pickers (§8.4.3).
 *
 *  ⚠ These are ADDITIONAL, never a replacement: every colour here is also on
 *  CTRL+digit / f7 / f8, and the SHIFT-key graphics bank is also typeable. What
 *  the pickers add is discoverability — the original's user knew the sixteen
 *  colours and the graphics keyboard by heart, and a new one does not — plus the
 *  one bank with no key route at all (C=+letter, since `C=` is Tab here and
 *  cannot be chorded with a letter).
 *
 *  They are pane furniture, NOT commands: §8.4.1's fourteen are a closed set, so
 *  nothing here may appear in the editor's row. */
function buildEditorTools(): void {
  // --- buffer size (§8.4.2) -------------------------------------------------
  // ⚠ Clamped at MIN_PAGES. The limit is the user's to choose, but below the
  // original's 15 the client would fail work a C64 could do, so that floor is
  // not offered. 50 is the default because this client captures every page
  // viewed: fifteen is six mail messages, and past that the oldest is dropped.
  const limitInput = $<HTMLInputElement>('edPageLimit');
  const showBuffer = (): void => {
    $('edBufferState').textContent = `${buf.pages.length} used · ${buf.free()} free`;
  };
  limitInput.value = String(buf.maxPages);
  limitInput.onchange = () => {
    const n = Math.max(MIN_PAGES, parseInt(limitInput.value, 10) || DEFAULT_MAX_PAGES);
    limitInput.value = String(n);
    buf.maxPages = n;
    try { localStorage.setItem(KEY_LIMIT, String(n)); } catch { /* not fatal */ }
    // Lowering the limit does not discard anything now — the buffer trims
    // itself as pages are added, so nothing is lost by changing your mind.
    showBuffer();
    status(`Editor holds ${n} pages`);
  };
  buf.onChange = () => { persistEditor(); showBuffer(); };
  showBuffer();

  const swatches = $('edSwatches');
  const target = () => $<HTMLSelectElement>('edTarget').value;

  const paint = (): void => {
    // Show which colour is current for whatever the dropdown is pointing at.
    const p = buf.page();
    const cur = target() === 'pen' ? p.colour : target() === 'screen' ? p.background : p.border;
    [...swatches.children].forEach((el, i) => el.classList.toggle('on', i === cur));
  };

  assets.palette.forEach((css, i) => {
    const b = document.createElement('button');
    b.className = 'swatch';
    b.style.background = css;
    b.title = `Colour ${i}`;
    b.onclick = () => {
      if (target() === 'pen') buf.setColour(i);
      else if (target() === 'screen') buf.setBackground(i);
      else buf.setBorder(i);
      paint();
      renderEditor();
      status(`${target()} colour ${i}`);
    };
    swatches.appendChild(b);
  });
  $<HTMLSelectElement>('edTarget').onchange = paint;

  // --- glyphs ---------------------------------------------------------------
  const BANKS: Record<string, [number, number]> = {
    shift:     [0x41, 0x5A],   // SHIFT + letter  (§5.3)
    commodore: [0x61, 0x7A],   // C= + letter — no key route here, picker only
    upper:     [0x01, 0x3F],   // A-Z, digits and punctuation
    lower:     [0x81, 0xBF],   // the lowercase/mixed set
  };
  const glyphs = $('edGlyphs');

  const drawBank = (): void => {
    const [lo, hi] = BANKS[$<HTMLSelectElement>('edBank').value];
    glyphs.replaceChildren();
    for (let code = lo; code <= hi; code++) {
      const b = document.createElement('button');
      b.className = 'glyph';
      b.title = `Screen code $${code.toString(16).toUpperCase().padStart(2, '0')}`;
      // Render the glyph itself from the C64 font, so the picker shows the
      // actual character rather than a name nobody knows.
      const c = document.createElement('canvas');
      c.width = c.height = 8;
      const cx = c.getContext('2d');
      if (cx) {
        const bmp = assets.font[code] || assets.font[0x20];
        cx.fillStyle = '#000'; cx.fillRect(0, 0, 8, 8);
        cx.fillStyle = '#fff';
        bmp.forEach((byte, y) => {
          for (let x = 0; x < 8; x++) if ((byte >> (7 - x)) & 1) cx.fillRect(x, y, 1, 1);
        });
        b.style.backgroundImage = `url(${c.toDataURL()})`;
        b.style.backgroundSize = '16px 16px';
        b.style.backgroundRepeat = 'no-repeat';
        b.style.backgroundPosition = 'center';
      }
      b.onclick = () => {
        if (!buf.editing) { status('Press EDIT first — the picker types onto the page'); return; }
        buf.typeGlyph(code);
        renderEditor();
        setFocus('editor');     // hand the keyboard straight back
      };
      glyphs.appendChild(b);
    }
  };
  $<HTMLSelectElement>('edBank').onchange = drawBank;
  drawBank();
  paint();
}

async function boot(): Promise<void> {
  assets = await (await fetch('./assets.json')).json();
  renderer = new Renderer(canvas, assets, wrap);
  edRenderer = new Renderer(edCanvas, assets, edWrap);
  $<HTMLButtonElement>('connect').onclick = connect;
  // Clicking a pane focuses it — the standard WIMP gesture (Tab also toggles).
  $('paneNet').addEventListener('mousedown', () => setFocus('net'));
  $('paneEditor').addEventListener('mousedown', () => setFocus('editor'));
  $<HTMLButtonElement>('edClose').onclick = () => leaveEditor();
  // Persistence is driven by the buffer's own change hook, so no edit path
  // has to remember to save. Subscribe BEFORE restoring, so a restore that
  // normalises anything is itself written back.
  // ⚠ Order matters. loadSettings sets the page limit; buildEditorTools reads it
  // into the control and subscribes to the buffer; restoreEditor then fires that
  // subscription, so the page count is right and its status line is the last
  // thing the user sees on a cold start.
  loadSettings();
  buildEditorTools();
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
  // ⚠ LAST, so its message survives. Restoring — or failing to restore — is the
  // most important thing the user can be told at startup, and boot's own
  // "Ready" line was overwriting it. A silent failure here is precisely the
  // case §8.4.2 exists to prevent: the user believes their pages are kept.
  restoreEditor();
}

void boot();
