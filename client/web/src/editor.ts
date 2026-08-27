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

/** ⚠ The page limit is a SETTING, with a conforming floor (§8.4.2).
 *
 *  The original's ceiling was RAM — "10-15 pages simultaneously", a range
 *  because pages compress differently (RLE, §6.4). 15 is therefore the floor: a
 *  buffer smaller than the original's would fail work a C64 could do.
 *
 *  The default is higher because the failure mode changed. On the original a
 *  user captured a handful of pages deliberately; this client captures EVERY
 *  page viewed (§8.4.2), so reading six mail messages fills fifteen and starts
 *  evicting. Storage is not the constraint — 50 pages costs ~0.1 MB once
 *  unedited captures are held as their original bytes. */
export const MIN_PAGES = 15;
export const DEFAULT_MAX_PAGES = 50;

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

/** A run of identical cells: [count, glyph, fg, bg, rv]. */
type Run = [number, number, number, number, number];

function rleEncode(cells: Cell[]): Run[] {
  const out: Run[] = [];
  for (const c of cells) {
    const last = out[out.length - 1];
    if (last && last[1] === c.g && last[2] === c.fg && last[3] === c.bg && last[4] === c.rv) last[0]++;
    else out.push([1, c.g, c.fg, c.bg, c.rv]);
  }
  return out;
}

function rleDecode(runs: Run[], bg: number): Cell[] {
  const cells: Cell[] = [];
  for (const [n, g, fg, b, rv] of runs)
    for (let i = 0; i < n && cells.length < CELLS; i++)
      cells.push({ g, fg, bg: b, rv: (rv ? 1 : 0) as 0 | 1 });
  // A short or damaged run list must not yield a short page.
  while (cells.length < CELLS) cells.push({ g: 0x20, fg: 1, bg, rv: 0 });
  return cells;
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
  /** ⚠ CTRL+9 / CTRL+0 — reverse video ($12/$92, §5.7), and like the pen colour
   *  it is NOT in the help frame (§8.4.3) because it is not an editor command.
   *  Verified in the ROM: the editor's key loop hands anything below $85 to
   *  CHROUT ($888F -> JSR $FFD2), so $12/$92 reach the KERNAL's own reverse
   *  handling unfiltered — the same route the colour keys take.
   *
   *  ⚠ A MODE, not a character. It stays on until $92 or a CARRIAGE RETURN, so
   *  it spans cells and lives on the buffer rather than on any one of them. */
  reverse = false;
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
    this.changed();
    return true;
  }

  /** Remember the starting state when an edit begins. */
  beginEdit(): void {
    this.editing = true;
    if (!this.original) this.original = this.page().cells.map((c) => ({ ...c }));
  }

  page(): Page { return this.pages[this.cur]; }

  /** Any change to a page's content invalidates its captured bytes. */
  /** ⚠ Fired whenever the buffer changes, so persistence cannot be forgotten.
   *
   *  Seventeen call sites mutate this buffer. Asking each to remember to save
   *  is a rule that holds until someone adds the eighteenth — and the symptom
   *  (pages quietly stop persisting) is invisible until a user loses work. The
   *  buffer announces its own changes instead. */
  onChange: (() => void) | null = null;
  private changed(): void { this.onChange?.(); }

  private touch(): void { delete this.page().raw; this.changed(); }

  // --- page navigation (LAST / NEXT) ---
  last(): boolean { if (this.cur === 0) return false; this.cur--; this.home(); return true; }
  next(): boolean { if (this.cur >= this.pages.length - 1) return false; this.cur++; this.home(); return true; }

  // --- page management (NEW / COPY / ERASE) ---
  /** NEW — a fresh BLANK page after the current one. Not COPY. */
  /** ⚠ NEW and COPY evict too. On the original they go through the SAME page
   *  allocator as capture ($8495 and $84CB both reach $849B), so a full buffer
   *  drops its oldest page for them exactly as it does for a page arriving from
   *  Compunet. Enforcing the limit only on capture — as this did — let a user
   *  walk past it by hand, which then became permanent once the buffer
   *  persisted across restarts. */
  newPage(): string | null {
    const note = this.makeRoom();
    this.pages.splice(++this.cur, 0, blankPage());
    this.home();
    this.changed();
    return note;
  }
  /** COPY — a DUPLICATE of the current page after it. Not NEW. */
  copyPage(): string | null {
    const note = this.makeRoom();
    const p = this.page();
    this.pages.splice(++this.cur, 0, { ...p, cells: p.cells.map((c) => ({ ...c })) });
    this.home();
    this.changed();
    return note;
  }
  /** ERASE — remove the current page. The buffer never becomes empty. */
  erasePage(): void {
    this.changed();
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

  /** The buffer's page limit. Changing it takes effect on the next page added;
   *  an over-limit buffer is trimmed by makeRoom() rather than truncated here,
   *  so the eviction rule stays in one place. */
  maxPages = DEFAULT_MAX_PAGES;

  /** ⚠ Make room by DELETING THE OLDEST PAGE — the original's behaviour.
   *
   *  Verified in the C64 ROM: the page allocator at $849B, on overflow, does
   *  `JSR $8C40` and then `JMP $849B` — it calls a routine and RETRIES, so that
   *  routine must free space. $8C40 takes the FIRST page in the buffer
   *  ($8015/$8016), deletes it, compacts everything down over it, and adjusts
   *  the current-page pointer so the user stays on the page they were looking
   *  at — unless that was the page evicted.
   *
   *  So capture never fails and never asks: the buffer is a rolling window of
   *  the most recent pages. NEW and COPY go through the same allocator, so they
   *  evict too. A page the user COMPOSED can be evicted by pages they merely
   *  read; the original drew no distinction between the two, and neither does
   *  this. That is a real way to lose work, which is why STORE exists and why
   *  the client says so on the way past. */
  private makeRoom(): string | null {
    let dropped = 0;
    while (this.pages.length >= Math.max(MIN_PAGES, this.maxPages)) {
      this.pages.shift();
      dropped++;
      // Follow the user's position down, as $8C40 does. If their page was the
      // one evicted, cur stays put and lands on what is now the oldest.
      if (this.cur > 0) this.cur--;
    }
    if (!dropped) return null;
    return `Buffer full — dropped the oldest page${dropped > 1 ? 's' : ''} (STORE keeps a copy)`;
  }

  /** Append a page viewed on Compunet (§8.4.2), and MOVE TO IT.
   *
   *  Always succeeds: the oldest page is evicted if need be. Returns a message
   *  when that happened, so the client can say so — the original said nothing,
   *  but it also could not persist a buffer or hold fifty pages, and silence
   *  about discarded work is the one thing §8.4.2 is right to insist on.
   *
   *  ⚠ The captured page BECOMES THE CURRENT ONE. The original's allocator does
   *  exactly this — `$849B` opens a page with `LDA $8017 / STA $8019`, writing
   *  the newly allocated address straight into the current-page pointer — so
   *  after reading, the editor is already on what you just read. §8.4.2 used to
   *  say capture "MUST NOT move the current page position"; that was invented
   *  for the two-pane case and is not what the C64 does.
   *
   *  The one exception is an edit IN PROGRESS. The original could not be in
   *  that state — one screen, so you cannot read and edit at once — but a
   *  client showing both at once can, and yanking the page out from under a
   *  cursor loses the user's place for no gain. */
  capture(p: Page): string | null {
    if (this.isPristine()) { this.pages[0] = p; return null; }
    const note = this.makeRoom();
    this.pages.push(p);
    if (!this.editing) { this.cur = this.pages.length - 1; this.home(); }
    this.changed();
    return note;
  }

  /** FREE — PAGES remaining (§8.4.1).
   *
   *  ⚠ The original reported characters, against a memory ceiling this client
   *  does not have. Reporting pages is honest about what actually limits us and
   *  needs no invented constant; the previous character figure was derived from
   *  a capacity that was never verified against the disassembly. */
  free(): number {
    return Math.max(0, Math.max(MIN_PAGES, this.maxPages) - this.pages.length);
  }

  // --- editing (EDIT mode) ---
  /** Overwrite-at-cursor, as the original edits (its f6 toggles insert). */
  typeChar(ch: string): void {
    const p = this.page();
    this.touch();
    const i = this.row * PAGE_COLS + this.col;
    // f6 off: the character changes, the colour under it does not.
    const fg = this.colourOn ? p.colour : p.cells[i].fg;
    p.cells[i] = { g: charToGlyph(ch, this.lowerCase), fg, bg: p.background,
                   rv: this.reverse ? 1 : 0 };
    // ⚠ The wrap does NOT clear reverse — only a CR does (§5.7). Running off
    // the right-hand edge is not a newline, and a bar drawn to the screen edge
    // is exactly the artwork that would break if it were.
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
  cycleBorder(d: number): void { const p = this.page(); p.border = ((p.border + d) % 16 + 16) % 16; this.changed(); }

  backspace(): void {
    if (this.col === 0) { if (this.row > 0) { this.row--; this.col = PAGE_COLS - 1; } return; }
    this.col--;
    const p = this.page();
    this.touch();
    p.cells[this.row * PAGE_COLS + this.col] = { g: 0x20, fg: p.colour, bg: p.background, rv: 0 };
  }

  /** ⚠ A CARRIAGE RETURN CLEARS REVERSE (§5.7), as it does on the C64.
   *
   *  This is not cosmetic: the server's encoder emits a `$92` before every CR
   *  (`_encode_cells`) and resets its own flag there, so a client that let the
   *  mode survive a newline would disagree with its own wire format — the page
   *  would come back un-reversed from that line on. */
  newline(): void { this.col = 0; this.reverse = false; this.moveRow(1); }

  moveRow(d: number): void { this.row = Math.max(0, Math.min(PAGE_ROWS - 1, this.row + d)); }
  moveCol(d: number): void { this.col = Math.max(0, Math.min(PAGE_COLS - 1, this.col + d)); }


  /** Set the pen directly — the C64's CTRL+1-8 / C=+1-8 colour keys (§8.4.3).
   *  ⚠ The pen is what the CURSOR is drawn in too, so changing it is visible
   *  immediately even before anything is typed. */
  setColour(c: number): void { this.page().colour = c & 0x0F; this.changed(); }

  /** Set screen / border directly, for a picker (§8.4.3). Screen colour must
   *  reach every cell — see cycleBackground for why. */
  setBackground(c: number): void {
    const p = this.page();
    p.background = c & 0x0F;
    for (const cell of p.cells) cell.bg = p.background;
    this.touch();
  }
  setBorder(c: number): void { this.page().border = c & 0x0F; this.changed(); }

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
    p.cells[i] = { g: code & 0xFF, fg, bg: p.background, rv: this.reverse ? 1 : 0 };
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

  /** ⚠ Pages are stored RUN-LENGTH ENCODED (`compunet-editor-3`).
   *
   *  A page written cell-by-cell is 38.5 KB of JSON; fifty of them is 1.9 MB,
   *  which is close enough to a browser's storage quota to be a gamble — some
   *  count it in UTF-16 units, halving what looks like 5 MB. Runs take a
   *  typical page to a few KB. This is the same format PUT and STORE write, so
   *  a persisted buffer and a STOREd file stay interchangeable — one format,
   *  one loader, and the version tag is the migration hook.
   *
   *  `raw` is kept beside the runs: it is small, and §8.4.2 needs it so an
   *  unedited captured page re-uploads as the bytes it arrived as. */
  toJSON(pagesOnly?: Page[]): string {
    const pages = (pagesOnly ?? this.pages).map((p) => ({
      rle: rleEncode(p.cells),
      border: p.border, background: p.background, colour: p.colour,
      ...(p.raw ? { raw: p.raw } : {}),
    }));
    return JSON.stringify({ format: 'compunet-editor-3', pages });
  }

  /** GET — replace the buffer from a previously PUT/STOREd file. */
  /** Accepts both formats: `-3` (runs) and `-2` (cells), so files written by an
   *  earlier build still load. */
  load(text: string): number {
    const data = JSON.parse(text) as
      { format?: string; pages?: (Partial<Page> & { rle?: Run[] })[] };
    const known = data.format === 'compunet-editor-3' || data.format === 'compunet-editor-2';
    if (!known || !Array.isArray(data.pages) || !data.pages.length)
      throw new Error('not an editor file');
    this.pages = data.pages.map((p) => {
      const bg = p.background ?? 0;
      const cells = p.rle
        ? rleDecode(p.rle, bg)
        : Array.from({ length: CELLS }, (_, i) =>
            p.cells?.[i] ? { ...p.cells[i] } : { g: 0x20, fg: 1, bg, rv: 0 as 0 | 1 });
      return { cells, border: p.border ?? 6, background: bg, colour: p.colour ?? 1, raw: p.raw };
    });
    this.cur = 0; this.row = 0; this.col = 0;
    this.changed();
    return this.pages.length;
  }
}
