// Spellings: how each glyph is typed (builder/inputs/components.csv). Pure helpers, no
// Svelte state: the app keeps a `Typing` map in state.svelte.ts and edits it through here.
// The checks mirror jzpbuild/typing_preview.py `issues()`; a clash or a malformed spelling
// would fail the font build, so it pauses Save.

import { original } from './renames';

export type Spelling = {
  vert_variant: string; common: string; latin: string; latin_alt: string;
  simplified: string; traditional: string; pinyin: string;
};
export type SpellField = keyof Spelling;
/** glyph name -> spelling. Glyph Name is the ID (it is the SVG file name). */
export type Typing = Record<string, Spelling>;

export const FIELDS: SpellField[] = ['latin', 'latin_alt', 'common', 'simplified', 'traditional', 'vert_variant', 'pinyin'];
/** Fields people type to get the glyph (Number/Symbol is built into the number rules). */
export const TYPED: SpellField[] = ['latin', 'latin_alt', 'simplified', 'traditional'];
export const EDITABLE: SpellField[] = ['latin', 'latin_alt', 'simplified', 'traditional', 'vert_variant', 'pinyin'];
export const LABEL: Record<SpellField, string> = {
  latin: 'Latin Entry', latin_alt: 'Latin Entry (Alt)', common: 'Number/Symbol',
  simplified: '简体', traditional: '繁體', vert_variant: 'Vertical form', pinyin: 'PinYin'
};
export const HELP: Record<SpellField, string> = {
  latin: 'What you type on an English keyboard: a one-letter shortcut (k) or the pinyin (lun). Letters and digits, starting with a letter.',
  latin_alt: 'A second way to type it (bl for banlun, fy for fanyin).',
  common: 'Digits and symbols typed the same in any input mode (7, 13+, /). Built into the font\'s number rules; shown, not edited.',
  simplified: 'The character(s) as typed with a simplified-Chinese input method.',
  traditional: 'The traditional form, only if it differs from 简体.',
  vert_variant: 'In vertical notation (after a colon) the font swaps this glyph for its centred version.',
  pinyin: 'Pinyin with tones, for search and labels. Not typed.'
};
export const CSV_FIELDS = ['glyph_name', 'vert_variant', 'common', 'latin', 'latin_alt', 'simplified', 'traditional', 'pinyin'] as const;

const LATIN_RE = /^[A-Za-z][A-Za-z0-9]*$/;
const HAN_RE = /^[㐀-鿿豈-﫿\u{20000}-\u{2ffff}]+$/u;
const RESERVED = new Set(['点', '點', '徽', '。', '，']);

export const empty = (): Spelling => ({ vert_variant: '', common: '', latin: '', latin_alt: '', simplified: '', traditional: '', pinyin: '' });
export const isEmpty = (s: Spelling | undefined) => !s || FIELDS.every((f) => !s[f]);
export const get = (t: Typing, g: string): Spelling => t[g] ?? empty();

/** md_7.6, md_13.9, md_4.blank: typed by pattern, never by a row. A renamed decimal still is one:
 *  the pattern is the name the build's code gives it (renames.ts original()). */
export const isDecimal = (g: string) => /^md_\d+\.(\d|blank)$/.test(original(g));

const CN = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二', '十三'];
/** How a position decimal is typed (no row needed). */
export function decimalPatterns(g: string): string[] {
  const m = /^md_(\d+)\.(\d|blank)$/.exec(original(g));
  if (!m) return [];
  const [n, d] = [+m[1], m[2]];
  if (d === 'blank') return [`${n}.`];   // no Chinese spelling reaches the blank decimal (七徽, 七点 give md_7)
  return [`${n}.${d}`, `${n}点${d}`, `${CN[n]}点${CN[+d]}`, `${CN[n]}徽${CN[+d]}`];
}

/** vertical form -> its horizontal partner. */
export function partners(t: Typing): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [g, s] of Object.entries(t)) if (s.vert_variant) out[s.vert_variant] = g;
  return out;
}

/** A spelling for display, falling back to the partner's for a vertical form. */
export function shown(t: Typing, g: string, f: SpellField): { value: string; inherited: string | null } {
  const own = get(t, g)[f];
  if (own || f === 'vert_variant' || f === 'common') return { value: own, inherited: null };
  const p = partners(t)[g];
  return p && t[p]?.[f] ? { value: t[p][f], inherited: p } : { value: '', inherited: null };
}

/** The tile label: the first spelling that types the glyph (Latin Entry, else Number/Symbol, else 简体). */
export function firstSpelling(t: Typing, g: string): { text: string; inherited: string | null } | null {
  for (const f of ['latin', 'common', 'simplified', 'latin_alt', 'traditional'] as SpellField[]) {
    const s = shown(t, g, f);
    if (s.value) return { text: s.value, inherited: s.inherited };
  }
  return null;
}

export type Issue =
  | { kind: 'clash'; space: 'latin' | 'simplified' | 'traditional'; value: string; glyphs: string[]; fields: { glyph: string; field: SpellField }[]; message: string }
  | { kind: 'invalid'; glyph: string; field: SpellField; value: string; message: string };

function latinKeys(s: Spelling): [SpellField, string][] {
  const k: [SpellField, string][] = [];
  if (s.latin) k.push(['latin', s.latin]);
  if (s.latin_alt) k.push(['latin_alt', s.latin_alt]);
  if (s.common && s.common.length > 1 && /^[A-Za-z]+$/.test(s.common)) k.push(['common', s.common]);
  return k;
}
const SPACES: Record<'latin' | 'simplified' | 'traditional', (s: Spelling) => [SpellField, string][]> = {
  latin: latinKeys,
  simplified: (s) => (s.simplified ? [['simplified', s.simplified]] : []),
  traditional: (s) => (s.traditional ? [['traditional', s.traditional]] : [])
};
const spaceOf = (f: SpellField): 'latin' | 'simplified' | 'traditional' | null =>
  f === 'latin' || f === 'latin_alt' || f === 'common' ? 'latin' : f === 'simplified' || f === 'traditional' ? f : null;

function isPair(t: Typing, a: string, b: string) {
  return t[a]?.vert_variant === b || t[b]?.vert_variant === a;
}

function formatProblem(f: SpellField, v: string, known?: Set<string>): string | null {
  if (!v) return null;
  if (f === 'latin' || f === 'latin_alt') {
    if (!LATIN_RE.test(v)) return /^\d/.test(v) ? 'start with a letter: a leading digit is read as a string or position number' : 'use only letters a–z, A–Z and digits';
  } else if (f === 'simplified' || f === 'traditional') {
    if (RESERVED.has(v)) return 'alone it marks a position; it can\'t type a glyph';
    if (!HAN_RE.test(v)) return 'Chinese characters only';
  } else if (f === 'vert_variant' && known && !known.has(v)) {
    return `${v} doesn't exist`;
  }
  return null;
}

/** Everything that pauses Save. `known`: every glyph that exists (SVGs, design areas). */
export function issues(t: Typing, known?: Set<string>): Issue[] {
  const out: Issue[] = [];
  for (const [space, keyfn] of Object.entries(SPACES) as [keyof typeof SPACES, (s: Spelling) => [SpellField, string][]][]) {
    const claims = new Map<string, { glyph: string; field: SpellField }[]>();
    for (const [g, s] of Object.entries(t)) for (const [f, v] of keyfn(s)) {
      if (!claims.has(v)) claims.set(v, []);
      claims.get(v)!.push({ glyph: g, field: f });
    }
    for (const [value, who] of claims) {
      const glyphs = [...new Set(who.map((w) => w.glyph))].sort();
      if (glyphs.length < 2 || (glyphs.length === 2 && isPair(t, glyphs[0], glyphs[1]))) continue;
      out.push({ kind: 'clash', space, value, glyphs, fields: who,
        message: `“${value}” types ${glyphs.length} glyphs (${glyphs.join(', ')}). A spelling can make only one glyph.` });
    }
  }
  for (const [g, s] of Object.entries(t))
    for (const f of ['latin', 'latin_alt', 'simplified', 'traditional', 'vert_variant'] as SpellField[]) {
      const p = formatProblem(f, s[f], known);
      if (p) out.push({ kind: 'invalid', glyph: g, field: f, value: s[f], message: `“${s[f]}”: ${p}.` });
    }
  return out;
}

export type CellNote = { level: 'free' | 'error' | 'shared' | 'joins'; text: string };
/** The line under a cell while typing `value` into glyph `g`'s field `f` (SpellInput adds the icon for its level). */
export function cellNote(t: Typing, g: string, f: SpellField, value: string, known?: Set<string>, char?: (g: string) => string): CellNote | null {
  const v = value.trim();
  if (!v || f === 'pinyin') return null;
  const p = formatProblem(f, v, known);
  if (p) return { level: 'error', text: p };
  const space = spaceOf(f);
  if (!space) return null;
  const name = (x: string) => (char?.(x) ? `${char(x)} (${x})` : x);
  const others = Object.entries(t).filter(([o, s]) => o !== g && SPACES[space](s).some(([, k]) => k === v)).map(([o]) => o);
  const clash = others.filter((o) => !isPair(t, g, o));
  if (clash.length) return { level: 'error', text: `already used by ${clash.map(name).join(', ')}` };
  if (others.length) return { level: 'shared', text: `shared with ${others[0]}, its vertical ${t[g]?.vert_variant === others[0] ? 'form' : 'partner'}` };
  if (space === 'latin' && v.length > 1) {
    const keys = new Map<string, string>();
    for (const [o, s] of Object.entries(t)) if (o !== g) for (const [, k] of latinKeys(s)) keys.set(k, o);
    for (let i = 1; i < v.length; i++) {
      const a = keys.get(v.slice(0, i)), b = keys.get(v.slice(i));
      if (a && b) return { level: 'joins', text: `joins ${v.slice(0, i)} + ${v.slice(i)}: typing ${v} gives this glyph instead of ${name(a)} then ${name(b)}` };
    }
  }
  return { level: 'free', text: 'free' };
}

/** Glyphs whose spelling differs from the saved one. */
export function changedGlyphs(saved: Typing, cur: Typing): string[] {
  const names = new Set([...Object.keys(saved), ...Object.keys(cur)]);
  return [...names].filter((g) => FIELDS.some((f) => get(saved, g)[f] !== get(cur, g)[f])).sort();
}

/** Records for the server (PUT /api/glyphs, /api/typing/preview). */
export function toRecords(t: Typing): Record<string, string>[] {
  return Object.entries(t).filter(([, s]) => !isEmpty(s)).map(([g, s]) => ({ glyph_name: g, ...s }));
}

export function fromCatalog(rows: { glyph: string; [k: string]: unknown }[]): Typing {
  const t: Typing = {};
  for (const r of rows) {
    const s = empty();
    for (const f of FIELDS) s[f] = String(r[f] ?? '').trim();
    if (!isEmpty(s)) t[r.glyph] = s;
  }
  return t;
}

// ---------------------------------------------------------------- CSV

function csvCell(v: string) {
  return /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}
export function toCsv(t: Typing, order: string[] = []): string {
  const idx = new Map(order.map((g, i) => [g, i]));
  const rows = toRecords(t).sort((a, b) => (idx.get(a.glyph_name) ?? 1e9) - (idx.get(b.glyph_name) ?? 1e9) || a.glyph_name.localeCompare(b.glyph_name));
  return [CSV_FIELDS.join(','), ...rows.map((r) => CSV_FIELDS.map((f) => csvCell(r[f] ?? '')).join(','))].join('\n') + '\n';
}

export function parseCsvRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = '', q = false;
  const s = text.replace(/^﻿/, '');
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q) {
      if (c === '"' && s[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') q = false;
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && s[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim()));
}

/** A components.csv (old columns ID/keys/filename are ignored) as a Typing map. */
export function fromCsv(text: string): Typing {
  const [head, ...body] = parseCsvRows(text);
  if (!head) return {};
  const col = (n: string) => head.findIndex((h) => h.trim() === n);
  const gi = col('glyph_name');
  if (gi < 0) throw new Error('no glyph_name column');
  const t: Typing = {};
  for (const r of body) {
    const g = (r[gi] ?? '').trim();
    if (!g) continue;
    const s = empty();
    for (const f of FIELDS) { const i = col(f); if (i >= 0) s[f] = (r[i] ?? '').trim(); }
    t[g] = s;
  }
  return t;
}

/** Tab-separated grid from a spreadsheet paste. */
export const parseGrid = (text: string): string[][] =>
  text.replace(/\r\n?/g, '\n').replace(/\n$/, '').split('\n').map((l) => l.split('\t'));

/** "wǎng" -> "wang", "bàn lún" -> "banlun": a Latin Entry suggestion from the PinYin. */
export const pinyinToLatin = (p: string) => p.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ü/g, 'v').replace(/[^A-Za-z]/g, '').toLowerCase();

/** Everything a search box should match for a glyph: its name, every spelling (inherited ones
 *  too), the PinYin with and without tones, and a decimal's typing patterns. Lower-case. */
export function searchText(t: Typing, g: string): string {
  const parts = [g];
  for (const f of FIELDS) {
    const v = shown(t, g, f).value;
    if (v) parts.push(v, ...(f === 'pinyin' ? [pinyinToLatin(v), v.replace(/\s+/g, '')] : []));
  }
  if (isDecimal(g)) parts.push(...decimalPatterns(g));
  return parts.join(' ').toLowerCase();
}
