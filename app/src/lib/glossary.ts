// The glossary on the font page (site/glossary.json, edited in Glyphs > Glossary): its sections,
// each with its rows in page order. A row is one glyph, or a word written together (少息: md_shao +
// md_xi); its ASCII, Chinese and pinyin come from the glyphs' spellings, its meaning is its own.
// The server makes the page's tables from these (builder jzpbuild/glossary.py).

export type GlyphRow = { glyph: string; meaning?: string };
export type WordRow = { word: string; glyphs: string[]; meaning?: string };
export type GRow = GlyphRow | WordRow;
/** section id -> its rows, in page order */
export type GlossaryRows = Record<string, GRow[]>;
/** 'usage': an example word per row (no words); 'vertical': each typed on its own; 'hidden': not on the page. */
export type SectionKind = 'usage' | 'vertical' | 'hidden';
export type Section = { id: string; title: string; kind: SectionKind };

export const isWord = (r: GRow): r is WordRow => 'word' in r;
/** A row's identity within its section: g:lg_gou, w:少息 */
export const rowKey = (r: GRow) => (isWord(r) ? `w:${r.word}` : `g:${r.glyph}`);
export const rowName = (r: GRow) => (isWord(r) ? r.word : r.glyph);
export const glyphsOfRow = (r: GRow) => (isWord(r) ? r.glyphs : [r.glyph]);

/** A row as the file keeps it (trimmed, no empty meaning), or null when it isn't one. */
export function cleanRow(x: unknown): GRow | null {
  if (!x || typeof x !== 'object') return null;
  const o = x as Record<string, unknown>;
  const meaning = String(o.meaning ?? '').trim();
  const m = meaning ? { meaning } : {};
  if (o.word != null) {
    const word = String(o.word).trim();
    const gs = Array.isArray(o.glyphs) ? o.glyphs.map((g) => String(g).trim()).filter(Boolean) : [];
    return word && gs.length ? { word, glyphs: gs, ...m } : null;
  }
  const glyph = String(o.glyph ?? '').trim();
  return glyph ? { glyph, ...m } : null;
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
  return [
    added.length ? `added ${added.join(', ')}` : '', removed.length ? `removed ${removed.join(', ')}` : '',
    moved.length ? `moved ${moved.join(', ')}` : '', meaning.length ? `meaning of ${meaning.join(', ')}` : ''
  ].filter(Boolean);
}
