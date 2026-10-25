import { describe, it, expect } from 'vitest';
import {
  empty, issues, cellNote, firstSpelling, shown, partners, changedGlyphs, toRecords, fromCatalog,
  toCsv, fromCsv, parseGrid, pinyinToLatin, isDecimal, decimalPatterns, type Typing, type Spelling
} from './typing';

const sp = (s: Partial<Spelling>): Spelling => ({ ...empty(), ...s });
const base = (): Typing => ({
  lg_gou: sp({ latin: 'k', simplified: '勾', pinyin: 'gōu' }),
  lg_tuo: sp({ latin: 'h', simplified: '托' }),
  lg_ti: sp({ latin: 'i', simplified: '剔' }),
  lg_lun: sp({ latin: 'lun', simplified: '轮', traditional: '輪', vert_variant: 'md_lun' }),
  md_lun: sp({}),
  md_san: sp({ common: '0', simplified: '散', vert_variant: 'md_san2' }),
  md_san2: sp({ latin: 'san' })
});

describe('issues', () => {
  it('finds nothing in a clean set', () => expect(issues(base())).toEqual([]));
  it('names the spelling and both glyphs of a clash', () => {
    const t = base(); t.lg_tuo.latin = 'k';
    const [e] = issues(t);
    expect(e).toMatchObject({ kind: 'clash', value: 'k', glyphs: ['lg_gou', 'lg_tuo'] });
    expect(e.message).toContain('lg_gou');
  });
  it('lets a vertical pair share a spelling, and nothing else', () => {
    const t = base(); t.md_lun.latin = 'lun';
    expect(issues(t)).toEqual([]);
    t.lg_ti.latin = 'lun';
    expect(issues(t).map((e) => e.kind)).toEqual(['clash']);
  });
  it('treats Latin Entry and its Alt as one namespace', () => {
    const t = base(); t.lg_tuo.latin_alt = 'k';
    expect(issues(t)).toHaveLength(1);
  });
  it.each([
    ['latin', '4xi', 'start with a letter'], ['latin', 'ban-lun', 'only letters'],
    ['simplified', 'abc', 'Chinese characters only'], ['simplified', '点', 'marks a position']
  ] as const)('rejects %s = %s', (f, v, msg) => {
    const t = base(); t.lg_ti[f] = v;
    expect(issues(t)[0].message).toContain(msg);
  });
  it('checks vertical forms against the known glyphs', () => {
    const t = base(); t.lg_ti.vert_variant = 'md_nope';
    expect(issues(t, new Set(Object.keys(t)))[0].message).toContain('md_nope');
  });
});

describe('cellNote', () => {
  it('says free, taken, shared, joins, invalid', () => {
    const t = base();
    expect(cellNote(t, 'lg_tuo', 'latin', 't')?.level).toBe('free');
    expect(cellNote(t, 'lg_tuo', 'latin', 'k', undefined, (g) => (g === 'lg_gou' ? '勾' : ''))?.text).toBe('already used by 勾 (lg_gou)');
    expect(cellNote(t, 'md_lun', 'latin', 'lun')?.level).toBe('shared');
    expect(cellNote(t, 'lg_tuo', 'latin', 'ki')?.level).toBe('joins');
    expect(cellNote(t, 'lg_tuo', 'latin', '4k')?.level).toBe('error');
    expect(cellNote(t, 'lg_tuo', 'latin', '')).toBeNull();
    expect(cellNote(t, 'lg_tuo', 'pinyin', 'tuō')).toBeNull();
    const titles = ['1a: Left Hand Finger', '2a: Basic Right Hand'];
    expect(cellNote(t, 'lg_tuo', 'glossary', '2a: Basic Right Hand', undefined, undefined, titles)).toBeNull();
    expect(cellNote(t, 'lg_tuo', 'glossary', '1a: Left Hand Finger; 2a: Basic Right Hand', undefined, undefined, titles)).toBeNull();
    expect(cellNote(t, 'lg_tuo', 'glossary', '2a: Basic Right Hand; 9z: Nowhere', undefined, undefined, titles)?.level).toBe('warn');
    expect(cellNote(t, 'lg_tuo', 'glossary', '2a', undefined, undefined, titles)?.level).toBe('warn');   // the id alone isn't the title
    expect(cellNote(t, 'lg_tuo', 'glossary', '9z')).toBeNull();     // no sections known: nothing to say
  });
});

describe('vertical forms and labels', () => {
  it('maps vertical forms to their partner', () => expect(partners(base())).toEqual({ md_lun: 'lg_lun', md_san2: 'md_san' }));
  it('shows the partner\'s spelling as inherited, but keeps its own', () => {
    const t = base();
    expect(shown(t, 'md_lun', 'latin')).toEqual({ value: 'lun', inherited: 'lg_lun' });
    expect(shown(t, 'md_san2', 'latin')).toEqual({ value: 'san', inherited: null });
    expect(shown(t, 'md_san2', 'simplified')).toEqual({ value: '散', inherited: 'md_san' });
  });
  it('labels a tile with the first working spelling', () => {
    const t = base();
    expect(firstSpelling(t, 'lg_gou')?.text).toBe('k');
    expect(firstSpelling(t, 'md_san')?.text).toBe('0');
    expect(firstSpelling(t, 'md_lun')).toEqual({ text: 'lun', inherited: 'lg_lun' });
    expect(firstSpelling(t, 'md_nothing')).toBeNull();
  });
});

describe('decimals', () => {
  it('recognises position decimals', () => {
    expect(isDecimal('md_7.6')).toBe(true);
    expect(isDecimal('md_13.blank')).toBe(true);
    expect(isDecimal('md_7')).toBe(false);
  });
  it('spells their patterns', () => {
    expect(decimalPatterns('md_7.6')).toEqual(['7.6', '7点6', '七点六', '七徽六']);
    expect(decimalPatterns('md_12.blank')).toEqual(['12.']);
  });
});

describe('records and CSV', () => {
  it('lists what changed', () => {
    const a = base(), b = base(); b.lg_gou.latin = 'g'; b.new_one = sp({ latin: 'x' });
    expect(changedGlyphs(a, b)).toEqual(['lg_gou', 'new_one']);
  });
  it('drops empty rows from records', () => {
    expect(toRecords(base()).map((r) => r.glyph_name)).not.toContain('md_lun');
  });
  it('reads the catalog, ignoring glyphs with nothing', () => {
    const t = fromCatalog([{ glyph: 'a', latin: 'x', areas: [] }, { glyph: 'b', latin: '' }]);
    expect(Object.keys(t)).toEqual(['a']);
  });
  it('round-trips through CSV, in the given order, quoting commas', () => {
    const t = base(); t.lg_ti.pinyin = 'a, b';
    const text = toCsv(t, ['md_san', 'lg_gou']);
    expect(text.split('\n')[0]).toBe('glyph_name,vert_variant,common,latin,latin_alt,simplified,traditional,pinyin,glossary');
    expect(text.split('\n')[1].startsWith('md_san,')).toBe(true);
    expect(text).toContain('"a, b"');
    const back = fromCsv(text);
    expect(back.lg_ti.pinyin).toBe('a, b');
    expect(back.lg_lun).toEqual(t.lg_lun);
  });
  it('imports an old CSV with ID/keys/filename columns', () => {
    const t = fromCsv('ID,keys,filename,glyph_name,vert_variant,common,latin,latin_alt,simplified,traditional,pinyin\n1,s,md_ming,md_ming,,,s,,名,,míng\n');
    expect(t.md_ming).toMatchObject({ latin: 's', simplified: '名', pinyin: 'míng', glossary: '' });
  });
  it('keeps the Glossary column, which no glyph inherits and nothing clashes on', () => {
    const t = base(); t.lg_gou.glossary = '2a: Basic Right Hand'; t.lg_tuo.glossary = '2a: Basic Right Hand';
    t.md_san.glossary = '1d: Special Cases; 3c: Related to String & Hui Number';
    expect(issues(t)).toEqual([]);
    expect(fromCsv(toCsv(t)).md_san.glossary).toBe('1d: Special Cases; 3c: Related to String & Hui Number');
    expect(shown(t, 'md_san2', 'glossary')).toEqual({ value: '', inherited: null });
    expect(changedGlyphs(base(), t)).toEqual(['lg_gou', 'lg_tuo', 'md_san']);
  });
  it('parses a spreadsheet paste', () => expect(parseGrid('a\tb\nc\td\n')).toEqual([['a', 'b'], ['c', 'd']]));
  it('suggests a Latin Entry from the PinYin', () => {
    expect(pinyinToLatin('wǎng')).toBe('wang');
    expect(pinyinToLatin('bàn lún')).toBe('banlun');
  });
});
