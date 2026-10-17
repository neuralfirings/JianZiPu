// Layout editor state: which word type is open, which optional parts the
// preview includes, which glyph each part previews with, and the selection.
import type { Design, GapEntry, Layout, Relationship, ResolvePayload, WordPiece } from './api';
import { app } from './state.svelte';
import { choiceForNames, defaultChoice, shapeElements, type Choice, type ShapeElement } from './shape';
import { entriesOf, isOtherwise } from './rules';

class Editor {
  layoutName = $state('');
  choice = $state<Choice>([]);
  pinned = $state<Record<string, string>>({});
  pinByArea: Record<string, string> = {};
  selected = $state<string | null>(null);
  showGlyphs = $state(true);
  showBoxes = $state(true);
  advanced = $state(false);
  resolved = $state<ResolvePayload | null>(null);
  resolving = $state(false);
  dragDesign = $state<Design | null>(null);
  dragLabel = $state<string | null>(null);
  selectedArrow = $state<string | null>(null);   // `${axis}:${relIndex}` of a selected rule arrow
  axis = $state<'x' | 'y'>('y');                 // rule panel tab
  viewedRel = $state<number | null>(null);        // relationship index whose rows the panel shows
  ruleEdit = $state<RuleEdit | null>(null);        // the rule editor, when open

  get design(): Design | null {
    return this.dragDesign ?? app.design;
  }
  get layout(): Layout | null {
    return this.design?.layouts.find((l) => l.name === this.layoutName) ?? null;
  }
  get elements(): ShapeElement[] {
    const l = this.layout;
    return l ? shapeElements(l, this.choice) : [];
  }

  /** Select a part; leaves any rule view / rule edit of the previous part. */
  select(name: string | null) {
    if (name !== this.selected) { this.viewedRel = null; this.ruleEdit = null; this.selectedArrow = null; }
    this.selected = name;
  }

  setLayout(name: string) {
    const l = app.design?.layouts.find((x) => x.name === name);
    if (!l) return;
    this.layoutName = name;
    this.choice = defaultChoice(l);
    this.selected = null;
    this.resolved = null;
    this.ensurePins();
  }

  /** Keep the choice array in step with the slots after structural edits. */
  syncChoice() {
    const l = this.layout;
    if (!l) return;
    const next: Choice = l.slots.map((s, i) => {
      const c = this.choice[i];
      if (s.repeat) {
        const arr = Array.isArray(c) ? c : c == null && s.optional ? null : [0];
        if (arr === null) return null;
        const n = Math.min(s.repeat[1], Math.max(s.repeat[0], arr.length));
        return Array.from({ length: n }, (_, j) => Math.min(arr[j] ?? 0, s.alternatives.length - 1));
      }
      if (c === null || c === undefined) return s.optional ? null : 0;
      return Math.min(typeof c === 'number' ? c : 0, s.alternatives.length - 1);
    });
    if (JSON.stringify(next) !== JSON.stringify(this.choice)) this.choice = next;
    this.ensurePins();
  }

  ensurePins() {
    const d = this.design;
    if (!d) return;
    const next = { ...this.pinned };
    let changed = false;
    for (const e of this.elements) {
      const glyphs = d.areas[e.area]?.glyphs ?? [];
      if (!next[e.name] || !glyphs.includes(next[e.name])) {
        const g = this.pinByArea[e.area] && glyphs.includes(this.pinByArea[e.area]) ? this.pinByArea[e.area] : glyphs[0];
        if (g) { next[e.name] = g; changed = true; }
      }
    }
    if (changed) this.pinned = next;
  }

  pin(name: string, glyph: string) {
    const e = this.elements.find((x) => x.name === name);
    if (e) this.pinByArea[e.area] = glyph;
    this.pinned = { ...this.pinned, [name]: glyph };
  }

  setChoice(i: number, c: number | number[] | null) {
    const next = [...this.choice];
    next[i] = c;
    this.choice = next;
    this.ensurePins();
    if (this.selected && !this.elements.some((e) => e.name === this.selected)) this.selected = null;
  }

  /** Show one word shape (element names as the resolver lists them) with the given glyphs. */
  openShape(layoutName: string, names: string[], pinned: Record<string, string>, select: string | null = null) {
    const l = app.design?.layouts.find((x) => x.name === layoutName);
    if (!l) return;
    this.layoutName = layoutName;
    this.choice = choiceForNames(l, names);
    this.viewedRel = null; this.ruleEdit = null; this.selectedArrow = null;
    this.pinned = { ...this.pinned, ...pinned };
    for (const e of this.elements) if (pinned[e.name]) this.pinByArea[e.area] = pinned[e.name];
    this.ensurePins();
    this.selected = select && this.elements.some((e) => e.name === select) ? select : null;
  }

  /** Load a shaped test word piece into the editor. */
  loadWord(piece: WordPiece) {
    if (!piece.layout || !piece.choice) return;
    this.layoutName = piece.layout;
    this.choice = piece.choice;
    const pins: Record<string, string> = {};
    for (const e of piece.elements) pins[e.name] = e.glyph;
    this.pinned = pins;
    for (const e of piece.elements) this.pinByArea[e.area] = e.glyph;
    this.selected = null;
  }

  /** Open the rule editor on one entry of a relationship (null = a new rule on top).
   *  `preTick` pre-selects that glyph of the part for a new rule. */
  openRule(axis: 'x' | 'y', relIndex: number, entryIndex: number | null, preTick: string | null = null) {
    const rel = this.layout?.relationships[relIndex];
    if (!rel) return;
    const entries = entriesOf(rel.gap);
    const e = entryIndex != null ? entries[entryIndex] : null;
    this.axis = axis;
    this.viewedRel = relIndex;
    this.selectedArrow = `${axis}:${relIndex}`;
    this.ruleEdit = {
      axis, relIndex, entryIndex, insertAt: entryIndex ?? 0,
      whenElem: e?.when_elem ? [...e.when_elem] : preTick ? [preTick] : [],
      whenBase: e?.when_base ? [...e.when_base] : [],
      value: e?.value ?? (entries.find(isOtherwise)?.value ?? entries[0]?.value ?? 0),
      overlay: true, step: 0, liveDelta: 0
    };
  }

  /** The relationship currently positioning `name` on `axis`, as an index into layout.relationships. */
  activeRel(axis: 'x' | 'y', name: string): { index: number; rel: Relationship } | null {
    const raw = this.resolved?.chosen?.[`${axis}:${name}`];
    const l = this.layout;
    if (!raw || !l) return null;
    const key = (r: Relationship) => JSON.stringify([r.axis, r.elem, r.base ?? null, r.base_edge ?? null, r.elem_edge ?? null]);
    const k = key(raw);
    const cands = l.relationships.map((r, i) => ({ r, i })).filter(({ r }) => key(r) === k);
    const exact = cands.find(({ r }) => JSON.stringify(r.gap) === JSON.stringify(raw.gap)) ?? cands[0];
    return exact ? { index: exact.i, rel: exact.r } : null;
  }

  /** Concrete element name a relationship's base refers to for element `name`. */
  baseName(name: string, rel: Relationship): string | null {
    const b = rel.base;
    if (b == null || b === 'prev') return null;
    const els = this.elements;
    const e = els.find((x) => x.name === name);
    if (!e) return null;
    const l = this.layout!;
    const slot = l.slots.find((s) => s.name === e.slot)!;
    const slotEls = new Set(slot.alternatives.flat().map((t) => (t.includes(':') ? t.split(':')[0] : t)));
    if (slotEls.has(b)) return els.find((x) => x.el === b && x.instance === e.instance)?.name ?? null;
    const direct = els.find((x) => x.el === b || x.name === b);
    if (direct) return direct.name;
    return els.find((x) => x.slot === b)?.name ?? null;
  }
}

export type RuleEdit = {
  axis: 'x' | 'y';
  relIndex: number;
  entryIndex: number | null;      // null = new rule
  insertAt: number;               // position the entry lands at on confirm (new rules: 0)
  whenElem: string[];
  whenBase: string[];
  value: number;
  overlay: boolean;
  step: number;                   // combination shown when overlay is off
  liveDelta: number;              // while dragging on the canvas
};

export const editor = new Editor();

/** Index of the gap-list entry that applies for the given glyphs (first match), or -1. */
export function gapEntryIndex(gap: Relationship['gap'], baseGlyph: string | null, elemGlyph: string | null): number {
  if (!Array.isArray(gap)) return -1;
  return gap.findIndex((e) => (!e.when_base || (baseGlyph != null && e.when_base.includes(baseGlyph))) && (!e.when_elem || (elemGlyph != null && e.when_elem.includes(elemGlyph))));
}

export function gapValue(gap: Relationship['gap'], baseGlyph: string | null, elemGlyph: string | null): number | null {
  if (!Array.isArray(gap)) return gap;
  const i = gapEntryIndex(gap, baseGlyph, elemGlyph);
  return i < 0 ? null : gap[i].value;
}

/** Add `delta` to the gap entry that applies for the given glyphs. Returns the new value, or null. */
export function bumpGap(rel: Relationship, delta: number, baseGlyph: string | null, elemGlyph: string | null): number | null {
  if (!Array.isArray(rel.gap)) { rel.gap = Math.round(rel.gap + delta); return rel.gap; }
  const i = gapEntryIndex(rel.gap, baseGlyph, elemGlyph);
  if (i < 0) return null;
  rel.gap[i].value = Math.round(rel.gap[i].value + delta);
  return rel.gap[i].value;
}

/** Which side of a rule its exceptions key on: the existing entries decide; for a plain
 *  number, the side whose area has more than one glyph (the stroke, usually). */
export function gapKeySide(gap: Relationship['gap'], elemGlyphCount: number, baseGlyphCount: number): 'base' | 'elem' {
  if (Array.isArray(gap)) {
    if (gap.some((e) => e.when_base)) return 'base';
    if (gap.some((e) => e.when_elem)) return 'elem';
  }
  return elemGlyphCount > 1 || baseGlyphCount <= 1 ? 'elem' : 'base';
}

/** Like bumpGap, but gives `glyph` its own exception row instead of widening a shared one. */
export function bumpGapOwn(rel: Relationship, delta: number, side: 'base' | 'elem', glyph: string, baseGlyph: string | null, elemGlyph: string | null): number | null {
  const key = side === 'base' ? 'when_base' : 'when_elem';
  if (!Array.isArray(rel.gap)) {
    const n = rel.gap;
    rel.gap = [{ [key]: [glyph], value: Math.round(n + delta) } as GapEntry, { value: n }];
    return rel.gap[0].value;
  }
  const i = gapEntryIndex(rel.gap, baseGlyph, elemGlyph);
  const cur = i < 0 ? rel.gap[rel.gap.length - 1] : rel.gap[i];
  const cond = cur?.[key];
  if (cond && cond.length === 1 && cond[0] === glyph) {
    cur.value = Math.round(cur.value + delta);
    return cur.value;
  }
  const entry = { [key]: [glyph], value: Math.round((cur?.value ?? 0) + delta) } as GapEntry;
  rel.gap.splice(i < 0 ? rel.gap.length : i, 0, entry);
  return entry.value;
}

/** True when the entry in effect for these glyphs is the unconditional "otherwise" row. */
export function hitsOtherwise(gap: Relationship['gap'], baseGlyph: string | null, elemGlyph: string | null): boolean {
  if (!Array.isArray(gap)) return false;
  const i = gapEntryIndex(gap, baseGlyph, elemGlyph);
  return i >= 0 && !gap[i].when_base && !gap[i].when_elem;
}
