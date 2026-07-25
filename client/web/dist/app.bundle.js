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
  if (mode === "directory" && dir) renderer.renderDirectory(dir, sel, colIdx);
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
var editorMode = null;
function openEditor(kind) {
  editorMode = kind;
  $("editor").hidden = false;
  $("editorTitle").textContent = kind === "upload" ? `Upload a page into "${dir?.title ?? "this directory"}"` : "Compose mail";
  $("edContentFields").hidden = kind !== "upload";
  $("edTo").hidden = kind !== "mail";
  $("edHint").textContent = kind === "upload" ? "Type and price are required (\xA78.3.2)." : "Recipients: up to five user IDs, comma-separated.";
  $("edTitle").value = "";
  $("edBody").value = "";
  $("edTitle").focus();
}
function closeEditor() {
  editorMode = null;
  $("editor").hidden = true;
}
function submitEditor() {
  const title = $("edTitle").value.trim();
  const lines = $("edBody").value.split("\n");
  if (!title) {
    status("A title is required");
    return;
  }
  if (editorMode === "mail") {
    const to = $("edTo").value.split(",").map((x) => x.trim()).filter(Boolean);
    if (!to.length) {
      status("At least one recipient is required");
      return;
    }
    gw.send({ type: "mail.send", to, subject: title, frames: [{ lines, colour: 1 }] });
  } else {
    gw.send({
      type: "upload",
      title,
      kind: $("edKind").value,
      price: parseFloat($("edPrice").value) || 0,
      life: parseInt($("edLife").value, 10) || 0,
      frames: [{ lines, colour: 5, border: 6, background: 0 }]
    });
  }
  closeEditor();
}
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
  const buf = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
  const url = URL.createObjectURL(new Blob([buf], { type: "application/octet-stream" }));
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
  HELP: () => status("HELP is a client feature \u2014 not implemented in this reference client"),
  SAVE: () => status("SAVE is a client feature \u2014 not implemented in this reference client"),
  PRINT: () => status("PRINT is a client feature \u2014 not implemented in this reference client"),
  LOAD: () => status("LOAD is a client feature \u2014 not implemented in this reference client"),
  EDITR: () => openEditor("upload"),
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
    openEditor("upload");
  },
  SEND: () => openEditor("mail"),
  LEAVE: () => {
    gw.send({ type: "leave" });
    gw.close();
  }
};
var CONTEXT_COMMANDS = {
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
  partyline: []
};
var NEEDS_SELECTION = /* @__PURE__ */ new Set(["SHOW", "DIR", "VOTE", "LIFE", "BUY"]);
function currentContext() {
  if (inParty) return "partyline";
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
  duck = CONTEXT_COMMANDS[ctx].filter((name) => {
    if (!actions[name]) return false;
    if (NEEDS_SELECTION.has(name) && ctx === "directory" && !hasSelection()) return false;
    return true;
  });
  const keep = duck.indexOf(prev);
  duckIx = duck.length ? keep >= 0 ? keep : 0 : 0;
  if (ctx === "frame" && frame && !frame.morePages) {
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
  if (name && actions[name]) actions[name]();
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
    if (i === sel) actions.SHOW();
    else {
      sel = i;
      render();
    }
  });
  $("edSubmit").onclick = submitEditor;
  $("edCancel").onclick = closeEditor;
  $("chatInput").addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const input = $("chatInput");
    const text = input.value.trim();
    if (!text) return;
    gw.send({ type: text.startsWith("*") ? "partyline.command" : "partyline.send", text });
    input.value = "";
  });
  status("Ready. Enter credentials and Connect.");
}
void boot();
//# sourceMappingURL=app.bundle.js.map
