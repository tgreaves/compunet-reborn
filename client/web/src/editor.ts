// The frame editor (spec §8.4 / §8.4.1).
//
// This is a CLIENT feature — it sends nothing. Its output leaves through the
// upload path (§8.3.2): UPLD for Jungle pages, SEND for Courier mail.
//
// ⚠ The editor holds a MULTI-PAGE BUFFER with a current position, not one page.
// LAST/NEXT/NEW/COPY/ERASE only mean anything against such a buffer, and PUT
// (one page) vs STORE (the whole buffer) only differ because it exists. A single
// text box is an upload form, not this context — see §8.4.1.

import type { EditorPage } from './protocol';

export const PAGE_COLS = 40, PAGE_ROWS = 23;

/** A page as the editor holds it: fixed-size character cells, one colour (see
 *  the known model gap in the Binding-B spec §5.4 — no mid-line colour yet). */
export interface Page { lines: string[]; colour: number; border: number; background: number; }

function blankPage(): Page {
  return { lines: Array(PAGE_ROWS).fill(''), colour: 5, border: 6, background: 0 };
}

/** The C64 editor reported free space in characters; keep the same units so
 *  FREE means the same thing to a user who knows the original (§8.4.1). */
const CAPACITY = 64 * PAGE_COLS * PAGE_ROWS;

export class EditorBuffer {
  pages: Page[] = [blankPage()];
  cur = 0;
  /** cursor within the current page, only meaningful in EDIT mode */
  row = 0;
  col = 0;
  editing = false;

  page(): Page { return this.pages[this.cur]; }

  // --- page navigation (LAST / NEXT) ---
  last(): boolean { if (this.cur === 0) return false; this.cur--; this.home(); return true; }
  next(): boolean { if (this.cur >= this.pages.length - 1) return false; this.cur++; this.home(); return true; }

  // --- page management (NEW / COPY / ERASE) ---
  /** NEW — a fresh BLANK page after the current one. Not COPY. */
  newPage(): void { this.pages.splice(++this.cur, 0, blankPage()); this.home(); }
  /** COPY — a DUPLICATE of the current page after it. Not NEW. */
  copyPage(): void {
    const p = this.page();
    this.pages.splice(++this.cur, 0, { ...p, lines: p.lines.slice() });
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

  /** FREE — characters remaining, in the original's units. */
  free(): number {
    const used = this.pages.reduce((n, p) => n + p.lines.reduce((m, l) => m + l.length, 0), 0);
    return Math.max(0, CAPACITY - used);
  }

  // --- editing (EDIT mode) ---
  private setLine(r: number, text: string): void {
    this.page().lines[r] = text.slice(0, PAGE_COLS);
  }

  /** Overwrite-at-cursor, as the original edits (its f6 toggles insert). */
  typeChar(ch: string): void {
    const line = (this.page().lines[this.row] ?? '').padEnd(this.col, ' ');
    this.setLine(this.row, line.slice(0, this.col) + ch.toUpperCase() + line.slice(this.col + 1));
    if (++this.col >= PAGE_COLS) { this.col = 0; this.moveRow(1); }
  }

  backspace(): void {
    if (this.col === 0) { if (this.row > 0) { this.row--; this.col = PAGE_COLS - 1; } return; }
    this.col--;
    const line = (this.page().lines[this.row] ?? '').padEnd(this.col + 1, ' ');
    this.setLine(this.row, line.slice(0, this.col) + ' ' + line.slice(this.col + 1));
  }

  newline(): void { this.col = 0; this.moveRow(1); }

  moveRow(d: number): void { this.row = Math.max(0, Math.min(PAGE_ROWS - 1, this.row + d)); }
  moveCol(d: number): void { this.col = Math.max(0, Math.min(PAGE_COLS - 1, this.col + d)); }

  /** DELETE/INSERT a line above the cursor (the original's f3/f4). */
  insertLine(): void {
    this.page().lines.splice(this.row, 0, '');
    this.page().lines.length = PAGE_ROWS;
  }
  deleteLine(): void {
    this.page().lines.splice(this.row, 1);
    while (this.page().lines.length < PAGE_ROWS) this.page().lines.push('');
  }

  // --- serialisation (GET / PUT / STORE) ---
  /** Wire form for upload / mail.send (§5.4 of the Binding-B spec). */
  toFrames(): EditorPage[] {
    return this.pages.map((p) => ({
      lines: p.lines.slice(), colour: p.colour, border: p.border, background: p.background,
    }));
  }

  /** True when nothing has actually been composed — used to refuse an upload
   *  of an empty buffer rather than send a blank page. */
  isEmpty(): boolean {
    return this.pages.every((p) => p.lines.every((l) => !l.trim()));
  }

  toJSON(pagesOnly?: Page[]): string {
    return JSON.stringify({ format: 'compunet-editor-1', pages: pagesOnly ?? this.pages });
  }

  /** GET — replace the buffer from a previously PUT/STOREd file. */
  load(text: string): number {
    const data = JSON.parse(text) as { format?: string; pages?: Page[] };
    if (data.format !== 'compunet-editor-1' || !Array.isArray(data.pages) || !data.pages.length)
      throw new Error('not an editor file');
    this.pages = data.pages.map((p) => ({
      lines: Array.from({ length: PAGE_ROWS }, (_, i) => String(p.lines?.[i] ?? '').slice(0, PAGE_COLS)),
      colour: p.colour ?? 5, border: p.border ?? 6, background: p.background ?? 0,
    }));
    this.cur = 0; this.row = 0; this.col = 0;
    return this.pages.length;
  }
}
