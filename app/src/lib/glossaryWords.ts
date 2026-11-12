// The glossary's words (builder/inputs/words.csv; lib/words.ts is the sample words for testing): rows written together, like :少息, with a
// section, an order and a meaning of their own. A word is typed through the glyphs' spellings, so
// it has no spellings itself; `glyphs` names the glyphs it types (filled in by Glyphs > Words).
// The ordering here is the same as the server's (glossary.py entries), for Renumber.
import * as T from './typing';

export type GWord = { word: string; glyphs: string; glossary: string; glossary_order: string; meaning: string };
export type Words = GWord[];
export const WORD_FIELDS = ['word', 'glyphs', 'glossary', 'glossary_order', 'meaning'] as const;
export const emptyWord = (word = ''): GWord => ({ word, glyphs: '', glossary: '', glossary_order: '', meaning: '' });
export const glyphsOf = (w: GWord) => w.glyphs.split(/\s+/).filter(Boolean);

/** A word as words.csv holds it: every field there, trimmed. */
export function cleanWord(x: Partial<GWord>): GWord {
  return Object.fromEntries(WORD_FIELDS.map((f) => [f, String(x[f] ?? '').trim()])) as GWord;
}

export function wordsToCsv(ws: Words): string {
  const cell = (v: string) => (/[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  return [WORD_FIELDS.join(','), ...ws.filter((w) => w.word).map((w) => WORD_FIELDS.map((f) => cell(w[f] ?? '')).join(','))].join('\n') + '\n';
}
export function wordsFromCsv(text: string): Words {
  const rows = T.parseCsvRows(text);
  if (!rows.length) return [];
  const head = rows[0].map((h) => h.trim());
  return rows.slice(1).map((r) => cleanWord(Object.fromEntries(head.map((h, i) => [h, r[i] ?? ''])))).filter((w) => w.word);
}

/** The words that differ between two lists (added, removed or edited), by word. */
export function changedWords(a: Words, b: Words): string[] {
  const m = new Map(a.map((w) => [w.word, JSON.stringify(cleanWord(w))]));
  const n = new Map(b.map((w) => [w.word, JSON.stringify(cleanWord(w))]));
  return [...new Set([...m.keys(), ...n.keys()])].filter((k) => m.get(k) !== n.get(k));
}

/** glyph -> the words it's in ("in words: 少息, 大息" under its row in List view). */
export function wordsOfGlyphs(ws: Words): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const w of ws) for (const g of new Set(glyphsOf(w))) (out[g] ??= []).push(w.word);
  return out;
}

/** The word list with every use of glyph `from` renamed to `to` (Rename…). */
export function renameInWords(ws: Words, from: string, to: string): { words: Words; changed: string[] } {
  const changed: string[] = [];
  const words = ws.map((w) => {
    const gs = glyphsOf(w);
    if (!gs.includes(from)) return w;
    changed.push(w.word);
    return { ...w, glyphs: gs.map((g) => (g === from ? to : g)).join(' ') };
  });
  return { words, changed };
}

// ---------------------------------------------------------------- order (glossary.py entries)

const sectionsOf = (glossary: string) => glossary.split(';').map((x) => x.trim()).filter(Boolean);
const idOf = (title: string) => title.split(':')[0].trim();
/** The Glossary order for each of a row's sections: one number for all, or one per section. */
function orders(glossary: string, order: string): (number | null)[] {
  const n = Math.max(1, sectionsOf(glossary).length);
  let parts = order.split(';').map((x) => x.trim());
  if (parts.length === 1) parts = Array(n).fill(parts[0]);
  return Array.from({ length: n }, (_, k) => (parts[k] && /^-?\d+(\.\d+)?$/.test(parts[k]) ? Number(parts[k]) : null));
}
const asciiOf = (t: T.Typing, g: string) => {
  const s = T.get(t, g);
  return s.latin || s.latin_alt || s.common || s.simplified || g;
};

export type Entry = { kind: 'glyph'; key: string } | { kind: 'word'; key: string };

/** Each section's rows in the order the font page shows them: by Glossary order, ties
 *  alphabetically by the ASCII spelling, rows without a number last in file order (glyphs in
 *  `order`, components.csv's, then words). */
export function sectionOrder(t: T.Typing, ws: Words, order: string[]): Map<string, Entry[]> {
  const idx = new Map(order.map((g, i) => [g, i]));
  const glyphs = Object.keys(t).sort((a, b) => (idx.get(a) ?? 1e9) - (idx.get(b) ?? 1e9) || a.localeCompare(b));
  const items: { sid: string; key: [number, number, string, number]; e: Entry }[] = [];
  glyphs.forEach((g, i) => {
    const s = T.get(t, g), secs = sectionsOf(s.glossary), os = orders(s.glossary, s.glossary_order);
    secs.forEach((title, k) => items.push({ sid: idOf(title), key: [os[k] == null ? 1 : 0, os[k] ?? 0, asciiOf(t, g).toLowerCase(), i], e: { kind: 'glyph', key: g } }));
  });
  ws.forEach((w, j) => {
    const secs = sectionsOf(w.glossary), os = orders(w.glossary, w.glossary_order);
    const alpha = glyphsOf(w).map((g) => asciiOf(t, g)).join('').toLowerCase();
    secs.forEach((title, k) => items.push({ sid: idOf(title), key: [os[k] == null ? 1 : 0, os[k] ?? 0, alpha, glyphs.length + j], e: { kind: 'word', key: w.word } }));
  });
  const cmp = (a: typeof items[number], b: typeof items[number]) =>
    a.key[0] - b.key[0] || a.key[1] - b.key[1] || (a.key[2] < b.key[2] ? -1 : a.key[2] > b.key[2] ? 1 : 0) || a.key[3] - b.key[3];
  const out = new Map<string, Entry[]>();
  for (const it of items.sort(cmp)) (out.get(it.sid) ?? out.set(it.sid, []).get(it.sid)!).push(it.e);
  return out;
}

/** Renumber: every section's rows get 1, 2, 3… in the order they show now (0.1 0.5 1 2 -> 1 2 3 4).
 *  A glyph or word in two sections gets one number per section ("3; 12"), or one when they match. */
export function renumber(t: T.Typing, ws: Words, order: string[]): { typing: T.Typing; words: Words } {
  const per = new Map<string, Map<string, number>>();     // 'glyph:md_x' / 'word:少息' -> section id -> n
  for (const [sid, list] of sectionOrder(t, ws, order)) {
    list.forEach((e, i) => {
      const k = `${e.kind}:${e.key}`;
      (per.get(k) ?? per.set(k, new Map()).get(k)!).set(sid, i + 1);
    });
  }
  const text = (k: string, glossary: string) => {
    const m = per.get(k);
    if (!m) return null;
    const ns = sectionsOf(glossary).map((title) => m.get(idOf(title))).filter((n): n is number => n != null);
    return new Set(ns).size <= 1 ? String(ns[0] ?? '') : ns.join('; ');
  };
  const typing: T.Typing = {};
  for (const [g, s] of Object.entries(t)) {
    const v = text(`glyph:${g}`, s.glossary);
    typing[g] = v == null ? s : { ...s, glossary_order: v };
  }
  const words = ws.map((w) => { const v = text(`word:${w.word}`, w.glossary); return v == null ? w : { ...w, glossary_order: v }; });
  return { typing, words };
}
