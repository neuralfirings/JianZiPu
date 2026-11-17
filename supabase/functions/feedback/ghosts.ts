// The font page's coming characters ("ghost" rows), as the feedback function's GET gives them: only
// what the page shows, from public.upcoming (supabase/009). Pure functions, tested in feedback_test.ts.

/** A row of public.upcoming, as the GET reads it. */
export type UpcomingRow = {
  id: string; zh: string; pinyin: string | null; ascii: string | null; meaning: string | null;
  section: string | null; after: string | null; stage: 'planned' | 'draft' | 'test' | 'released';
  note: string | null; drawing: string | null; version: string | null; glyphs: string[] | null; updated_at: string;
};

/** One ghost on the page. `testFont` is the release candidate's font (stage test). */
export type Ghost = {
  id: string; zh: string; pinyin: string | null; ascii: string | null; meaning: string | null;
  section: string; after: string | null; stage: 'planned' | 'draft' | 'test';
  note: string | null; drawing: string | null; release: string | null; testFont: string | null; glyphs: string[];
};

/** What the GET asks Supabase for: the rows the page shows, oldest first, so a section's ghosts keep
 *  the order they were taken on. Never feedback_id or change_request_id. */
export const GHOSTS_QUERY = 'select=id,zh,pinyin,ascii,meaning,section,after,stage,note,drawing,version,glyphs,updated_at'
  + '&stage=in.(planned,draft,test)&section=not.is.null&order=created_at.asc,id.asc';

/** The repository whose releases hold the test fonts. */
export const REPO = 'neuralfirings/JianZiPu';

/** A row as the page gets it: the drawing as its public address (the time it changed added, so a
 *  redraw shows at once), the release it's in (3.400 of 3.400-rc.2) and that candidate's font. */
export function ghostOf(r: UpcomingRow, supabaseUrl: string): Ghost | null {
  if (!r.section || r.stage === 'released' || !r.zh) return null;
  const drawing = r.drawing && r.stage !== 'planned'
    ? `${supabaseUrl}/storage/v1/object/public/upcoming/${encodeURIComponent(r.drawing)}?v=${encodeURIComponent(r.updated_at)}` : null;
  const test = r.stage === 'test' && r.version ? r.version : null;
  return {
    id: r.id, zh: r.zh, pinyin: r.pinyin, ascii: r.ascii, meaning: r.meaning, section: r.section, after: r.after || null,
    stage: r.stage, note: r.note, drawing, glyphs: r.glyphs ?? [],
    release: test ? test.replace(/-rc\.\d+$/, '') : null,
    testFont: test ? `https://github.com/${REPO}/releases/download/v${test}/JianZiPu.ttf` : null,
  };
}
