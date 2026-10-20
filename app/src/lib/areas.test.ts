import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { addArea, areaIdProblem, wordTypeIdProblem, decimalGrid, deleteAreaProblems, splitMembers, usedIn } from './areas';

const design = (): Design => ({
  version: 2,
  center: { x: 500, y: 500 },
  areas: {
    left: { label: 'Left hand', size: [350, 350], glyphs: ['md_ming'] },
    hui: { label: '徽 position', size: [350, 350], glyphs: ['md_7', 'md_7.6', 'md_7.blank', 'md_wai'] },
    lonely: { label: 'Lonely', size: [100, 100], glyphs: [] }
  },
  layouts: [
    { name: 'standard', slots: [{ name: 'left', alternatives: [['left']] }, { name: 'hui', alternatives: [['hui']] }] },
    { name: 'chord', slots: [{ name: 'pos', alternatives: [['a:hui', 'b:left']] }] }
  ]
} as unknown as Design);

describe('areas', () => {
  it('deletes only an empty area no word type uses, and says why otherwise', () => {
    const d = design();
    expect(deleteAreaProblems(d, 'lonely')).toEqual([]);
    const hui = deleteAreaProblems(d, 'hui');
    expect(hui).toHaveLength(2);
    expect(hui[0]).toMatch(/still has 4 glyphs/);
    expect(hui[1]).toMatch(/^standard, chord use it/);
    d.areas.left.glyphs = [];
    expect(deleteAreaProblems(d, 'left')).toEqual(['standard, chord use it. Take it out of those word types in Structure (Advanced) first.']);
    d.areas.lonely.glyphs = ['md_x'];
    expect(deleteAreaProblems(d, 'lonely')).toEqual(['It still has 1 glyph. Remove it first: Manage, then × on each.']);
  });
  it('lists the word types that use an area, through named elements too', () => {
    expect(usedIn(design(), 'hui').map((l) => l.name)).toEqual(['standard', 'chord']);
    expect(usedIn(design(), 'lonely')).toEqual([]);
  });
  it('splits members into glyph chips and position decimals', () => {
    expect(splitMembers(design().areas.hui.glyphs)).toEqual({ chips: ['md_7', 'md_wai'], decimals: ['md_7.6', 'md_7.blank'] });
  });
  it('lays the decimals out as 13 hui × (blank, .1–.9)', () => {
    const g = decimalGrid(['md_7.6', 'md_7.blank'], (x) => x !== 'md_13.9');
    expect(g).toHaveLength(13);
    expect(g[0].map((c) => c.label)).toEqual(['1.', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9']);
    expect(g[6][6]).toMatchObject({ glyph: 'md_7.6', label: '7.6', member: true, exists: true });
    expect(g[6][0]).toMatchObject({ glyph: 'md_7.blank', label: '7.', member: true });
    expect(g[12][9]).toMatchObject({ glyph: 'md_13.9', member: false, exists: false });
  });
  it('checks a new area id and adds the area', () => {
    const d = design();
    expect(areaIdProblem(d, '')).toMatch(/id/);
    expect(areaIdProblem(d, '2x')).toMatch(/starting with a letter/);
    expect(areaIdProblem(d, 'left')).toMatch(/already/);
    expect(areaIdProblem(d, 'thumb')).toBeNull();
    addArea(d, 'thumb', ' Thumb mark ', [350, 300]);
    expect(d.areas.thumb).toEqual({ label: 'Thumb mark', size: [350, 300], glyphs: [] });
  });
  it('says why a word type id is not usable', () => {
    const d = design();
    const taken = d.layouts[0].name;
    expect(wordTypeIdProblem(d, '')).toMatch(/Give/);
    expect(wordTypeIdProblem(d, 'new word')).toMatch(/letters, digits and _/);
    expect(wordTypeIdProblem(d, taken)).toBe(`"${taken}" is already a word type.`);
    expect(wordTypeIdProblem(d, 'chord_2')).toBeNull();
  });
});
