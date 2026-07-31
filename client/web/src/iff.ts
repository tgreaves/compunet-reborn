/* IFF/ILBM picture decoder (§7.4.1 type `F`).
 *
 * A faithful port of the reconstructed Amiga decoder in client/amiga/src/download.c
 * (iff_feed_byte / iff_setup / iff_row_uncompressed / iff_row_byterun1), reduced to a
 * pure function so it is unit-testable and has no canvas/DOM dependency. The web client
 * is the only client that decodes an F itself — the native Amiga has its own viewer, and
 * the C64 is refused the download server-side (§7.4.1).
 *
 * Supports: 1–8 bitplanes, uncompressed and ByteRun1 (PackBits) BODY, optional mask
 * plane, and EHB (Extra-HalfBrite). HAM is detected and rejected with a clear message
 * rather than rendered wrong — it is rare and needs a different pixel model.
 */

export interface IFFImage {
  width: number;
  height: number;
  /** RGBA, row-major, 4 bytes/pixel — ready for ImageData. */
  rgba: Uint8ClampedArray<ArrayBuffer>;
}

function fourcc(b: Uint8Array, at: number): string {
  return String.fromCharCode(b[at], b[at + 1], b[at + 2], b[at + 3]);
}

export function isILBM(b: Uint8Array): boolean {
  return b.length >= 12 && fourcc(b, 0) === 'FORM' && fourcc(b, 8) === 'ILBM';
}

export function decodeILBM(bytes: Uint8Array): IFFImage {
  if (!isILBM(bytes)) throw new Error('not an IFF ILBM (FORM..ILBM)');
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

  let w = 0, h = 0, nplanes = 0, masking = 0, compression = 0, camg = 0;
  let cmap: number[][] = [];
  let body: Uint8Array | null = null;

  let pos = 12;
  while (pos + 8 <= bytes.length) {
    const id = fourcc(bytes, pos);
    const len = dv.getUint32(pos + 4);
    const data = bytes.subarray(pos + 8, pos + 8 + len);
    if (id === 'BMHD') {
      // w@0 h@2 (x@4 y@6) nPlanes@8 masking@9 compression@10 (§ standard BitMapHeader)
      w = (data[0] << 8) | data[1];
      h = (data[2] << 8) | data[3];
      nplanes = data[8];
      masking = data[9];
      compression = data[10];
    } else if (id === 'CMAP') {
      cmap = [];
      for (let i = 0; i + 2 < data.length; i += 3) cmap.push([data[i], data[i + 1], data[i + 2]]);
    } else if (id === 'CAMG') {
      camg = (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3];
    } else if (id === 'BODY') {
      body = data;
    }
    pos += 8 + len + (len & 1);   // chunks pad to an even length
  }

  if (!w || !h || !nplanes || !body) throw new Error('ILBM missing BMHD or BODY');
  if (compression > 1) throw new Error('unsupported ILBM compression ' + compression);
  if (camg & 0x800) throw new Error('HAM pictures are not supported');
  if (nplanes > 8) throw new Error('unsupported plane count ' + nplanes);

  // Extra-HalfBrite: colours 32..63 are colours 0..31 halved. Flagged in CAMG, or
  // inferred from a 6-plane picture that only carries 32 CMAP entries.
  if ((camg & 0x80) || (nplanes === 6 && cmap.length === 32)) {
    for (let i = 0; i < 32 && i < cmap.length; i++) {
      cmap.push([cmap[i][0] >> 1, cmap[i][1] >> 1, cmap[i][2] >> 1]);
    }
  }

  const rowbytes = ((w + 15) >> 4) * 2;
  const rgba = new Uint8ClampedArray(new ArrayBuffer(w * h * 4));

  // BODY reader: hands back one plane-row (rowbytes bytes), depacking ByteRun1 on the fly.
  let bp = 0;
  const planeRow = new Uint8Array(rowbytes);
  function readPlaneRow(): void {
    if (compression === 0) {
      planeRow.set(body!.subarray(bp, bp + rowbytes));
      bp += rowbytes;
      return;
    }
    let n = 0;                                   // ByteRun1 / PackBits
    while (n < rowbytes && bp < body!.length) {
      const c = body![bp++];
      if (c <= 127) {
        for (let i = 0; i <= c && n < rowbytes; i++) planeRow[n++] = body![bp++];
      } else if (c >= 129) {
        const val = body![bp++];
        for (let i = 0; i < 257 - c && n < rowbytes; i++) planeRow[n++] = val;
      }
      // c === 128 is a no-op
    }
  }

  for (let y = 0; y < h; y++) {
    // Accumulate the row's colour indices across the planes.
    const idx = new Uint16Array(w);
    for (let p = 0; p < nplanes; p++) {
      readPlaneRow();
      for (let x = 0; x < w; x++) {
        const bit = (planeRow[x >> 3] >> (7 - (x & 7))) & 1;
        idx[x] |= bit << p;
      }
    }
    if (masking === 1) readPlaneRow();           // mask plane: read and discard

    const rowbase = y * w * 4;
    for (let x = 0; x < w; x++) {
      const c = cmap[idx[x]] || [0, 0, 0];
      const o = rowbase + x * 4;
      rgba[o] = c[0]; rgba[o + 1] = c[1]; rgba[o + 2] = c[2]; rgba[o + 3] = 255;
    }
  }

  return { width: w, height: h, rgba };
}
