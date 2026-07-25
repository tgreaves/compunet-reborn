// Canvas renderer: draws a 40x24 cell grid with the C64 font/palette, and
// composes a directory screen from its JSON (client owns layout, §7.5-§7.7).

import type { Assets, Cell, DirectoryMsg, FrameMsg } from './protocol';

export const COLS = 40, ROWS = 24, CELL = 8;
const RED = 2, BLUE = 6, WHITE = 1, TEMPLATE_BG = 15;

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
    this.canvas.height = ROWS * CELL * scale;
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
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++) this.drawGlyph(cells[r * COLS + c], c, r);
  }

  setBorder(idx: number): void { this.wrap.style.background = this.assets.palette[idx & 0x0F]; }

  renderFrame(frame: FrameMsg): void {
    this.renderGrid(frame.cells, frame.background);
    this.setBorder(frame.border);
  }

  private put(grid: Cell[], row: number, col: number, text: string, fg: number, bg: number): void {
    const t = (text || '').toUpperCase();
    for (let i = 0; i < t.length && col + i < COLS; i++) {
      if (col + i < 0) continue;
      grid[row * COLS + (col + i)] = { g: asciiGlyph(t[i]), fg, bg, rv: 0 };
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
    if (dir.breadcrumb[0]) this.put(g, 7, 2, dir.breadcrumb[0], BLUE, TEMPLATE_BG);
    if (dir.breadcrumb[1]) this.put(g, 8, 2, dir.breadcrumb[1], BLUE, TEMPLATE_BG);
    if (dir.mailWaiting) this.put(g, 8, 22, 'MAIL', RED, TEMPLATE_BG);
    this.put(g, 8, 31, dir.columns[colIdx] || '', BLUE, TEMPLATE_BG);

    dir.entries.forEach((e, i) => {
      const row = 10 + i;
      const colour = i === 0 ? RED : BLUE;          // first entry always red (§7.7)
      const selected = i === sel;
      const fg = selected ? WHITE : colour;
      const bg = selected ? colour : TEMPLATE_BG;
      if (selected)
        for (let c = 1; c <= 38; c++) g[row * COLS + c] = { g: 0x20, fg: WHITE, bg: colour, rv: 0 };
      if (selected) {                                // page number only on selected row
        const ps = String(e.page);
        this.put(g, row, 8 - ps.length, ps, fg, bg);
      }
      this.put(g, row, 9, e.title, fg, bg);
      const type = e.type + (e.size ? String(e.size) : '') + (e.hasSubdir ? '+' : '');
      this.put(g, row, 26, type, fg, bg);
      const val = e.values?.[dir.columns[colIdx]] || '';
      if (val) this.put(g, row, 31, val, fg, bg);
    });

    (dir.advert || []).slice(0, 2).forEach((line, i) => {
      const col = Math.max(0, Math.floor((COLS - line.length) / 2));
      this.put(g, 22 + i, col, line, BLUE, TEMPLATE_BG);
    });

    this.renderGrid(g, TEMPLATE_BG);
    this.setBorder(this.assets.template.border);
  }
}
