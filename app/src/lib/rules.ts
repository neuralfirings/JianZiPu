// Helpers for the rule panel / rule editor: a part's chain of bases per
// axis, the entries of one rule, coverage and shadowing.
import type { GapEntry, Layout, Relationship } from './api';
import type { ShapeElement } from './shape';

export type ChainItem = { index: number; rel: Relationship };

/** The relationships positioning `el` on `axis`, in file order (= search order). */
export function chainFor(layout: Layout, el: ShapeElement, axis: 'x' | 'y'): ChainItem[] {
  return layout.relationships.map((rel, index) => ({ index, rel })).filter(({ rel }) => rel.axis === axis && (rel.elem === el.el || rel.elem === el.slot));
}

/** A gap as a list of entries (a plain number is one "otherwise" entry). */
export function entriesOf(gap: Relationship['gap']): GapEntry[] {
  return Array.isArray(gap) ? gap : [{ value: gap }];
}
export function isOtherwise(e: GapEntry) {
  return !e.when_base?.length && !e.when_elem?.length;
}
/** Store a list back: a lone otherwise collapses to a number. */
export function normalizeGap(entries: GapEntry[]): Relationship['gap'] {
  const clean = entries.map((e) => {
    const o: GapEntry = { value: e.value };
    if (e.when_base?.length) o.when_base = [...e.when_base];
    if (e.when_elem?.length) o.when_elem = [...e.when_elem];
    return o;
  });
  return clean.length === 1 && isOtherwise(clean[0]) ? clean[0].value : clean;
}

/** Does entry `e` catch the pair (elem glyph, base glyph)? null = "any". */
export function catches(e: GapEntry, elemGlyph: string | null, baseGlyph: string | null): boolean {
  if (e.when_elem?.length && (elemGlyph == null || !e.when_elem.includes(elemGlyph))) return false;
  if (e.when_base?.length && (baseGlyph == null || !e.when_base.includes(baseGlyph))) return false;
  return true;
}

/** Glyphs of one side that no entry reaches (assuming any glyph on the other side). */
export function uncovered(entries: GapEntry[], side: 'elem' | 'base', glyphs: string[]): string[] {
  if (entries.some(isOtherwise)) return [];
  const key = side === 'elem' ? 'when_elem' : 'when_base';
  const other = side === 'elem' ? 'when_base' : 'when_elem';
  return glyphs.filter((g) => !entries.some((e) => (!e[key]?.length || e[key]!.includes(g)) && !e[other]?.length));
}

/** Earliest entry before `before` that would catch glyph `g` on `side`, given the
 *  other side's selection (empty = any). Returns its index or -1. */
export function shadowedBy(entries: GapEntry[], before: number, side: 'elem' | 'base', g: string, otherSel: string[]): number {
  const key = side === 'elem' ? 'when_elem' : 'when_base';
  const other = side === 'elem' ? 'when_base' : 'when_elem';
  for (let i = 0; i < before && i < entries.length; i++) {
    const e = entries[i];
    if (e[key]?.length && !e[key]!.includes(g)) continue;
    if (e[other]?.length && otherSel.length && !otherSel.some((x) => e[other]!.includes(x))) continue;
    return i;
  }
  return -1;
}

/** Preset filters for a glyph grid (position numbers have whole / fraction forms). */
export function presetsFor(glyphs: string[]): { label: string; glyphs: string[] }[] {
  const out: { label: string; glyphs: string[] }[] = [];
  const whole = glyphs.filter((g) => !/\.[\w]+$/.test(g));
  const frac = glyphs.filter((g) => /\.[\w]+$/.test(g));
  if (frac.length && whole.length) {
    out.push({ label: `whole · ${whole.length}`, glyphs: whole });
    out.push({ label: `with fraction · ${frac.length}`, glyphs: frac });
  }
  return out;
}

import type { Design } from './api';
import type { RuleEdit } from './editor.svelte';

/** The design with an in-progress rule edit applied (for live preview and confirm). */
export function applyRuleEdit(design: Design, layoutName: string, re: RuleEdit, delta = 0): Design {
  const d: Design = JSON.parse(JSON.stringify(design));
  const l = d.layouts.find((x) => x.name === layoutName)!;
  const rel = l.relationships[re.relIndex];
  const entries = entriesOf(rel.gap).map((e) => ({ ...e }));
  const entry: GapEntry = { value: Math.round(re.value + delta) };
  if (re.whenElem.length) entry.when_elem = [...re.whenElem];
  if (re.whenBase.length) entry.when_base = [...re.whenBase];
  if (re.entryIndex == null) entries.splice(Math.min(re.insertAt, entries.length), 0, entry);
  else {
    entries[re.entryIndex] = entry;
    if (re.insertAt !== re.entryIndex) {
      const [x] = entries.splice(re.entryIndex, 1);
      entries.splice(re.insertAt > re.entryIndex ? re.insertAt - 1 : re.insertAt, 0, x);
    }
  }
  rel.gap = normalizeGap(entries);
  return d;
}

/** The glyph combinations an edit covers, and the one shown when overlay is off.
 *  An unticked side means "any": every glyph of that side (`elemAll` / `baseAll`). */
export function combosOf(re: RuleEdit, elemAll: string[], baseAll: string[]) {
  const elems = re.whenElem.length ? re.whenElem : elemAll;
  const bases = re.whenBase.length ? re.whenBase : baseAll;
  const n = Math.max(1, elems.length) * Math.max(1, bases.length);
  const k = ((re.step % n) + n) % n;
  const shown = { elem: elems.length ? elems[Math.floor(k / Math.max(1, bases.length))] : null, base: bases.length ? bases[k % bases.length] : null };
  return { elems, bases, n, k, shown };
}

/** The stepper position that shows glyph `g` on `side`, keeping the other side's current glyph. */
export function stepFor(c: ReturnType<typeof combosOf>, side: 'elem' | 'base', g: string): number {
  const nb = Math.max(1, c.bases.length);
  let ei = Math.floor(c.k / nb), bi = c.k % nb;
  if (side === 'elem') ei = Math.max(0, c.elems.indexOf(g)); else bi = Math.max(0, c.bases.indexOf(g));
  return ei * nb + bi;
}
