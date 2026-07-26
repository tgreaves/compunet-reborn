// The frame editor (spec §8.4 / §8.4.1 / §8.4.2).
//
// This is a CLIENT feature — it sends nothing. Its output leaves through the
// upload path (§8.3.2): UPLD for Jungle pages, SEND for Courier mail.
//
// ⚠ A page is a CELL GRID, not lines of text. Frames carry per-cell colour,
// reverse video and two character sets, and pages viewed on Compunet are stored
// here VERBATIM (§8.4.2) — a text model would silently discard all of that. The
// grid is the full 40x24: an editor page and a frame are the same thing.
//
// ⚠ The editor holds a MULTI-PAGE BUFFER with a current position, not one page.
// LAST/NEXT/NEW/COPY/ERASE only mean anything against such a buffer, and PUT
// (one page) vs STORE (the whole buffer) only differ because it exists.

import type { Cell, EditorPage, FrameMsg } from './protocol';

export const PAGE_COLS = 40, PAGE_ROWS = 24;
const CELLS = PAGE_COLS * PAGE_ROWS;

/** A page as the editor holds it: exactly what a frame holds. */
export interface Page {
  cells: Cell[];
  border: number;
  background: number;
  /** current typing colour (not part of the page's content) */
  colour: number;
  /** ⚠ base64 of the EXACT bytes this page was captured from, when it came from
   *  Compunet and has not been edited since. Kept so an untouched captured page
   *  re-uploads byte-for-byte instead of being re-encoded (§8.4.2). Any edit
   *  clears it — the bytes would no longer describe the page. */
  raw?: string;
}

function blankCells(bg: number, fg: number): Cell[] {
  return Array.from({ length: CELLS }, () => ({ g: 0x20, fg, bg, rv: 0 as 0 | 1 }));
}

function blankPage(): Page {
  return { cells: blankCells(0, 1), border: 6, background: 0, colour: 1 };
}

/** The C64 editor reported free space in characters; keep the same units so
 *  FREE means the same thing to a user who knows the original (§8.4.1).
 *  The original held "10-15 pages simultaneously" (docs/PROTOCOL.md) — a range,
 *  because its limit was MEMORY and pages compress differently (RLE, §6.4).
 *  ⚠ The exact byte figure is NOT verified against the disassembly; 12 pages is
 *  an approximation of the right magnitude, not a reconstructed constant. */
const CAPACITY = 12 * CELLS;
/** Hard stop matching the top of the original's quoted range. */
export const MAX_PAGES = 15;

/** ASCII -> glyph index, in whichever character set the editor is in (§5.3).
 *  ⚠ The sets index letters DIFFERENTLY: in the lowercase/mixed set a-z are
 *  $01-$1A and capitals live at $41-$5A; in uppercase/graphics A-Z are $01-$1A.
 *  Glyphs >= 128 select the lowercase set. Both may appear on one page — the
 *  server emits the $0E/$8E switches when it encodes. */
function charToGlyph(ch: string, lower: boolean): number {
  const c = ch.charCodeAt(0) & 0xFF;
  if (lower) {
    if (c >= 0x61 && c <= 0x7A) return 128 + (c - 0x60);   // a-z
    if (c >= 0x41 && c <= 0x5A) return 128 + c;            // A-Z
    if (c >= 0x20 && c <= 0x3F) return 128 + c;
    return 128 + 0x20;
  }
  const b = ch.toUpperCase().charCodeAt(0) & 0xFF;
  if (b >= 0x20 && b <= 0x3F) return b;
  if (b >= 0x40 && b <= 0x5F) return b & 0x1F;
  return 0x20;
}

/** Capture a displayed frame as an editor page — VERBATIM (§8.4.2).
 *  The cells are copied exactly as rendered, and the bytes they came from are
 *  kept for re-upload. Nothing is converted to text, so nothing is lost. */
export function frameToPage(f: FrameMsg): Page {
  return {
    cells: f.cells.map((c) => ({ ...c })),
    border: f.border,
    background: f.background,
    colour: 1,
    raw: (f as FrameMsg & { raw?: string }).raw,
  };
}

export class EditorBuffer {
  pages: Page[] = [blankPage()];
  cur = 0;
  /** cursor within the current page, only meaningful in EDIT mode */
  row = 0;
  col = 0;
  editing = false;

  // --- editing modes, from the editor's own help frame (§A.9 / §8.4.3) ---
  /** SHIFT-C= "change case overwrite": which set typed text goes into. */
  lowerCase = false;
  /** f6 "on/off colour": when off, typing keeps each cell's existing colour. */
  colourOn = true;
  /** f5 "on/off auto-repeat": when off, held keys do not repeat. */
  autoRepeat = true;
  /** The page as last STORED, for RUN ("restore original"). */
  private original: Cell[] | null = null;

  /** STOP — stop editing and store the frame (§A.9). */
  stopEdit(): void { this.editing = false; this.original = this.page().cells.map((c) => ({ ...c })); }

  /** RUN — restore the frame to its last stored state (§A.9). */
  restoreOriginal(): boolean {
    if (!this.original) return false;
    this.page().cells = this.original.map((c) => ({ ...c }));
    delete this.page().raw;
    return true;
  }

  /** Remember the starting state when an edit begins. */
  beginEdit(): void {
    this.editing = true;
    if (!this.original) this.original = this.page().cells.map((c) => ({ ...c }));
  }

  page(): Page { return this.pages[this.cur]; }

  /** Any change to a page's content invalidates its captured bytes. */
  private touch(): void { delete this.page().raw; }

  // --- page navigation (LAST / NEXT) ---
  last(): boolean { if (this.cur === 0) return false; this.cur--; this.home(); return true; }
  next(): boolean { if (this.cur >= this.pages.length - 1) return false; this.cur++; this.home(); return true; }

  // --- page management (NEW / COPY / ERASE) ---
  /** NEW — a fresh BLANK page after the current one. Not COPY. */
  newPage(): void { this.pages.splice(++this.cur, 0, blankPage()); this.home(); }
  /** COPY — a DUPLICATE of the current page after it. Not NEW. */
  copyPage(): void {
    const p = this.page();
    this.pages.splice(++this.cur, 0, { ...p, cells: p.cells.map((c) => ({ ...c })) });
    this.home();
  }
  /** ERASE — remove the current page. The buffer never becomes empty. */
  erasePage(): void {
    this.pages.splice(this.cur, 1);
    if (!this.pages.length) this.pages.push(blankPage());
    if (this.cur >= this.pages.length) this.cur = this.pages.length - 1;
    this.home();
  }

  private home(): void { this.row = 0; this.col = 0; }

  /** True while the buffer is just its initial untouched blank page. */
  private isPristine(): boolean { return this.pages.length === 1 && this.isBlank(this.pages[0]); }

  private isBlank(p: Page): boolean {
    return p.cells.every((c) => (c.g & 0x7F) === 0x20 && !c.rv);
  }

  /** Append a page viewed on Compunet (§8.4.2). Returns false when the buffer
   *  is full — the original's limit was memory, and it does not silently
   *  discard. The user's current position is NOT disturbed: capture happens
   *  while they may be editing something else entirely. */
  capture(p: Page): boolean {
    if (this.isPristine()) { this.pages[0] = p; return true; }
    if (this.pages.length >= MAX_PAGES || this.free() < this.cost(p)) return false;
    this.pages.push(p);
    return true;
  }

  private cost(p: Page): number {
    return p.cells.filter((c) => (c.g & 0x7F) !== 0x20 || c.rv).length;
  }

  /** FREE — characters remaining, in the original's units. */
  free(): number {
    return Math.max(0, CAPACITY - this.pages.reduce((n, p) => n + this.cost(p), 0));
  }

  // --- editing (EDIT mode) ---
  /** Overwrite-at-cursor, as the original edits (its f6 toggles insert). */
  typeChar(ch: string): void {
    const p = this.page();
    this.touch();
    const i = this.row * PAGE_COLS + this.col;
    // f6 off: the character changes, the colour under it does not.
    const fg = this.colourOn ? p.colour : p.cells[i].fg;
    p.cells[i] = { g: charToGlyph(ch, this.lowerCase), fg, bg: p.background, rv: 0 };
    if (++this.col >= PAGE_COLS) { this.col = 0; this.moveRow(1); }
  }

  /** f7 / f8 — screen (background) and border colour (§A.9). */
  cycleBackground(d: number): void { const p = this.page(); p.background = ((p.background + d) % 16 + 16) % 16; this.touch(); }
  cycleBorder(d: number): void { const p = this.page(); p.border = ((p.border + d) % 16 + 16) % 16; }

  backspace(): void {
    if (this.col === 0) { if (this.row > 0) { this.row--; this.col = PAGE_COLS - 1; } return; }
    this.col--;
    const p = this.page();
    this.touch();
    p.cells[this.row * PAGE_COLS + this.col] = { g: 0x20, fg: p.colour, bg: p.background, rv: 0 };
  }

  newline(): void { this.col = 0; this.moveRow(1); }

  moveRow(d: number): void { this.row = Math.max(0, Math.min(PAGE_ROWS - 1, this.row + d)); }
  moveCol(d: number): void { this.col = Math.max(0, Math.min(PAGE_COLS - 1, this.col + d)); }

  /** Change the colour subsequent typing uses (the original's f7/f8). */
  cycleColour(d: number): void {
    const p = this.page();
    p.colour = ((p.colour + d) % 16 + 16) % 16;
  }

  /** DELETE/INSERT a line above the cursor (the original's f3/f4). */
  insertLine(): void {
    const p = this.page();
    this.touch();
    p.cells.splice(this.row * PAGE_COLS, 0, ...blankCells(p.background, p.colour).slice(0, PAGE_COLS));
    p.cells.length = CELLS;
  }
  deleteLine(): void {
    const p = this.page();
    this.touch();
    p.cells.splice(this.row * PAGE_COLS, PAGE_COLS);
    p.cells.push(...blankCells(p.background, p.colour).slice(0, PAGE_COLS));
  }

  // --- serialisation (GET / PUT / STORE) ---
  /** Wire form for upload / mail.send (§5.4 of the Binding-B spec).
   *  ⚠ An unedited captured page goes back as its ORIGINAL BYTES; only pages
   *  the user actually composed or altered are re-encoded from cells. */
  toFrames(): EditorPage[] {
    return this.pages.map((p) => (p.raw
      ? { raw: p.raw }
      : { cells: p.cells, border: p.border, background: p.background }));
  }

  /** True when nothing has been composed or captured — used to refuse an
   *  upload of an empty buffer rather than send a blank page. */
  isEmpty(): boolean { return this.pages.every((p) => this.isBlank(p)); }

  toJSON(pagesOnly?: Page[]): string {
    return JSON.stringify({ format: 'compunet-editor-2', pages: pagesOnly ?? this.pages });
  }

  /** GET — replace the buffer from a previously PUT/STOREd file. */
  load(text: string): number {
    const data = JSON.parse(text) as { format?: string; pages?: Page[] };
    if (data.format !== 'compunet-editor-2' || !Array.isArray(data.pages) || !data.pages.length)
      throw new Error('not an editor file');
    this.pages = data.pages.map((p) => {
      const cells = Array.from({ length: CELLS }, (_, i) =>
        p.cells?.[i] ? { ...p.cells[i] } : { g: 0x20, fg: 1, bg: p.background ?? 0, rv: 0 as 0 | 1 });
      return { cells, border: p.border ?? 6, background: p.background ?? 0, colour: p.colour ?? 1, raw: p.raw };
    });
    this.cur = 0; this.row = 0; this.col = 0;
    return this.pages.length;
  }
}
