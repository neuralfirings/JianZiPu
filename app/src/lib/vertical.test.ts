import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { verticalOnlyGlyphs } from './vertical';

const slot = (name: string, ...alts: string[][]) => ({ name, alternatives: alts });
const layout = (name: string, ...slots: ReturnType<typeof slot>[]) => ({ name, slots, relationships: [], center: {} });
const design = (areas: Record<string, string[]>): Design => ({
  version: 2, center: { x: 0, y: 0 },
  areas: Object.fromEntries(Object.entries(areas).map(([n, glyphs]) => [n, { size: [100, 100] as [number, number], glyphs }])),
  layouts: [
    layout('vertical', slot('colon', ['colon']), slot('row', ['char'])),
    layout('basic', slot('left', ['left']), slot('string', ['string_top:string']))
  ]
});

describe('verticalOnlyGlyphs', () => {
  it('a glyph only a colon word type can hold needs no colon; one another word type uses does', () => {
    const d = design({ colon: ['blank_colon'], char: ['md_shang', 'md_zhong'], left: ['md_zhong'], string: ['md_7'] });
    expect([...verticalOnlyGlyphs(d)]).toEqual(['md_shang']);
  });
  it('follows the design being edited: a glyph just added to the area counts at once', () => {
    const d = design({ colon: ['blank_colon'], char: ['md_shang', 'md_quzhong'], left: [], string: [] });
    expect(verticalOnlyGlyphs(d).has('md_quzhong')).toBe(true);
    expect(verticalOnlyGlyphs(null).size).toBe(0);
  });
});
