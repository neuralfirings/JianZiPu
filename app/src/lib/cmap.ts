// Which characters a TrueType/OpenType font maps (its `cmap`), so previews can show the
// characters it lacks in red: a browser would otherwise draw them with an installed font
// and nothing would look wrong.

/** Code points mapped by the font in `buf` (cmap formats 4 and 12). */
export function cmapCodepoints(buf: ArrayBuffer): Set<number> {
  const v = new DataView(buf);
  const out = new Set<number>();
  const numTables = v.getUint16(4);
  let cmap = -1;
  for (let i = 0; i < numTables; i++) {
    const rec = 12 + i * 16;
    const tag = String.fromCharCode(v.getUint8(rec), v.getUint8(rec + 1), v.getUint8(rec + 2), v.getUint8(rec + 3));
    if (tag === 'cmap') { cmap = v.getUint32(rec + 8); break; }
  }
  if (cmap < 0) return out;
  const n = v.getUint16(cmap + 2);
  for (let i = 0; i < n; i++) {
    const off = cmap + v.getUint32(cmap + 4 + i * 8 + 4);
    const format = v.getUint16(off);
    if (format === 4) {
      const segX2 = v.getUint16(off + 6);
      const ends = off + 14, starts = ends + segX2 + 2, deltas = starts + segX2, ranges = deltas + segX2;
      for (let s = 0; s < segX2; s += 2) {
        const end = v.getUint16(ends + s), start = v.getUint16(starts + s);
        const delta = v.getInt16(deltas + s), rangeOff = v.getUint16(ranges + s);
        for (let c = start; c <= end && c !== 0xffff; c++) {
          let gid: number;
          if (rangeOff === 0) gid = (c + delta) & 0xffff;
          else {
            const g = v.getUint16(ranges + s + rangeOff + (c - start) * 2);
            gid = g === 0 ? 0 : (g + delta) & 0xffff;
          }
          if (gid) out.add(c);
        }
      }
    } else if (format === 12) {
      const groups = v.getUint32(off + 12);
      for (let g = 0; g < groups; g++) {
        const p = off + 16 + g * 12;
        const start = v.getUint32(p), end = v.getUint32(p + 4), gid = v.getUint32(p + 8);
        for (let c = start; c <= end; c++) if (gid + (c - start)) out.add(c);
      }
    }
  }
  return out;
}

export type Segment = { text: string; missing: boolean };
/** Split text into runs the font has and runs it lacks (whitespace always counts as present). */
export function segments(text: string, has: Set<number> | null): Segment[] {
  if (!has) return [{ text, missing: false }];
  const out: Segment[] = [];
  for (const ch of text) {
    const missing = !/\s/.test(ch) && !has.has(ch.codePointAt(0)!);
    const last = out.at(-1);
    if (last && last.missing === missing) last.text += ch;
    else out.push({ text: ch, missing });
  }
  return out;
}
