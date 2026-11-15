import { describe, expect, it } from 'vitest';
import { glossarySection, glossaryWhat, itemName, type GlossaryItem } from './merge';
import type { GRow } from './glossary';

const g = (glyph: string, meaning?: string): GRow => ({ glyph, ...(meaning ? { meaning } : {}) });
const item = (base: GRow[], theirs: GRow[], title?: string): GlossaryItem => ({
  id: 'glossary:1b', kind: 'glossary', key: '1b', status: 'changed', conflict: false, base, theirs, current: base,
  ...(title ? { meta: { base: { title }, theirs: { title } } } : {}),
});

describe('naming a glossary change by its rows', () => {
  it('says which rows it adds, takes out or edits', () => {
    expect(glossaryWhat(item([g('mod_ji')], [g('mod_ji'), g('ji2_md')]))).toBe('ji2_md');
    expect(glossaryWhat(item([], [g('a'), g('b')]))).toBe('a and b');
    expect(glossaryWhat(item([], [g('a'), g('b'), g('c')]))).toBe('a and 2 more');
    expect(glossaryWhat(item([g('mod_ji'), g('x')], [g('x')]))).toBe('without mod_ji');
    expect(glossaryWhat(item([g('x', 'old')], [g('x', 'new')]))).toBe('x');
    expect(glossaryWhat(item([g('x')], [g('y'), { glyphs: ['a', 'b'], word: '带起' }]))).toBe('y and 带起, without x');
  });
  it('names the subtitle when no row is added, taken out or edited', () => {
    expect(glossaryWhat(item([g('a'), g('b')], [g('b'), g('a')], 'Speed'))).toBe('the order of Speed');
    expect(glossaryWhat(item([g('a')], [g('a')], 'Speed'))).toBe('Speed');          // its title or description
    expect(glossaryWhat(item([g('a')], [g('a')]))).toBe('1b');                       // a draft with no titles
  });
  it('the list name and the subtitle it is in', () => {
    const it = item([g('mod_ji')], [g('mod_ji'), g('ji2_md')], 'Speed');
    expect(itemName(it)).toBe('Glossary · ji2_md');
    expect(glossarySection(it)).toBe('1b · Speed');
  });
});
