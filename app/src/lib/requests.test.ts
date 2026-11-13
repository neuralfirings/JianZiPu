// @vitest-environment node
// Change Requests: which draft changes a request holds (locks), and the snapshot a request
// carries (only the chosen changes, on the draft's own base).
import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { makeBundle } from './bundle';
import { buildInputs, canWithdraw, draftItems, inTheFont, lockedItems, releasedItems, snapshot, startingTicks, type ChangeRequest } from './requests';
import * as T from './typing';

const design = (): Design => ({
  version: 2, center: { x: 500, y: 300 },
  areas: { left: { label: 'Left hand', size: [350, 350], glyphs: ['md_ming'] }, hui: { label: '徽', size: [350, 350], glyphs: ['md_7'] } },
  layouts: [{ name: 'standard', slots: [], relationships: [], center: {} }]
} as unknown as Design);
const sp = (latin: string): T.Spelling => ({ ...T.empty(), latin });
const SVG = (d: string) => `<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="${d}"/></svg>`;
const font = { md_ming: SVG('M0 0h10v10z'), md_7: SVG('M1 1h10v10z') };

function draft() {
  const d = design();
  d.areas.hui.size = [380, 350];
  d.areas.left.label = 'Left';
  d.areas.hui.glyphs.push('md_new');
  return makeBundle({
    design: d, typing: { md_7: sp('qi'), md_new: sp('xin') },
    svgs: { ...font, md_7: SVG('M1 1h20v20z'), md_new: SVG('M3 3h9v9z') },
    baseDesign: design(), baseTyping: { md_7: sp('7') }, baseSvgs: font,
    base: { commit: 'abc', design_hash: 'd0', csv_hash: 'c0' }, author: { id: 'u1', name: 'Mei' }
  });
}

const req = (o: Partial<ChangeRequest>): ChangeRequest => ({
  id: 'r1', author: 'u1', title: 'Hui spacing', notes: '', credit: '', bundle: draft(), item_ids: [], base_commit: 'abc',
  status: 'sent', decisions: {}, reply: '', release: null, created_at: '2026-10-20T10:00:00Z', updated_at: '', reviewed_at: null, released_at: null, ...o
});

describe('locks', () => {
  it('an open request holds all its changes; later on only the kept ones; withdrawn and declined none', () => {
    const ids = ['design:area:hui', 'spelling:md_7'];
    expect(Object.keys(lockedItems([req({ item_ids: ids })]))).toEqual(ids);
    expect(Object.keys(lockedItems([req({ item_ids: ids, status: 'in_review', decisions: { 'design:area:hui': 'skip' } })]))).toEqual(ids);
    expect(Object.keys(lockedItems([req({ item_ids: ids, status: 'in_candidate', decisions: { 'design:area:hui': 'keep', 'spelling:md_7': 'skip' } })]))).toEqual(['design:area:hui']);
    expect(lockedItems([req({ item_ids: ids, status: 'withdrawn' }), req({ id: 'r2', item_ids: ids, status: 'declined' })])).toEqual({});
  });
  it('a released change is the font\'s: it stays changeable, and says which release has it', () => {
    const ids = ['design:area:hui', 'spelling:md_7'];
    const r = req({ item_ids: ids, status: 'released', release: '3.200', decisions: { 'design:area:hui': 'keep', 'spelling:md_7': 'skip' } });
    expect(lockedItems([r])).toEqual({});
    expect(Object.keys(releasedItems([r]))).toEqual(['design:area:hui']);
    expect(releasedItems([r])['design:area:hui'].release).toBe('3.200');
  });
  it('names the request that holds a change', () => {
    expect(lockedItems([req({ item_ids: ['spelling:md_7'] })])['spelling:md_7']).toEqual({ id: 'r1', title: 'Hui spacing', sent: '2026-10-20T10:00:00Z' });
  });
  it('can be withdrawn until a change is kept', () => {
    expect(canWithdraw({ status: 'sent', decisions: {} })).toBe(true);
    expect(canWithdraw({ status: 'in_review', decisions: { a: 'skip' } })).toBe(true);
    expect(canWithdraw({ status: 'in_review', decisions: { a: 'keep' } })).toBe(false);
    expect(canWithdraw({ status: 'in_candidate', decisions: {} })).toBe(false);
  });
});

describe('draft request', () => {
  it('starts with everything ticked, or where a saved draft left off; newer changes start ticked', () => {
    expect(startingTicks(['a', 'b'], null)).toEqual({ a: true, b: true });
    const d = { title: 't', notes: '', credit: '', chosen: ['a'], seen: ['a', 'b', 'gone'], saved_at: '' };
    expect(startingTicks(['a', 'b', 'new'], d)).toEqual({ a: true, b: false, new: true });
  });
});

describe('snapshot', () => {
  it('carries the notes of the chosen changes only', () => {
    const b = draft();
    b.manifest.notes = { 'design:area:hui': 'Wider box', 'design:area:left': 'Renamed', 'glyph:gone': 'x' };
    expect(snapshot(b, font, ['design:area:hui']).bundle.manifest.notes).toEqual({ 'design:area:hui': 'Wider box' });
    expect(snapshot(b, font, ['glyph:md_new']).bundle.manifest.notes).toBeUndefined();
  });
  it('carries only the chosen changes, on the draft base', () => {
    const b = draft();
    expect(draftItems(b, font).map((i) => i.id)).toEqual(['glyph:md_7', 'glyph:md_new', 'spelling:md_7', 'spelling:md_new', 'design:area:left', 'design:area:hui']);
    const { bundle, itemIds } = snapshot(b, font, ['design:area:hui', 'glyph:md_new', 'spelling:md_new']);
    expect(itemIds).toEqual(['glyph:md_new', 'spelling:md_new', 'design:area:hui']);
    expect(bundle.design.areas.hui.size).toEqual([380, 350]);
    expect(bundle.design.areas.left.label).toBe('Left hand');   // not chosen
    expect(bundle.typing).toEqual({ md_7: sp('7'), md_new: sp('xin') });
    expect(bundle.manifest.svgs).toEqual({ added: ['md_new'], changed: [], deleted: [] });
    expect(bundle.manifest.base.commit).toBe('abc');
    // compared with its base, the snapshot is exactly the chosen items
    expect(draftItems(bundle, font).map((i) => i.id).sort()).toEqual([...itemIds].sort());
  });
  it('carries the chosen glossary sections and titles, and only those', () => {
    const rows = { '1a': [{ glyph: 'md_ming' }], '1b': [{ glyph: 'md_7' }] };
    const lay = { groups: [{ id: '1', title: '1: Left Hand', sections: ['1a', '1b'] }],
      sections: { '1a': { title: '1a: Left Hand Finger' }, '1b': { title: '1b: Hui' } } };
    const b = makeBundle({
      design: design(), typing: {}, svgs: font, baseDesign: design(), baseTyping: {}, baseSvgs: font,
      base: { commit: 'abc', design_hash: 'd0', csv_hash: 'c0' },
      glossary: { '1a': [{ glyph: 'md_ming', meaning: 'ring finger' }], '1b': [{ glyph: 'md_7', meaning: 'seventh hui' }] },
      baseGlossary: rows,
      glossaryLayout: { groups: [{ ...lay.groups[0], title: '1. Left Hand' }],
        sections: { '1a': { title: '1.1. Which Finger to Use' }, '1b': { title: '1.2. Hui' } } },
      baseGlossaryLayout: lay
    });
    expect(draftItems(b, font).map((i) => i.id)).toEqual(['glossary:1a', 'glossary:1b', 'glossary-titles']);
    const { bundle, itemIds } = snapshot(b, font, ['glossary:1a', 'glossary-titles']);
    expect(itemIds).toEqual(['glossary:1a', 'glossary-titles']);
    expect(bundle.glossary).toEqual({ '1a': [{ glyph: 'md_ming', meaning: 'ring finger' }], '1b': [{ glyph: 'md_7' }] });
    expect(bundle.glossaryLayout!.sections).toEqual({ '1a': { title: '1.1. Which Finger to Use' }, '1b': { title: '1b: Hui' } });
    expect(bundle.glossaryLayout!.groups[0].title).toBe('1. Left Hand');
    // what Review sees in the request: exactly the chosen items
    expect(draftItems(bundle, font).map((i) => i.id).sort()).toEqual([...itemIds].sort());
  });
  it('builds as the font plus those changes', () => {
    const { bundle } = snapshot(draft(), font, ['glyph:md_7']);
    expect(buildInputs(bundle, font)).toMatchObject({ svgs: { md_7: SVG('M1 1h20v20z') }, deleted: [] });
  });
});

describe('in the font', () => {
  it('finds the draft changes the font has now, and leaves the rest', () => {
    const b = draft();
    const now = design();
    now.areas.hui = structuredClone(b.design.areas.hui);
    const fontNow = { design: now, typing: { md_7: sp('qi') }, svgs: { ...font, md_7: b.svgs.md_7 } };
    const items = draftItems(b, font);
    expect([...inTheFont(items, b, fontNow)].sort()).toEqual(['design:area:hui', 'glyph:md_7', 'spelling:md_7']);
    expect(inTheFont(items, b, { design: design(), typing: { md_7: sp('7') }, svgs: font }).size).toBe(0);
  });
});
