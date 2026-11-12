import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { renameIn, renameProblem } from './rename';
import * as T from './typing';

const design = (): Design => ({
  version: 2, center: { x: 500, y: 300 },
  areas: { char: { label: 'Character', size: [350, 350], glyphs: ['md_ming', 'md_foo'] }, left: { label: 'Left hand', size: [350, 350], glyphs: ['md_foo'] } },
  layouts: [{ name: 'standard', slots: [{ name: 'char', alternatives: [['char']] }], center: {},
    relationships: [{ a: 'char', b: 'left', gap: [{ glyphs: ['md_foo'], gap: 20 }, { glyphs: ['md_ming'], gap: 10 }] }] }]
} as unknown as Design);

describe('renaming a glyph', () => {
  it('refuses names the server wouldn\'t take, or that are taken (capitals too)', () => {
    const have = ['md_foo', 'md_ming', 'lg_gou'];
    expect(renameProblem('md_foo', 'md_tuichu', have)).toBeNull();
    expect(renameProblem('md_foo', '  md_tuichu ', have)).toBeNull();
    expect(renameProblem('md_foo', '', have)).toMatch(/Type the new name/);
    expect(renameProblem('md_foo', 'md_foo', have)).toMatch(/its name already/);
    expect(renameProblem('md_foo', 'md foo', have)).toMatch(/Letters, digits/);
    expect(renameProblem('md_foo', 'md_9.', have)).toMatch(/Letters, digits/);
    expect(renameProblem('md_foo', '推出', have)).toMatch(/Letters, digits/);
    expect(renameProblem('md_foo', 'MD_MING', have)).toBe('md_ming already exists.');
    expect(renameProblem('md_foo', 'MD_FOO', have)).toBeNull();          // its own name in other capitals
  });
  it('changes the name everywhere it is used, and says where', () => {
    const typing = { md_foo: { ...T.empty(), latin: 'tc', simplified: '推出' }, md_san: { ...T.empty(), vert_variant: 'md_foo' }, md_ming: { ...T.empty(), latin: 's' } } as T.Typing;
    const r = renameIn(design(), typing, 'md_foo', 'md_tuichu');
    expect(r.design.areas.char.glyphs).toEqual(['md_ming', 'md_tuichu']);
    expect(r.design.areas.left.glyphs).toEqual(['md_tuichu']);
    expect(JSON.stringify(r.design.layouts)).toContain('"glyphs":["md_tuichu"]');
    expect(JSON.stringify(r.design)).not.toContain('md_foo');
    expect(r.typing.md_tuichu).toMatchObject({ latin: 'tc', simplified: '推出' });
    expect(r.typing.md_foo).toBeUndefined();
    expect(r.typing.md_san.vert_variant).toBe('md_tuichu');
    expect(r.impact).toEqual({ spellings: true, areas: ['char', 'left'], rules: 1, vertical: ['md_san'] });
    expect(r.design.layouts[0].name).toBe('standard');                        // names that aren't glyphs stay
  });
});
