import { describe, expect, it } from 'vitest';
import { applyMerge, glossaryItems, glossarySection, glossaryWhat, itemName, revertItems, type Current, type GlossaryItem, type GlossaryRowItem, type Item } from './merge';
import { upgradeGlossary } from './requests';
import type { Bundle } from './bundle';
import type { GlossaryLayout, GlossaryRows, GRow } from './glossary';

const g = (glyph: string, meaning?: string): GRow => ({ glyph, ...(meaning ? { meaning } : {}) });
const lay = (sections: Record<string, string>): GlossaryLayout => ({
  groups: [{ id: 'all', title: '', sections: Object.keys(sections) }],
  sections: Object.fromEntries(Object.entries(sections).map(([k, title]) => [k, { title }])),
});
/** A draft with only a glossary: its rows and titles now (`theirs`) and where it started (`base`). */
const draft = (base: GlossaryRows, theirs: GlossaryRows, baseLay = lay({ '2b': 'Chords' }), theirsLay = baseLay) =>
  ({ glossary: theirs, glossaryLayout: theirsLay, base: { glossary: base, glossaryLayout: baseLay } }) as unknown as Bundle;
const font = (glossary: GlossaryRows, glossaryLayout = lay({ '2b': 'Chords' })) => ({ design: { areas: {}, layouts: [] }, typing: {}, svgs: {}, glossary, glossaryLayout }) as unknown as Current;
const keepAll = (items: Item[]) => Object.fromEntries(items.map((i) => [i.id, true]));
const names = (rs?: GRow[]) => (rs ?? []).map((r) => ('glyph' in r ? r.glyph : r.word));

const start = { '2b': [g('xl_cuo'), g('xl_dacuo')] };

describe('the glossary, one row at a time', () => {
  it('two rows added to a subtitle are two items, each added', () => {
    const items = glossaryItems(draft(start, { '2b': [g('xl_cuo'), g('xl_dacuo'), g('qia1'), g('qia2')] }), font(start));
    expect(items.map((i) => [i.id, i.status])).toEqual([['glossary-row:2b:g:qia1', 'added'], ['glossary-row:2b:g:qia2', 'added']]);
    expect(items.map((i) => itemName(i))).toEqual(['Glossary · qia1', 'Glossary · qia2']);
    expect(glossarySection(items[0] as GlossaryRowItem)).toBe('2b · Chords');
  });

  it('keeps one row without the other, between the same neighbours', () => {
    const items = glossaryItems(draft(start, { '2b': [g('xl_cuo'), g('qia1'), g('xl_dacuo'), g('qia2')] }), font(start));
    const one = applyMerge(items, { 'glossary-row:2b:g:qia2': true }, font(start));
    expect(names(one.glossary!['2b'])).toEqual(['xl_cuo', 'xl_dacuo', 'qia2']);
    const both = applyMerge(items, keepAll(items), font(start));
    expect(names(both.glossary!['2b'])).toEqual(['xl_cuo', 'qia1', 'xl_dacuo', 'qia2']);
    // the font added a row since: the draft's rows still go next to theirs, the font's stays
    const since = font({ '2b': [g('xl_cuo'), g('xl_new'), g('xl_dacuo')] });
    expect(names(applyMerge(glossaryItems(draft(start, { '2b': [g('xl_cuo'), g('qia1'), g('xl_dacuo')] }), since), { 'glossary-row:2b:g:qia1': true }, since).glossary!['2b']))
      .toEqual(['xl_cuo', 'qia1', 'xl_new', 'xl_dacuo']);
  });

  it('a row taken out, and a row whose definition changed', () => {
    const items = glossaryItems(draft(start, { '2b': [g('xl_cuo', 'pluck two strings')] }), font(start));
    expect(items.map((i) => [i.id, i.status, i.conflict])).toEqual([['glossary-row:2b:g:xl_cuo', 'changed', false], ['glossary-row:2b:g:xl_dacuo', 'deleted', false]]);
    expect(glossaryWhat(items[1] as GlossaryRowItem)).toBe('xl_dacuo');
    const m = applyMerge(items, keepAll(items), font(start));
    expect(m.glossary!['2b']).toEqual([g('xl_cuo', 'pluck two strings')]);
  });

  it('a row the font changed too conflicts; one the font already has is no change', () => {
    const items = glossaryItems(draft(start, { '2b': [g('xl_cuo', 'mine'), g('xl_dacuo')] }), font({ '2b': [g('xl_cuo', 'theirs'), g('xl_dacuo')] }));
    expect(items.map((i) => i.conflict)).toEqual([true]);
    expect(glossaryItems(draft(start, { '2b': [g('xl_cuo', 'same'), g('xl_dacuo')] }), font({ '2b': [g('xl_cuo', 'same'), g('xl_dacuo')] }))).toEqual([]);
  });

  it('a new order, or a new title, is the subtitle\'s own item', () => {
    const items = glossaryItems(draft(start, { '2b': [g('xl_dacuo'), g('xl_cuo'), g('qia1')] }), font(start));
    expect(items.map((i) => i.id)).toEqual(['glossary-row:2b:g:qia1', 'glossary:2b']);
    const sec = items[1] as GlossaryItem;
    expect([sec.whole, sec.order, glossaryWhat(sec)]).toEqual([false, true, 'the order of Chords']);
    // the order alone: the rows that are there go into the draft's order, without the new row
    expect(names(applyMerge(items, { 'glossary:2b': true }, font(start)).glossary!['2b'])).toEqual(['xl_dacuo', 'xl_cuo']);
    expect(names(applyMerge(items, keepAll(items), font(start)).glossary!['2b'])).toEqual(['xl_dacuo', 'xl_cuo', 'qia1']);
    const titled = glossaryItems(draft(start, start, lay({ '2b': 'Chords' }), lay({ '2b': 'Chords and Multi-Note' })), font(start));
    expect(titled.map((i) => [i.id, (i as GlossaryItem).order, glossaryWhat(i as GlossaryItem)])).toEqual([['glossary:2b', false, 'Chords and Multi-Note']]);
  });

  it('a new subtitle is one item, with its rows', () => {
    const items = glossaryItems(draft(start, { ...start, '2c': [g('a'), g('b')] }, lay({ '2b': 'Chords' }), lay({ '2b': 'Chords', '2c': 'Slides' })), font(start));
    const sub = items.find((i) => i.id === 'glossary:2c') as GlossaryItem;
    expect([sub.status, sub.whole, itemName(sub)]).toEqual(['added', true, 'Glossary · Slides']);
    expect(items.some((i) => i.kind === 'glossary-row')).toBe(false);
  });

  it('Undo puts a row back where it was, or takes a new one out', () => {
    const now = { '2b': [g('qia1'), g('xl_dacuo')] };      // xl_cuo taken out, qia1 added
    const items = glossaryItems(draft(start, now), font(start));
    expect(names(revertItems(items.filter((i) => i.id === 'glossary-row:2b:g:xl_cuo'), font(now)).glossary!['2b'])).toEqual(['qia1', 'xl_cuo', 'xl_dacuo']);
    expect(names(revertItems(items.filter((i) => i.id === 'glossary-row:2b:g:qia1'), font(now)).glossary!['2b'])).toEqual(['xl_dacuo']);
  });

  it('a Change Request sent with a subtitle whole reads as its rows, with its decision', () => {
    const bundle = draft(start, { '2b': [g('xl_cuo'), g('xl_dacuo'), g('qia1'), g('qia2')] });
    const old = upgradeGlossary({ bundle, item_ids: ['glyph:qia1', 'glossary:2b'], decisions: { 'glossary:2b': 'keep' } });
    expect(old.item_ids).toEqual(['glyph:qia1', 'glossary-row:2b:g:qia1', 'glossary-row:2b:g:qia2']);
    expect(old.decisions).toEqual({ 'glossary-row:2b:g:qia1': 'keep', 'glossary-row:2b:g:qia2': 'keep' });
    const now = { bundle, item_ids: ['glossary-row:2b:g:qia1'], decisions: {} };
    expect(upgradeGlossary(now)).toEqual(now);                 // sent since: nothing to read differently
  });
});
