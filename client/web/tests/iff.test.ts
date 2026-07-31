/* Decoder tests for src/iff.ts (§7.4.1 type F).
 *
 * Run:  npm test   (esbuild bundles this + iff.ts, node runs it — no framework)
 *
 * The browser end-to-end test views the real uncompressed fixture, so the value here
 * is the paths that does NOT exercise: ByteRun1 depacking (both the literal and the
 * repeat control) and multi-plane colour reconstruction.
 */
import assert from 'node:assert';
import { decodeILBM, isILBM } from '../src/iff';

let passed = 0;
function test(name: string, fn: () => void): void {
  fn();
  passed++;
  console.log('  ok  ' + name);
}

function u32(n: number): number[] { return [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255]; }
function u16(n: number): number[] { return [(n >>> 8) & 255, n & 255]; }
function chunk(id: string, data: number[]): number[] {
  const out = [...[...id].map((c) => c.charCodeAt(0)), ...u32(data.length), ...data];
  if (data.length & 1) out.push(0);
  return out;
}
function form(bmhd: number[], cmap: number[], body: number[], compression: number): Uint8Array {
  // patch compression byte (BMHD offset 10) so callers pass one BMHD shape
  bmhd = bmhd.slice(); bmhd[10] = compression;
  const inner = [...[...'ILBM'].map((c) => c.charCodeAt(0)),
    ...chunk('BMHD', bmhd), ...chunk('CMAP', cmap), ...chunk('BODY', body)];
  return new Uint8Array([...[...'FORM'].map((c) => c.charCodeAt(0)), ...u32(inner.length), ...inner]);
}
// BMHD: w h x y nPlanes masking compression pad transparent xa ya pageW pageH
function bmhd(w: number, h: number, planes: number): number[] {
  return [...u16(w), ...u16(h), ...u16(0), ...u16(0), planes, 0, 0, 0, ...u16(0), 10, 11, ...u16(w), ...u16(h)];
}

const BARS_CMAP = [0, 0, 0, 255, 0, 0, 0, 255, 0, 255, 255, 0, 0, 0, 255, 255, 0, 255, 0, 255, 255, 255, 255, 255];

test('rejects a non-ILBM', () => {
  assert.equal(isILBM(new Uint8Array([1, 2, 3, 4])), false);
  assert.throws(() => decodeILBM(new Uint8Array([1, 2, 3, 4])));
});

test('uncompressed 8-colour bars decode to 0..7 across the planes', () => {
  const w = 320, h = 2, planes = 3, rowbytes = ((w + 15) >> 4) * 2;
  const bar = w / 8;
  const body: number[] = [];
  for (let y = 0; y < h; y++) {
    for (let p = 0; p < planes; p++) {
      for (let bi = 0; bi < rowbytes; bi++) {
        let acc = 0;
        for (let bit = 0; bit < 8; bit++) {
          const x = bi * 8 + bit;
          if (x < w && ((Math.min((x / bar) | 0, 7) >> p) & 1)) acc |= 1 << (7 - bit);
        }
        body.push(acc);
      }
    }
  }
  const img = decodeILBM(form(bmhd(w, h, planes), BARS_CMAP, body, 0));
  assert.equal(img.width, 320); assert.equal(img.height, 2);
  for (let b = 0; b < 8; b++) {
    const x = b * bar + 1, o = (x * 4);
    const c = BARS_CMAP.slice(b * 3, b * 3 + 3);
    assert.deepEqual([img.rgba[o], img.rgba[o + 1], img.rgba[o + 2]], c, 'bar ' + b);
  }
});

test('ByteRun1 repeat run: control 255 repeats the next byte', () => {
  // 16x1, 1 plane, rowbytes 2. Packed [255, 0xFF] => 0xFF 0xFF => all 16 px colour 1.
  const img = decodeILBM(form(bmhd(16, 1, 1), [0, 0, 0, 255, 255, 255], [255, 0xFF], 1));
  for (let x = 0; x < 16; x++) {
    const o = x * 4;
    assert.deepEqual([img.rgba[o], img.rgba[o + 1], img.rgba[o + 2]], [255, 255, 255], 'px ' + x);
  }
});

test('ByteRun1 literal run: control 1 copies the next 2 bytes', () => {
  // Packed [1, 0x80, 0x00] => 0x80 0x00 => only pixel 0 set (colour 1).
  const img = decodeILBM(form(bmhd(16, 1, 1), [0, 0, 0, 9, 9, 9], [1, 0x80, 0x00], 1));
  assert.deepEqual([img.rgba[0], img.rgba[1], img.rgba[2]], [9, 9, 9], 'px 0 set');
  assert.deepEqual([img.rgba[4], img.rgba[5], img.rgba[6]], [0, 0, 0], 'px 1 clear');
});

console.log(`\n${passed} passed`);
