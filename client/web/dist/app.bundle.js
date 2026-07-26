// src/render.ts
var COLS = 40;
var ROWS = 24;
var CELL = 8;
var RED = 2;
var BLUE = 6;
var WHITE = 1;
var TEMPLATE_BG = 15;
var DIVIDER_COL = 30;
var DUCK_CELL = {
  HELP: " HELP ",
  DIR: " DIR  ",
  SHOW: " SHOW ",
  BACK: " BACK ",
  GOTO: " GOTO ",
  UCAT: " UCAT ",
  MAIL: " MAIL ",
  ACCNT: "ACCNT ",
  SAVE: " SAVE ",
  EDITR: "EDITR ",
  LEAVE: "LEAVE ",
  PRINT: "PRINT ",
  LIFE: " LIFE ",
  BUY: " BUY  ",
  UPLD: " UPLD ",
  VOTE: " VOTE ",
  MORE: " MORE ",
  ALL: " ALL  ",
  SEND: " SEND ",
  FINISH: "FINISH",
  ABORT: "ABORT ",
  LOAD: " LOAD ",
  LAST: " LAST ",
  NEXT: " NEXT ",
  GET: " GET  ",
  DOS: " DOS  ",
  ID: "  ID  ",
  DONE: " DONE ",
  COL: " COL  "
};
function petsciiToScreencode(b) {
  if (b >= 32 && b <= 63) return b;
  if (b >= 64 && b <= 95) return b & 31;
  if (b >= 96 && b <= 127) return b & 31 | 64;
  if (b >= 160 && b <= 191) return b & 31 | 96;
  if (b >= 192 && b <= 222) return b & 127;
  if (b === 255) return 94;
  return b & 127;
}
function asciiGlyph(ch) {
  return petsciiToScreencode(ch.charCodeAt(0) & 255);
}
var Renderer = class {
  constructor(canvas2, assets2, wrap2, scale = 2) {
    this.canvas = canvas2;
    this.assets = assets2;
    this.wrap = wrap2;
    this.scale = scale;
    this.canvas.width = COLS * CELL * scale;
    this.canvas.height = (ROWS + 1) * CELL * scale;
    const ctx = canvas2.getContext("2d");
    if (!ctx) throw new Error("no 2d context");
    this.ctx = ctx;
  }
  drawGlyph(cell, col, row) {
    const bmp = this.assets.font[cell.g] || this.assets.font[32];
    const s = this.scale, px = col * CELL * s, py = row * CELL * s;
    this.ctx.fillStyle = this.assets.palette[cell.bg];
    this.ctx.fillRect(px, py, CELL * s, CELL * s);
    this.ctx.fillStyle = this.assets.palette[cell.fg];
    for (let y = 0; y < 8; y++) {
      const byte = bmp[y];
      for (let x = 0; x < 8; x++) {
        let on = byte >> 7 - x & 1;
        if (cell.rv) on ^= 1;
        if (on) this.ctx.fillRect(px + x * s, py + y * s, s, s);
      }
    }
  }
  renderGrid(cells, background) {
    this.ctx.fillStyle = this.assets.palette[background & 15];
    this.ctx.fillRect(0, 0, this.canvas.width, ROWS * CELL * this.scale);
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) this.drawGlyph(cells[r * COLS + c], c, r);
  }
  setBorder(idx) {
    this.wrap.style.background = this.assets.palette[idx & 15];
  }
  renderFrame(frame2) {
    this.renderGrid(frame2.cells, frame2.background);
    this.setBorder(frame2.border);
  }
  put(grid, row, col, text, fg, bg) {
    const t = (text || "").toUpperCase();
    for (let i = 0; i < t.length && col + i < COLS; i++) {
      if (col + i < 0) continue;
      grid[row * COLS + (col + i)] = { g: asciiGlyph(t[i]), fg, bg, rv: 0 };
    }
  }
  /** Compose the 40x24 directory screen: template chrome + overlaid entries. */
  renderDirectory(dir2, sel2, colIdx2) {
    const g = this.assets.template.cells.map((x) => ({ ...x }));
    if (dir2.header) {
      const h = dir2.header.cells;
      for (let r = 0; r <= 6; r++)
        for (let c = 0; c < COLS; c++) {
          const cell = h[r * COLS + c];
          if (cell.g !== 32 || cell.rv || cell.bg !== TEMPLATE_BG) g[r * COLS + c] = { ...cell };
        }
    }
    if (dir2.breadcrumb[0]) this.put(g, 7, 1, dir2.breadcrumb[0], BLUE, TEMPLATE_BG);
    if (dir2.breadcrumb[1]) this.put(g, 8, 1, dir2.breadcrumb[1], BLUE, TEMPLATE_BG);
    if (dir2.mailWaiting) this.put(g, 8, 25, "MAIL", RED, TEMPLATE_BG);
    this.put(g, 8, 31, dir2.columns[colIdx2] || "", BLUE, TEMPLATE_BG);
    dir2.entries.forEach((e, i) => {
      const row = 10 + i;
      const colour = i === 0 ? RED : BLUE;
      const selected = i === sel2;
      const fg = selected ? WHITE : colour;
      const bg = selected ? colour : TEMPLATE_BG;
      if (selected)
        for (let c = 1; c <= 38; c++) {
          if (c === DIVIDER_COL) continue;
          g[row * COLS + c] = { g: 32, fg: WHITE, bg: colour, rv: 0 };
        }
      if (selected) {
        const ps = String(e.page);
        this.put(g, row, 7 - ps.length, ps, fg, bg);
      }
      this.put(g, row, 8, e.title, fg, bg);
      const type = e.type + (e.size ? String(e.size) : "") + (e.hasSubdir ? "+" : "");
      this.put(g, row, 25, type, fg, bg);
      const val = e.values?.[colIdx2] || "";
      if (val) this.put(g, row, 31, val, fg, bg);
    });
    (dir2.advert || []).slice(0, 2).forEach((line, i) => {
      const col = Math.max(0, Math.floor((COLS - line.length) / 2));
      this.put(g, 22 + i, col, line, BLUE, TEMPLATE_BG);
    });
    this.renderGrid(g, TEMPLATE_BG);
    this.setBorder(this.assets.template.border);
  }
  /** The Compunet pane before a session exists. Deliberately plain: with no
   *  session there is no Compunet screen and no command row (§8.4). */
  renderIdle() {
    const g = Array.from({ length: COLS * ROWS }, () => ({ g: 32, fg: 6, bg: 0, rv: 0 }));
    const put2 = (r, t, fg) => {
      const c0 = Math.max(0, Math.floor((COLS - t.length) / 2));
      for (let i = 0; i < t.length && c0 + i < COLS; i++)
        g[r * COLS + c0 + i] = { g: asciiGlyph(t[i]), fg, bg: 0, rv: 0 };
    };
    put2(10, "COMPUNET REBORN", 14);
    put2(12, "NOT CONNECTED", 11);
    this.renderGrid(g, 0);
    this.setBorder(6);
  }
  /** Draw the editor's current page (§8.4.1).
   *  ⚠ The page is the FULL 40x24 grid — an editor page and a frame are the
   *  same thing (§8.4.2), so nothing may be reserved here for chrome. The
   *  buffer position ("page 2 of 5") belongs in the pane's own furniture, not
   *  in a row stolen from the page. */
  renderEditorPage(cells, background, border, row, col, editing) {
    const g = cells.map((c) => ({ ...c }));
    if (editing) {
      const i = row * COLS + col;
      if (g[i]) g[i] = { ...g[i], rv: g[i].rv ? 0 : 1 };
    }
    this.renderGrid(g, background);
    this.setBorder(border);
  }
  /** Draw the duckshoot on the row below the content grid (§4.9).
   *  The ROW scrolls and the CENTRE cell is the selection — words are laid out
   *  around `centre`, which always lands in the middle of the screen. */
  /** The single-frame case has no duckshoot at all — just a prompt (§4.8). */
  renderPrompt(text) {
    const s = this.scale, row = ROWS;
    this.ctx.fillStyle = this.assets.palette[0];
    this.ctx.fillRect(0, row * CELL * s, this.canvas.width, CELL * s);
    const start = Math.max(0, Math.floor((COLS - text.length) / 2));
    for (let i = 0; i < text.length && start + i < COLS; i++)
      this.drawGlyph({ g: asciiGlyph(text[i]), fg: 1, bg: 0, rv: 0 }, start + i, row);
  }
  renderDuckshoot(words, centre) {
    const s = this.scale, row = ROWS, WORD = 6, VISIBLE = 7, MID = 3;
    this.ctx.fillStyle = this.assets.palette[0];
    this.ctx.fillRect(0, row * CELL * s, this.canvas.width, CELL * s);
    if (!words.length) return;
    if (words.length === 1 && words[0] === "\0PRESSANYKEY") return;
    const startCol = Math.floor((COLS - VISIBLE * WORD) / 2);
    for (let slot = 0; slot < VISIBLE; slot++) {
      const wi = ((centre + slot - MID) % words.length + words.length) % words.length;
      const name = words[wi];
      const text = (DUCK_CELL[name] ?? name.padEnd(WORD)).slice(0, WORD);
      const selected = slot === MID;
      for (let i = 0; i < WORD; i++) {
        const col = startCol + slot * WORD + i;
        if (col < 0 || col >= COLS) continue;
        this.drawGlyph(
          { g: asciiGlyph(text[i]), fg: selected ? 0 : 1, bg: selected ? 1 : 0, rv: 0 },
          col,
          row
        );
      }
    }
  }
};

// src/gateway.ts
var Gateway = class {
  constructor() {
    this.ws = null;
  }
  /** Exchange credentials for a bearer token (spec §2). */
  async login(httpBase, user, pass) {
    const r = await fetch(httpBase + "/v1/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user, pass })
    });
    if (!r.ok) throw new Error("login failed (" + r.status + ")");
    return r.json();
  }
  /** Open the gateway and authenticate the socket with the token. */
  connect(wsBase, token, onMessage2, onClose, onError) {
    const ws = new WebSocket(wsBase + "/v1/gateway");
    this.ws = ws;
    ws.onopen = () => this.send({ type: "auth", token });
    ws.onmessage = (ev) => onMessage2(JSON.parse(ev.data));
    ws.onclose = onClose;
    ws.onerror = onError;
  }
  send(msg) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg));
  }
  close() {
    this.ws?.close();
  }
};

// src/editor.ts
var PAGE_COLS = 40;
var PAGE_ROWS = 24;
var CELLS = PAGE_COLS * PAGE_ROWS;
function blankCells(bg, fg) {
  return Array.from({ length: CELLS }, () => ({ g: 32, fg, bg, rv: 0 }));
}
function blankPage() {
  return { cells: blankCells(0, 1), border: 6, background: 0, colour: 1 };
}
var CAPACITY = 12 * CELLS;
var MAX_PAGES = 15;
function charToGlyph(ch, lower) {
  const c = ch.charCodeAt(0) & 255;
  if (lower) {
    if (c >= 97 && c <= 122) return 128 + (c - 96);
    if (c >= 65 && c <= 90) return 128 + c;
    if (c >= 32 && c <= 63) return 128 + c;
    return 128 + 32;
  }
  const b = ch.toUpperCase().charCodeAt(0) & 255;
  if (b >= 32 && b <= 63) return b;
  if (b >= 64 && b <= 95) return b & 31;
  return 32;
}
function frameToPage(f) {
  return {
    cells: f.cells.map((c) => ({ ...c })),
    border: f.border,
    background: f.background,
    colour: 1,
    raw: f.raw
  };
}
var EditorBuffer = class {
  constructor() {
    this.pages = [blankPage()];
    this.cur = 0;
    /** cursor within the current page, only meaningful in EDIT mode */
    this.row = 0;
    this.col = 0;
    this.editing = false;
    // --- editing modes, from the editor's own help frame (§A.9 / §8.4.3) ---
    /** SHIFT-C= "change case overwrite": which set typed text goes into. */
    this.lowerCase = false;
    /** f6 "on/off colour": when off, typing keeps each cell's existing colour. */
    this.colourOn = true;
    /** f5 "on/off auto-repeat": when off, held keys do not repeat. */
    this.autoRepeat = true;
    /** The page as last STORED, for RUN ("restore original"). */
    this.original = null;
  }
  /** STOP — stop editing and store the frame (§A.9). */
  stopEdit() {
    this.editing = false;
    this.original = this.page().cells.map((c) => ({ ...c }));
  }
  /** RUN — restore the frame to its last stored state (§A.9). */
  restoreOriginal() {
    if (!this.original) return false;
    this.page().cells = this.original.map((c) => ({ ...c }));
    delete this.page().raw;
    return true;
  }
  /** Remember the starting state when an edit begins. */
  beginEdit() {
    this.editing = true;
    if (!this.original) this.original = this.page().cells.map((c) => ({ ...c }));
  }
  page() {
    return this.pages[this.cur];
  }
  /** Any change to a page's content invalidates its captured bytes. */
  touch() {
    delete this.page().raw;
  }
  // --- page navigation (LAST / NEXT) ---
  last() {
    if (this.cur === 0) return false;
    this.cur--;
    this.home();
    return true;
  }
  next() {
    if (this.cur >= this.pages.length - 1) return false;
    this.cur++;
    this.home();
    return true;
  }
  // --- page management (NEW / COPY / ERASE) ---
  /** NEW — a fresh BLANK page after the current one. Not COPY. */
  newPage() {
    this.pages.splice(++this.cur, 0, blankPage());
    this.home();
  }
  /** COPY — a DUPLICATE of the current page after it. Not NEW. */
  copyPage() {
    const p = this.page();
    this.pages.splice(++this.cur, 0, { ...p, cells: p.cells.map((c) => ({ ...c })) });
    this.home();
  }
  /** ERASE — remove the current page. The buffer never becomes empty. */
  erasePage() {
    this.pages.splice(this.cur, 1);
    if (!this.pages.length) this.pages.push(blankPage());
    if (this.cur >= this.pages.length) this.cur = this.pages.length - 1;
    this.home();
  }
  home() {
    this.row = 0;
    this.col = 0;
  }
  /** True while the buffer is just its initial untouched blank page. */
  isPristine() {
    return this.pages.length === 1 && this.isBlank(this.pages[0]);
  }
  isBlank(p) {
    return p.cells.every((c) => (c.g & 127) === 32 && !c.rv);
  }
  /** Append a page viewed on Compunet (§8.4.2). Returns false when the buffer
   *  is full — the original's limit was memory, and it does not silently
   *  discard. The user's current position is NOT disturbed: capture happens
   *  while they may be editing something else entirely. */
  capture(p) {
    if (this.isPristine()) {
      this.pages[0] = p;
      return true;
    }
    if (this.pages.length >= MAX_PAGES || this.free() < this.cost(p)) return false;
    this.pages.push(p);
    return true;
  }
  cost(p) {
    return p.cells.filter((c) => (c.g & 127) !== 32 || c.rv).length;
  }
  /** FREE — characters remaining, in the original's units. */
  free() {
    return Math.max(0, CAPACITY - this.pages.reduce((n, p) => n + this.cost(p), 0));
  }
  // --- editing (EDIT mode) ---
  /** Overwrite-at-cursor, as the original edits (its f6 toggles insert). */
  typeChar(ch) {
    const p = this.page();
    this.touch();
    const i = this.row * PAGE_COLS + this.col;
    const fg = this.colourOn ? p.colour : p.cells[i].fg;
    p.cells[i] = { g: charToGlyph(ch, this.lowerCase), fg, bg: p.background, rv: 0 };
    if (++this.col >= PAGE_COLS) {
      this.col = 0;
      this.moveRow(1);
    }
  }
  /** f7 / f8 — screen (background) and border colour (§A.9). */
  cycleBackground(d) {
    const p = this.page();
    p.background = ((p.background + d) % 16 + 16) % 16;
    this.touch();
  }
  cycleBorder(d) {
    const p = this.page();
    p.border = ((p.border + d) % 16 + 16) % 16;
  }
  backspace() {
    if (this.col === 0) {
      if (this.row > 0) {
        this.row--;
        this.col = PAGE_COLS - 1;
      }
      return;
    }
    this.col--;
    const p = this.page();
    this.touch();
    p.cells[this.row * PAGE_COLS + this.col] = { g: 32, fg: p.colour, bg: p.background, rv: 0 };
  }
  newline() {
    this.col = 0;
    this.moveRow(1);
  }
  moveRow(d) {
    this.row = Math.max(0, Math.min(PAGE_ROWS - 1, this.row + d));
  }
  moveCol(d) {
    this.col = Math.max(0, Math.min(PAGE_COLS - 1, this.col + d));
  }
  /** Change the colour subsequent typing uses (the original's f7/f8). */
  cycleColour(d) {
    const p = this.page();
    p.colour = ((p.colour + d) % 16 + 16) % 16;
  }
  /** DELETE/INSERT a line above the cursor (the original's f3/f4). */
  insertLine() {
    const p = this.page();
    this.touch();
    p.cells.splice(this.row * PAGE_COLS, 0, ...blankCells(p.background, p.colour).slice(0, PAGE_COLS));
    p.cells.length = CELLS;
  }
  deleteLine() {
    const p = this.page();
    this.touch();
    p.cells.splice(this.row * PAGE_COLS, PAGE_COLS);
    p.cells.push(...blankCells(p.background, p.colour).slice(0, PAGE_COLS));
  }
  // --- serialisation (GET / PUT / STORE) ---
  /** Wire form for upload / mail.send (§5.4 of the Binding-B spec).
   *  ⚠ An unedited captured page goes back as its ORIGINAL BYTES; only pages
   *  the user actually composed or altered are re-encoded from cells. */
  toFrames() {
    return this.pages.map((p) => p.raw ? { raw: p.raw } : { cells: p.cells, border: p.border, background: p.background });
  }
  /** True when nothing has been composed or captured — used to refuse an
   *  upload of an empty buffer rather than send a blank page. */
  isEmpty() {
    return this.pages.every((p) => this.isBlank(p));
  }
  toJSON(pagesOnly) {
    return JSON.stringify({ format: "compunet-editor-2", pages: pagesOnly ?? this.pages });
  }
  /** GET — replace the buffer from a previously PUT/STOREd file. */
  load(text) {
    const data = JSON.parse(text);
    if (data.format !== "compunet-editor-2" || !Array.isArray(data.pages) || !data.pages.length)
      throw new Error("not an editor file");
    this.pages = data.pages.map((p) => {
      const cells = Array.from({ length: CELLS }, (_, i) => p.cells?.[i] ? { ...p.cells[i] } : { g: 32, fg: 1, bg: p.background ?? 0, rv: 0 });
      return { cells, border: p.border ?? 6, background: p.background ?? 0, colour: p.colour ?? 1, raw: p.raw };
    });
    this.cur = 0;
    this.row = 0;
    this.col = 0;
    return this.pages.length;
  }
};

// src/main.ts
var $ = (id) => document.getElementById(id);
var canvas = $("screen");
var wrap = $("screenWrap");
var edCanvas = $("edScreen");
var edWrap = $("edWrap");
var statusEl = $("status");
var assets;
var renderer;
var edRenderer;
var gw = new Gateway();
var focusPane = "net";
var mode = "idle";
var dir = null;
var frame = null;
var sel = 0;
var colIdx = 0;
var account = null;
var accountName = "";
var isWelcome = false;
var inMail = false;
var exitingMail = false;
function status(s, bad = false) {
  statusEl.textContent = s;
  statusEl.classList.toggle("bad", bad);
}
function setFocus(p) {
  if (p === "editor" && !inEditor) return;
  focusPane = p;
  $("paneNet").classList.toggle("focused", p === "net");
  $("paneEditor").classList.toggle("focused", p === "editor");
  updateBar();
}
function render() {
  if (pendingMail && courier?.kind === "send") {
    const p = buf.page();
    renderer.renderEditorPage(p.cells, p.background, p.border, 0, 0, false);
  } else if (courier) drawCourier();
  else if (mode === "directory" && dir) renderer.renderDirectory(dir, sel, colIdx);
  else if (mode === "frame" && frame) renderer.renderFrame(frame);
  else renderer.renderIdle();
  if (inEditor) renderEditor();
  updateBar();
}
function onMessage(m) {
  const rid = m.id;
  if (typeof rid === "number" && pending.has(rid)) {
    pending.get(rid)(m);
    pending.delete(rid);
    if (m.type === "idlookup") return;
  }
  switch (m.type) {
    case "ready": {
      const r = m;
      account = r.account;
      $("credit").textContent = `${account.user} \xB7 \xA3${account.credit.toFixed(2)}`;
      if (r.welcome) {
        mode = "frame";
        frame = r.welcome;
        isWelcome = true;
        inMail = false;
      }
      render();
      status(`Welcome, ${account.user} \u2014 press DIR to enter the system`);
      break;
    }
    case "directory":
      mode = "directory";
      dir = m;
      sel = 0;
      colIdx = 0;
      isWelcome = false;
      const wasMail = inMail;
      inMail = m.context === "mail";
      if (wasMail && !inMail) {
        delete lastCommand.mail;
        delete lastCommand.mailFrame;
      }
      if (inMail) accountName = (m.breadcrumb[1] || "").trim();
      courier = null;
      render();
      if (submitting) {
        submitting = false;
        setFocus("net");
      }
      if (exitingMail) {
        if (inMail) gw.send({ type: "back" });
        else exitingMail = false;
      }
      status(`${m.title} \u2014 ${m.entries.length} entries`);
      break;
    case "frame": {
      mode = "frame";
      frame = m;
      isWelcome = false;
      render();
      if (m.goodbye) {
        status("Goodbye \u2014 disconnected.");
        gw.close();
        return;
      }
      captureViewedFrame(m);
      if (exitingMail && inMail) gw.send({ type: "back" });
      status("Reading page" + (m.morePages ? " \u2014 MORE follows" : ""));
      break;
    }
    case "download": {
      const d = m;
      status(`Download: ${d.title} \u2014 ${d.size} bytes (${d.machine})`);
      if (confirm(`Download "${d.title}" (${d.size} bytes)?`)) gw.send({ type: "download.fetch" });
      break;
    }
    case "download.data": {
      const d = m;
      saveBase64(d.bytes, (d.title || "download").replace(/\s+/g, "_").toLowerCase() + ".prg");
      status(`Saved ${d.title} (${d.size} bytes)`);
      break;
    }
    case "account":
      status(`You are ${m.creditText} in credit`);
      break;
    case "idlookup": {
      const u = m.users;
      status(u.map((x) => `${x.id} = ${x.name ?? "(unknown)"}`).join(" \xB7 ") || "No such user");
      break;
    }
    case "ack":
      if (m.of === "mail.send" && sentTo) {
        status(`Message sent to ${sentTo} \u2014 it is in THEIR mailbox, not yours.`);
        sentTo = "";
      } else status(`${m.of ?? "command"} accepted`);
      if (submitting) {
        submitting = false;
        setFocus("net");
      }
      break;
    case "partyline.entering":
      status("Joining Partyline\u2026");
      break;
    case "partyline.entered":
      setChatVisible(true);
      updateBar();
      chatLog("*** Partyline \u2014 room " + m.room + " ***");
      status("In Partyline. *help for commands, *quit to leave.");
      break;
    case "partyline":
      chatLog(m.line);
      break;
    case "partyline.left":
      setChatVisible(false);
      updateBar();
      status("Left Partyline.");
      break;
    case "error":
      status("\u26A0 " + m.code + (m.message ? ": " + m.message : ""), true);
      submitting = false;
      break;
    default:
      status("\xB7 " + m.type);
  }
}
function curEntry() {
  return dir ? dir.entries[sel] : void 0;
}
function curPrice() {
  const e = curEntry();
  if (!e || inMail) return "";
  return (e.values?.[0] ?? "").trim();
}
var buf = new EditorBuffer();
var inEditor = false;
var editorReturn = null;
var submitMode = null;
var submitting = false;
function enterEditor() {
  inEditor = true;
  buf.editing = false;
  $("paneEditor").hidden = false;
  setFocus("editor");
  render();
  status("Editor \u2014 EDIT types on the page, RETURN leaves. Page " + (buf.cur + 1) + " of " + buf.pages.length);
}
function leaveEditor() {
  inEditor = false;
  buf.editing = false;
  $("paneEditor").hidden = true;
  setFocus("net");
  if (editorReturn) {
    const f = editorReturn;
    editorReturn = null;
    f();
  } else render();
  status(mode === "idle" ? "Left the editor \u2014 the buffer is kept. Connect, then UPLD or SEND submits it." : "Left the editor. UPLD or SEND submits the buffer.");
}
function captureViewedFrame(f) {
  const wasEmpty = buf.isEmpty();
  if (!buf.capture(frameToPage(f))) {
    status("Editor buffer full \u2014 this page was not stored (use STORE, then ERASE)", true);
    return;
  }
  if (inEditor) renderEditor();
  if (wasEmpty) $("edMeta").textContent = `page ${buf.cur + 1}/${buf.pages.length}`;
}
function renderEditor() {
  const p = buf.page();
  edRenderer.renderEditorPage(p.cells, p.background, p.border, buf.row, buf.col, buf.editing);
  $("edMeta").textContent = `page ${buf.cur + 1}/${buf.pages.length}` + (buf.editing ? ` \xB7 EDIT ${buf.row + 1},${buf.col + 1}` : "") + (p.raw ? " \xB7 captured" : "");
}
var pendingUpload = null;
function openSubmit(kind) {
  submitMode = kind;
  if (!inEditor) {
    editorReturn = () => render();
    enterEditor();
  }
  setFocus("editor");
  $("submit").hidden = false;
  $("submitTitle").textContent = kind === "upload" ? `Upload ${buf.pages.length} page(s) into "${dir?.title ?? "this directory"}"` : `Send ${buf.pages.length} page(s) as mail`;
  $("edContentFields").hidden = kind !== "upload";
  $("edTo").hidden = kind !== "mail";
  $("edHint").textContent = kind === "upload" ? "Type and price are required (\xA78.3.2). Body comes from the editor buffer." : "Recipients: up to five user IDs, comma-separated.";
  $("edTitle").value = "";
  $("edTitle").focus();
}
function closeSubmit() {
  submitMode = null;
  $("submit").hidden = true;
}
function doSubmit() {
  const title = $("edTitle").value.trim();
  if (!title) {
    status("A title is required");
    return;
  }
  const frames = buf.toFrames();
  if (submitMode === "mail") {
    const to = $("edTo").value.split(",").map((x) => x.trim()).filter(Boolean);
    if (!to.length) {
      status("At least one recipient is required");
      return;
    }
    gw.send({ type: "mail.send", to, subject: title, frames });
  } else {
    const meta = {
      title,
      kind: $("edKind").value,
      price: parseFloat($("edPrice").value) || 0,
      life: parseInt($("edLife").value, 10) || 0
    };
    if (buf.isEmpty()) {
      pendingUpload = meta;
      closeSubmit();
      if (!inEditor) {
        editorReturn = () => render();
        enterEditor();
      }
      setFocus("editor");
      status(`"${title}" ready to upload \u2014 compose the page, then UPLD again`);
      return;
    }
    gw.send({ type: "upload", ...meta, frames });
    pendingUpload = null;
  }
  submitting = true;
  status(`Sending ${frames.length} page(s)\u2026`);
  closeSubmit();
}
function saveText(text, filename) {
  const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
function loadFile() {
  const inp = document.createElement("input");
  inp.type = "file";
  inp.accept = ".json,application/json";
  inp.onchange = () => {
    const f = inp.files?.[0];
    if (!f) return;
    f.text().then((t) => {
      try {
        const n = buf.load(t);
        status(`GET \u2014 loaded ${n} page(s)`);
        render();
      } catch (e) {
        status("GET failed: " + e.message);
      }
    });
  };
  inp.click();
}
var editorActions = {
  // ⚠ The EDITOR's help frame (§A.9) — a different asset from §A.8's.
  HELP: () => {
    if (!assets.editorHelp) {
      status("No editor help frame embedded");
      return;
    }
    edRenderer.renderFrame(assets.editorHelp);
    edRenderer.renderDuckshoot(rows.editor.words, rows.editor.ix);
    status("Editor help \u2014 any other editor command returns to the page");
  },
  EDIT: () => {
    if (buf.editing) {
      buf.stopEdit();
      status("STOP \u2014 edit stopped, frame stored");
    } else {
      buf.beginEdit();
      status("EDIT \u2014 ESC stops & stores \xB7 SHIFT+ESC restores \xB7 SHIFT+TAB case \xB7 f3/f4 line \xB7 f6 colour \xB7 f7/f8 screen/border");
    }
    render();
  },
  LAST: () => {
    status(buf.last() ? `Page ${buf.cur + 1} of ${buf.pages.length}` : "Already at the first page");
    render();
  },
  NEXT: () => {
    status(buf.next() ? `Page ${buf.cur + 1} of ${buf.pages.length}` : "Already at the last page");
    render();
  },
  // ⚠ NEW is a BLANK page; COPY duplicates. Not the same command (§8.4.1).
  NEW: () => {
    buf.newPage();
    status(`New blank page \u2014 ${buf.cur + 1} of ${buf.pages.length}`);
    render();
  },
  COPY: () => {
    buf.copyPage();
    status(`Copied \u2014 page ${buf.cur + 1} of ${buf.pages.length}`);
    render();
  },
  ERASE: () => {
    buf.erasePage();
    status(`Erased \u2014 page ${buf.cur + 1} of ${buf.pages.length}`);
    render();
  },
  GET: () => loadFile(),
  // ⚠ PUT is ONE page, STORE is the WHOLE buffer — the editor's SHOW/BUY (§8.4.1).
  PUT: () => {
    saveText(buf.toJSON([buf.page()]), `page-${buf.cur + 1}.json`);
    status("PUT \u2014 current page saved");
  },
  STORE: () => {
    saveText(buf.toJSON(), "editor-buffer.json");
    status(`STORE \u2014 all ${buf.pages.length} page(s) saved`);
  },
  PRINT: () => {
    window.print();
  },
  FREE: () => status(`${buf.free()} CHARS FREE \u2014 ${buf.pages.length} page(s) in the buffer`),
  RETURN: () => leaveEditor(),
  // DOS names a local filesystem facility this environment does not have. §8.4.1
  // permits disabling it; it does NOT permit renaming or removing it.
  DOS: () => status("DOS is not available in a sandboxed browser client")
};
var inParty = false;
function setChatVisible(on) {
  inParty = on;
  $("chat").hidden = !on;
  $("screenWrap").hidden = on;
  $("netTitle").textContent = on ? "Partyline" : "Compunet";
  if (on) {
    setFocus("net");
    $("chatInput").value = "";
    $("chatInput").focus();
  } else {
    $("chatLog").textContent = "";
    render();
  }
}
function chatLog(line) {
  const log = $("chatLog");
  log.textContent += (log.textContent ? "\n" : "") + line;
  log.scrollTop = log.scrollHeight;
}
function ask(title, fields) {
  return new Promise((resolve) => {
    $("askTitle").textContent = title;
    const host = $("askFields");
    host.textContent = "";
    const inputs = fields.map((f) => {
      const el = document.createElement("input");
      el.placeholder = f.label;
      el.value = f.value ?? "";
      if (f.maxlength) el.maxLength = f.maxlength;
      if (f.type) el.type = f.type;
      host.appendChild(el);
      return el;
    });
    $("ask").hidden = false;
    inputs[0]?.focus();
    const done = (v) => {
      $("ask").hidden = true;
      $("askOk").onclick = null;
      $("askCancel").onclick = null;
      host.onkeydown = null;
      resolve(v);
    };
    $("askOk").onclick = () => done(inputs.map((i) => i.value.trim()));
    $("askCancel").onclick = () => done(null);
    host.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        done(inputs.map((i) => i.value.trim()));
      }
      if (e.key === "Escape") {
        e.preventDefault();
        done(null);
      }
    };
  });
}
async function askConfirm(title) {
  return await ask(title, []) !== null;
}
var nextId = 1;
var pending = /* @__PURE__ */ new Map();
function request(msg) {
  const id = nextId++;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    gw.send({ ...msg, id });
    setTimeout(() => {
      if (pending.delete(id)) resolve({ type: "error", code: "timeout" });
    }, 1e4);
  });
}
var courier = null;
var C_BLUE = 6;
var C_BLACK = 0;
function put(cells, row, col, text, fg, bg) {
  const t = text.toUpperCase();
  for (let i = 0; i < t.length && col + i < 40; i++) {
    const b = t.charCodeAt(i) & 255;
    const sc = b >= 64 && b <= 95 ? b & 31 : b >= 32 && b <= 63 ? b : 32;
    cells[row * 40 + col + i] = { g: sc, fg, bg, rv: 0 };
  }
}
function drawCourier() {
  if (!courier) return;
  const f = courier.kind === "send" ? assets.courierSend : assets.courier;
  if (!f) return;
  const cells = f.cells.map((c) => ({ ...c }));
  if (courier.kind === "id") {
    courier.lines.slice(0, 5).forEach((l, i) => put(cells, 6 + i, 3, l.text, l.colour, f.background));
  } else {
    put(cells, 6, 10, account?.user ?? "", C_BLUE, f.background);
    put(cells, 7, 10, accountName, C_BLUE, f.background);
    const now = /* @__PURE__ */ new Date();
    const p2 = (n) => String(n).padStart(2, "0");
    put(cells, 9, 10, `${p2(now.getDate())}-${p2(now.getMonth() + 1)}-${p2(now.getFullYear() % 100)}`, C_BLUE, f.background);
    put(cells, 10, 10, `${p2(now.getHours())}:${p2(now.getMinutes())}`, C_BLUE, f.background);
    put(cells, 12, 13, courier.subject, C_BLUE, f.background);
    courier.to.slice(0, 5).forEach((r, i) => {
      put(cells, 16 + i, 3, r.id, C_BLUE, f.background);
      if (r.name === null) put(cells, 16 + i, 14, "*** NO SUCH USER ***", C_BLACK, f.background);
      else if (r.name) put(cells, 16 + i, 14, r.name, C_BLUE, f.background);
    });
  }
  renderer.renderGrid(cells, f.background);
  renderer.setBorder(f.border);
}
async function idCheck() {
  courier = { kind: "id", lines: [] };
  render();
  const r = await ask("ID TO CHECK?", Array.from({ length: 5 }, (_, i) => ({ label: `ID ${i + 1}`, maxlength: 8 })));
  if (!r) {
    courier = null;
    render();
    return;
  }
  const ids = r.filter(Boolean);
  if (!ids.length) {
    courier = null;
    render();
    return;
  }
  const reply = await request({ type: "idlookup", ids });
  const users = reply.users ?? [];
  courier = {
    kind: "id",
    lines: ids.map((id) => {
      const u = users.find((x) => x.id.trim().toUpperCase() === id.toUpperCase());
      return u?.name ? { text: `${id.padEnd(8)} : ${u.name}`, colour: C_BLUE } : { text: `${id.padEnd(8)} : *** NO SUCH USER ***`, colour: C_BLACK };
    })
  };
  awaitingKey = true;
  render();
  status(`${users.filter((u) => u.name).length} of ${ids.length} ID(s) known \u2014 press any key`);
}
var pendingMail = null;
var outgoing = [];
var awaitingKey = false;
var sentTo = "";
var courierActions = {
  // SEND transmits the frames one at a time, as the original does; FINISH ends
  // the message. Two commands, two jobs — not one "send it all" button.
  SEND: () => {
    outgoing.push(buf.toFrames()[buf.cur]);
    status(`Page ${buf.cur + 1} added \u2014 ${outgoing.length} frame(s) in the message. FINISH to send.`);
  },
  FINISH: () => {
    if (!pendingMail) return;
    if (!outgoing.length) {
      status("Nothing sent yet \u2014 SEND at least one frame first", true);
      return;
    }
    gw.send({ type: "mail.send", to: pendingMail.ids, subject: pendingMail.subject, frames: outgoing });
    submitMode = "mail";
    submitting = true;
    sentTo = pendingMail.ids.join(", ");
    status(`SENDING ${outgoing.length} frame(s) to ${sentTo}\u2026`);
    pendingMail = null;
    outgoing = [];
    courier = null;
    gw.send({ type: "mail.list" });
  },
  LAST: () => {
    buf.last();
    render();
    status(`Frame ${buf.cur + 1} of ${buf.pages.length}`);
  },
  NEXT: () => {
    buf.next();
    render();
    status(`Frame ${buf.cur + 1} of ${buf.pages.length}`);
  },
  EDITR: () => {
    if (!inEditor) {
      editorReturn = () => render();
      enterEditor();
    }
    setFocus("editor");
  }
};
async function sendMail() {
  courier = { kind: "send", subject: "", to: [] };
  render();
  const subj = await ask("SUBJECT?", [{ label: "subject", maxlength: 16 }]);
  if (!subj?.[0]) {
    courier = null;
    render();
    return;
  }
  courier = { kind: "send", subject: subj[0], to: [] };
  render();
  const dest = await ask("DESTINATION ID?", Array.from({ length: 5 }, (_, i) => ({ label: `ID ${i + 1}`, maxlength: 8 })));
  if (!dest) {
    courier = null;
    render();
    return;
  }
  const ids = dest.filter(Boolean);
  if (!ids.length) {
    status("At least one recipient is required");
    return;
  }
  const reply = await request({ type: "idlookup", ids });
  const users = reply.users ?? [];
  const resolved = ids.map((id) => ({
    id,
    name: users.find((u) => u.id.trim().toUpperCase() === id.toUpperCase())?.name ?? null
  }));
  const bad = resolved.filter((r) => !r.name);
  courier = { kind: "send", subject: subj[0], to: resolved };
  render();
  if (bad.length) {
    status(`Unknown ID(s): ${bad.map((b) => b.id).join(", ")} \u2014 nothing sent`, true);
    return;
  }
  if (!await askConfirm("OKAY?")) {
    courier = null;
    render();
    return;
  }
  pendingMail = { subject: subj[0], ids };
  outgoing = [];
  if (!inEditor) {
    editorReturn = () => render();
    enterEditor();
  }
  setFocus("net");
  render();
  status("SEND each frame of the message, then FINISH. EDITR to compose.");
}
function saveBase64(b64, filename) {
  const bin = atob(b64);
  const buf2 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf2[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([buf2], { type: "application/octet-stream" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
var actions = {
  // In the mailbox, SHOW reads the highlighted message (§8.2); otherwise it opens the entry.
  // SHOW refuses a paid page — the user must go through BUY (§8.6.4).
  SHOW: () => {
    const e = curEntry();
    if (!e) return;
    if (dir?.context === "mail") {
      gw.send({ type: "mail.read", index: e.index });
      return;
    }
    if (curPrice()) {
      status("PLEASE USE BUY");
      return;
    }
    gw.send({ type: "open", page: e.page });
  },
  // BUY is the same wire command as SHOW, plus the price confirmation (§8.6.4).
  // The server deducts the credit and allows overdraft; we never check locally.
  BUY: () => {
    const e = curEntry();
    if (!e) return;
    const price = curPrice();
    if (!price) {
      gw.send({ type: "open", page: e.page });
      return;
    }
    void askConfirm(`BUY FOR ${price} - SURE?`).then((ok) => {
      if (ok) gw.send({ type: "open", page: e.page });
    });
  },
  // In a directory: enter the highlighted entry. On the welcome frame (no directory
  // context): DIR reaches the root — a bare `dir` (§4.7 / Binding-B schema).
  DIR: () => {
    if (inMail) {
      gw.send({ type: "back" });
      return;
    }
    if (mode === "directory" && curEntry()) gw.send({ type: "enter", page: curEntry().page });
    else gw.send({ type: "dir" });
  },
  BACK: () => gw.send({ type: "back" }),
  // DONE returns the user where they were before Courier. `back` unwinds one
  // level at a time (message -> listing -> page -> out), so keep going until the
  // session is actually out of mail (§4.8).
  // DONE from the COURIER screen (ID / SEND) returns to the MAILBOX — that
  // screen is client-side, so this is a redraw, not a wire command (§8.2.1).
  // Only from the mailbox itself does DONE leave Courier.
  DONE: () => {
    if (courier) {
      courier = null;
      pendingMail = null;
      outgoing = [];
      render();
      status("Back to the mailbox");
      return;
    }
    delete lastCommand.mail;
    delete lastCommand.mailFrame;
    exitingMail = true;
    gw.send({ type: "back" });
  },
  // HELP shows the embedded help frame (§A.8) — a client asset, nothing is sent.
  HELP: () => {
    if (!assets.help) {
      status("No help frame embedded");
      return;
    }
    mode = "frame";
    frame = assets.help;
    isWelcome = false;
    render();
    status("Help \u2014 FINISH returns");
  },
  SAVE: () => status("SAVE is a client feature \u2014 not implemented in this reference client"),
  PRINT: () => status("PRINT is a client feature \u2014 not implemented in this reference client"),
  LOAD: () => status("LOAD is a client feature \u2014 not implemented in this reference client"),
  // EDITR enters the EDITOR context (§8.4.1) — it does not open an upload form.
  EDITR: () => {
    editorReturn = () => render();
    enterEditor();
  },
  ALL: () => gw.send({ type: "more" }),
  // page to the end
  MORE: () => gw.send({ type: "more" }),
  FINISH: () => gw.send({ type: "finish" }),
  GOTO: () => {
    void ask("GOTO", [{ label: "page number or keyword" }]).then((r) => {
      if (r?.[0]) gw.send({ type: "goto", target: r[0] });
    });
  },
  // (column cycling is F7/F8, §7.7 — not a command)
  ACCNT: () => gw.send({ type: "account" }),
  MAIL: () => gw.send({ type: "mail.list" }),
  UCAT: () => gw.send({ type: "ucat" }),
  VOTE: () => {
    const e = curEntry();
    if (!e) {
      status("Highlight an entry to vote on");
      return;
    }
    void ask(`Vote on "${e.title}"`, [{ label: "score 1-9", type: "number" }]).then((r) => {
      if (r?.[0]) gw.send({ type: "vote", page: e.page, score: parseInt(r[0], 10) });
    });
  },
  LIFE: () => {
    const e = curEntry();
    if (!e) {
      status("Highlight an entry to extend");
      return;
    }
    void ask(`Extend life of "${e.title}"`, [{ label: "days", type: "number" }]).then((r) => {
      if (r?.[0]) gw.send({ type: "life", page: e.page, days: parseInt(r[0], 10) });
    });
  },
  // ID — "ID TO CHECK?" ($B0D9). Up to five, shown on the COURIER frame (§8.2).
  ID: () => {
    void idCheck();
  },
  UPLD: () => {
    if (mode !== "directory" || !dir) {
      status("Navigate to a directory first");
      return;
    }
    if (dir.entries.length >= 11) {
      status("This directory is full (11 entries max)");
      return;
    }
    if (pendingUpload && !buf.isEmpty()) {
      gw.send({ type: "upload", ...pendingUpload, frames: buf.toFrames() });
      pendingUpload = null;
      submitMode = "upload";
      submitting = true;
      setFocus("editor");
      status("Uploading\u2026");
      return;
    }
    openSubmit("upload");
  },
  SEND: () => {
    void sendMail();
  },
  // §3.8: read and render the goodbye frame BEFORE handling the close — do not
  // close the socket here; the server closes after sending it.
  LEAVE: () => {
    gw.send({ type: "leave" });
    status("Leaving\u2026");
  }
};
var CONTEXT_COMMANDS = {
  // ⚠ Empty, and NOT because the editor is unavailable offline. With no session
  // there is no Compunet screen, so there is no duckshoot — the original sits at
  // the BASIC prompt, where EDITOR is a BASIC command ($8249), not a row entry.
  // Offline entry is a HOST-ENVIRONMENT affordance (our "Editor" button, beside
  // Connect); the duckshoot reappears inside the editor with its own row (§8.4).
  idle: [],
  // The welcome screen carries the DIRECTORY row, with HELP centred by default (§4.8).
  welcome: ["HELP", "DIR", "SHOW", "BACK", "GOTO", "UCAT", "MAIL", "ACCNT", "SAVE", "EDITR", "LEAVE"],
  directory: [
    "HELP",
    "DIR",
    "SHOW",
    "BACK",
    "GOTO",
    "UCAT",
    "MAIL",
    "ACCNT",
    "SAVE",
    "EDITR",
    "LEAVE",
    "PRINT",
    "LIFE",
    "BUY",
    "LOAD",
    "UPLD",
    "VOTE"
  ],
  frame: ["MORE", "ALL", "FINISH"],
  // multi-frame only; single frame shows PRESS ANY KEY
  mail: ["SEND", "SHOW", "MORE", "ID", "EDITR", "DONE"],
  mailFrame: ["SEND", "SHOW", "MORE", "ID", "EDITR", "DONE"],
  // Message composition (§8.2.1), reached once subject and recipients are
  // accepted. SEND adds a frame, FINISH transmits — distinct commands.
  courierSend: ["SEND", "FINISH", "LAST", "NEXT", "EDITR"],
  // ⚠ §8.4.1 order — it ends FREE, RETURN, DOS. Storage order (…FREE DOS RETURN)
  // is NOT display order: the C64 offset table is non-monotonic at the tail.
  editor: [
    "HELP",
    "EDIT",
    "LAST",
    "NEXT",
    "NEW",
    "COPY",
    "ERASE",
    "GET",
    "PUT",
    "STORE",
    "PRINT",
    "FREE",
    "RETURN",
    "DOS"
  ],
  partyline: []
};
var NEEDS_SELECTION = /* @__PURE__ */ new Set(["SHOW", "DIR", "VOTE", "LIFE", "BUY"]);
function netContext() {
  if (inParty) return "partyline";
  if (courier?.kind === "send" && pendingMail) return "courierSend";
  if (mode === "idle") return "idle";
  if (mode === "frame") return isWelcome ? "welcome" : inMail ? "mailFrame" : "frame";
  return inMail ? "mail" : "directory";
}
function hasSelection() {
  const e = curEntry();
  return !!e && e.title.trim() !== "(EMPTY)" && e.title.trim() !== "(NO MAIL)";
}
var rows = { net: { words: [], ix: 0 }, editor: { words: [], ix: 0 } };
var lastCommand = {};
function rememberRow(pane) {
  const r = rows[pane];
  const ctx = pane === "editor" ? "editor" : netContext();
  if (r.words[r.ix]) lastCommand[ctx] = r.words[r.ix];
}
function tableFor(ctx) {
  if (ctx === "editor") return editorActions;
  if (ctx === "courierSend") return courierActions;
  return actions;
}
function buildRow(ctx) {
  const table = tableFor(ctx);
  return CONTEXT_COMMANDS[ctx].filter((name) => {
    if (!table[name]) return false;
    if (NEEDS_SELECTION.has(name) && ctx === "directory" && !hasSelection()) return false;
    return true;
  });
}
function updateBar() {
  const nctx = netContext();
  rows.net.words = buildRow(nctx);
  const keep = rows.net.words.indexOf(lastCommand[nctx] ?? "");
  rows.net.ix = rows.net.words.length ? keep >= 0 ? keep : 0 : 0;
  if (awaitingKey || nctx === "frame" && frame && !frame.morePages) renderer?.renderPrompt("PRESS ANY KEY");
  else renderer?.renderDuckshoot(rows.net.words, rows.net.ix);
  if (inEditor) {
    rows.editor.words = buildRow("editor");
    const keepE = rows.editor.words.indexOf(lastCommand.editor ?? "");
    rows.editor.ix = keepE >= 0 ? keepE : rows.editor.ix;
    edRenderer?.renderDuckshoot(rows.editor.words, rows.editor.ix);
  }
  $("netMeta").textContent = mode === "idle" ? "not connected" : nctx;
  $("hint").textContent = focusPane === "editor" ? "Editor focused \xB7 \u2190/\u2192 scroll the row \xB7 Enter runs it \xB7 EDIT then type \xB7 ESC stops editing" : "\u2191/\u2193 highlight an entry \xB7 \u2190/\u2192 scroll the row \xB7 Enter runs it \xB7 F7/F8 cycle the right column";
}
function duckScroll(delta) {
  const r = rows[focusPane];
  if (!r.words.length) return;
  r.ix = ((r.ix + delta) % r.words.length + r.words.length) % r.words.length;
  rememberRow(focusPane);
  (focusPane === "editor" ? edRenderer : renderer).renderDuckshoot(r.words, r.ix);
}
function duckCommit() {
  const r = rows[focusPane];
  const name = r.words[r.ix];
  const table = tableFor(focusPane === "editor" ? "editor" : netContext());
  rememberRow(focusPane);
  if (name && table[name]) table[name]();
}
async function connect() {
  const wsBase = $("host").value.trim().replace(/\/$/, "");
  const httpBase = wsBase.replace(/^ws/, "http");
  try {
    const { token } = await gw.login(httpBase, $("user").value, $("pass").value);
    gw.connect(
      wsBase,
      token,
      onMessage,
      () => status("Disconnected."),
      () => status("WebSocket error.")
    );
    $("connect").disabled = true;
    $("pass").classList.remove("bad");
  } catch (e) {
    const msg = e.message;
    const bad = /401|403/.test(msg);
    $("pass").classList.toggle("bad", bad);
    if (bad) $("pass").focus();
    status(bad ? "Login refused \u2014 check the user ID and password." : "Connect error: " + msg, true);
  }
}
window.addEventListener("keydown", (e) => {
  const el = e.target;
  if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
  if (inParty) return;
  if (awaitingKey) {
    awaitingKey = false;
    courier = null;
    render();
    e.preventDefault();
    return;
  }
  if (e.key === "Tab" && e.ctrlKey && inEditor) {
    setFocus(focusPane === "net" ? "editor" : "net");
    e.preventDefault();
    return;
  }
  if (focusPane === "editor" && inEditor && buf.editing) {
    if (e.repeat && !buf.autoRepeat) {
      e.preventDefault();
      return;
    }
    if (e.key === "Escape" && e.shiftKey) {
      status(buf.restoreOriginal() ? "RUN \u2014 frame restored to its stored state" : "Nothing stored to restore");
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "Escape") {
      buf.stopEdit();
      status("STOP \u2014 edit stopped, frame stored");
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "Tab" && e.shiftKey) {
      buf.lowerCase = !buf.lowerCase;
      status(`Case: ${buf.lowerCase ? "lower/mixed" : "upper/graphics"}`);
      e.preventDefault();
      return;
    }
    if (e.key === "F5") {
      buf.autoRepeat = !buf.autoRepeat;
      status(`Auto-repeat ${buf.autoRepeat ? "on" : "off"}`);
      e.preventDefault();
      return;
    }
    if (e.key === "F6") {
      buf.colourOn = !buf.colourOn;
      status(`Colour ${buf.colourOn ? "on" : "off"}`);
      e.preventDefault();
      return;
    }
    if (e.key === "F7") {
      buf.cycleBackground(e.shiftKey ? -1 : 1);
      render();
      status(`Screen colour ${buf.page().background}`);
      e.preventDefault();
      return;
    }
    if (e.key === "F8") {
      buf.cycleBorder(e.shiftKey ? -1 : 1);
      render();
      status(`Border colour ${buf.page().border}`);
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowUp") {
      buf.moveRow(-1);
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowDown") {
      buf.moveRow(1);
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowLeft") {
      buf.moveCol(-1);
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowRight") {
      buf.moveCol(1);
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "Enter") {
      buf.newline();
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "Backspace") {
      buf.backspace();
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "F3") {
      buf.deleteLine();
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "F4") {
      buf.insertLine();
      render();
      e.preventDefault();
      return;
    }
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
      buf.typeChar(e.key);
      render();
      e.preventDefault();
      return;
    }
    return;
  }
  if (focusPane === "editor" && inEditor) {
    if (e.key === "ArrowLeft") {
      duckScroll(-1);
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowRight") {
      duckScroll(1);
      e.preventDefault();
      return;
    }
    if (e.key === "Enter") {
      duckCommit();
      e.preventDefault();
      return;
    }
    return;
  }
  if (mode === "directory" && dir) {
    if (e.key === "ArrowDown") {
      sel = Math.min(sel + 1, dir.entries.length - 1);
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "ArrowUp") {
      sel = Math.max(sel - 1, 0);
      render();
      e.preventDefault();
      return;
    }
  }
  if (e.key === "F7" || e.key === "F8") {
    if (dir) {
      const n = dir.columns.length;
      colIdx = ((colIdx + (e.key === "F8" ? 1 : -1)) % n + n) % n;
      render();
      status("Column: " + dir.columns[colIdx].trim());
    }
    e.preventDefault();
    return;
  }
  if (e.key === "ArrowLeft") {
    duckScroll(-1);
    e.preventDefault();
    return;
  }
  if (e.key === "ArrowRight") {
    duckScroll(1);
    e.preventDefault();
    return;
  }
  if (e.key === "Enter") {
    duckCommit();
    e.preventDefault();
    return;
  }
});
async function boot() {
  assets = await (await fetch("./assets.json")).json();
  renderer = new Renderer(canvas, assets, wrap);
  edRenderer = new Renderer(edCanvas, assets, edWrap);
  $("connect").onclick = connect;
  $("paneNet").addEventListener("mousedown", () => setFocus("net"));
  $("paneEditor").addEventListener("mousedown", () => setFocus("editor"));
  $("edClose").onclick = () => leaveEditor();
  $("openEditor").onclick = () => {
    if (inEditor) return;
    editorReturn = () => render();
    enterEditor();
  };
  canvas.addEventListener("click", (ev) => {
    if (mode !== "directory" || !dir) return;
    const r = canvas.getBoundingClientRect();
    const col = Math.floor((ev.clientX - r.left) / r.width * 40);
    const row = Math.floor((ev.clientY - r.top) / r.height * 25);
    if (row === 21 && col >= 30 && col <= 38) {
      const n = dir.columns.length;
      colIdx = ((colIdx + (col >= 34 ? 1 : -1)) % n + n) % n;
      render();
      status("Column: " + dir.columns[colIdx].trim());
      return;
    }
    const i = row - 10;
    if (i < 0 || i >= dir.entries.length) return;
    sel = i;
    render();
  });
  canvas.addEventListener("dblclick", (ev) => {
    if (mode !== "directory" || !dir) return;
    if (inMail) return;
    const r = canvas.getBoundingClientRect();
    const row = Math.floor((ev.clientY - r.top) / r.height * 25);
    const i = row - 10;
    if (i < 0 || i >= dir.entries.length) return;
    sel = i;
    render();
    actions.DIR();
  });
  $("edSubmit").onclick = doSubmit;
  $("edCancel").onclick = closeSubmit;
  $("chatInput").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const input = $("chatInput");
    const text = input.value.trim();
    if (!text) return;
    gw.send({ type: text.startsWith("*") ? "partyline.command" : "partyline.send", text });
    input.value = "";
  });
  render();
  status("Ready. Connect \u2014 or open the Editor now: it works offline.");
}
void boot();
//# sourceMappingURL=app.bundle.js.map
