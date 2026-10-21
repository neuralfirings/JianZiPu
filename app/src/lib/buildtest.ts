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
