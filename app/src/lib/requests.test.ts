// @vitest-environment node
// Change Requests: which draft changes a request holds (locks), and the snapshot a request
// carries (only the chosen changes, on the draft's own base).
import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { makeBundle } from './bundle';
import { buildInputs, canWithdraw, draftItems, lockedItems, snapshot, type ChangeRequest } from './requests';
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

describe('snapshot', () => {
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
  it('builds as the font plus those changes', () => {
    const { bundle } = snapshot(draft(), font, ['glyph:md_7']);
    expect(buildInputs(bundle, font)).toMatchObject({ svgs: { md_7: SVG('M1 1h20v20z') }, deleted: [] });
  });
});
