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
