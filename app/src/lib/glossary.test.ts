import { describe, expect, it } from 'vitest';
import { byId, changedSections, cleanRows, describeUses, moveRow, refuse, renameInRows, sectionSummary, usesOf, type Section } from './glossary';

const g = (glyph: string, meaning?: string) => ({ glyph, ...(meaning ? { meaning } : {}) });
const w = (word: string, ...glyphs: string[]) => ({ word, glyphs });
const sections: Section[] = [{ id: '1a', title: '1a: A', kind: 'usage' }, { id: '3e', title: '3e: E', kind: 'vertical' }, { id: '99', title: '99: Hidden', kind: 'hidden' }];

describe('the glossary rows', () => {
  it('moves a row within a section and to another, counting the gaps before the move', () => {
    const rows = { '1a': [g('a'), g('b'), g('c')], '3e': [g('x')] };
    expect(moveRow(rows, { sid: '1a', index: 0 }, { sid: '1a', index: 3 })['1a']).toEqual([g('b'), g('c'), g('a')]);
    expect(moveRow(rows, { sid: '1a', index: 2 }, { sid: '1a', index: 0 })['1a']).toEqual([g('c'), g('a'), g('b')]);
    expect(moveRow(rows, { sid: '1a', index: 1 }, { sid: '1a', index: 2 })['1a']).toEqual(rows['1a']);     // the gap after itself
    const m = moveRow(rows, { sid: '1a', index: 1 }, { sid: '3e', index: 0 });
    expect(m).toEqual({ '1a': [g('a'), g('c')], '3e': [g('b'), g('x')] });
    expect(rows['1a']).toHaveLength(3);                                                                       // not changed in place
    expect(moveRow(rows, { sid: '1a', index: 0 }, { sid: '4', index: 0 })['4']).toEqual([g('a')]);           // into an empty section
  });
  it('refuses a word in an example-word section and a row twice in one section', () => {
    expect(refuse({}, w('少息', 'a', 'b'), sections[0])).toMatch(/can't go there/);
    expect(refuse({ '3e': [g('a')] }, g('a'), sections[1])).toMatch(/already/);
    expect(refuse({ '3e': [g('a')] }, g('a'), sections[1], 0)).toBeNull();
    expect(refuse({ '3e': [g('a')] }, w('少息', 'a', 'b'), sections[1])).toBeNull();
  });
  it('says where a glyph is used, a section at a time', () => {
    const uses = usesOf({ '1a': [g('a')], '3e': [w('少息', 'a', 'b'), w('大息', 'c', 'b'), g('b')], '99': [g('d')] }, sections);
    expect(describeUses(uses.a, sections)).toEqual(['1a: own row', '3e: in 少息']);
    expect(describeUses(uses.b, sections)).toEqual(['3e: own row, in 少息, 大息']);
    expect(describeUses(uses.d, sections)).toEqual(['99 (hidden): own row']);
    expect(uses.e).toBeUndefined();
  });
  it('renames a glyph in its rows and words', () => {
    const r = renameInRows({ '1a': [g('a', 'm')], '3e': [w('少息', 'a', 'b')], '99': [g('c')] }, 'a', 'z');
    expect(r.rows).toEqual({ '1a': [g('z', 'm')], '3e': [w('少息', 'z', 'b')], '99': [g('c')] });
    expect(r.changed).toEqual(['1a', '3e']);
  });
  it('cleans rows from a draft and tells sections apart', () => {
    expect(cleanRows({ '1a': [{ glyph: ' a ', meaning: '' }, { nope: 1 }, { word: 'x', glyphs: [] }], '3e': 'no' })).toEqual({ '1a': [g('a')] });
    expect(cleanRows([])).toBeUndefined();
    expect(changedSections({ '1a': [g('a')], '3e': [] }, { '1a': [g('a')], '99': [g('b')] })).toEqual(['99']);
    expect(['99', '3x', '1a', '4', '1d-v', '1d'].sort(byId)).toEqual(['1a', '1d', '1d-v', '3x', '4', '99']);
  });
  it('sums up what changed in a section', () => {
    expect(sectionSummary([g('a'), g('b'), g('c')], [g('c'), g('a', 'x'), w('少息', 'a', 'b')]))
      .toEqual(['added 少息', 'removed b', 'moved c, a', 'meaning of a']);
  });
});
