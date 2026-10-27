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

/** A changelog entry's lines by their `### ` heading, in order ('' for lines before any heading). */
function sections(md: string): Map<string, string[]> {
  const out = new Map<string, string[]>();
  let head = '';
  for (const line of md.split('\n')) {
    const m = /^###\s+(.*)$/.exec(line);
    if (m) { head = m[1].trim(); if (!out.has(head)) out.set(head, []); continue; }
    if (!line.trim()) continue;
    if (!out.has(head)) out.set(head, []);
    out.get(head)!.push(line);
  }
  return out;
}

/** The changelog entry (Keep a Changelog) for a release: what this release's last candidate wrote
 *  (`previous`, on a second candidate), the lines code changes queued under Unreleased
 *  (`queued`), and the requests in it with their credit, each line once. */
export function releaseNotes(reqs: ChangeRequest[], queued = '', previous = ''): string {
  const lines = reqs.map((r) => `- ${r.title.trim()}${r.credit.trim() ? ` (thanks to ${r.credit.trim()})` : ''}`);
  if (!queued.trim() && !previous.trim()) return lines.length ? `### Changed\n\n${lines.join('\n')}\n` : '### Changed\n\n- ';
  const all = sections(previous);
  const add = (head: string, line: string) => {
    if ([...all.values()].some((ls) => ls.includes(line))) return;
    all.set(head, [...(all.get(head) ?? []), line]);
  };
  for (const [head, ls] of sections(queued)) ls.forEach((l) => add(head, l));
  lines.forEach((l) => add('Changed', l));
  return [...all].filter(([, ls]) => ls.length).map(([head, ls]) => (head ? `### ${head}\n\n` : '') + ls.join('\n')).join('\n\n') + '\n';
}

/** The queued changes under "## [Unreleased]" as plain lines, for Build & test. */
export function unreleasedLines(text: string | null | undefined): string[] {
  return (text ?? '').split('\n').filter((l) => /^\s*[-*]\s+/.test(l)).map((l) => l.replace(/^\s*[-*]\s+/, '').trim());
}

/** The commit message for the design changes a candidate takes. */
export function commitMessage(version: string, reqs: ChangeRequest[]): string {
  const head = `${version}: changes from ${reqs.length} Change Request${reqs.length === 1 ? '' : 's'}`;
  return [head, '', ...reqs.map((r) => `- ${r.title.trim()} (${r.author_name ?? 'a tester'}, ${keptIds(r).length} of ${r.item_ids.length} kept)`)].join('\n');
}
