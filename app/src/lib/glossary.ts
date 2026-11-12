// The glossary on the font page (site/glossary.json, edited in Glyphs > Glossary): its sections,
// each with its rows in page order. A row is one glyph, or a word written together (少息: md_shao +
// md_xi); its ASCII, Chinese and pinyin come from the glyphs' spellings, its meaning is its own.
// The server makes the page's tables from these (builder jzpbuild/glossary.py).
import * as T from './typing';

/** `usage`: the row's own example word as [ASCII, 中文] templates ({} = the glyph's spelling), in a usage section. */
/** `typed`: what was typed to add or edit the row (k, 勾, :shaoxi), shown again to edit it. */
export type GlyphRow = { glyph: string; meaning?: string; usage?: [string, string]; typed?: string };
export type WordRow = { word: string; glyphs: string[]; meaning?: string; typed?: string; usage?: [string, string] };
export type GRow = GlyphRow | WordRow;
/** section id -> its rows, in page order */
export type GlossaryRows = Record<string, GRow[]>;
/** 'usage': an example word per row; 'vertical': each typed on its own after a colon. */
export type SectionKind = 'usage' | 'vertical';
/** `usage`: a usage section's example for rows without their own, as [ASCII, 中文] templates; `hidden`:
 *  off the page, by its own switch or its section title's. */
export type Section = { id: string; title: string; kind: SectionKind; usage?: [string, string] | null; hidden?: boolean };

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
    return word && gs.length ? { word, glyphs: gs, ...m, ...usageOf(o) } : null;
  }
  const glyph = String(o.glyph ?? '').trim();
  return glyph ? { glyph, ...m, ...usageOf(o) } : null;
}

function usageOf(o: Record<string, unknown>): { usage?: [string, string] } {
  const u = Array.isArray(o.usage) && o.usage.length === 2 ? (o.usage.map((x) => String(x ?? '').trim()) as [string, string]) : null;
  return u && (u[0] || u[1]) ? { usage: u } : {};
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
  const hidden = new Set(sections.filter((s) => s.hidden).map((s) => s.id));
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
  const usage = theirs.filter((r) => { const b = base[bk.indexOf(rowKey(r))]; return b && JSON.stringify(b.usage ?? null) !== JSON.stringify(r.usage ?? null); }).map(rowName);
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
/** A template as HTML, the glyph's spelling and any <r>…</r> marked: `<span class="r">`. `mark` false
 *  (a vertical section's row, whole on its own): nothing marked. */
export const exampleHtml = (t: string, spelling: string, mark = true) => mark
  ? t.split('{}').map((p) => p.replace(/<r>/g, '<span class="r">').replace(/<\/r>/g, '</span>')).join(`<span class="r">${esc(spelling)}</span>`)
  : t.replace(/<\/?r>/g, '').split('{}').join(esc(spelling));
/** A vertical section's row as it is typed on its own, after a colon: [ASCII, 中文] templates. */
export function verticalTemplate(t: T.Typing, r: GRow): [string, string] {
  if (!isWord(r)) return [':{}', ':{}'];
  const sp = r.glyphs.map((g) => mainSpellings(t, g));
  return [':' + esc(sp.map((x) => x[0]).join('')), ':' + esc(sp.map((x) => x[1]).join(''))];
}
/** The glyph's main spelling in each language, as the page fills the example with. */
export function mainSpellings(t: T.Typing, g: string): [string, string] {
  const s = T.get(t, g);
  return [s.latin || s.latin_alt || s.common || T.shown(t, g, 'latin').value, s.simplified || s.traditional || T.shown(t, g, 'simplified').value];
}

const CN = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二', '十三'];
// marks written differently in the two languages (the font reads them: , separates, | divides a chord); the
// colon that starts vertical text is : in both (the page writes :大息), and ： typed in Chinese becomes it
const PUNCT: [string, string][] = [[',', '，'], ['|', '｜']];
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
const punct = (text: string, zh: boolean) => [...text].map((c) => (zh && c === '：' ? ':' : PUNCT.find((p) => p[zh ? 1 : 0] === c)?.[zh ? 0 : 1] ?? c)).join('');

/** A row's example from what someone typed (`text`, in either language) and how the font typed it: the
 *  [ASCII, 中文] templates, the other language made from the glyphs' spellings. `row`: a glyph (it becomes
 *  {} in the templates) or a word's glyphs (written out); a vertical form counts as its glyph (:san, 散).
 *  `other` is null where a glyph has no spelling in that language (`missing` names it). */
export function usageFrom(text: string, typed: { glyphs: string[]; texts: string[]; clusters?: number[] }, row: string | string[], t: T.Typing):
  { error: string } | { source: string; other: string | null; zh: boolean; missing: string[] } {
  const zh = hasHan(text);
  const horizontal = T.partners(t);
  const norm = (g: string) => horizontal[g] ?? g;
  const glyph = typeof row === 'string' ? row : null;
  const need = typeof row === 'string' ? [row] : row;
  const got = new Set(typed.glyphs.map(norm));
  const lacking = need.filter((g) => !got.has(g));
  if (lacking.length) {
    const name = (g: string) => g + (mainSpellings(t, g)[1] ? ` (${mainSpellings(t, g)[1]})` : '');
    return { error: `${text} doesn't type ${lacking.map(name).join(', ')}: an example has the row's glyph${need.length > 1 ? 's' : ''} in it.` };
  }
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
    // 十一 十二 十三 as a position: two numerals after a finger read as a decimal (名十二 is 名 10.2), 徽 keeps them whole
    const hui = (g: string) => (!zh && /^md_1[123]$/.test(g) && !/^[徽点點]/.test(punct(rest, zh)) ? '徽' : '');
    if (glyph && gs.map(norm).includes(glyph)) { source += '{}' + esc(rest); other += '{}' + hui(gs[0]) + esc(punct(rest, zh)); continue; }
    source += esc(gr.text);
    if (!gs.length) { other += esc(punct(gr.text, zh)); continue; }
    const made = gs.map((g) => spellingsIn(t, g, !zh)[0]);
    if (made.some((x) => !x)) { missing.push(gr.text); continue; }
    other += esc(made.join('') + (gs.length === 1 ? hui(gs[0]) : '') + punct(rest, zh));
  }
  // the colon that starts vertical text is written : in Chinese too, as the page has it (:大息)
  return { source: zh ? source.replace(/：/g, ':') : source, other: missing.length ? null : other, zh, missing };
}

// ---------------------------------------------------------------- section titles, subtitles, descriptions

/** A section title ("1: Left Hand"): its short name in the page's contents, a description, its subtitles in order. */
export type Group = { id: string; title: string; nav?: string; description?: string; hidden?: boolean; sections: string[] };
/** A subtitle's own settings (its rows are in GlossaryRows); `hidden`: switched off, not on the page. */
export type SectionMeta = { title: string; kind: SectionKind; usage?: [string, string] | null; description?: string; hidden?: boolean };
/** The glossary's titles and descriptions: site/glossary.json without the rows. */
export type GlossaryLayout = { groups: Group[]; sections: Record<string, SectionMeta> };
export const emptyLayout = (): GlossaryLayout => ({ groups: [], sections: {} });

/** The subtitles in page order (by their section titles, then any no title holds), as Section. */
export function sectionList(l: GlossaryLayout): (Section & { description?: string })[] {
  const ids = [...new Set([...l.groups.flatMap((g) => g.sections), ...Object.keys(l.sections)])].filter((id) => id in l.sections);
  const off = new Set(l.groups.filter((g) => g.hidden).flatMap((g) => g.sections));
  return ids.map((id) => ({ id, ...l.sections[id], usage: l.sections[id].usage ?? null, hidden: !!l.sections[id].hidden || off.has(id) }));
}

/** A layout from anywhere (a draft, the server), cleaned; undefined when it isn't one. */
export function cleanLayout(x: unknown): GlossaryLayout | undefined {
  if (!x || typeof x !== 'object') return undefined;
  const o = x as Record<string, unknown>;
  if (!Array.isArray(o.groups) || !o.sections || typeof o.sections !== 'object') return undefined;
  const str = (v: unknown) => (typeof v === 'string' ? v.trim() : '');
  const sections: Record<string, SectionMeta> = {};
  for (const [id, m] of Object.entries(o.sections as Record<string, Record<string, unknown>>)) {
    if (!m || typeof m !== 'object') continue;
    // the old kind 'hidden' is a vertical subtitle switched off
    const kind = (m.kind === 'usage' ? 'usage' : 'vertical') as SectionKind, hidden = !!m.hidden || m.kind === 'hidden';
    const u = Array.isArray(m.usage) && m.usage.length === 2 ? (m.usage.map((v) => String(v ?? '')) as [string, string]) : null;
    sections[id] = { title: str(m.title), kind, ...(hidden ? { hidden: true } : {}), ...(kind === 'usage' ? { usage: u ?? ['{}', '{}'] } : {}),
      ...(str(m.description) ? { description: str(m.description) } : {}) };
  }
  const groups = (o.groups as Record<string, unknown>[]).filter((g) => g && typeof g === 'object' && str(g.id)).map((g) => ({
    id: str(g.id), title: str(g.title), ...(str(g.nav) ? { nav: str(g.nav) } : {}), ...(str(g.description) ? { description: str(g.description) } : {}),
    ...(g.hidden ? { hidden: true } : {}),
    sections: Array.isArray(g.sections) ? (g.sections as unknown[]).map(String).filter((s) => s in sections) : []
  }));
  return { groups, sections };
}

/** An id for a new section title or subtitle: what its title starts with ("3f: Ornaments" -> 3f) when
 *  that's free, else a word of the title, else s1, s2… (builder ID_RE: letters, digits, - and _). */
export function newId(title: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  const lead = /^\s*([A-Za-z0-9][A-Za-z0-9_-]{0,31})\s*[:.]/.exec(title)?.[1];
  const word = title.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 24);
  for (const c of [lead, word]) if (c && /^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$/.test(c) && !used.has(c)) return c;
  let n = 1;
  while (used.has(`s${n}`)) n++;
  return `s${n}`;
}

// a little Markdown, the same as builder jzpbuild/glossary.py markdown(): the page's own <u>, <jzp>, <text>,
// <small> and <br>; any other HTML shows as text
const TAGS = /&lt;(\/?)(u|jzp|text|small|br ?\/?)&gt;/g;
const LINK = /\[([^\]]+)\]\(((?:https?:\/\/|\/|#)[^\s()<>"]*)\)/g;
function inline(s: string): string {
  const codes: string[] = [];
  s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  s = s.replace(TAGS, (_, slash, tag) => `<${slash}${tag}>`);
  s = s.replace(LINK, (_, t, href) => `<a href="${href}">${t}</a>`);
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])/g, '<em>$1</em>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<text>${codes[+i]}</text>`);
}
/** A description's HTML: paragraphs, line breaks, "- " lists, **bold**, *italic*, `typed examples`, [links](…). */
export function markdown(text: string): string {
  const out: string[] = [];
  for (const block of esc(text.trim()).split(/\n\s*\n/)) {
    const lines = block.trim().split('\n').map((l) => l.trim()).filter(Boolean);
    if (!lines.length) continue;
    if (lines.every((l) => l.startsWith('- '))) out.push('<ul>' + lines.map((l) => `<li>${inline(l.slice(2))}</li>`).join('') + '</ul>');
    else out.push('<p>' + lines.map(inline).join('<br />') + '</p>');
  }
  return out.join('\n');
}

/** What differs between two layouts: the subtitles whose title, kind, example or description changed
 *  (or that came or went), and 'titles' when the section titles changed (names, descriptions, order). */
export function changedLayout(a: GlossaryLayout, b: GlossaryLayout): string[] {
  const ids = [...new Set([...Object.keys(a.sections), ...Object.keys(b.sections)])]
    .filter((id) => JSON.stringify(a.sections[id] ?? null) !== JSON.stringify(b.sections[id] ?? null));
  return [...ids.sort(byId), ...(JSON.stringify(a.groups) !== JSON.stringify(b.groups) ? ['titles'] : [])];
}

/** What changed in a subtitle's settings, in words: "title: 1a: Fingers", "description", "example". */
export function metaSummary(a: SectionMeta | undefined, b: SectionMeta | undefined): string[] {
  if (!a && b) return [`new subtitle: ${b.title}`];
  if (a && !b) return [`subtitle deleted: ${a.title}`];
  if (!a || !b) return [];
  return [a.title !== b.title ? `title: ${b.title}` : '', a.kind !== b.kind ? `kind: ${b.kind}` : '',
    !!a.hidden !== !!b.hidden ? (b.hidden ? 'hidden' : 'shown') : '',
    (a.description ?? '') !== (b.description ?? '') ? 'description' : '', JSON.stringify(a.usage ?? null) !== JSON.stringify(b.usage ?? null) ? 'example' : ''].filter(Boolean);
}
/** What changed in the section titles, in words. */
export function titlesSummary(a: Group[], b: Group[]): string[] {
  const by = (gs: Group[]) => new Map(gs.map((g) => [g.id, g]));
  const ma = by(a), mb = by(b), out: string[] = [];
  for (const g of b) {
    const o = ma.get(g.id);
    if (!o) { out.push(`new: ${g.title}`); continue; }
    if (o.title !== g.title) out.push(`renamed: ${o.title} → ${g.title}`);
    if (!!o.hidden !== !!g.hidden) out.push(`${g.hidden ? 'hidden' : 'shown'}: ${g.title}`);
    if ((o.nav ?? '') !== (g.nav ?? '')) out.push(`short name of ${g.title}`);
    if ((o.description ?? '') !== (g.description ?? '')) out.push(`description of ${g.title}`);
    if (o.sections.join() !== g.sections.join()) out.push(`subtitles of ${g.title}`);
  }
  for (const g of a) if (!mb.has(g.id)) out.push(`deleted: ${g.title}`);
  if (!out.length && a.map((g) => g.id).join() !== b.map((g) => g.id).join()) out.push('order');
  return out;
}

/** An example with more in it than the row's glyph alone (s9{}k3, :{}5; not {} or :{}): the page marks the glyph in it. */
export const marksGlyph = (t: [string, string]) => t.some((x) => x.includes('{}') && x.replace(/<\/?r>/g, '').replace(/[:：]?\{\}/, '').trim() !== '');

/** A glyph with spellings that no glossary row shows (its vertical form counts as its partner):
 *  List view's "not in the glossary". `uses`: usesOf(); `any`: the glossary has sections at all. */
export function leftOut(t: T.Typing, g: string, uses: Record<string, Use[]>, any: boolean): boolean {
  return any && !uses[g] && !T.partners(t)[g] && !T.isEmpty(t[g])
    && (['latin', 'latin_alt', 'common', 'simplified', 'traditional'] as T.SpellField[]).some((f) => T.get(t, g)[f]);
}

/** What List view's search box finds in the Glossary column: where the glyph is ("1c: own row", the
 *  section's title, "in 少息"), or "not in the glossary". Lower-case. */
export function glossarySearchText(t: T.Typing, g: string, uses: Record<string, Use[]>, sections: Section[]): string {
  if (leftOut(t, g, uses, sections.length > 0)) return 'not in the glossary';
  const us = uses[g] ?? [];
  return [...describeUses(us, sections), ...us.map((u) => u.title)].join(' ').toLowerCase();
}
