import { describe, expect, it } from 'vitest';
import { byId, changedLayout, cleanLayout, glossarySearchText, marksGlyph, markdown, newId, sectionList, titlesSummary, exampleHtml, exampleText, usageFrom, verticalTemplate, changedSections, cleanRows, describeUses, moveRow, refuse, renameInRows, sectionSummary, usesOf, type Section } from './glossary';

import type { Typing } from './typing';
import { empty } from './typing';

const g = (glyph: string, meaning?: string) => ({ glyph, ...(meaning ? { meaning } : {}) });
const w = (word: string, ...glyphs: string[]) => ({ word, glyphs });
const sections: Section[] = [{ id: '1a', title: '1a: A', kind: 'usage' }, { id: '3e', title: '3e: E', kind: 'vertical' }, { id: '99', title: '99: Hidden', kind: 'vertical', hidden: true }];

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
  it('refuses only a row twice in one section', () => {
    expect(refuse({}, w('少息', 'a', 'b'), sections[0])).toBeNull();          // a word fits any section
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
    expect(cleanRows({ '3e': [{ word: '少息', glyphs: ['a', 'b'], typed: ' :shaoxi ' }, { glyph: 'k', typed: '' }] })).toEqual({ '3e': [{ word: '少息', glyphs: ['a', 'b'], typed: ':shaoxi' }, g('k')] });
    expect(cleanRows({ '1a': [{ glyph: 'a', usage: [' s9{} ', ''] }, { glyph: 'b', usage: ['', ''] }] })).toEqual({ '1a': [{ glyph: 'a', usage: ['s9{}', ''] }, g('b')] });
    expect(changedSections({ '1a': [g('a')], '3e': [] }, { '1a': [g('a')], '99': [g('b')] })).toEqual(['99']);
    expect(['99', '3x', '1a', '4', '1d-v', '1d'].sort(byId)).toEqual(['1a', '1d', '1d-v', '3x', '4', '99']);
  });
  it('sums up what changed in a section', () => {
    expect(sectionSummary([g('a'), g('b'), g('c')], [g('c'), g('a', 'x'), w('少息', 'a', 'b')]))
      .toEqual(['added 少息', 'removed b', 'moved c, a', 'definition of a']);
    expect(sectionSummary([g('a')], [{ glyph: 'a', usage: ['{}5', '{}五'] }])).toEqual(['example of a']);
  });
});

describe("a row's example word", () => {
  const sp = (o: Record<string, string>) => ({ ...empty(), ...o });
  const t: Typing = { md_ming: sp({ latin: 's', simplified: '名' }), md_9: sp({ common: '9', simplified: '九' }), lg_gou: sp({ latin: 'k', simplified: '勾' }),
    md_3: sp({ common: '3', simplified: '三' }), md_7: sp({ common: '7', simplified: '七' }), md_zhong: sp({ latin: 'd', simplified: '中' }),
    md_san: sp({ common: '0', simplified: '散' }), md_6: sp({ common: '6', simplified: '六' }), xl_cuo: sp({ latin: 'C', simplified: '撮' }), md_x: sp({ latin: 'zz' }) };
  const typed = (glyphs: string[], texts: string[]) => ({ glyphs, texts, clusters: texts.map((_, i) => i) });
  it('makes the Chinese from ASCII, the row glyph as {}', () => {
    const r = usageFrom('s9k3', typed(['md_ming', 'md_9', 'lg_gou', 'md_3'], ['s', '9', 'k', '3']), 'lg_gou', t);
    expect(r).toEqual({ source: 's9{}3', other: '名九{}三', zh: false, missing: [] });
  });
  it('makes the ASCII from Chinese, commas and the chord bar included', () => {
    const r = usageFrom('撮中七，七｜散六', typed(['xl_cuo', 'md_zhong', 'md_7', 'md_7', 'blank_bar', 'md_san', 'md_6'], ['撮', '中', '七，', '七', '｜', '散', '六']), 'xl_cuo', t);
    expect(r).toEqual({ source: '{}中七，七｜散六', other: '{}d7,7|06', zh: true, missing: [] });
    // 十二 after a finger reads as 10.2 in Chinese: 徽 keeps it the twelfth hui, as the row's glyph or not
    const t12: Typing = { ...t, md_12: sp({ common: '12', simplified: '十二' }), md_5: sp({ common: '5', simplified: '五' }) };
    expect(usageFrom('s12k5', typed(['md_ming', 'md_12', 'lg_gou', 'md_5'], ['s', '12', 'k', '5']), 'md_12', t12)).toMatchObject({ other: '名{}徽勾五' });
    expect(usageFrom('s12k5', typed(['md_ming', 'md_12', 'lg_gou', 'md_5'], ['s', '12', 'k', '5']), 'lg_gou', t12)).toMatchObject({ other: '名十二徽{}五' });
    // a hui number then 半 (or a numeral) reads as a decimal in Chinese: a comma keeps them apart; and the
    // row's glyph keeps the spelling typed (bl, not banlun), marked
    const tb: Typing = { ...t, lg_banlun: sp({ latin: 'banlun', latin_alt: 'bl', simplified: '半轮' }) };
    expect(usageFrom('s9bl7', typed(['md_ming', 'md_9', 'lg_banlun', 'md_7'], ['s', '9', 'bl', '7']), 'lg_banlun', tb))
      .toMatchObject({ source: 's9<r>bl</r>7', other: '名九，{}七' });
    expect(usageFrom('s9banlun7', typed(['md_ming', 'md_9', 'lg_banlun', 'md_7'], ['s', '9', 'banlun', '7']), 'lg_banlun', tb))
      .toMatchObject({ source: 's9{}7' });
    expect(usageFrom('s9bl7', typed(['md_ming', 'md_9', 'lg_banlun', 'md_7'], ['s', '9', 'bl', '7']), 'md_ming', tb))
      .toMatchObject({ other: '{}九，半轮七' });
    expect(exampleText('s9<r>bl</r>7', 'banlun')).toBe('s9bl7');
    const p = usageFrom('5.4k3', typed(['md_5.4', 'lg_gou', 'md_3'], ['5.4', 'k', '3']), 'lg_gou', t);
    expect(p).toMatchObject({ other: '五点四{}三' });
  });
  it("says which part has no spelling in the other language, and refuses an example without the row's glyph", () => {
    expect(usageFrom('zzk', typed(['md_x', 'lg_gou'], ['zz', 'k']), 'lg_gou', t)).toMatchObject({ other: null, missing: ['zz'] });
    expect(usageFrom('s9', typed(['md_ming', 'md_9'], ['s', '9']), 'lg_gou', t)).toMatchObject({ error: expect.stringMatching(/doesn't type lg_gou \(勾\)/) });
  });
  it("makes a vertical row's example: a glyph as {} (its vertical form counts), a word written out, the colon kept", () => {
    const tv: Typing = { ...t, md_san: sp({ common: '0', simplified: '散', vert_variant: 'md_san2' }), md_san2: sp({ latin: 'san' }),
      md_da: sp({ latin: 'v', simplified: '大' }), md_xi: sp({ latin: 'xi', simplified: '息' }) };
    expect(usageFrom(':san5', typed(['blank_colon', 'md_san2', 'md_5'], [':', 'san', '5']), 'md_san', { ...tv, md_5: sp({ common: '5', simplified: '五' }) }))
      .toEqual({ source: ':{}5', other: ':{}五', zh: false, missing: [] });
    expect(usageFrom('：大息七', typed(['blank_colon', 'md_da', 'md_xi', 'md_7'], ['：', '大', '息', '七']), ['md_da', 'md_xi'], tv))
      .toEqual({ source: ':大息七', other: ':vxi7', zh: true, missing: [] });
    expect(usageFrom(':v7', typed(['blank_colon', 'md_da', 'md_7'], [':', 'v', '7']), ['md_da', 'md_xi'], tv))
      .toMatchObject({ error: expect.stringMatching(/doesn't type md_xi \(息\)/) });
    expect(verticalTemplate(tv, { word: '大息', glyphs: ['md_da', 'md_xi'] })).toEqual([':vxi', ':大息']);
    expect(verticalTemplate(tv, { glyph: 'md_san' })).toEqual([':{}', ':{}']);
    // a glyph the font sets vertically by itself needs no colon, nor does a word holding one
    expect(verticalTemplate(tv, { glyph: 'md_da' }, new Set(['md_da']))).toEqual(['{}', '{}']);
    expect(verticalTemplate(tv, { word: '大息', glyphs: ['md_da', 'md_xi'] }, new Set(['md_xi']))).toEqual(['vxi', '大息']);
    expect(exampleHtml(':{}<r>|</r>', 'san', false)).toBe(':san|');
    // the glyph is marked when the example has more in it than the glyph
    expect([[':{}5', ':{}五'], ['s9{}k3', ''], ['{}', '{}'], [':{}', ':{}'], [':vxi', ':大息']].map((u) => marksGlyph(u as [string, string])))
      .toEqual([true, true, false, false, false]);
    expect(marksGlyph(['s9<r>bl</r>7', ''])).toBe(true);
    expect(marksGlyph([':<r>bl</r>', ':{}'])).toBe(false);
  });
  it('fills a template as text and as marked HTML', () => {
    expect(exampleText('{}d7,7<r>|</r>06', 'C')).toBe('Cd7,7|06');
    expect(exampleHtml('s9{}k3', '&gt;')).toBe('s9<span class="r">&amp;gt;</span>k3');
    expect(exampleHtml('{}d7<r>|</r>0', 'C')).toBe('<span class="r">C</span>d7<span class="r">|</span>0');
  });
});

describe('section titles, subtitles and descriptions', () => {
  it('reads a little Markdown, the same as the server', () => {
    expect(markdown('Preface with `:`. **Best** use *Chinese*.')).toBe('<p>Preface with <text>:</text>. <strong>Best</strong> use <em>Chinese</em>.</p>');
    expect(markdown('<u>Vertical only</u>\n<small>see [this](#glossary-left)</small>')).toBe('<p><u>Vertical only</u><br /><small>see <a href="#glossary-left">this</a></small></p>');
    expect(markdown('one\n\n- a\n- `s9k3`')).toBe('<p>one</p>\n<ul><li>a</li><li><text>s9k3</text></li></ul>');
    expect(markdown('ex: <jzp>Cs9,3|05</jzp>')).toBe('<p>ex: <jzp>Cs9,3|05</jzp></p>');
    const bad = markdown('<img src=x onerror=alert(1)> <script>x</script> <u onclick="x">u</u> [x](javascript:alert(1))');
    expect(bad).not.toMatch(/<img|<script|<u |href="javascript/);
  });
  it('orders subtitles by their section titles and names new ones', () => {
    const l = { groups: [{ id: 'b', title: 'B', sections: ['2a'] }, { id: 'a', title: 'A', sections: ['1a'] }],
      sections: { '1a': { title: '1a', kind: 'usage' as const, usage: ['{}', '{}'] as [string, string] }, '2a': { title: '2a', kind: 'vertical' as const }, '99': { title: 'h', kind: 'vertical' as const, hidden: true } } };
    expect(sectionList(l).map((x) => x.id)).toEqual(['2a', '1a', '99']);
    // visibility is its own switch; a hidden section title hides its subtitles; the old kind 'hidden' reads as one
    expect(sectionList({ ...l, groups: [...l.groups, { id: 'h', title: 'H', hidden: true, sections: ['99'] }] }).map((x) => !!x.hidden)).toEqual([false, false, true]);
    expect(sectionList({ groups: [{ id: 'x', title: 'X', hidden: true, sections: ['2a'] }], sections: { '2a': l.sections['2a'] } })[0].hidden).toBe(true);
    expect(cleanLayout({ groups: [], sections: { o: { title: 'old', kind: 'hidden' } } })!.sections.o).toEqual({ title: 'old', kind: 'vertical', hidden: true });
    expect(newId('3f: Ornaments', ['3e'])).toBe('3f');
    expect(newId('3e: Again', ['3e'])).toBe('3e-again');
    expect(newId('五', ['s1'])).toBe('s2');
    const m = { ...l, groups: [{ ...l.groups[0], title: 'B!' }, l.groups[1]], sections: { ...l.sections, '2a': { ...l.sections['2a'], description: 'd' } } };
    expect(changedLayout(l, m)).toEqual(['2a', 'titles']);
    expect(titlesSummary(l.groups, m.groups)).toEqual(['renamed: B → B!']);
  });
});

describe("List view's search in the Glossary column", () => {
  it('finds where a glyph is, and a glyph left out', () => {
    const sp = (o: Record<string, string>) => ({ ...empty(), ...o });
    const t: Typing = { a: sp({ latin: 'k' }), b: sp({ latin: 'u' }), c: sp({ pinyin: 'x' }) };
    const uses = usesOf({ '1a': [g('a')], '3e': [w('少息', 'a', 'x')] }, sections);
    expect(glossarySearchText(t, 'a', uses, sections)).toContain('1a: own row');
    expect(glossarySearchText(t, 'a', uses, sections)).toContain('3e: e');
    expect(glossarySearchText(t, 'b', uses, sections)).toBe('not in the glossary');
    expect(glossarySearchText(t, 'c', uses, sections)).toBe('');              // no spelling: nothing to show
  });
});
