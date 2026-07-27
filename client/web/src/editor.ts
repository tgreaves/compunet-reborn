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
import { CONTRAST } from './render';

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

  // --- cursor blink (§8.4.3) -----------------------------------------------
  //
  // ⚠ The cursor blinks in COLOUR as well as in reverse video, and that is what
  // stops it disappearing. Reconstructed from the original's blink routine at
  // $87A0 in the cartridge ROM:
  //
  //   $87CC  LDA ($D1),Y / EOR #$80 / STA ($D1),Y   toggle reverse video
  //   $87D2  LDX $0286                              intended cursor colour
  //   $87D6  EOR ($F3),Y / AND #$0F                 XOR with the cell's colour
  //   $87DA  BNE +                                    differ -> keep $0286
  //   $87DC  LDX $C158                                SAME  -> use the alternate
  //   $87E0  STA ($F3),Y                            write the choice back
  //
  // Because the choice is written back, the test flips on the next tick, so the
  // colour oscillates between the two. A single "pick a contrasting colour"
  // would give a statically-coloured cursor blinking only in reverse — visibly
  // different, and it is why guessing this from first principles gets it wrong.
  //
  // The page is NEVER mutated by any of this: `cursorColour` is the colour-RAM
  // cell, held here so the cell underneath is restored simply by not drawing.

  /** ⚠ The OTHER half of the original's answer, and both are needed.
   *
   *  The blink routine only stops the cursor vanishing into the CHARACTER's
   *  colour. What stops it vanishing into the BACKGROUND is that the colour it
   *  uses ($0286) is itself derived from the background, through the CONTRAST
   *  table ($93A4) that render.ts owns — the same table that colours the
   *  duckshoot row (§4.9.3) and every string the client prints over a frame.
   *
   *  In the editor the user picks the drawing colour and can pick the
   *  background's, so this is applied as the final guard: whatever the blink
   *  chooses, it may not equal the cell's background. */

  /** Reverse-video phase — the `EOR #$80` ($87CE). */
  cursorReverse = false;
  /** What is currently "written" in the cursor cell's colour RAM. */
  private cursorColour = 0;
  /** $C158 — the colour to fall back on when the intended one clashes. */
  private cursorAlternate = 0;
  /** Which cell the above describes; a move re-captures ($8B30). */
  private cursorCell = -1;

  /** $87A1-$87AB — on arriving at a cell, remember its alternate colour.
   *
   *  Polarity VERIFIED: bit 7 of $C15B SET means colour ON (the cell takes the
   *  pen), clear means OFF (it keeps its own). `BIT $C15B / BPL` at $87A3 skips
   *  the `LDA $0286`, so only the set case picks up the pen. $C15B is f6's flag
   *  — the editor's function-key table at $88BC, indexed by (key - $85) * 2,
   *  sends f6 to the toggle at $88E8, with f5 toggling the KERNAL's RPTFLG
   *  ($028A, auto-repeat) beside it.
   *
   *  ⚠ Note WHERE the flag acts: not on the typing path at all. $C15B is read
   *  in exactly one place, this cursor routine, and the colour reaches the cell
   *  through the cursor's restore ($87ED writes $C158 back). "Typing does not
   *  change the colour under it" is a property of the CURSOR, which is why the
   *  editor never writes colour RAM directly. */
  private captureCursorCell(): void {
    const p = this.page();
    const i = this.row * PAGE_COLS + this.col;
    const own = p.cells[i]?.fg ?? p.colour;
    this.cursorAlternate = this.colourOn ? p.colour : own;
    this.cursorColour = own;
    this.cursorCell = i;
  }

  /** One blink tick ($87CA-$87E0). Call on the blink interval while editing. */
  tickCursor(): void {
    const i = this.row * PAGE_COLS + this.col;
    if (i !== this.cursorCell) this.captureCursorCell();
    this.cursorReverse = !this.cursorReverse;
    const draw = this.page().colour;
    // The clash test, XOR-equality on the colour nybble: identical means the
    // cursor would be indistinguishable, so take the alternate instead.
    this.cursorColour = (this.cursorColour === draw) ? this.cursorAlternate : draw;
  }

  /** The cursor's current appearance, or null when not editing. */
  cursorState(): { colour: number; reverse: boolean } | null {
    if (!this.editing) return null;
    const i = this.row * PAGE_COLS + this.col;
    if (i !== this.cursorCell) this.captureCursorCell();
    // The background guard, applied last: a cursor the same colour as the cell
    // it sits on is invisible in BOTH blink phases, which is the reported bug.
    const bg = this.page().cells[i]?.bg ?? this.page().background;
    const colour = this.cursorColour === bg
      ? CONTRAST[bg & 0x0F]
      : this.cursorColour;
    return { colour, reverse: this.cursorReverse };
  }

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
  /** f7 — screen colour. Each press steps one colour through the palette and
   *  wraps (verified on the C64: yellow, orange, brown, light red, dark grey…).
   *
   *  ⚠ The screen background must be written to EVERY CELL, not just the page.
   *  The C64 has one background register ($D021) for the whole screen and colour
   *  RAM holds only a foreground, so a page where cells disagree with the page's
   *  background cannot occur on hardware — the invariant is that they are all
   *  equal. Our `Cell` carries `bg` per cell (the binding fills it in, api §5.4,
   *  and the directory chrome uses it for the selection bar), so the renderer
   *  paints from it and updating the page field alone changed nothing visible:
   *  f7 looked completely dead while quietly working. Only freshly typed cells
   *  picked the new colour up, because `typeChar` writes `bg: p.background`. */
  cycleBackground(d: number): void {
    const p = this.page();
    p.background = ((p.background + d) % 16 + 16) % 16;
    for (const c of p.cells) c.bg = p.background;
    this.touch();
  }
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


  /** Set the pen directly — the C64's CTRL+1-8 / C=+1-8 colour keys (§8.4.3).
   *  ⚠ The pen is what the CURSOR is drawn in too, so changing it is visible
   *  immediately even before anything is typed. */
  setColour(c: number): void { this.page().colour = c & 0x0F; }

  /** Set screen / border directly, for a picker (§8.4.3). Screen colour must
   *  reach every cell — see cycleBackground for why. */
  setBackground(c: number): void {
    const p = this.page();
    p.background = c & 0x0F;
    for (const cell of p.cells) cell.bg = p.background;
    this.touch();
  }
  setBorder(c: number): void { this.page().border = c & 0x0F; }

  /** Write a raw SCREEN CODE at the cursor and advance — the route for glyphs
   *  that have no letter to type: the graphics banks (§5.3).
   *
   *  ⚠ charToGlyph only maps letters, digits and punctuation, so before this
   *  existed the editor could not produce a single graphics character — on a
   *  client whose whole purpose is composing PETSCII pages. */
  typeGlyph(code: number): void {
    const p = this.page();
    const i = this.row * PAGE_COLS + this.col;
    this.touch();
    const fg = this.colourOn ? p.colour : p.cells[i].fg;
    p.cells[i] = { g: code & 0xFF, fg, bg: p.background, rv: 0 };
    if (++this.col >= PAGE_COLS) { this.col = 0; this.moveRow(1); }
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
