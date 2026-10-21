// @vitest-environment node
// (fflate tells files from folders with instanceof Uint8Array, which jsdom's realm breaks)
import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { applySvgs, BundleError, diffSvgs, fromJson, fromStored, fromZip, isEmptyBundle, makeBundle, toJson, toZip, validate, zipName } from './bundle';
import { applyMerge, defaultKeep, designSummary, diffBundle, fontUpdateItems, hunks, lineDiff, revertItems, revertRule, ruleChanges, usesOfGlyph } from './merge';
import type { Layout, Relationship } from './api';
import * as T from './typing';

const design = (): Design => ({
  version: 2,
  center: { x: 500, y: 300 },
  areas: {
    left: { label: 'Left hand', size: [350, 350], glyphs: ['md_ming'] },
    hui: { label: '徽 position', size: [350, 350], glyphs: ['md_7'] }
  },
  layouts: [{ name: 'standard', slots: [{ name: 'left', alternatives: [['left']] }], relationships: [], center: {} }]
} as unknown as Design);
const sp = (latin: string): T.Spelling => ({ ...T.empty(), latin });
const SVG = (d: string) => `<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="${d}"/></svg>`;
const base = { commit: 'abc', design_hash: 'd0', csv_hash: 'c0' };
const baseSvgs = { md_ming: SVG('M0 0h10v10z'), md_7: SVG('M1 1h10v10z'), md_old: SVG('M2 2h5v5z') };

function draft() {
  const d = design();
  d.areas.hui.size = [380, 350];
  d.areas.char = { label: 'Character', size: [350, 350], glyphs: ['md_new'] };
  return makeBundle({
    design: d, typing: { md_7: sp('qi'), md_new: sp('xin') },
    svgs: { md_ming: baseSvgs.md_ming, md_7: SVG('M1 1h20v20z'), md_new: SVG('M3 3h9v9z') },
    baseDesign: design(), baseTyping: { md_7: sp('7') }, baseSvgs, base,
    author: { id: 'u1', name: 'Mei Lin' }, now: new Date('2026-10-18T10:00:00Z')
  });
}

describe('draft bundle', () => {
  it('lists added, changed and deleted glyph files, ignoring a trailing newline', () => {
    expect(diffSvgs({ a: 'x', b: 'y', c: 'z' }, { a: 'x\n', b: 'Y', d: 'w' })).toEqual({ added: ['d'], changed: ['b'], deleted: ['c'] });
  });
  it('reads a stored draft whether the jsonb column holds the object or the same JSON as a string', () => {
    const b = draft();
    expect(fromStored(JSON.parse(toJson(b)))).toEqual(fromJson(toJson(b)));
    expect(fromStored(toJson(b))).toEqual(fromJson(toJson(b)));
    expect(() => fromStored('"not a draft"')).toThrow(BundleError);
  });
  it('keeps only changed glyphs, plus the originals a merge needs', () => {
    const b = draft();
    expect(b.manifest.svgs).toEqual({ added: ['md_new'], changed: ['md_7'], deleted: ['md_old'] });
    expect(Object.keys(b.svgs).sort()).toEqual(['md_7', 'md_new']);
    expect(Object.keys(b.base.svgs).sort()).toEqual(['md_7', 'md_old']);
    expect(b.manifest.base).toEqual(base);
    expect(applySvgs(baseSvgs, b)).toEqual({ md_ming: baseSvgs.md_ming, md_7: SVG('M1 1h20v20z'), md_new: SVG('M3 3h9v9z') });
    expect(isEmptyBundle(b)).toBe(false);
  });
  it('round-trips through JSON and zip', () => {
    const b = draft();
    expect(fromJson(toJson(b))).toEqual(b);
    const z = fromZip(toZip(b));
    expect(z.manifest).toEqual(b.manifest);
    expect(z.design).toEqual(b.design);
    expect(z.svgs).toEqual(b.svgs);
    expect(z.base.svgs).toEqual(b.base.svgs);
    expect(z.typing.md_new.latin).toBe('xin');
    expect(z.base.typing.md_7.latin).toBe('7');
    expect(zipName(b)).toBe('jzp-draft-mei-lin-2026-10-18.zip');
  });
  it('refuses what it cannot open, in words', () => {
    expect(() => validate({})).toThrow(BundleError);
    const b = draft();
    expect(() => validate({ ...b, manifest: { ...b.manifest, format: 99 } })).toThrow(/newer Builder/);
    expect(() => validate({ ...b, svgs: { '../x': 'y' } })).toThrow(/Bad glyph name/);
    expect(() => fromZip(new Uint8Array([1, 2, 3]))).toThrow(/not a .zip/);
  });
  it('an untouched draft is empty', () => {
    const b = makeBundle({ design: design(), typing: {}, svgs: baseSvgs, baseDesign: design(), baseTyping: {}, baseSvgs, base });
    expect(isEmptyBundle(b)).toBe(true);
  });
});

describe('three-way merge', () => {
  const current = () => ({ design: design(), typing: { md_7: sp('7') } as T.Typing, svgs: { ...baseSvgs } });

  it('turns a draft into reviewable items, none conflicting when the font did not move', () => {
    const items = diffBundle(draft(), current());
    expect(items.map((i) => i.id)).toEqual([
      'glyph:md_7', 'glyph:md_new', 'glyph:md_old', 'spelling:md_7', 'spelling:md_new', 'design:area:hui', 'design:area:char'
    ]);
    expect(items.every((i) => !i.conflict)).toBe(true);
    const hui = items.find((i) => i.id === 'design:area:hui')!;
    expect(hui.kind === 'design' && hui.summary).toEqual(['box 350 × 350 → 380 × 350']);
    expect(items.find((i) => i.id === 'glyph:md_old')!.status).toBe('deleted');
  });
  it('flags conflicts where the font changed the same thing differently, and skips what it already has', () => {
    const cur = current();
    cur.design.areas.hui.size = [400, 350];                  // the font changed the same area
    cur.typing.md_new = sp('xin');                            // the font already has this spelling
    cur.svgs.md_7 = SVG('M1 1h30v30z');                       // and changed the same glyph
    const items = diffBundle(draft(), cur);
    expect(items.find((i) => i.id === 'design:area:hui')!.conflict).toBe(true);
    expect(items.find((i) => i.id === 'glyph:md_7')!.conflict).toBe(true);
    expect(items.some((i) => i.id === 'spelling:md_new')).toBe(false);
    const keep = defaultKeep(items);
    expect(keep['design:area:hui']).toBe(false);
    expect(keep['design:area:char']).toBe(true);
  });
  it('applies only the kept items', () => {
    const cur = current();
    const items = diffBundle(draft(), cur);
    const keep = { ...defaultKeep(items), 'glyph:md_old': false, 'spelling:md_7': false };
    const m = applyMerge(items, keep, cur);
    expect(m.design.areas.hui.size).toEqual([380, 350]);
    expect(m.design.areas.char.glyphs).toEqual(['md_new']);
    expect(m.typing.md_7.latin).toBe('7');
    expect(m.typing.md_new.latin).toBe('xin');
    expect(Object.keys(m.svgWrites).sort()).toEqual(['md_7', 'md_new']);
    expect(m.svgDeletes).toEqual([]);
    expect(cur.design.areas.hui.size).toEqual([350, 350]);   // the current font object is untouched
  });
  it('adds, replaces and removes word types by name', () => {
    const t = design();
    t.layouts[0].label = 'Standard word';
    t.layouts.push({ ...t.layouts[0], name: 'chord', label: 'Chord' });
    const b = makeBundle({ design: t, typing: {}, svgs: baseSvgs, baseDesign: design(), baseTyping: {}, baseSvgs, base });
    const cur = current();
    const items = diffBundle(b, cur);
    expect(items.map((i) => i.id)).toEqual(['design:layout:standard', 'design:layout:chord']);
    const m = applyMerge(items, defaultKeep(items), cur);
    expect(m.design.layouts.map((l) => l.name)).toEqual(['standard', 'chord']);
    expect(m.design.layouts[0].label).toBe('Standard word');
  });
  it('summarises an imported design in words', () => {
    const f = design();
    f.areas.left.glyphs.push('md_a', 'md_b');
    expect(designSummary(design(), f)).toEqual(['Area · Left hand: adds md_a, md_b']);
  });
});

describe('updating a draft to a newer font', () => {
  it('brings in what the draft did not touch and asks about what both changed', () => {
    const base = { design: design(), typing: { md_7: sp('7') } as T.Typing, svgs: { md_7: baseSvgs.md_7 } };
    // the font since: area hui resized, md_ming redrawn, md_7 redrawn, a new spelling
    const font = { design: design(), typing: { md_7: sp('7'), md_ming: sp('ming') } as T.Typing, svgs: { ...baseSvgs, md_ming: SVG('M0 0h11v11z'), md_7: SVG('M1 1h40v40z') } };
    font.design.areas.hui.size = [360, 350];
    // the draft: md_7 redrawn its own way, area left relabelled; md_ming rides the font already
    const mine = { design: design(), typing: { md_7: sp('7') } as T.Typing, svgs: { ...font.svgs, md_7: SVG('M1 1h20v20z') } };
    mine.design.areas.left.label = 'Left';
    const items = fontUpdateItems(base, font, mine);
    expect(items.map((i) => [i.id, i.conflict])).toEqual([['glyph:md_7', true], ['spelling:md_ming', false], ['design:area:hui', false]]);
    const m = applyMerge(items, defaultKeep(items), mine);
    expect(m.svgWrites).toEqual({});                          // Keep mine for md_7
    expect(m.design.areas.hui.size).toEqual([360, 350]);
    expect(m.design.areas.left.label).toBe('Left');
    expect(m.typing.md_ming.latin).toBe('ming');
    const take = applyMerge(items, { ...defaultKeep(items), 'glyph:md_7': true }, mine);
    expect(take.svgWrites).toEqual({ md_7: SVG('M1 1h40v40z') });
  });
  it('drops changes the font already has', () => {
    const base = { design: design(), typing: {}, svgs: { md_7: baseSvgs.md_7 } };
    const font = { design: design(), typing: {}, svgs: { ...baseSvgs, md_7: SVG('M9 9h1v1z') } };
    const mine = { design: design(), typing: {}, svgs: { ...baseSvgs, md_7: SVG('M9 9h1v1z') } };
    expect(fontUpdateItems(base, font, mine)).toEqual([]);
  });
});

describe('line diff', () => {
  it('marks removed and added lines and folds unchanged runs', () => {
    const d = lineDiff('a\nb\nc\nd\ne\nf\ng', 'a\nb\nC\nd\ne\nf\ng');
    expect(d.filter((l) => l.op !== ' ')).toEqual([{ op: '-', text: 'c' }, { op: '+', text: 'C' }]);
    const h = hunks(d, 1);
    expect(h.map((l) => l.op)).toEqual(['…', ' ', '-', '+', ' ', '…']);
  });
});

describe('undoing one change (Your changes)', () => {
  // what Review's "mine" view compares the draft with: what it started from
  const startedFrom = (b: ReturnType<typeof draft>) => {
    const svgs: Record<string, string> = { ...baseSvgs, ...b.base.svgs };
    for (const n of b.manifest.svgs.added) delete svgs[n];
    return { design: b.base.design, typing: b.base.typing, svgs };
  };
  const now = (b: ReturnType<typeof draft>) => ({ design: b.design, typing: b.typing, svgs: { ...baseSvgs, ...b.svgs } });

  it('puts one item back and leaves the rest', () => {
    const b = draft();
    const items = diffBundle(b, startedFrom(b));
    const one = (id: string) => revertItems(items.filter((i) => i.id === id), now(b));
    expect(one('design:area:hui').design.areas.hui.size).toEqual([350, 350]);
    expect(one('design:area:hui').design.areas.char).toBeDefined();        // other changes stay
    expect(one('design:area:char').design.areas.char).toBeUndefined();     // a new area goes
    expect(one('glyph:md_7').svgWrites).toEqual({ md_7: baseSvgs.md_7 });  // the original outline
    expect(one('glyph:md_new').svgDeletes).toEqual(['md_new']);            // a new glyph goes
    expect(one('glyph:md_old').svgWrites).toEqual({ md_old: baseSvgs.md_old }); // a deleted one comes back
    expect(one('spelling:md_7').typing.md_7.latin).toBe('7');
    expect(one('spelling:md_new').typing.md_new).toBeUndefined();
  });

  it('says what still uses a glyph', () => {
    const b = draft();
    expect(usesOfGlyph('md_new', b.design, b.typing)).toEqual({ spellings: true, areas: ['char'] });
    expect(usesOfGlyph('md_old', b.design, b.typing)).toEqual({ spellings: false, areas: [] });
  });

  const rel = (elem: string, gap: number, base: string | null = 'left', axis: 'x' | 'y' = 'y'): Relationship => ({ axis, elem, base, gap });
  const layout = (rs: Relationship[]): Layout => ({ name: 'standard', slots: [], relationships: rs, center: {} } as unknown as Layout);

  it('lists spacing rules that changed, one by one', () => {
    const before = layout([rel('a', 10), rel('b', 20), rel('c', 30)]);
    const after = layout([rel('a', 10), rel('b', 25), rel('d', 5)]);
    expect(ruleChanges(before, after).map((r) => [r.key, r.status])).toEqual([['y|b|left||', 'changed'], ['y|c|left||', 'deleted'], ['y|d|left||', 'added']]);
    expect(ruleChanges(before, after)[0].label).toBe('Vertical · b from left · gap 25');
  });

  it('undoes one rule and keeps the others', () => {
    const before = layout([rel('a', 10), rel('b', 20), rel('c', 30)]);
    const after = layout([rel('a', 10), rel('b', 25), rel('d', 5)]);
    expect(revertRule(after, before, 'y|b|left||').relationships).toEqual([rel('a', 10), rel('b', 20), rel('d', 5)]);
    expect(revertRule(after, before, 'y|d|left||').relationships).toEqual([rel('a', 10), rel('b', 25)]);
    // a removed rule comes back where it was
    expect(revertRule(after, before, 'y|c|left||').relationships).toEqual([rel('a', 10), rel('b', 25), rel('c', 30), rel('d', 5)]);
    expect(revertRule(layout([rel('b', 25)]), before, 'y|a|left||').relationships).toEqual([rel('a', 10), rel('b', 25)]);
  });
});
