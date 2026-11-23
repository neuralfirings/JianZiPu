// The Text tool: characters typed in the base font (TW-Kai), set as one line of outlines.
// The server sends each character's outline in the font's own units (GET /api/base-font/outline,
// jzpbuild/base_outline.py); this sets them side by side at a size, as SVG the scene imports.
import type { BaseOutline } from '$lib/api';

/** The size a new text starts at: the glyph box's height, so one character fills the box. */
export function defaultTextSize(box: [number, number]): number {
  return Math.round(box[1]);
}

/** The typed characters as one SVG, `size` units to the em, the first character's origin at 0, 0
 *  (baseline at y 0, y down). Null when there's nothing to draw. Each character keeps its own
 *  advance, so a line of them is spaced as the font spaces it. */
export function textSvg(o: Pick<BaseOutline, 'upm' | 'chars'>, size: number): string | null {
  const k = size / (o.upm || 1000);
  if (!(k > 0)) return null;
  let x = 0;
  const parts: string[] = [];
  for (const c of o.chars) {
    if (c.d) parts.push(`<path transform="translate(${r3(x)} 0) scale(${r6(k)})" d="${c.d}"/>`);
    x += c.advance * k;
  }
  if (!parts.length) return null;
  return `<svg xmlns="http://www.w3.org/2000/svg"><g fill="black">${parts.join('')}</g></svg>`;
}
const r3 = (n: number) => Math.round(n * 1000) / 1000;
const r6 = (n: number) => Math.round(n * 1e6) / 1e6;

/** Say which characters the base font hasn't got ("TW-Kai has no 这 or 么"). */
export function missingNote(missing: string[], font = 'TW-Kai'): string | null {
  if (!missing.length) return null;
  const list = missing.length === 1 ? missing[0] : `${missing.slice(0, -1).join(', ')} or ${missing[missing.length - 1]}`;
  return `${font} has no ${list}. A simplified character may be there in its traditional form.`;
}
