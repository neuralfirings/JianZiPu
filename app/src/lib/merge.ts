// Three-way merge of a draft into the current font: base (what the draft started from),
// theirs (the draft), current (the font as it is now). Each change is one reviewable item:
// a glyph file, one glyph's spellings, or one unit of design.json (an area, a word type, the
// page center, the stroke weight, the sample sets). An item conflicts when the current font
// also changed it since the base, differently. Pure functions; the Review screen and the
// "font changed since you started" update both use them.
import type { Area, Design, Layout, Relationship } from './api';
import type { Bundle, SvgMap } from './bundle';
import * as T from './typing';

export type Status = 'added' | 'changed' | 'deleted';
type Base = { id: string; status: Status; conflict: boolean };
export type GlyphItem = Base & { kind: 'glyph'; key: string; base?: string; theirs?: string; current?: string };
export type FieldChange = { field: T.SpellField; base: string; theirs: string; current: string; conflict: boolean };
export type SpellingItem = Base & { kind: 'spelling'; key: string; fields: FieldChange[] };
export type DesignUnit = { type: 'area' | 'layout' | 'center' | 'glyph_weight' | 'test_sets'; name?: string };
export type DesignItem = Base & {
  kind: 'design'; key: string; unit: DesignUnit; label: string; summary: string[];
  base?: unknown; theirs?: unknown; current?: unknown;
};
export type Item = GlyphItem | SpellingItem | DesignItem;
export type Current = { design: Design; typing: T.Typing; svgs: SvgMap };

const same = (a: unknown, b: unknown) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null);
const svgSame = (a?: string, b?: string) => (a == null || b == null ? a === b : a.replace(/\s+$/, '') === b.replace(/\s+$/, ''));
const status = (base: unknown, theirs: unknown): Status => (base === undefined ? 'added' : theirs === undefined ? 'deleted' : 'changed');

/** Every change the draft makes, compared with the current font. Changes the current font
 *  already has are left out. */
export function diffBundle(b: Bundle, cur: Current): Item[] {
  return [...glyphItems(b, cur), ...spellingItems(b, cur), ...designItems(b.base.design, b.design, cur.design)];
}

function glyphItems(b: Bundle, cur: Current): GlyphItem[] {
  const m = b.manifest.svgs, out: GlyphItem[] = [];
  for (const key of [...m.added, ...m.changed, ...m.deleted].sort()) {
    const base = b.base.svgs[key], theirs = b.svgs[key], current = cur.svgs[key];
    if (svgSame(theirs, current)) continue;
    const st = m.deleted.includes(key) ? 'deleted' : m.added.includes(key) ? 'added' : 'changed';
    out.push({ id: `glyph:${key}`, kind: 'glyph', key, status: st, base, theirs, current, conflict: !svgSame(current, base) });
  }
  return out;
}

function spellingItems(b: Bundle, cur: Current): SpellingItem[] {
  const out: SpellingItem[] = [];
  for (const g of T.changedGlyphs(b.base.typing, b.typing)) {
    const bs = T.get(b.base.typing, g), ts = T.get(b.typing, g), cs = T.get(cur.typing, g);
    const fields = T.FIELDS.filter((f) => bs[f] !== ts[f] && ts[f] !== cs[f])
      .map((f) => ({ field: f, base: bs[f], theirs: ts[f], current: cs[f], conflict: cs[f] !== bs[f] }));
    if (!fields.length) continue;
    const st: Status = T.isEmpty(b.base.typing[g]) ? 'added' : T.isEmpty(b.typing[g]) ? 'deleted' : 'changed';
    out.push({ id: `spelling:${g}`, kind: 'spelling', key: g, status: st, fields, conflict: fields.some((f) => f.conflict) });
  }
  return out;
}

/** The units of design.json, as key -> value. */
function units(d: Design): Map<string, { unit: DesignUnit; value: unknown }> {
  const m = new Map<string, { unit: DesignUnit; value: unknown }>();
  for (const [name, a] of Object.entries(d.areas)) m.set(`area:${name}`, { unit: { type: 'area', name }, value: a });
  for (const l of d.layouts) m.set(`layout:${l.name}`, { unit: { type: 'layout', name: l.name }, value: l });
  m.set('center', { unit: { type: 'center' }, value: d.center });
  if (d.glyph_weight != null) m.set('glyph_weight', { unit: { type: 'glyph_weight' }, value: d.glyph_weight });
  if (d.test_sets != null) m.set('test_sets', { unit: { type: 'test_sets' }, value: d.test_sets });
  return m;
}

/** The value of one design unit ("area:left", "layout:standard", "center"…), undefined if absent. */
export function unitOf(d: Design, key: string): unknown {
  return units(d).get(key)?.value;
}

export function designItems(base: Design, theirs: Design, current: Design): DesignItem[] {
  const B = units(base), Th = units(theirs), C = units(current), out: DesignItem[] = [];
  for (const key of new Set([...B.keys(), ...Th.keys()])) {
    const b = B.get(key)?.value, t = Th.get(key)?.value, c = C.get(key)?.value;
    if (same(b, t) || same(t, c)) continue;
    const unit = (Th.get(key) ?? B.get(key))!.unit;
    out.push({
      id: `design:${key}`, kind: 'design', key, unit, label: unitLabel(unit, (t ?? b) as Area | Layout),
      summary: unitSummary(unit, b, t), status: status(b, t), base: b, theirs: t, current: c, conflict: !same(c, b)
    });
  }
  return out;
}

export function unitLabel(u: DesignUnit, v?: Area | Layout): string {
  if (u.type === 'area') return `Area · ${(v as Area)?.label || u.name}`;
  if (u.type === 'layout') return `Word type · ${(v as Layout)?.label ?? u.name}`;
  return { center: 'Page center', glyph_weight: 'Stroke weight', test_sets: 'Sample word sets' }[u.type];
}

/** One line per thing that changed inside a unit, in words. */
export function unitSummary(u: DesignUnit, b: unknown, t: unknown): string[] {
  if (b === undefined) return ['new'];
  if (t === undefined) return ['removed'];
  if (u.type === 'area') {
    const a = b as Area, z = t as Area, out: string[] = [];
    if (!same(a.size, z.size)) out.push(`box ${a.size.join(' × ')} → ${z.size.join(' × ')}`);
    if ((a.advance ?? 0) !== (z.advance ?? 0)) out.push(`advance ${a.advance ?? 0} → ${z.advance ?? 0}`);
    const plus = z.glyphs.filter((g) => !a.glyphs.includes(g)), minus = a.glyphs.filter((g) => !z.glyphs.includes(g));
    if (plus.length) out.push(`adds ${list(plus)}`);
    if (minus.length) out.push(`removes ${list(minus)}`);
    if ((a.label ?? '') !== (z.label ?? '')) out.push(`shown as "${z.label ?? ''}"`);
    return out.length ? out : ['changed'];
  }
  if (u.type === 'layout') {
    const a = b as Layout, z = t as Layout, out: string[] = [];
    const n = ruleChanges(a, z).length;
    if (n) out.push(`${n} spacing rule${n === 1 ? '' : 's'} changed`);
    if (!same(a.slots, z.slots)) out.push('structure (parts) changed');
    if (!same(a.center, z.center)) out.push('centering changed');
    if ((a.label ?? '') !== (z.label ?? '')) out.push(`shown as "${z.label ?? ''}"`);
    return out.length ? out : ['changed'];
  }
  if (u.type === 'center') return [`${fmt(b)} → ${fmt(t)}`];
  if (u.type === 'glyph_weight') return [`${b} → ${t}`];
  return ['changed'];
}
const list = (gs: string[]) => (gs.length <= 4 ? gs.join(', ') : `${gs.slice(0, 3).join(', ')} and ${gs.length - 3} more`);
const fmt = (v: unknown) => (v && typeof v === 'object' ? Object.values(v as object).join(', ') : String(v));

/** The design summary the Import dialog shows (design.json only, no base). */
export function designSummary(current: Design, file: Design): string[] {
  return designItems(current, file, current).map((i) => `${i.label}: ${i.summary.join(', ')}`);
}

/** "Update my draft to the font": the font's changes since the draft's base, as items to bring
 *  into the draft (theirs = the font now, current = the draft). Glyphs the draft never touched
 *  already show the font's outline, so only the draft's own glyphs can conflict. With
 *  `defaultKeep`, everything the draft didn't change comes in and conflicts keep the draft's. */
export function fontUpdateItems(base: Current, font: Current, mine: Current): Item[] {
  // `base.svgs` holds the original of every glyph the draft changed or deleted (Bundle.base.svgs)
  const names = new Set([...Object.keys(base.svgs), ...Object.keys(mine.svgs).filter((n) => !svgSame(mine.svgs[n], font.svgs[n]))]);
  const added: string[] = [], changed: string[] = [], deleted: string[] = [];
  const baseSvgs: SvgMap = {}, fontSvgs: SvgMap = {};
  for (const n of names) {
    const b = base.svgs[n], t = font.svgs[n];
    if (svgSame(b, t)) continue;
    if (b !== undefined) baseSvgs[n] = b;
    if (t !== undefined) fontSvgs[n] = t;
    (b === undefined ? added : t === undefined ? deleted : changed).push(n);
  }
  const pseudo = {
    manifest: { svgs: { added, changed, deleted } }, design: font.design, typing: font.typing, svgs: fontSvgs,
    base: { design: base.design, typing: base.typing, svgs: baseSvgs }
  } as unknown as Bundle;
  return diffBundle(pseudo, mine);
}

// ---------------------------------------------------------------- applying

export type Merged = { design: Design; typing: T.Typing; svgWrites: SvgMap; svgDeletes: string[]; applied: Item[] };

/** Apply the kept items (`keep[id] === true`) to the current font. */
export function applyMerge(items: Item[], keep: Record<string, boolean>, cur: Current): Merged {
  const design: Design = JSON.parse(JSON.stringify(cur.design));
  const typing: T.Typing = JSON.parse(JSON.stringify(cur.typing));
  const svgWrites: SvgMap = {}, svgDeletes: string[] = [], applied: Item[] = [];
  for (const it of items) {
    if (!keep[it.id]) continue;
    applied.push(it);
    if (it.kind === 'glyph') {
      if (it.theirs == null) svgDeletes.push(it.key);
      else svgWrites[it.key] = it.theirs;
    } else if (it.kind === 'spelling') {
      const s = { ...T.get(typing, it.key) };
      for (const f of it.fields) s[f.field] = f.theirs;
      if (T.isEmpty(s)) delete typing[it.key];
      else typing[it.key] = s;
    } else setUnit(design, it.unit, it.theirs);
  }
  return { design, typing, svgWrites, svgDeletes, applied };
}

function setUnit(d: Design, u: DesignUnit, v: unknown) {
  const val = v === undefined ? undefined : JSON.parse(JSON.stringify(v));
  if (u.type === 'area') {
    if (val === undefined) delete d.areas[u.name!];
    else d.areas[u.name!] = val as Area;
  } else if (u.type === 'layout') {
    const i = d.layouts.findIndex((l) => l.name === u.name);
    if (val === undefined) { if (i >= 0) d.layouts.splice(i, 1); }
    else if (i >= 0) d.layouts[i] = val as Layout;
    else d.layouts.push(val as Layout);
  } else if (u.type === 'center') d.center = val as Design['center'];
  else if (u.type === 'glyph_weight') { if (val === undefined) delete d.glyph_weight; else d.glyph_weight = val as number; }
  else { if (val === undefined) delete d.test_sets; else d.test_sets = val as Design['test_sets']; }
}

/** Default choices: keep everything that doesn't conflict; conflicts keep the current font. */
export function defaultKeep(items: Item[]): Record<string, boolean> {
  return Object.fromEntries(items.map((i) => [i.id, !i.conflict]));
}

// ---------------------------------------------------------------- undoing (Your changes)

/** Put items back the way the draft started (each item's `base`), on top of `cur` (the draft now).
 *  The items come from comparing the draft with its base (Review's "mine" view). */
export function revertItems(items: Item[], cur: Current): Merged {
  const back = items.map((it): Item =>
    it.kind === 'spelling' ? { ...it, fields: it.fields.map((f) => ({ ...f, theirs: f.base })) } : { ...it, theirs: it.base } as Item);
  return applyMerge(back, Object.fromEntries(back.map((i) => [i.id, true])), cur);
}

/** One spacing rule of a word type, as it differs between two versions of the layout. */
export type RuleChange = { key: string; status: Status; base?: Relationship; theirs?: Relationship; label: string };

/** A rule's identity within a word type: which part it places, on which axis, from what. */
export function ruleKey(r: Relationship): string {
  return [r.axis, r.elem, r.base ?? '', r.base_edge ?? '', r.elem_edge ?? ''].join('|');
}
/** Keys made unique within one layout (a repeat of the same placement gets #2, #3…). */
function keyed(rs: Relationship[]): Map<string, Relationship> {
  const m = new Map<string, Relationship>(), seen: Record<string, number> = {};
  for (const r of rs) {
    const k = ruleKey(r), n = (seen[k] = (seen[k] ?? 0) + 1);
    m.set(n === 1 ? k : `${k}#${n}`, r);
  }
  return m;
}
export const gapText = (r: Relationship) => (typeof r.gap === 'number' ? `gap ${r.gap}` : `${r.gap.length} gap${r.gap.length === 1 ? '' : 's'} by glyph`);
export function ruleLabel(r: Relationship): string {
  return `${r.axis === 'x' ? 'Horizontal' : 'Vertical'} · ${r.elem} from ${r.base ?? 'the page'} · ${gapText(r)}`;
}

/** The spacing rules that differ between two versions of a word type. */
export function ruleChanges(base: Layout, theirs: Layout): RuleChange[] {
  const B = keyed(base.relationships), Th = keyed(theirs.relationships), out: RuleChange[] = [];
  for (const key of new Set([...B.keys(), ...Th.keys()])) {
    const b = B.get(key), t = Th.get(key);
    if (same(b, t)) continue;
    out.push({ key, status: status(b, t), base: b, theirs: t, label: ruleLabel((t ?? b)!) });
  }
  return out;
}

/** `layout` with one rule put back the way it is in `base` (removed if `base` doesn't have it). */
export function revertRule(layout: Layout, base: Layout, key: string): Layout {
  const B = keyed(base.relationships), Cur = keyed(layout.relationships);
  const b = B.get(key);
  const out: Relationship[] = [];
  let placed = false;
  for (const [k, r] of Cur) {
    if (k !== key) out.push(r);
    else if (b) { out.push(JSON.parse(JSON.stringify(b))); placed = true; }
  }
  if (b && !placed) {
    // a rule the draft removed: back where it was among the base's rules that are still there
    const order = [...B.keys()], i = order.indexOf(key);
    const after = order.slice(0, i).reverse().map((k) => Cur.get(k)).find((r) => r && out.includes(r));
    out.splice(after ? out.indexOf(after) + 1 : 0, 0, JSON.parse(JSON.stringify(b)));
  }
  return { ...layout, relationships: out };
}

/** What still uses a glyph: its spellings and the areas it is a member of (before undoing a new glyph). */
export function usesOfGlyph(g: string, design: Design, typing: T.Typing): { spellings: boolean; areas: string[] } {
  return { spellings: !T.isEmpty(typing[g]), areas: Object.entries(design.areas).filter(([, a]) => a.glyphs.includes(g)).map(([n]) => n) };
}

// ---------------------------------------------------------------- line diff (for showing a unit)

export type DiffLine = { op: ' ' | '+' | '-'; text: string };

/** Line diff of two texts (longest common subsequence). Big inputs fall back to remove-all/add-all. */
export function lineDiff(a: string, b: string, maxCells = 4_000_000): DiffLine[] {
  const x = a.split('\n'), y = b.split('\n');
  if (x.length * y.length > maxCells) return [...x.map((t) => ({ op: '-' as const, text: t })), ...y.map((t) => ({ op: '+' as const, text: t }))];
  const n = x.length, m = y.length;
  const L = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out: DiffLine[] = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (x[i] === y[j]) { out.push({ op: ' ', text: x[i] }); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) out.push({ op: '-', text: x[i++] });
    else out.push({ op: '+', text: y[j++] });
  }
  while (i < n) out.push({ op: '-', text: x[i++] });
  while (j < m) out.push({ op: '+', text: y[j++] });
  return out;
}

/** Only the changed lines with `context` lines around them; gaps become one "…" line. */
export function hunks(d: DiffLine[], context = 2): (DiffLine | { op: '…'; text: string })[] {
  const keepIdx = new Set<number>();
  d.forEach((l, i) => { if (l.op !== ' ') for (let k = i - context; k <= i + context; k++) keepIdx.add(k); });
  const out: (DiffLine | { op: '…'; text: string })[] = [];
  let skipped = 0;
  d.forEach((l, i) => {
    if (keepIdx.has(i)) { if (skipped) out.push({ op: '…', text: `${skipped} unchanged line${skipped === 1 ? '' : 's'}` }); skipped = 0; out.push(l); }
    else skipped++;
  });
  if (skipped && out.length) out.push({ op: '…', text: `${skipped} unchanged line${skipped === 1 ? '' : 's'}` });
  return out;
}

export const pretty = (v: unknown) => (v === undefined ? '' : JSON.stringify(v, null, 2));
