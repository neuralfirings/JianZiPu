// Client-side mirror of jzpbuild.positioning.shapes: which concrete
// elements a preview choice produces, so the UI can show pins and labels
// before the server resolve returns.
import type { Layout, Slot } from './api';
import { parseElement } from './state.svelte';

export type Choice = (number | number[] | null)[];
export type ShapeElement = { name: string; el: string; area: string; slot: string; instance: number };

export function defaultChoice(layout: Layout): Choice {
  return layout.slots.map((s) => {
    if (s.repeat) {
      const n = Math.min(s.repeat[1], Math.max(s.repeat[0], 2));
      return Array.from({ length: n }, () => 0);
    }
    return 0;
  });
}

export function shapeElements(layout: Layout, choice: Choice): ShapeElement[] {
  const out: ShapeElement[] = [];
  layout.slots.forEach((s, i) => {
    const c = choice[i];
    if (c === null || c === undefined) return;
    if (Array.isArray(c)) {
      c.forEach((k, j) => {
        for (const t of s.alternatives[k] ?? s.alternatives[0]) {
          const { name, area } = parseElement(t);
          out.push({ name: `${name}@${j + 1}`, el: name, area, slot: s.name, instance: j + 1 });
        }
      });
    } else {
      for (const t of s.alternatives[c] ?? s.alternatives[0]) {
        const { name, area } = parseElement(t);
        out.push({ name, el: name, area, slot: s.name, instance: 0 });
      }
    }
  });
  return out;
}

/** Element and slot names a layout knows (for pickers). */
export function elementNames(layout: Layout): { name: string; area: string; slot: string }[] {
  const out: { name: string; area: string; slot: string }[] = [];
  for (const s of layout.slots)
    for (const alt of s.alternatives)
      for (const t of alt) {
        const { name, area } = parseElement(t);
        if (!out.some((o) => o.name === name)) out.push({ name, area, slot: s.name });
      }
  return out;
}

export function slotIsSimple(s: Slot) {
  return s.alternatives.length === 1 && s.alternatives[0].length === 1 && parseElement(s.alternatives[0][0]).name === s.name;
}

/** Human description of a concrete element name: "char@2" -> "Character, row 2". */
export function elementLabel(layout: Layout, name: string, areaLabel: (a: string) => string) {
  const [el, inst] = name.split('@');
  const found = elementNames(layout).find((e) => e.name === el);
  const base = found ? (found.name === found.area ? areaLabel(found.area) : `${areaLabel(found.area)} (${el})`) : el;
  return inst ? `${base}, row ${inst}` : base;
}

/** Names of the anchors: the first glyph of each attachment chain. A chain
 *  starts at the first part of the word and after every part whose area has
 *  an advance (the colon, the bar), which is marked but never attached. */
export function anchorNames(elements: { name: string; area: string }[], areas: Record<string, { advance?: number }>): Set<string> {
  const out = new Set<string>();
  let newChain = true;
  for (const e of elements) {
    if (areas[e.area]?.advance) { newChain = true; continue; }
    if (newChain) { out.add(e.name); newChain = false; }
  }
  return out;
}

/** The choice array that produces a shape with exactly these element names
 *  (as the resolver lists them: "el" or "el@instance"). */
export function choiceForNames(layout: Layout, names: string[]): Choice {
  const set = new Set(names);
  return layout.slots.map((s) => {
    const altMatches = (alt: string[], inst: number) => alt.every((t) => set.has(inst ? `${parseElement(t).name}@${inst}` : parseElement(t).name));
    if (s.repeat) {
      const picks: number[] = [];
      for (let inst = 1; inst <= s.repeat[1]; inst++) {
        const k = s.alternatives.findIndex((alt) => altMatches(alt, inst));
        if (k < 0) break;
        picks.push(k);
      }
      return picks.length ? picks : s.optional ? null : [0];
    }
    const k = s.alternatives.findIndex((alt) => altMatches(alt, 0));
    return k >= 0 ? k : s.optional ? null : 0;
  });
}

/** The page span a word preview shows: 0 to the right edge of its rightmost part, at least one em.
 *  Not `advance + 1000`: a vertical word's colon box already spans its em (advance 1000), so that
 *  doubled its canvas and drew it at half the size of a standard word. */
export function wordPage(w: { advance: number; pieces: { elements: { x: number | null; size: [number, number] }[] }[] }): [number, number] {
  let right = Math.max(1000, w.advance);
  for (const p of w.pieces) for (const e of p.elements) if (e.x != null) right = Math.max(right, e.x + e.size[0]);
  return [0, right];
}

type Placed = { x: number | null; y: number | null; size: [number, number]; glyph?: string | null };

/** A word canvas's viewBox, in canvas units with y flipped (svg y = -y).
 *  `fit`: frame the elements with a margin (the editors). Otherwise a fixed page, like a line of
 *  the font, grown only by parts that draw something: an inkless spacer (blank_colon, which the
 *  build makes with no SVG) would otherwise stretch a vertical word's page and shrink the word. */
export function canvasBox(
  elements: Placed[],
  o: { page: [number, number]; pageHeight: [number, number]; showPage: boolean; fit: boolean },
  hasInk: (glyph: string) => boolean
): { x: number; y: number; w: number; h: number } {
  let x0 = o.showPage ? o.page[0] : Infinity, x1 = o.showPage ? o.page[1] : -Infinity;
  let y0 = o.showPage ? o.pageHeight[0] : Infinity, y1 = o.showPage ? o.pageHeight[1] : -Infinity;
  for (const e of elements) {
    if (e.x == null || e.y == null) continue;
    if (!o.fit && e.glyph && !hasInk(e.glyph)) continue;
    x0 = Math.min(x0, e.x); x1 = Math.max(x1, e.x + e.size[0]);
    y0 = Math.min(y0, e.y); y1 = Math.max(y1, e.y + e.size[1]);
  }
  if (!isFinite(x0)) { x0 = 0; x1 = 1000; y0 = -500; y1 = 1100; }
  const m = o.fit ? 60 : 0;
  return { x: x0 - m, y: -(y1 + m), w: x1 - x0 + 2 * m, h: y1 - y0 + 2 * m };
}
