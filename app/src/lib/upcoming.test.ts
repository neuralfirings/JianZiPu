// @vitest-environment node
// Coming characters: suggesting which one a new glyph draws, and the draft rows a Change Request
// puts on the font page.
import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { makeBundle } from './bundle';
import { draftRows, functionUrl, heldBy, newGlyphs, stageLabel, suggestGhost, zhOf, type UpcomingRow } from './upcoming';
import * as T from './typing';
import type { Item } from './merge';

const design = { version: 2, center: { x: 500, y: 300 }, areas: {}, layouts: [] } as unknown as Design;
const sp = (o: Partial<T.Spelling>): T.Spelling => ({ ...T.empty(), ...o });
const SVG = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M0 0h9v9z"/></svg>';
const ghosts = [
  { id: 'u12', zh: '不动', pinyin: 'bù dòng' },
  { id: 'u14', zh: '索铃 · 索鈴', pinyin: 'suǒ líng' },
];

describe('coming characters', () => {
  it('suggests the ghost a new glyph draws, by its 中文, else its pinyin', () => {
    expect(suggestGhost(sp({ simplified: '不动', pinyin: 'bu2 dong4' }), ghosts)).toBe('u12');
    expect(suggestGhost(sp({ traditional: '索鈴' }), ghosts)).toBe('u14');           // the traditional half of 索铃 · 索鈴
    expect(suggestGhost(sp({ simplified: '急二', pinyin: 'suo ling' }), ghosts)).toBe('u14');
    expect(suggestGhost(sp({ simplified: '撮' }), ghosts)).toBe(null);
    expect(suggestGhost(undefined, ghosts)).toBe(null);
  });

  it('a Change Request\'s new glyphs with a glossary row become draft rows, after the row above them', () => {
    const typing = { md_xia: sp({ latin: 'xia', simplified: '下', pinyin: 'xià' }), budong_md: sp({ latin: 'budong', simplified: '不动', traditional: '不動', pinyin: 'bù dòng' }),
      lone_md: sp({ latin: 'lone', simplified: '孤' }) };
    const b = makeBundle({ design, typing, svgs: { budong_md: SVG, lone_md: SVG }, baseDesign: design, baseTyping: {}, baseSvgs: {},
      base: { commit: null, design_hash: '', csv_hash: '' },
      glossary: { '1e': [{ glyph: 'md_xia', meaning: 'slide down' }, { glyph: 'budong_md', meaning: 'keep the hand still' }] } });
    const { rows, unplaced } = draftRows(b, { budong_md: 'u12' });
    expect(rows).toEqual([{ glyph: 'budong_md', ghost: 'u12', zh: '不动 · 不動', pinyin: 'bù dòng', ascii: 'budong', meaning: 'keep the hand still', section: '1e', after: '下' }]);
    expect(unplaced).toEqual(['lone_md']);                                         // no glossary row: nowhere to show it
    expect(draftRows(b, {}).rows[0].ghost).toBe(null);                             // untagged: a new ghost
    expect(zhOf({ word: '泛起', glyphs: ['md_fan', 'md_qi'] }, typing)).toBe('泛起');
  });

  it('a candidate holds a ghost only with every glyph that draws it', () => {
    const row = (id: string, stage: UpcomingRow['stage'], glyphs: string[]) => ({ id, stage, glyphs }) as UpcomingRow;
    const rows = [row('u1', 'draft', ['ji2_md', 'ji3_md']), row('u2', 'draft', ['budong_md']), row('u3', 'planned', ['x']), row('u4', 'draft', [])];
    expect(heldBy(rows, new Set(['ji2_md', 'budong_md', 'x']), ['draft', 'test']).map((r) => r.id)).toEqual(['u2']);
  });

  it('badges and the function address', () => {
    expect(stageLabel({ stage: 'test', version: '3.400-rc.2' })).toBe('In release 3.400');
    expect(stageLabel({ stage: 'draft' })).toBe('Draft design');
    expect(functionUrl('https://p.supabase.co/')).toBe('https://p.supabase.co/functions/v1/feedback');
    expect(newGlyphs([{ kind: 'glyph', status: 'added', key: 'a' }, { kind: 'glyph', status: 'changed', key: 'b' }] as Item[])).toEqual(['a']);
  });
});
