// Canvas renderer: draws a 40x24 cell grid with the C64 font/palette, and
// composes a directory screen from its JSON (client owns layout, §7.5-§7.7).

import type { Assets, Cell, DirectoryMsg, FrameMsg } from './protocol';

export const COLS = 40, ROWS = 24, CELL = 8;
// ⚠ No WHITE here any more. The selection bar used to draw its text white; the
// original reverses the cell instead, so the text shows in the screen background
// (§7.7, $A6DC). Nothing in the directory is white.
const RED = 2, BLUE = 6, TEMPLATE_BG = 15;

/** ⚠ The original's contrast table at `$93A4`, indexed by the SCREEN background.
 *
 *  Every entry is black (0) or white (1), chosen by luminance. The client keeps
 *  anything it draws over a frame in this colour — `$90A0` loads it into `$0286`
 *  before printing a string, and `$938B` writes it into the duckshoot row's
 *  colour RAM — so its own furniture stays legible whatever the page background
 *  is. That is also why the duckshoot is only ever black or white.
 *
 *  Shared with the editor's cursor (§8.4.3), which needs the same guarantee. */
export const CONTRAST = [1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0];
/** template geometry: left border 0, divider 30, right border 39 (§7.7/§A.6) */
const DIVIDER_COL = 30;

/** ⚠ The original's 6-character duckshoot cells (§4.9.3). These carry their own
 *  padding — that is what puts a space between words. `FINISH` fills its cell
 *  with none of its own, so the gap after it comes from the NEXT word's leading
 *  space; padding the bare names instead runs FINISH into whatever follows. */
const DUCK_CELL: Record<string, string> = {
  HELP: ' HELP ', DIR: ' DIR  ', SHOW: ' SHOW ', BACK: ' BACK ', GOTO: ' GOTO ',
  UCAT: ' UCAT ', MAIL: ' MAIL ', ACCNT: 'ACCNT ', SAVE: ' SAVE ', EDITR: 'EDITR ',
  LEAVE: 'LEAVE ', PRINT: 'PRINT ', LIFE: ' LIFE ', BUY: ' BUY  ', UPLD: ' UPLD ',
  VOTE: ' VOTE ', MORE: ' MORE ', ALL: ' ALL  ', SEND: ' SEND ', FINISH: 'FINISH',
  ABORT: 'ABORT ', LOAD: ' LOAD ', LAST: ' LAST ', NEXT: ' NEXT ', GET: ' GET  ',
  DOS: ' DOS  ', ID: '  ID  ', DONE: ' DONE ', COL: ' COL  ',
};

/** PETSCII byte -> C64 screen code (spec §5.3). */
export function petsciiToScreencode(b: number): number {
  if (b >= 0x20 && b <= 0x3F) return b;
  if (b >= 0x40 && b <= 0x5F) return b & 0x1F;
  if (b >= 0x60 && b <= 0x7F) return (b & 0x1F) | 0x40;
  if (b >= 0xA0 && b <= 0xBF) return (b & 0x1F) | 0x60;
  if (b >= 0xC0 && b <= 0xDE) return b & 0x7F;
  if (b === 0xFF) return 0x5E;
  return b & 0x7F;
}

/** directory text is unshifted uppercase ASCII (§7.2) -> uppercase/graphics glyph */
function asciiGlyph(ch: string): number {
  return petsciiToScreencode(ch.charCodeAt(0) & 0xFF);
}

export class Renderer {
  private ctx: CanvasRenderingContext2D;
  constructor(
    private canvas: HTMLCanvasElement,
    private assets: Assets,
    private wrap: HTMLElement,
    private scale = 2,
  ) {
    this.canvas.width = COLS * CELL * scale;
    // One extra row for the duckshoot: it lives OUTSIDE the 40x24 content grid
    // (§4.9.2) — which is exactly why the content area is 24 rows, not 25.
    this.canvas.height = (ROWS + 1) * CELL * scale;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('no 2d context');
    this.ctx = ctx;
  }

  private drawGlyph(cell: Cell, col: number, row: number): void {
    const bmp = this.assets.font[cell.g] || this.assets.font[0x20];
    const s = this.scale, px = col * CELL * s, py = row * CELL * s;
    this.ctx.fillStyle = this.assets.palette[cell.bg]; this.ctx.fillRect(px, py, CELL * s, CELL * s);
    this.ctx.fillStyle = this.assets.palette[cell.fg];
    for (let y = 0; y < 8; y++) {
      const byte = bmp[y];
      for (let x = 0; x < 8; x++) {
        let on = (byte >> (7 - x)) & 1;
        if (cell.rv) on ^= 1;
        if (on) this.ctx.fillRect(px + x * s, py + y * s, s, s);
      }
    }
  }

  renderGrid(cells: Cell[], background: number): void {
    this.ctx.fillStyle = this.assets.palette[background & 0x0F];
    this.ctx.fillRect(0, 0, this.canvas.width, ROWS * CELL * this.scale);
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) this.drawGlyph(cells[r * COLS + c], c, r);
  }

  setBorder(idx: number): void { this.wrap.style.background = this.assets.palette[idx & 0x0F]; }

  renderFrame(frame: FrameMsg): void {
    this.renderGrid(frame.cells, frame.background);
    this.setBorder(frame.border);
  }

  private put(grid: Cell[], row: number, col: number, text: string,
              fg: number, bg: number, rv: 0 | 1 = 0): void {
    const t = (text || '').toUpperCase();
    for (let i = 0; i < t.length && col + i < COLS; i++) {
      if (col + i < 0) continue;
      grid[row * COLS + (col + i)] = { g: asciiGlyph(t[i]), fg, bg, rv };
    }
  }

  /** Compose the 40x24 directory screen: template chrome + overlaid entries. */
  renderDirectory(dir: DirectoryMsg, sel: number, colIdx: number): void {
    const g: Cell[] = this.assets.template.cells.map((x) => ({ ...x }));
    // Part-1 header (COMPUNET logo) overlays the top rows (§7.7). Copy only inked
    // cells so blank header cells don't clobber the template box below.
    if (dir.header) {
      const h = dir.header.cells;
      for (let r = 0; r <= 6; r++)
        for (let c = 0; c < COLS; c++) {
          const cell = h[r * COLS + c];
          if (cell.g !== 0x20 || cell.rv || cell.bg !== TEMPLATE_BG) g[r * COLS + c] = { ...cell };
        }
    }
    // Content sits at the box interior: base column 1 (left border col 0), title col 8,
    // type col 25; right pane base col 31 (one past the divider at col 30). §7.3/§7.7.
    if (dir.breadcrumb[0]) this.put(g, 7, 1, dir.breadcrumb[0], BLUE, TEMPLATE_BG);
    if (dir.breadcrumb[1]) this.put(g, 8, 1, dir.breadcrumb[1], BLUE, TEMPLATE_BG);
    if (dir.mailWaiting) this.put(g, 8, 25, 'MAIL', RED, TEMPLATE_BG);   // aligned with the type column
    this.put(g, 8, 31, dir.columns[colIdx] || '', BLUE, TEMPLATE_BG);

    dir.entries.forEach((e, i) => {
      const row = 10 + i;
      const colour = i === 0 ? RED : BLUE;          // first entry always red (§7.7)
      const selected = i === sel;
      // ⚠ The selection bar is REVERSE VIDEO, not a coloured background.
      //
      // Verified in the original ($A6DC): it walks the row setting `ORA #$80` on
      // each screen code and writing the bar colour to COLOUR RAM. It cannot do
      // anything else — the C64 has one background register for the whole screen
      // (§8.4.3), so a per-cell background does not exist and `cnet.prg` contains
      // no colour-RAM write that could fake one.
      //
      // The consequence is visible: reversing a glyph fills the cell with the
      // FOREGROUND and knocks the character out in the BACKGROUND, so the text
      // inside the bar appears in the screen's background colour — not white, as
      // this drew it before. Selected and unselected therefore differ ONLY by
      // `rv`, exactly as they differ only by bit 7 on the original.
      const fg = colour;
      const bg = TEMPLATE_BG;
      const rv: 0 | 1 = selected ? 1 : 0;
      if (selected)
        // Columns 1-38, SKIPPING the divider at 30 — it stays visible through the
        // highlighted row (§7.7, and `CPY #$1E / BEQ` at $A6E7 in the original).
        for (let c = 1; c <= 38; c++) {
          if (c === DIVIDER_COL) continue;
          g[row * COLS + c] = { g: 0x20, fg, bg, rv: 1 };
        }
      if (selected) {                                // page number only on selected row
        const ps = String(e.page);
        this.put(g, row, 7 - ps.length, ps, fg, bg, rv);  // right-justified, ending at col 6
      }
      this.put(g, row, 8, e.title, fg, bg, rv);
      const type = e.type + (e.size ? String(e.size) : '') + (e.hasSubdir ? '+' : '');
      this.put(g, row, 25, type, fg, bg, rv);
      // right pane rendered verbatim from col 31 (one past the divider at 30); the
      // server already applied the per-column justification (§7.3), so no client layout.
      const val = e.values?.[colIdx] || '';
      if (val) this.put(g, row, 31, val, fg, bg, rv);
    });

    (dir.advert || []).slice(0, 2).forEach((line, i) => {
      const col = Math.max(0, Math.floor((COLS - line.length) / 2));
      this.put(g, 22 + i, col, line, BLUE, TEMPLATE_BG);
    });

    this.renderGrid(g, TEMPLATE_BG);
    this.setBorder(this.assets.template.border);
  }

  /** The Compunet pane before a session exists. Deliberately plain: with no
   *  session there is no Compunet screen and no command row (§8.4). */
  renderIdle(): void {
    const g: Cell[] = Array.from({ length: COLS * ROWS }, () => ({ g: 0x20, fg: 6, bg: 0, rv: 0 as 0 | 1 }));
    const put = (r: number, t: string, fg: number): void => {
      const c0 = Math.max(0, Math.floor((COLS - t.length) / 2));
      for (let i = 0; i < t.length && c0 + i < COLS; i++)
        g[r * COLS + c0 + i] = { g: asciiGlyph(t[i]), fg, bg: 0, rv: 0 };
    };
    put(10, 'COMPUNET REBORN', 14);
    put(12, 'NOT CONNECTED', 11);
    this.renderGrid(g, 0);
    this.setBorder(6);
  }

  /** Draw the editor's current page (§8.4.1).
   *  ⚠ The page is the FULL 40x24 grid — an editor page and a frame are the
   *  same thing (§8.4.2), so nothing may be reserved here for chrome. The
   *  buffer position ("page 2 of 5") belongs in the pane's own furniture, not
   *  in a row stolen from the page. */
  /** `cursor` carries the blink phase AND the colour chosen for this tick
   *  (§8.4.3) — the original blinks the cursor in colour as well as in reverse
   *  video, which is what keeps it visible over any background. Pass null when
   *  not editing. */
  renderEditorPage(cells: Cell[], background: number, border: number,
                   row: number, col: number,
                   cursor: { colour: number; reverse: boolean } | null): void {
    const g: Cell[] = cells.map((c) => ({ ...c }));
    if (cursor) {
      const i = row * COLS + col;
      // ⚠ Both halves matter. Reverse alone leaves the cursor invisible
      // wherever the cell's colour matches the background; the colour alone
      // would not read as a cursor at all.
      if (g[i]) g[i] = { ...g[i], fg: cursor.colour, rv: cursor.reverse ? 1 : 0 };
    }
    this.renderGrid(g, background);
    this.setBorder(border);
  }

  /** Draw the duckshoot on the row below the content grid (§4.9).
   *  The ROW scrolls and the CENTRE cell is the selection — words are laid out
   *  around `centre`, which always lands in the middle of the screen. */
  /** The single-frame case has no duckshoot at all — just a prompt (§4.8).
   *  Printed in the contrast colour on the screen background, like any string
   *  the client puts over a frame ($90A0 loads `$93A4[bg]` into `$0286`). */
  renderPrompt(text: string, background = 0): void {
    const s = this.scale, row = ROWS, ink = CONTRAST[background & 0x0F];
    this.ctx.fillStyle = this.assets.palette[background & 0x0F];
    this.ctx.fillRect(0, row * CELL * s, this.canvas.width, CELL * s);
    // ⚠ LEFT justified, not centred (§4.8). The prompt replaces the duckshoot,
    // and the duckshoot starts at the left edge — centring it makes the bottom
    // row jump sideways as the client moves between reading and choosing.
    for (let i = 0; i < text.length && i < COLS; i++)
      this.drawGlyph({ g: asciiGlyph(text[i]), fg: ink, bg: background, rv: 0 }, i, row);
  }

  /** ⚠ The row is a solid BAR with the words knocked out of it, and the centre
   *  cell is the one that is NOT reversed (§4.9.3).
   *
   *  Verified in the original. `$938B` fills all forty cells of row 24 with
   *  `$A0` — a reversed space, i.e. a solid block — coloured `$93A4[$D021]`.
   *  `$945A` then writes each character with `ORA #$80`, EXCEPT columns 18-23
   *  (`CPX #$12 / BCC + / CPX #$18 / BCC`), and gives every cell that same one
   *  colour. So the selection is a HOLE in the bar, not a differently-coloured
   *  cell, and the row's two colours are the contrast colour and the screen
   *  background — never a fixed black and white.
   *
   *  That is what makes it invert: over a light page the bar is black, over a
   *  dark one it is white. Hardcoding black-with-white-text looks right on a
   *  directory (background 15) and is exactly inverted on a dark editor page. */
  renderDuckshoot(words: string[], centre: number, background = 0): void {
    const s = this.scale, row = ROWS, WORD = 6, VISIBLE = 7, MID = 3;
    const bar = CONTRAST[background & 0x0F];
    this.ctx.fillStyle = this.assets.palette[background & 0x0F];
    this.ctx.fillRect(0, row * CELL * s, this.canvas.width, CELL * s);
    if (!words.length) return;
    if (words.length === 1 && words[0] === ' PRESSANYKEY') return;
    // ⚠ Cells start at column 0 — 0, 6, 12, 18, 24, 30, 36 — so the CENTRE is
    // columns 18-23 and only the LAST cell clips (4 of its 6 characters). The
    // original starts its write loop at `LDX #$00` ($9458). Centring the 42
    // columns instead put the row at -1, shifting every cell one left, clipping
    // BOTH ends, and costing the first word its leading character.
    const startCol = 0;
    for (let slot = 0; slot < VISIBLE; slot++) {
      // ⚠ The row is a CIRCULAR BUFFER: every visible cell is filled, wrapping
      // as needed, so a short set REPEATS rather than leaving blanks. Verified
      // against the C64's mail row — six commands in seven cells:
      //   ID EDITR DONE [SEND] SHOW MORE ID    <- ID appears twice, by design
      // Suppressing the repeat leaves the row blank on the left (§4.9.4).
      const wi = (((centre + slot - MID) % words.length) + words.length) % words.length;
      const name = words[wi];
      const text = (DUCK_CELL[name] ?? name.padEnd(WORD)).slice(0, WORD);
      const selected = slot === MID;
      for (let i = 0; i < WORD; i++) {
        const col = startCol + slot * WORD + i;
        if (col < 0 || col >= COLS) continue;         // clip at the screen edges
        // Every cell carries the SAME colour; only `rv` differs, and only for
        // the centre cell — one bit, as on the original.
        this.drawGlyph(
          { g: asciiGlyph(text[i]), fg: bar, bg: background, rv: selected ? 0 : 1 },
          col, row,
        );
      }
    }
  }
}
