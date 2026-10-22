// @vitest-environment node
import { afterEach, describe, expect, it } from 'vitest';
import type { Design } from './api';
import { fromJson, makeBundle, toJson, translateBundle } from './bundle';
import { diffBundle } from './merge';
import { current, setRenames, translateDesign, translateId, translateTyping } from './renames';
import * as T from './typing';

const design = (g = 'mod_fy'): Design => ({
  version: 2,
  center: { x: 500, y: 300 },
  areas: { fy: { label: '泛音', size: [350, 350], glyphs: [g] }, left: { label: 'Left hand', size: [350, 350], glyphs: ['md_ming'] } },
  layouts: [{
    name: 'standard', slots: [{ name: 'fy', alternatives: [['fy']] }], center: {},
    relationships: [{ axis: 'y', elem: 'fy', base: 'left', gap: [{ when_elem: [g], when_base: ['md_ming'], value: 10 }, { value: 0 }] }]
  }]
} as unknown as Design);
const sp = (latin: string, vert = ''): T.Spelling => ({ ...T.empty(), latin, vert_variant: vert });
const SVG = (d: string) => `<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="${d}"/></svg>`;
const RENAMED = [{ from: 'mod_fy', to: 'mod_fanyin', date: '2026-10-22' }];

afterEach(() => setRenames([]));

describe('glyph renames', () => {
  it('follow each other in order and leave other names alone', () => {
    const r = [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }, { from: 'x', to: 'y' }];
    expect(current('a', r)).toBe('c');
    expect(current('b', r)).toBe('c');
    expect(current('c', r)).toBe('c');
    expect(current('q', r)).toBe('q');
  });

  it('reach areas, spacing conditions, spelling keys, vertical links and item ids', () => {
    const d = translateDesign(design(), RENAMED);
    expect(d.areas.fy.glyphs).toEqual(['mod_fanyin']);
    const gap = d.layouts[0].relationships[0].gap as { when_elem?: string[]; when_base?: string[] }[];
    expect(gap[0].when_elem).toEqual(['mod_fanyin']);
    expect(gap[0].when_base).toEqual(['md_ming']);
    expect(gap[1]).toEqual({ value: 0 });
    expect(translateTyping({ mod_fy: sp('fy'), md_x: sp('x', 'mod_fy') }, RENAMED)).toEqual({ mod_fanyin: sp('fy'), md_x: sp('x', 'mod_fanyin') });
    expect(translateId('glyph:mod_fy', RENAMED)).toBe('glyph:mod_fanyin');
    expect(translateId('spelling:mod_fy', RENAMED)).toBe('spelling:mod_fanyin');
    expect(translateId('design:area:fy', RENAMED)).toBe('design:area:fy');
  });

  it('keep a name the draft already uses for another glyph', () => {
    expect(translateTyping({ mod_fy: sp('a'), mod_fanyin: sp('b') }, RENAMED)).toEqual({ mod_fy: sp('a'), mod_fanyin: sp('b') });
  });

  it('turn a draft made before the rename into the same changes under the new name', () => {
    const svgs = { mod_fy: SVG('M0 0h10v10z'), md_ming: SVG('M1 1h5v5z') };
    const b = makeBundle({
      design: design(), typing: { mod_fy: sp('fanyin2') }, svgs: { ...svgs, mod_fy: SVG('M0 0h20v20z') },
      baseDesign: design(), baseTyping: { mod_fy: sp('fanyin') }, baseSvgs: svgs,
      base: { commit: 'abc', design_hash: 'd0', csv_hash: 'c0' }, author: { name: 'Mei Lin' }
    });
    setRenames(RENAMED);
    const t = fromJson(toJson(b));                    // what the app opens goes through validate
    expect(t.manifest.svgs.changed).toEqual(['mod_fanyin']);
    expect(Object.keys(t.svgs)).toContain('mod_fanyin');
    expect(Object.keys(t.base.svgs)).toEqual(['mod_fanyin']);
    expect(t.typing.mod_fanyin.latin).toBe('fanyin2');
    expect(t.base.typing.mod_fanyin.latin).toBe('fanyin');
    // against the font as it is now (renamed), the draft's changes are its glyph and spelling
    const font = { design: design('mod_fanyin'), typing: { mod_fanyin: sp('fanyin') }, svgs: { mod_fanyin: svgs.mod_fy, md_ming: svgs.md_ming } };
    const ids = diffBundle(t, font).map((i) => i.id).sort();
    expect(ids).toEqual(['glyph:mod_fanyin', 'spelling:mod_fanyin']);
    expect(translateBundle(t)).toEqual(t);            // translating twice changes nothing
  });
});
