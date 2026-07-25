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
  /** Draw the editor's current page (§8.4.1): 23 rows of page, then a status
   *  line showing the buffer position — the editor is a multi-page buffer, so
   *  "page 2 of 5" is part of the interface, not decoration. */
  renderEditorPage(lines, colour, background, border, cur, total, row, col, editing) {
    const g = Array.from({ length: COLS * ROWS }, () => ({ g: 32, fg: colour, bg: background, rv: 0 }));
    for (let r = 0; r < ROWS - 1; r++) {
      const t = (lines[r] ?? "").toUpperCase();
      for (let c = 0; c < COLS && c < t.length; c++)
        g[r * COLS + c] = { g: asciiGlyph(t[c]), fg: colour, bg: background, rv: 0 };
    }
    if (editing && row < ROWS - 1) {
      const i = row * COLS + col;
      g[i] = { ...g[i], rv: 1 };
    }
    const bar = ` PAGE ${cur + 1} OF ${total}${editing ? "   EDIT \u2014 ESC STOPS" : ""}`;
    for (let c = 0; c < COLS; c++) {
      const ch = bar[c] ?? " ";
      g[(ROWS - 1) * COLS + c] = { g: asciiGlyph(ch.toUpperCase()), fg: 0, bg: 1, rv: 0 };
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
var PAGE_ROWS = 23;
function blankPage() {
  return { lines: Array(PAGE_ROWS).fill(""), colour: 5, border: 6, background: 0 };
}
var CAPACITY = 64 * PAGE_COLS * PAGE_ROWS;
var EditorBuffer = class {
  constructor() {
    this.pages = [blankPage()];
    this.cur = 0;
    /** cursor within the current page, only meaningful in EDIT mode */
    this.row = 0;
    this.col = 0;
    this.editing = false;
  }
  page() {
    return this.pages[this.cur];
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
    this.pages.splice(++this.cur, 0, { ...p, lines: p.lines.slice() });
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
  /** FREE — characters remaining, in the original's units. */
  free() {
    const used = this.pages.reduce((n, p) => n + p.lines.reduce((m, l) => m + l.length, 0), 0);
    return Math.max(0, CAPACITY - used);
  }
  // --- editing (EDIT mode) ---
  setLine(r, text) {
    this.page().lines[r] = text.slice(0, PAGE_COLS);
  }
  /** Overwrite-at-cursor, as the original edits (its f6 toggles insert). */
  typeChar(ch) {
    const line = (this.page().lines[this.row] ?? "").padEnd(this.col, " ");
    this.setLine(this.row, line.slice(0, this.col) + ch.toUpperCase() + line.slice(this.col + 1));
    if (++this.col >= PAGE_COLS) {
      this.col = 0;
      this.moveRow(1);
    }
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
    const line = (this.page().lines[this.row] ?? "").padEnd(this.col + 1, " ");
    this.setLine(this.row, line.slice(0, this.col) + " " + line.slice(this.col + 1));
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
  /** DELETE/INSERT a line above the cursor (the original's f3/f4). */
  insertLine() {
    this.page().lines.splice(this.row, 0, "");
    this.page().lines.length = PAGE_ROWS;
  }
  deleteLine() {
    this.page().lines.splice(this.row, 1);
    while (this.page().lines.length < PAGE_ROWS) this.page().lines.push("");
  }
  // --- serialisation (GET / PUT / STORE) ---
  /** Wire form for upload / mail.send (§5.4 of the Binding-B spec). */
  toFrames() {
    return this.pages.map((p) => ({
      lines: p.lines.slice(),
      colour: p.colour,
      border: p.border,
      background: p.background
    }));
  }
  /** True when nothing has actually been composed — used to refuse an upload
   *  of an empty buffer rather than send a blank page. */
  isEmpty() {
    return this.pages.every((p) => p.lines.every((l) => !l.trim()));
  }
  toJSON(pagesOnly) {
    return JSON.stringify({ format: "compunet-editor-1", pages: pagesOnly ?? this.pages });
  }
  /** GET — replace the buffer from a previously PUT/STOREd file. */
  load(text) {
    const data = JSON.parse(text);
    if (data.format !== "compunet-editor-1" || !Array.isArray(data.pages) || !data.pages.length)
      throw new Error("not an editor file");
    this.pages = data.pages.map((p) => ({
      lines: Array.from({ length: PAGE_ROWS }, (_, i) => String(p.lines?.[i] ?? "").slice(0, PAGE_COLS)),
      colour: p.colour ?? 5,
      border: p.border ?? 6,
      background: p.background ?? 0
    }));
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
var statusEl = $("status");
var assets;
var renderer;
var gw = new Gateway();
var mode = "idle";
var dir = null;
var frame = null;
var sel = 0;
var colIdx = 0;
var account = null;
var isWelcome = false;
var inMail = false;
var exitingMail = false;
function status(s) {
  statusEl.textContent = s;
}
function render() {
  if (inEditor) renderEditor();
  else if (mode === "directory" && dir) renderer.renderDirectory(dir, sel, colIdx);
  else if (mode === "frame" && frame) renderer.renderFrame(frame);
  updateBar();
}
function onMessage(m) {
  switch (m.type) {
    case "ready": {
      const r = m;
      account = r.account;
      if (r.welcome) {
        mode = "frame";
        frame = r.welcome;
        isWelcome = true;
        inMail = false;
        render();
      }
      status(`Welcome, ${account.user} \u2014 press DIR to enter the system`);
      break;
    }
    case "directory":
      mode = "directory";
      dir = m;
      sel = 0;
      colIdx = 0;
      isWelcome = false;
      inMail = m.context === "mail";
      render();
      if (exitingMail) {
        if (inMail) gw.send({ type: "back" });
        else exitingMail = false;
      }
      status(`${m.title} \u2014 ${m.entries.length} entries`);
      break;
    case "frame":
      mode = "frame";
      frame = m;
      isWelcome = false;
      render();
      if (m.goodbye) {
        status("Goodbye \u2014 disconnected.");
        gw.close();
        return;
      }
      if (exitingMail && inMail) gw.send({ type: "back" });
      status("Reading page" + (m.morePages ? " \u2014 MORE follows" : ""));
      break;
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
      status(`${m.of ?? "command"} accepted`);
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
      status("\u26A0 " + m.code + (m.message ? ": " + m.message : ""));
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
function enterEditor() {
  inEditor = true;
  buf.editing = false;
  status("Editor \u2014 EDIT types on the page, RETURN leaves. Page " + (buf.cur + 1) + " of " + buf.pages.length);
  render();
}
function leaveEditor() {
  inEditor = false;
  buf.editing = false;
  if (editorReturn) {
    const f = editorReturn;
    editorReturn = null;
    f();
  } else render();
  status(mode === "idle" ? "Left the editor. Connect, then UPLD or SEND submits the buffer." : "Left the editor. UPLD or SEND submits the buffer.");
}
function renderEditor() {
  const p = buf.page();
  renderer.renderEditorPage(
    p.lines,
    p.colour,
    p.background,
    p.border,
    buf.cur,
    buf.pages.length,
    buf.row,
    buf.col,
    buf.editing
  );
}
function openSubmit(kind) {
  if (buf.isEmpty()) {
    status("Nothing composed yet \u2014 use EDITR to write a page first");
    return;
  }
  submitMode = kind;
  $("editor").hidden = false;
  $("editorTitle").textContent = kind === "upload" ? `Upload ${buf.pages.length} page(s) into "${dir?.title ?? "this directory"}"` : `Send ${buf.pages.length} page(s) as mail`;
  $("edContentFields").hidden = kind !== "upload";
  $("edTo").hidden = kind !== "mail";
  $("edHint").textContent = kind === "upload" ? "Type and price are required (\xA78.3.2). Body comes from the editor buffer." : "Recipients: up to five user IDs, comma-separated.";
  $("edTitle").value = "";
  $("edTitle").focus();
}
function closeSubmit() {
  submitMode = null;
  $("editor").hidden = true;
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
    gw.send({
      type: "upload",
      title,
      kind: $("edKind").value,
      price: parseFloat($("edPrice").value) || 0,
      life: parseInt($("edLife").value, 10) || 0,
      frames
    });
  }
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
    renderer.renderFrame(assets.editorHelp);
    renderer.renderDuckshoot(duck, duckIx);
    status("Editor help \u2014 any editor command returns");
  },
  EDIT: () => {
    buf.editing = !buf.editing;
    status(buf.editing ? "EDIT \u2014 typing on the page; ESC stops" : "Edit stopped");
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
  if (on) {
    $("chatInput").value = "";
    $("chatInput").focus();
  } else {
    $("chatLog").textContent = "";
  }
}
function chatLog(line) {
  const log = $("chatLog");
  log.textContent += (log.textContent ? "\n" : "") + line;
  log.scrollTop = log.scrollHeight;
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
    if (price && !confirm(`BUY FOR ${price} - SURE?`)) return;
    gw.send({ type: "open", page: e.page });
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
  DONE: () => {
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
    const t = prompt("GOTO page number or keyword:");
    if (t) gw.send({ type: "goto", target: t });
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
    const s = prompt(`Vote on "${e.title}" \u2014 score 1-9:`);
    if (s) gw.send({ type: "vote", page: e.page, score: parseInt(s, 10) });
  },
  LIFE: () => {
    const e = curEntry();
    if (!e) {
      status("Highlight an entry to extend");
      return;
    }
    const d = prompt(`Extend life of "${e.title}" by how many days?`);
    if (d) gw.send({ type: "life", page: e.page, days: parseInt(d, 10) });
  },
  ID: () => {
    const u = prompt("Look up user ID(s), comma-separated:");
    if (u) gw.send({ type: "idlookup", ids: u.split(",").map((x) => x.trim()).filter(Boolean) });
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
    openSubmit("upload");
  },
  SEND: () => openSubmit("mail"),
  // §3.8: read and render the goodbye frame BEFORE handling the close — do not
  // close the socket here; the server closes after sending it.
  LEAVE: () => {
    gw.send({ type: "leave" });
    status("Leaving\u2026");
  }
};
var CONTEXT_COMMANDS = {
  // ⚠ Not empty: the EDITOR works offline (§8.4), so it is reachable before any
  // login and after a disconnect. Nothing else is available with no session.
  idle: ["EDITR"],
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
function currentContext() {
  if (inParty) return "partyline";
  if (inEditor) return "editor";
  if (mode === "idle") return "idle";
  if (mode === "frame") return isWelcome ? "welcome" : inMail ? "mailFrame" : "frame";
  return inMail ? "mail" : "directory";
}
function hasSelection() {
  const e = curEntry();
  return !!e && e.title.trim() !== "(EMPTY)" && e.title.trim() !== "(NO MAIL)";
}
var duck = [];
var duckIx = 0;
function updateBar() {
  const ctx = currentContext();
  const prev = duck[duckIx];
  const table = ctx === "editor" ? editorActions : actions;
  duck = CONTEXT_COMMANDS[ctx].filter((name) => {
    if (!table[name]) return false;
    if (NEEDS_SELECTION.has(name) && ctx === "directory" && !hasSelection()) return false;
    return true;
  });
  const keep = duck.indexOf(prev);
  duckIx = duck.length ? keep >= 0 ? keep : 0 : 0;
  if (ctx === "frame" && frame && !frame.morePages && !inEditor) {
    renderer?.renderPrompt("PRESS ANY KEY");
  } else renderer?.renderDuckshoot(duck, duckIx);
  $("ctx").textContent = ctx === "idle" ? "" : `context: ${ctx}`;
}
function duckScroll(delta) {
  if (!duck.length) return;
  duckIx = ((duckIx + delta) % duck.length + duck.length) % duck.length;
  renderer.renderDuckshoot(duck, duckIx);
}
function duckCommit() {
  const name = duck[duckIx];
  const table = currentContext() === "editor" ? editorActions : actions;
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
  } catch (e) {
    status("Connect error: " + e.message);
  }
}
window.addEventListener("keydown", (e) => {
  const el = e.target;
  if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return;
  if (inParty) return;
  if (inEditor && buf.editing) {
    if (e.key === "Escape") {
      buf.editing = false;
      status("Edit stopped");
      render();
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
      buf.insertLine();
      render();
      e.preventDefault();
      return;
    }
    if (e.key === "F4") {
      buf.deleteLine();
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
  if (inEditor) {
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
  $("connect").onclick = connect;
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
  updateBar();
  status("Ready. Connect \u2014 or use EDITR now: the editor works offline.");
}
void boot();
//# sourceMappingURL=app.bundle.js.map
