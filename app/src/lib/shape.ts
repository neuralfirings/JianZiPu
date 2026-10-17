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
