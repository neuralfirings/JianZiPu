// Renaming a glyph: its name is its ID, so the new name goes everywhere the old one is used. That is
// its drawing (the file's name), its spellings row, other glyphs' Vertical form links, and design.json:
// the areas that hold it and any spacing rule that names it. The state applies it as one undo step
// (app.renameGlyph).
import type { Design } from './api';
import * as T from './typing';

/** The names the server takes for a glyph file (webserver.SVG_NAME, and no trailing dot). */
export const GLYPH_NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;

/** Why `to` can't be the new name of `from`, or null. `existing`: every glyph name there is.
 *  Names that differ only in capitals clash too (a Mac's disk keeps one file for both). */
export function renameProblem(from: string, to: string, existing: Iterable<string>): string | null {
  const n = to.trim();
  if (!n) return 'Type the new name, e.g. md_tuichu.';
  if (n === from) return 'That is its name already.';
  if (!GLYPH_NAME.test(n) || n.endsWith('.')) return 'Letters, digits, _ - and . only, starting with a letter or digit.';
  for (const e of existing)
    if (e !== from && e.toLowerCase() === n.toLowerCase()) return `${e} already exists.`;
  return null;
}

/** What renaming changes, in words for the confirmation. */
export type RenameImpact = { spellings: boolean; areas: string[]; rules: number; vertical: string[] };

/** The design and spellings with `from` renamed to `to`, and what changed. In the design, every
 *  value that is exactly the glyph's name is a use of it (area members, glyph conditions in spacing
 *  rules); names of areas, word types and elements never look like glyph names. */
export function renameIn(design: Design, typing: T.Typing, from: string, to: string) {
  let rules = 0;
  const areas: string[] = [];
  const walk = (v: unknown, inArea: string | null): unknown => {
    if (typeof v === 'string') {
      if (v !== from) return v;
      if (inArea) areas.push(inArea); else rules++;
      return to;
    }
    if (Array.isArray(v)) return v.map((x) => walk(x, inArea));
    if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, walk(x, inArea)]));
    return v;
  };
  const { areas: designAreas, ...rest } = design;
  const next = {
    ...(walk(rest, null) as Omit<Design, 'areas'>),
    areas: Object.fromEntries(Object.entries(designAreas).map(([k, a]) => [k, walk(a, k)]))
  } as Design;
  const t: T.Typing = {};
  const vertical: string[] = [];
  for (const [g, sp] of Object.entries(typing)) {
    const s = { ...sp };
    if (s.vert_variant === from) { s.vert_variant = to; vertical.push(g === from ? to : g); }
    t[g === from ? to : g] = s;
  }
  const impact: RenameImpact = { spellings: from in typing, areas: [...new Set(areas)], rules, vertical };
  return { design: next, typing: t, impact };
}
