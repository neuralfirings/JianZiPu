// @vitest-environment node
// Coming characters: suggesting which one a new glyph draws, and the draft rows a Change Request
// puts on the font page.
import { describe, expect, it } from 'vitest';
import type { Design } from './api';
import { makeBundle } from './bundle';
import { draftRows, exampleSvg, placedGhosts, functionUrl, heldBy, newGlyphs, stageLabel, suggestGhost, zhOf, type UpcomingRow } from './upcoming';
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
    expect(rows).toEqual([{ glyph: 'budong_md', ghost: 'u12', zh: '不动 · 不動', pinyin: 'bù dòng', ascii: 'budong', meaning: 'keep the hand still', section: '1e', after: '下', example: null, marked: false }]);
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

  it('a row with its own example sends it, and its whole word as one drawing', () => {
    const typing = { yin3_md: sp({ latin: 'yin3', simplified: '引' }) };
    const b = makeBundle({ design, typing, svgs: { yin3_md: SVG }, baseDesign: design, baseTyping: {}, baseSvgs: {},
      base: { commit: null, design_hash: '', csv_hash: '' }, glossary: { '1e': [{ glyph: 'yin3_md', usage: ['<r>{}</r>shang9', '<r>{}</r>上九'] }] } });
    expect(draftRows(b, {}).rows[0]).toMatchObject({ example: ['<r>引</r>上九', '<r>yin3</r>shang9'], marked: true });
    const alone = makeBundle({ design, typing, svgs: { yin3_md: SVG }, baseDesign: design, baseTyping: {}, baseSvgs: {},
      base: { commit: null, design_hash: '', csv_hash: '' }, glossary: { '1e': [{ glyph: 'yin3_md', usage: ['{}', '{}'] }] } });
    expect(draftRows(alone, {}).rows[0]).toMatchObject({ example: ['引', 'yin3'], marked: false });   // the row on its own: no red
    const el = (glyph: string, x: number, y: number) => ({ name: glyph, area: 'a', glyph, x, y, size: [350, 350] as [number, number] });
    const svg = exampleSvg([{ glyphs: [], layout: 'v', pen: 0, elements: [el('yin3_md', 0, 700), el('md_shang', 0, 350), el('blank_colon', 0, 0), el('nodrawing', 0, 0)] }],
      { yin3_md: SVG, md_shang: SVG.replace('fill="black"', ''), blank_colon: SVG }, ['yin3_md'], ['blank_colon'])!;
    expect(svg.match(/<g transform=/g)?.length).toBe(2);                    // the colon and a glyph with no drawing left out
    expect(svg).toContain('color="#a3352b"');                               // the row's glyph in red
    expect(svg).toContain('translate(0 -1050) scale(1)');                    // its drawing in its part's box, as a group (the ink can be measured)
    expect(svg).toContain('viewBox="-70 -1120 490 840"');                     // the word's box, padded a tenth
    expect(exampleSvg([], {}, [])).toBe(null);
  });

  it('a glyph published before goes back to its own row: this request\'s first, else the latest', () => {
    const row = (id: string, glyphs: string[], cr: string | null, at: string, stage: UpcomingRow['stage'] = 'draft') => ({ id, glyphs, change_request_id: cr, updated_at: at, stage });
    const rows = [row('u20', ['qc2s_md'], 'cr-1', '2026-11-17'), row('u22', ['qc2s_md'], 'cr-1', '2026-11-18'), row('u21', ['qc3s_md'], 'cr-0', '2026-11-18'),
      row('u5', ['qc3s_md'], 'cr-1', '2026-11-01'), row('u9', ['old_md'], 'cr-1', '2026-11-18', 'released')];
    expect(placedGhosts(rows, ['qc2s_md', 'qc3s_md', 'old_md', 'new_md'], 'cr-1')).toEqual({ qc2s_md: 'u22', qc3s_md: 'u5' });
  });
});
