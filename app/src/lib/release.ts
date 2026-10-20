// The Release screen's helpers (routes/release): which Change Requests a release candidate takes,
// whether their kept changes are in the Builder yet, and the changelog entry they make.
import type { SvgMap } from './bundle';
import { diffBundle, type Current, type Item } from './merge';
import { keptIds, snapshot, type ChangeRequest } from './requests';

/** 3.100 → 3.200: the next minor release. */
export function nextVersion(v: string | null | undefined): string {
  const m = /^(\d+)\.(\d{3})$/.exec(v ?? '');
  if (!m) return '3.200';
  const minor = Math.floor(Number(m[2]) / 100) * 100 + 100;
  return minor >= 1000 ? `${Number(m[1]) + 1}.000` : `${m[1]}.${String(minor).padStart(3, '0')}`;
}

/** Requests with kept changes that belong in this release: reviewed ones not in a release yet,
 *  and ones already in this release's candidate. Oldest first, the order they're applied in. */
export function forRelease(reqs: ChangeRequest[], version: string): ChangeRequest[] {
  return reqs
    .filter((r) => keptIds(r).length && (r.status === 'in_review' || (r.status === 'in_candidate' && r.release === version)))
    .sort((a, b) => a.created_at.localeCompare(b.created_at));
}

/** A request's kept changes that the Builder doesn't have yet (empty: all in). */
export function missing(r: ChangeRequest, fontSvgs: SvgMap, cur: Current): Item[] {
  const { bundle } = snapshot(r.bundle, fontSvgs, keptIds(r));
  return diffBundle(bundle, cur);
}

/** The changelog entry (Keep a Changelog) for the requests in a release, with their credit. */
export function releaseNotes(reqs: ChangeRequest[]): string {
  if (!reqs.length) return '### Changed\n\n- ';
  const lines = reqs.map((r) => `- ${r.title.trim()}${r.credit.trim() ? ` (thanks to ${r.credit.trim()})` : ''}`);
  return `### Changed\n\n${lines.join('\n')}\n`;
}

/** The commit message for the design changes a candidate takes. */
export function commitMessage(version: string, reqs: ChangeRequest[]): string {
  const head = `${version}: changes from ${reqs.length} Change Request${reqs.length === 1 ? '' : 's'}`;
  return [head, '', ...reqs.map((r) => `- ${r.title.trim()} (${r.author_name ?? 'a tester'}, ${keptIds(r).length} of ${r.item_ids.length} kept)`)].join('\n');
}
