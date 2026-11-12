// The glossary on the font page (site/glossary.json, edited in Glyphs > Glossary): its sections,
// each with its rows in page order. A row is one glyph, or a word written together (少息: md_shao +
// md_xi); its ASCII, Chinese and pinyin come from the glyphs' spellings, its meaning is its own.
// The server makes the page's tables from these (builder jzpbuild/glossary.py).
import * as T from './typing';

/** `usage`: the row's own example word as [ASCII, 中文] templates ({} = the glyph's spelling), in a usage section. */
/** `typed`: what was typed to add or edit the row (k, 勾, :shaoxi), shown again to edit it. */
export type GlyphRow = { glyph: string; meaning?: string; usage?: [string, string]; typed?: string };
export type WordRow = { word: string; glyphs: string[]; meaning?: string; typed?: string };
export type GRow = GlyphRow | WordRow;
/** section id -> its rows, in page order */
export type GlossaryRows = Record<string, GRow[]>;
/** 'usage': an example word per row (no words); 'vertical': each typed on its own; 'hidden': not on the page. */
export type SectionKind = 'usage' | 'vertical' | 'hidden';
/** `usage`: a usage section's example for rows without their own, as [ASCII, 中文] templates. */
export type Section = { id: string; title: string; kind: SectionKind; usage?: [string, string] | null };

export const isWord = (r: GRow): r is WordRow => 'word' in r;
/** A row's identity within its section: g:lg_gou, w:少息 */
export const rowKey = (r: GRow) => (isWord(r) ? `w:${r.word}` : `g:${r.glyph}`);
export const rowName = (r: GRow) => (isWord(r) ? r.word : r.glyph);
export const glyphsOfRow = (r: GRow) => (isWord(r) ? r.glyphs : [r.glyph]);

/** A row as the file keeps it (trimmed, no empty meaning), or null when it isn't one. */
export function cleanRow(x: unknown): GRow | null {
  if (!x || typeof x !== 'object') return null;
  const o = x as Record<string, unknown>;
  const meaning = String(o.meaning ?? '').trim(), typed = String(o.typed ?? '').trim();
  const m = { ...(meaning ? { meaning } : {}), ...(typed ? { typed } : {}) };
  if (o.word != null) {
    const word = String(o.word).trim();
    const gs = Array.isArray(o.glyphs) ? o.glyphs.map((g) => String(g).trim()).filter(Boolean) : [];
    return word && gs.length ? { word, glyphs: gs, ...m } : null;
  }
  const glyph = String(o.glyph ?? '').trim();
  const u = Array.isArray(o.usage) && o.usage.length === 2 ? (o.usage.map((x) => String(x ?? '').trim()) as [string, string]) : null;
  return glyph ? { glyph, ...m, ...(u && (u[0] || u[1]) ? { usage: u } : {}) } : null;
}

/** Rows by section from anywhere (a draft, the server), cleaned; undefined when it isn't that. */
export function cleanRows(x: unknown): GlossaryRows | undefined {
  if (!x || typeof x !== 'object' || Array.isArray(x)) return undefined;
  const out: GlossaryRows = {};
  for (const [sid, rows] of Object.entries(x as Record<string, unknown>)) {
    if (Array.isArray(rows)) out[sid] = rows.map(cleanRow).filter((r): r is GRow => !!r);
  }
  return out;
}

const json = (rows: GRow[] | undefined) => JSON.stringify((rows ?? []).map(cleanRow));

/** The sections whose rows differ between two versions (added, removed, moved or edited). */
export function changedSections(a: GlossaryRows, b: GlossaryRows): string[] {
  return [...new Set([...Object.keys(a), ...Object.keys(b)])].filter((s) => json(a[s]) !== json(b[s])).sort(byId);
}

/** Section ids in page order: 1a, 1b, …, 3x, 4, 99 (numbers by value, then the letters). */
export function byId(a: string, b: string): number {
  const p = (s: string) => { const m = /^(\d+)(.*)$/.exec(s); return m ? [Number(m[1]), m[2]] as const : [Infinity, s] as const; };
  const [an, ar] = p(a), [bn, br] = p(b);
  return an - bn || (ar < br ? -1 : ar > br ? 1 : 0);
}

export type Use = { sid: string; title: string; word?: string; index: number };

/** glyph -> every place it's in the glossary: its own row in a section, or a word's. */
export function usesOf(rows: GlossaryRows, sections: Section[]): Record<string, Use[]> {
  const out: Record<string, Use[]> = {};
  const title = new Map(sections.map((s) => [s.id, s.title]));
  const order = [...new Set([...sections.map((s) => s.id), ...Object.keys(rows)])];
  for (const sid of order) {
    (rows[sid] ?? []).forEach((r, index) => {
      for (const g of new Set(glyphsOfRow(r))) {
        (out[g] ??= []).push({ sid, title: title.get(sid) ?? sid, index, ...(isWord(r) ? { word: r.word } : {}) });
      }
    });
  }
  return out;
}

/** "1c", "3e in 少息, 大息", "99 (hidden)": a glyph's uses, a section at a time. */
export function describeUses(uses: Use[], sections: Section[]): string[] {
  const hidden = new Set(sections.filter((s) => s.kind === 'hidden').map((s) => s.id));
  const by = new Map<string, Use[]>();
  for (const u of uses) (by.get(u.sid) ?? by.set(u.sid, []).get(u.sid)!).push(u);
  return [...by].map(([sid, us]) => {
    const own = us.some((u) => !u.word), words = us.filter((u) => u.word).map((u) => u.word!);
    const parts = [own ? 'own row' : '', words.length ? `in ${words.join(', ')}` : ''].filter(Boolean).join(', ');
    return `${sid}${hidden.has(sid) ? ' (hidden)' : ''}: ${parts}`;
  });
}

/** The rows with every use of glyph `from` renamed to `to` (Rename…); `changed`: the sections touched. */
export function renameInRows(rows: GlossaryRows, from: string, to: string): { rows: GlossaryRows; changed: string[] } {
  const changed: string[] = [];
  const out: GlossaryRows = {};
  for (const [sid, list] of Object.entries(rows)) {
    let hit = false;
    out[sid] = list.map((r) => {
      if (!glyphsOfRow(r).includes(from)) return r;
      hit = true;
      return isWord(r) ? { ...r, glyphs: r.glyphs.map((g) => (g === from ? to : g)) } : { ...r, glyph: to };
    });
    if (hit) changed.push(sid);
  }
  return { rows: out, changed };
}

/** Move the row at `from` to `to` (in the same section or another); `to.index` counts the target's
 *  rows before the move, so dropping on the gap after the row itself leaves it where it was. */
export function moveRow(rows: GlossaryRows, from: { sid: string; index: number }, to: { sid: string; index: number }): GlossaryRows {
  const out = { ...rows, [from.sid]: [...(rows[from.sid] ?? [])] };
  const [r] = out[from.sid].splice(from.index, 1);
  if (!r) return rows;
  let i = to.index;
  if (to.sid === from.sid && i > from.index) i--;
  out[to.sid] = [...(to.sid === from.sid ? out[from.sid] : rows[to.sid] ?? [])];
  out[to.sid].splice(Math.max(0, Math.min(i, out[to.sid].length)), 0, r);
  return out;
}

/** Why `r` can't go into section `sec` (null: it can). */
export function refuse(rows: GlossaryRows, r: GRow, sec: Section, except?: number): string | null {
  if (isWord(r) && sec.kind === 'usage') return `${sec.title} shows each glyph in an example word, so a word can't go there: put it in a vertical section.`;
  const k = rowKey(r);
  if ((rows[sec.id] ?? []).some((x, i) => i !== except && rowKey(x) === k)) return `${rowName(r)} is in ${sec.title} already.`;
  return null;
}

/** What changed in a section between two versions, a line per kind: "added 少息, lg_foo",
 *  "removed md_x", "moved lg_gou", "meaning of lg_gou". */
export function sectionSummary(base: GRow[], theirs: GRow[]): string[] {
  const bk = base.map(rowKey), tk = theirs.map(rowKey);
  const added = theirs.filter((r) => !bk.includes(rowKey(r))).map(rowName);
  const removed = base.filter((r) => !tk.includes(rowKey(r))).map(rowName);
  // moved: out of order among the rows both have
  const common = tk.filter((k) => bk.includes(k)), was = bk.filter((k) => tk.includes(k));
  const moved = common.filter((k, i) => k !== was[i]).map((k) => rowName(theirs[tk.indexOf(k)]));
  const meaning = theirs.filter((r) => { const b = base[bk.indexOf(rowKey(r))]; return b && (b.meaning ?? '') !== (r.meaning ?? ''); }).map(rowName);
  const usage = theirs.filter((r) => { const b = base[bk.indexOf(rowKey(r))]; return b && !isWord(r) && JSON.stringify((b as GlyphRow).usage ?? null) !== JSON.stringify(r.usage ?? null); }).map(rowName);
  return [
    added.length ? `added ${added.join(', ')}` : '', removed.length ? `removed ${removed.join(', ')}` : '',
    moved.length ? `moved ${moved.join(', ')}` : '', meaning.length ? `meaning of ${meaning.join(', ')}` : '',
    usage.length ? `example of ${usage.join(', ')}` : ''
  ].filter(Boolean);
}

// ---------------------------------------------------------------- a row's example word (usage sections)

const esc = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const unesc = (t: string) => t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
/** A template as plain text, the glyph's spelling in place of {} (what typing it means). */
export const exampleText = (t: string, spelling: string) => unesc(t.replace(/<\/?r>/g, '').split('{}').join(spelling));
/** A template as HTML, the glyph's spelling and any <r>…</r> marked: `<span class="r">`. */
export const exampleHtml = (t: string, spelling: string) =>
  t.split('{}').map((p) => p.replace(/<r>/g, '<span class="r">').replace(/<\/r>/g, '</span>')).join(`<span class="r">${esc(spelling)}</span>`);
/** The glyph's main spelling in each language, as the page fills the example with. */
export function mainSpellings(t: T.Typing, g: string): [string, string] {
  const s = T.get(t, g);
  return [s.latin || s.latin_alt || s.common || T.shown(t, g, 'latin').value, s.simplified || s.traditional || T.shown(t, g, 'simplified').value];
}

const CN = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二', '十三'];
// marks that type the same in either language (the font reads them: , separates, | divides a chord, : starts vertical text)
const PUNCT: [string, string][] = [[',', '，'], ['|', '｜'], [':', '：']];
const hasHan = (t: string) => /[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]/.test(t);

/** How glyph `g` is written in a language: its spellings there, main first (a position decimal by its pattern). */
function spellingsIn(t: T.Typing, g: string, zh: boolean): string[] {
  const m = /^md_(\d+)\.(\d)$/.exec(g);
  if (m) return zh ? [`${CN[+m[1]]}点${CN[+m[2]]}`, `${CN[+m[1]]}徽${CN[+m[2]]}`] : [`${m[1]}.${m[2]}`];
  const s = T.get(t, g);
  const own = zh ? [s.simplified, s.traditional] : [s.latin, s.latin_alt, s.common];
  const shown = zh ? [T.shown(t, g, 'simplified').value, T.shown(t, g, 'traditional').value] : [T.shown(t, g, 'latin').value, T.shown(t, g, 'latin_alt').value];
  return [...new Set([...own, ...shown].filter(Boolean))];
}
const punct = (text: string, zh: boolean) => [...text].map((c) => PUNCT.find((p) => p[zh ? 1 : 0] === c)?.[zh ? 0 : 1] ?? c).join('');

/** A row's example from what someone typed (`text`, in either language) and how the font typed it: the
 *  [ASCII, 中文] templates, the row's glyph as {}, the other language made from the glyphs' spellings.
 *  `other` is null where a glyph has no spelling in that language (`missing` names it). */
export function usageFrom(text: string, typed: { glyphs: string[]; texts: string[]; clusters?: number[] }, glyph: string, t: T.Typing):
  { error: string } | { source: string; other: string | null; zh: boolean; missing: string[] } {
  const zh = hasHan(text);
  if (!typed.glyphs.includes(glyph)) return { error: `${text} doesn't type ${glyph}${mainSpellings(t, glyph)[1] ? ` (${mainSpellings(t, glyph)[1]})` : ''}: an example has the row's glyph in it.` };
  // the clusters: the glyphs one stretch of the text became
  const groups: { glyphs: string[]; text: string }[] = [];
  typed.glyphs.forEach((g, i) => {
    const c = typed.clusters?.[i] ?? i;
    const last = groups[groups.length - 1];
    if (last && (typed.clusters?.[i - 1] ?? i - 1) === c) last.glyphs.push(g);
    else groups.push({ glyphs: [g], text: typed.texts[i] ?? '' });
  });
  let source = '', other = '';
  const missing: string[] = [];
  for (const gr of groups) {
    const gs = gr.glyphs.filter((g) => g !== 'blank_colon' && g !== 'blank_bar');
    // the glyph's spelling the text starts with, and what's left (a comma the font swallowed: 7, → md_7)
    const spelled = gs.length === 1 ? spellingsIn(t, gs[0], zh).find((sp) => gr.text.startsWith(sp)) ?? '' : '';
    const rest = spelled ? gr.text.slice(spelled.length) : gs.length ? '' : gr.text;
    if (gs.includes(glyph)) { source += '{}' + esc(rest); other += '{}' + esc(punct(rest, zh)); continue; }
    source += esc(gr.text);
    if (!gs.length) { other += esc(punct(gr.text, zh)); continue; }
    const made = gs.map((g) => spellingsIn(t, g, !zh)[0]);
    if (made.some((x) => !x)) { missing.push(gr.text); continue; }
    other += esc(made.join('') + punct(rest, zh));
  }
  return { source, other: missing.length ? null : other, zh, missing };
}
