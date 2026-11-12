import { describe, expect, it } from 'vitest';
import * as T from './typing';
import { changedWords, renameInWords, renumber, sectionOrder, wordsFromCsv, wordsOfGlyphs, wordsToCsv, type Words } from './glossaryWords';

const sp = (latin: string, glossary: string, glossary_order = '') => ({ ...T.empty(), latin, glossary, glossary_order });
const typing = (): T.Typing => ({
  md_a: sp('ka', '3c: N', '2'), md_b: sp('kb', '3c: N', '0.5'), md_c: sp('kc', '3c: N; 3d: M', '2; 1'),
  md_d: sp('kd', '3c: N'), md_e: sp('ke', '3c: N', '0.1')
});
const words = (): Words => [{ word: '甲乙', glyphs: 'md_a md_b', glossary: '3c: N', glossary_order: '1', meaning: 'two' }];
const order = ['md_a', 'md_b', 'md_c', 'md_d', 'md_e'];

describe('the glossary words', () => {
  it('orders a section like the font page: number, then ASCII, then no number last', () => {
    const o = sectionOrder(typing(), words(), order);
    expect(o.get('3c')!.map((e) => e.key)).toEqual(['md_e', 'md_b', '甲乙', 'md_a', 'md_c', 'md_d']);
    expect(o.get('3d')!.map((e) => e.key)).toEqual(['md_c']);
  });
  it('renumbers to 1, 2, 3… keeping that order, one number per section where they differ', () => {
    const r = renumber(typing(), words(), order);
    expect(['md_e', 'md_b', 'md_a', 'md_c', 'md_d'].map((g) => r.typing[g].glossary_order)).toEqual(['1', '2', '4', '5; 1', '6']);
    expect(r.words[0].glossary_order).toBe('3');
    expect(sectionOrder(r.typing, r.words, order).get('3c')!.map((e) => e.key)).toEqual(['md_e', 'md_b', '甲乙', 'md_a', 'md_c', 'md_d']);
  });
  it('round-trips through words.csv and says which words changed', () => {
    const w = [...words(), { word: '少息', glyphs: 'md_shao md_xi', glossary: '3e: E, rests', glossary_order: '2', meaning: 'a "short" rest' }];
    expect(wordsFromCsv(wordsToCsv(w))).toEqual(w);
    expect(changedWords(w, [{ ...w[0], meaning: 'changed' }])).toEqual(['甲乙', '少息']);
  });
  it('knows which words a glyph is in, and follows a rename', () => {
    expect(wordsOfGlyphs(words())).toEqual({ md_a: ['甲乙'], md_b: ['甲乙'] });
    const r = renameInWords(words(), 'md_b', 'md_bb');
    expect(r.words[0].glyphs).toBe('md_a md_bb');
    expect(r.changed).toEqual(['甲乙']);
  });
});
