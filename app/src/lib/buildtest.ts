// Build & test screen helpers: which build to show, which view, and where the old
// Tester links (/tester?build=…) land now that both screens are one.
import type { Build } from './api';

/** Words = one cell per word (live preview and/or the built font); Text = running text in one exact TTF. */
export type TestView = 'words' | 'text';

export const parseView = (v: string | null): TestView => (v === 'text' ? 'text' : 'words');

/** The build a link asks for, else the newest one (builds come newest first). */
export function pickBuild(builds: Build[], wanted: string | null): Build | null {
  return (wanted && builds.find((b) => b.id === wanted)) || builds[0] || null;
}

/** /tester?build=b3 → /test?view=text&build=b3 (the old Tester was the text view). */
export function testerRedirect(search: URLSearchParams): string {
  const q = new URLSearchParams({ view: 'text' });
  const b = search.get('build');
  if (b) q.set('build', b);
  return `/test?${q}`;
}

const EXCEPTION = /^(?:[A-Za-z_]\w*\.)*([A-Za-z_]\w*(?:Error|Exception)): ?(.*)$/;

/** The message to show above a failed build's log: the traceback's last exception line (module
 *  path dropped) with the indented issue lines under it, e.g. "ValidationError: input validation
 *  failed (1 issue(s)):\n  - components.csv: latin spelling 'k' is claimed by…". Not the first line
 *  that mentions an error: a traceback quotes source lines such as "raise ValidationError(". */
export function buildFailure(log: string[]): string {
  for (let i = log.length - 1; i >= 0; i--) {
    const m = log[i].match(EXCEPTION);
    if (!m) continue;
    const more = [];
    for (let j = i + 1; j < log.length && more.length < 6 && /^\s+\S/.test(log[j]); j++) more.push(log[j]);
    return [`${m[1]}: ${m[2]}`.trimEnd(), ...more].join('\n');
  }
  return log.find((l) => /too large/i.test(l))?.trim() || 'Build failed: see the log.';
}

/** Glyphs a word has that aren't drawn because no word type placed them, and why, for the warning
 *  beside it (Build & test, Test the design). A glyph in no area can't be placed at all; one in an
 *  area fits no word type with the glyphs around it. Empty: every glyph found a place. */
export function unplacedNote(pieces: { layout: string | null; glyphs: string[] }[], areas: Record<string, { label?: string; glyphs: string[] }>): string {
  const skip = new Set(['space', 'numbersign', 'advance']);
  const all = [...new Set(pieces.filter((p) => p.layout === null).flatMap((p) => p.glyphs).filter((g) => !skip.has(g)))];
  const typo = all.includes('.notdef'), lost = all.filter((g) => g !== '.notdef');
  if (!all.length) return '';
  const areaOf = (g: string) => Object.entries(areas).find(([, a]) => a.glyphs.includes(g));
  const none = lost.filter((g) => !areaOf(g)), some = lost.filter((g) => areaOf(g));
  const list = (gs: string[]) => gs.join(', ');
  return [
    ...(typo ? ["Part of it isn't a spelling of any glyph: check it in Glyphs › List view."] : []),
    ...(none.length ? [`${list(none)} ${none.length === 1 ? "isn't" : "aren't"} in an area, so no word type can place ${none.length === 1 ? 'it' : 'them'}. Add ${none.length === 1 ? 'it' : 'them'} to one in Layouts › Area Properties.`] : []),
    ...(some.length ? [`${some.map((g) => `${g} (${areaOf(g)![1].label || areaOf(g)![0]})`).join(', ')} ${some.length === 1 ? 'fits' : 'fit'} no word type with the glyphs around ${some.length === 1 ? 'it' : 'them'} here. Check the word types in Layouts › Structure.`] : [])
  ].join(' ');
}
