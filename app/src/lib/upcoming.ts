// Coming characters: the font page's "ghost" rows (supabase/009_upcoming.sql, one row each in the
// `upcoming` table). A visitor's request set to wip makes one (Planned); a tester tags each new glyph
// of a Change Request with the one it draws (Send Change Request, kept in manifest.upcoming);
// Review's Publish draft to glossary writes the request's drawing and words into it (Draft);
// building a release candidate moves the drafts it holds to test (In release 3.400); publishing the
// release moves them to released, and the page shows the real row from then on.
// Testers read the public list (the feedback function's GET); the local Builder, signed in as an
// admin, reads and writes the table itself.
import type { SupabaseClient } from '@supabase/supabase-js';
import type { WordPiece } from './api';
import type { Bundle, SvgMap } from './bundle';
import { rowExample, type GRow } from './glossary';
import { parseSvg } from './svg';
import type { Item } from './merge';
import type * as T from './typing';

export type Stage = 'planned' | 'draft' | 'test' | 'released';
/** One ghost as the font page gets it (the feedback function's GET). */
export type Ghost = {
  id: string; zh: string; pinyin: string | null; ascii: string | null; meaning: string | null;
  section: string; after: string | null; stage: Exclude<Stage, 'released'>;
  note: string | null; drawing: string | null; release: string | null; testFont: string | null; glyphs: string[];
  example: [string, string] | null;
};
/** A row of the upcoming table, as an admin reads it. */
export type UpcomingRow = {
  id: string; zh: string; pinyin: string | null; ascii: string | null; meaning: string | null;
  section: string | null; after: string | null; stage: Stage; note: string | null; drawing: string | null;
  version: string | null; glyphs: string[]; feedback_id: string | null; change_request_id: string | null; updated_at: string;
  example?: string[] | null;
};

export const TABLE = 'upcoming';
export const BUCKET = 'upcoming';

/** The feedback function, whose GET lists the ghosts. */
export const functionUrl = (supabaseUrl: string) => `${supabaseUrl.replace(/\/+$/, '')}/functions/v1/feedback`;

/** The public list (what the font page shows); [] when it can't be read. */
export async function publicGhosts(supabaseUrl: string, f: typeof fetch = fetch): Promise<Ghost[]> {
  try {
    const r = await f(functionUrl(supabaseUrl));
    if (!r.ok) return [];
    const j = await r.json() as { ghosts?: Ghost[] };
    return Array.isArray(j.ghosts) ? j.ghosts : [];
  } catch {
    return [];
  }
}

/** The badge a ghost shows on the page. */
export function stageLabel(g: { stage: Stage; release?: string | null; version?: string | null }): string {
  const rel = g.release ?? g.version?.replace(/-rc\.\d+$/, '') ?? '';
  return g.stage === 'planned' ? 'Planned' : g.stage === 'draft' ? 'Draft design' : g.stage === 'test' ? `In release ${rel}`.trim() : 'Released';
}

/** The glyphs a set of changes adds. */
export const newGlyphs = (items: Item[]): string[] => items.filter((i) => i.kind === 'glyph' && i.status === 'added').map((i) => i.key);

const plain = (s: string | null | undefined) => (s ?? '').normalize('NFD').replace(/[̀-ͯ\s\d·]/g, '').toLowerCase();
const chars = (zh: string) => zh.split('·').map((x) => x.trim()).filter(Boolean);

/** The coming character a new glyph most likely draws: one whose 中文 is its simplified or traditional
 *  spelling, else one with the same pinyin (tones, numbers and spaces aside). */
export function suggestGhost(sp: Partial<T.Spelling> | undefined, ghosts: Pick<Ghost, 'id' | 'zh' | 'pinyin'>[]): string | null {
  if (!sp) return null;
  const zh = [sp.simplified, sp.traditional].filter(Boolean) as string[];
  const byZh = ghosts.find((g) => chars(g.zh).some((c) => zh.includes(c)));
  if (byZh) return byZh.id;
  const py = plain(sp.pinyin);
  return (py && ghosts.find((g) => plain(g.pinyin) === py)?.id) || null;
}

/** What Publish draft to glossary writes for one new glyph: its row on the page, from the request. */
export type DraftRow = {
  glyph: string; ghost: string | null;
  zh: string; pinyin: string | null; ascii: string | null; meaning: string | null; section: string; after: string | null;
  /** The row's own example, [中文, ASCII] (引上九, yin3shang9): the page shows it typed, and its drawing is
   *  the whole word; null: the drawing is the glyph alone. */
  example: [string, string] | null;
};

/** A glossary row's 中文, as the page's first column shows it (simplified, then traditional). */
export function zhOf(row: GRow, typing: T.Typing): string {
  if ('word' in row) return row.word;
  const s = typing[row.glyph];
  return s ? [...new Set([s.simplified, s.traditional].filter(Boolean))].join(' · ') : row.glyph;
}

/** A Change Request's new glyphs that have a row in its glossary, as drafts for the page, each with
 *  the ghost it's tagged with (`tags`: glyph → ghost id; none: a new ghost). New glyphs without a
 *  glossary row can't be placed on the page, so they're left out (`unplaced` lists them). */
export function draftRows(b: Bundle, tags: Record<string, string | null | undefined>): { rows: DraftRow[]; unplaced: string[] } {
  const rows: DraftRow[] = [], unplaced: string[] = [];
  for (const glyph of b.manifest.svgs.added) {
    let found: { section: string; i: number; rows: GRow[] } | null = null;
    for (const [section, list] of Object.entries(b.glossary ?? {})) {
      const i = list.findIndex((r) => 'glyph' in r && r.glyph === glyph);
      if (i >= 0) { found = { section, i, rows: list }; break; }
    }
    if (!found) { unplaced.push(glyph); continue; }
    const sp = b.typing[glyph], row = found.rows[found.i];
    const before = found.rows[found.i - 1];
    rows.push({
      glyph, ghost: tags[glyph] || null,
      zh: zhOf(row, b.typing), pinyin: sp?.pinyin || null, ascii: sp?.latin || null,
      meaning: row.meaning || null, section: found.section,
      after: before ? zhOf(before, b.typing).split(' · ')[0] : null,
      example: rowExample(row, b.typing)
    });
  }
  return { rows, unplaced };
}

/** Admin: every row of the table, oldest first. */
export async function allUpcoming(c: SupabaseClient): Promise<UpcomingRow[]> {
  const { data, error } = await c.from(TABLE).select('*').order('created_at', { ascending: true });
  if (error) throw new Error(/relation .*upcoming.* does not exist|schema cache/.test(error.message) ? 'Supabase has no upcoming table yet: run supabase/009_upcoming.sql.' : error.message);
  return (data ?? []) as UpcomingRow[];
}

/** An example word as one standalone SVG, as Glyphs › Glossary draws it (GlossaryExample.svelte): each
 *  glyph at its place in the word, the row's glyphs (`mark`) in the font page's red, the rest in ink;
 *  the control glyphs (a vertical word's colon) left out. Null when nothing in it has a drawing. */
export function exampleSvg(pieces: WordPiece[], svgs: SvgMap, mark: string[], control: string[] = []): string | null {
  const els = pieces.flatMap((p) => p.elements).filter((e) => e.glyph && !control.includes(e.glyph) && parseSvg(svgs[e.glyph]));
  if (!els.length) return null;
  const x0 = Math.min(...els.map((e) => e.x)), x1 = Math.max(...els.map((e) => e.x + e.size[0]));
  const y0 = Math.min(...els.map((e) => e.y)), y1 = Math.max(...els.map((e) => e.y + e.size[1]));
  const pad = 0.1 * Math.max(x1 - x0, y1 - y0);
  const r = (n: number) => Math.round(n * 100) / 100;
  const box = [x0 - pad, -(y1 + pad), x1 - x0 + 2 * pad, y1 - y0 + 2 * pad].map(r);
  const parts = els.map((e) => {
    const g = parseSvg(svgs[e.glyph])!;
    const color = mark.includes(e.glyph) ? '#a3352b' : '#2b2724';   // site/index.html's --accent and --ink
    return `<svg x="${r(e.x)}" y="${r(-(e.y + e.size[1]))}" width="${r(e.size[0])}" height="${r(e.size[1])}" viewBox="${g.viewBox}" color="${color}" overflow="visible">${g.inner}</svg>`;
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box.join(' ')}" width="${box[2]}" height="${box[3]}" overflow="visible">${parts.join('')}</svg>\n`;
}

/** Admin: put a Change Request's drawings on the page as drafts. Rows tagged with the same ghost
 *  (two variants of one character) share it: the first glyph's drawing shows. `pictures`: a whole
 *  example word's drawing for a row with an example (exampleSvg), by glyph; else the glyph alone.
 *  Returns the ghost ids. */
export async function publishDrafts(c: SupabaseClient, requestId: string, rows: DraftRow[], svgs: SvgMap, pictures: Record<string, string> = {}): Promise<string[]> {
  const out: string[] = [];
  const byGhost = new Map<string, DraftRow[]>(), fresh: DraftRow[] = [];
  for (const r of rows) (r.ghost ? byGhost.set(r.ghost, [...(byGhost.get(r.ghost) ?? []), r]) : fresh.push(r));
  for (const r of fresh) {
    const { data, error } = await c.from(TABLE).insert({ zh: r.zh, stage: 'planned' }).select('id').single();
    if (error) throw new Error(error.message);
    byGhost.set((data as { id: string }).id, [r]);
  }
  for (const [id, group] of byGhost) {
    const first = group[0];
    const picture = first.example ? pictures[first.glyph] : undefined;
    const svg = picture ?? svgs[first.glyph];
    if (!svg) throw new Error(`The request has no drawing for ${first.glyph}.`);
    const file = `${id}.svg`;
    const up = await c.storage.from(BUCKET).upload(file, new Blob([svg], { type: 'image/svg+xml' }), { upsert: true, contentType: 'image/svg+xml' });
    if (up.error) throw new Error(`Uploading ${file}: ${up.error.message}`);
    const { error } = await c.from(TABLE).update({
      zh: first.zh, pinyin: first.pinyin, ascii: first.ascii, meaning: first.meaning, section: first.section, after: first.after,
      stage: 'draft', drawing: file, version: null, glyphs: group.map((r) => r.glyph), change_request_id: requestId,
      example: picture ? first.example : null
    }).eq('id', id);
    if (error) throw new Error(error.message);
    out.push(id);
  }
  return out;
}

/** The rows a font with these glyphs holds whole: every glyph that draws them is in it. */
export const heldBy = (rows: UpcomingRow[], glyphs: Set<string>, stages: Stage[]) =>
  rows.filter((r) => stages.includes(r.stage) && r.glyphs.length && r.glyphs.every((g) => glyphs.has(g)));

/** Admin: after a release candidate (tag v3.400-rc.1), its drafts are in the test font. */
export async function toCandidate(c: SupabaseClient, glyphs: Set<string>, candidate: string): Promise<UpcomingRow[]> {
  const rows = heldBy(await allUpcoming(c), glyphs, ['draft', 'test']);
  if (rows.length) {
    const { error } = await c.from(TABLE).update({ stage: 'test', version: candidate }).in('id', rows.map((r) => r.id));
    if (error) throw new Error(error.message);
  }
  return rows;
}

/** Admin: once the release is out, its coming characters are ordinary rows: off the list. */
export async function toReleased(c: SupabaseClient, glyphs: Set<string>, version: string): Promise<UpcomingRow[]> {
  const rows = heldBy(await allUpcoming(c), glyphs, ['test']).filter((r) => (r.version ?? '').replace(/-rc\.\d+$/, '') === version);
  if (rows.length) {
    const { error } = await c.from(TABLE).update({ stage: 'released', version }).in('id', rows.map((r) => r.id));
    if (error) throw new Error(error.message);
  }
  return rows;
}
