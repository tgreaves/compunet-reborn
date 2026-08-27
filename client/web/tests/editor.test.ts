/* Editor tests for src/editor.ts — reverse video (§5.7 / §8.4.3) and the
 * per-cell state it writes.
 *
 * Run:  npm test   (esbuild bundles this + editor.ts, node runs it — no framework)
 *
 * Reverse is the one typing attribute with a LIFETIME: it spans cells, and a
 * carriage return ends it. Those are the cases here, because they are the ones
 * a cell-at-a-time reading of the code gets wrong.
 */
import assert from 'node:assert';
import { EditorBuffer, PAGE_COLS } from '../src/editor';

let passed = 0;
function test(name: string, fn: () => void): void {
  fn();
  passed++;
  console.log('  ok  ' + name);
}

const cellAt = (b: EditorBuffer, row: number, col: number) =>
  b.page().cells[row * PAGE_COLS + col];

test('typing is not reversed by default', () => {
  const b = new EditorBuffer();
  b.typeChar('A');
  assert.equal(cellAt(b, 0, 0).rv, 0);
});

test('reverse on: typed cells carry rv=1', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeChar('A');
  b.typeChar('B');
  assert.equal(cellAt(b, 0, 0).rv, 1);
  assert.equal(cellAt(b, 0, 1).rv, 1, 'the mode spans cells');
});

test('reverse off again: later cells are plain', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeChar('A');
  b.reverse = false;
  b.typeChar('B');
  assert.equal(cellAt(b, 0, 0).rv, 1);
  assert.equal(cellAt(b, 0, 1).rv, 0);
});

test('graphics glyphs honour the mode too', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeGlyph(0x51);              // a filled circle, first graphics bank
  assert.equal(cellAt(b, 0, 0).g, 0x51);
  assert.equal(cellAt(b, 0, 0).rv, 1);
});

test('RETURN clears the mode (§5.7)', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeChar('A');
  b.newline();
  assert.equal(b.reverse, false, 'CR ends the run, as on the C64');
  b.typeChar('B');
  assert.equal(cellAt(b, 1, 0).rv, 0);
});

test('the column-40 wrap does NOT clear the mode', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  for (let i = 0; i < PAGE_COLS; i++) b.typeChar('X');   // fills row 0, wraps
  assert.equal(b.row, 1, 'wrapped to the next row');
  assert.equal(b.col, 0);
  assert.equal(b.reverse, true, 'a wrap is not a carriage return');
  b.typeChar('Y');
  assert.equal(cellAt(b, 1, 0).rv, 1, 'a bar can run past the right edge');
});

test('backspace clears the cell rather than reversing it', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeChar('A');
  b.backspace();
  assert.equal(cellAt(b, 0, 0).rv, 0);
  assert.equal(cellAt(b, 0, 0).g, 0x20);
});

test('reverse survives the RLE round-trip (PUT/STORE then GET)', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeChar('A');
  b.reverse = false;
  b.typeChar('B');
  const saved = b.toJSON();

  const back = new EditorBuffer();
  back.load(saved);
  assert.equal(back.page().cells[0].rv, 1, 'reversed cell came back reversed');
  assert.equal(back.page().cells[1].rv, 0);
});

test('runs of differing rv are not merged by the RLE encoder', () => {
  const b = new EditorBuffer();
  b.reverse = true;
  b.typeChar('A');
  b.reverse = false;
  b.typeChar('A');                // same glyph and colour, different rv
  const runs = (JSON.parse(b.toJSON()) as { pages: { rle: number[][] }[] }).pages[0].rle;
  assert.equal(runs[0][0], 1, 'first run is one cell, not two');
  assert.equal(runs[0][4], 1, 'and it is the reversed one');
  assert.equal(runs[1][4], 0);
});

console.log(`\n${passed} passed`);
