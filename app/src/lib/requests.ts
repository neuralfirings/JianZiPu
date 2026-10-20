// Change Requests (supabase/004_change_requests.sql): a tester sends chosen changes from their
// draft, with a title, notes and how they'd like to be credited; an admin keeps or skips each
// change and replies; kept changes go into a release candidate, then a release. A sent change is
// locked in the tester's draft until the request is withdrawn or declined (or, for a skipped
// change, once the request moves on to a release candidate).
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BuildInputs } from './api';
import { diffSvgs, fromStored, makeBundle, toJson, type Bundle, type SvgMap } from './bundle';
import { applyMerge, diffBundle, type Item } from './merge';
import * as T from './typing';

export const TABLE = 'change_requests';

export type RequestStatus = 'sent' | 'in_review' | 'in_candidate' | 'released' | 'declined' | 'withdrawn';
export type Decision = 'keep' | 'skip';
export type ChangeRequest = {
  id: string; author: string; title: string; notes: string; credit: string;
  bundle: Bundle; item_ids: string[]; base_commit: string | null;
  status: RequestStatus; decisions: Record<string, Decision>; reply: string; release: string | null;
  created_at: string; updated_at: string; reviewed_at: string | null; released_at: string | null;
  /** Filled in for admins (allRequests). */
  author_name?: string; author_email?: string;
};

export const STATUS_LABEL: Record<RequestStatus, string> = {
  sent: 'Sent', in_review: 'In review', in_candidate: 'In a release candidate',
  released: 'Released', declined: 'Declined', withdrawn: 'Withdrawn'
};
/** The pill each status shows (app.css .pill.*): colour + icon + word. */
export const STATUS_PILL: Record<RequestStatus, 'info' | 'draft' | 'saved' | 'danger' | ''> = {
  sent: 'info', in_review: 'info', in_candidate: 'draft', released: 'saved', declined: 'danger', withdrawn: ''
};
export const OPEN: RequestStatus[] = ['sent', 'in_review'];

/** The author can take it back until an admin keeps one of its changes. */
export function canWithdraw(r: Pick<ChangeRequest, 'status' | 'decisions'>): boolean {
  return r.status === 'sent' || (r.status === 'in_review' && !Object.values(r.decisions).includes('keep'));
}
export const keptIds = (r: Pick<ChangeRequest, 'item_ids' | 'decisions'>) => r.item_ids.filter((id) => r.decisions[id] === 'keep');

/** A Change Request written but not sent yet (kept on the drafts row, drafts.ts). `seen` is every
 *  change the form listed when it was saved, so a change made since starts ticked. */
export type RequestDraft = { title: string; notes: string; credit: string; chosen: string[]; seen: string[]; saved_at: string };

/** The ticks to start the Send form with: everything, or what a saved draft request chose (changes
 *  made since it was saved start ticked; changes that are gone drop out). */
export function startingTicks(ids: string[], d: RequestDraft | null): Record<string, boolean> {
  return Object.fromEntries(ids.map((id) => [id, !d || d.chosen.includes(id) || !d.seen.includes(id)]));
}

export type Lock = { id: string; title: string; sent: string };
/** The draft items a tester's requests hold: every change of an open request, and the kept
 *  changes of one in a release candidate or released. Withdrawn and declined hold nothing. */
export function lockedItems(reqs: ChangeRequest[]): Record<string, Lock> {
  const out: Record<string, Lock> = {};
  for (const r of [...reqs].sort((a, b) => a.created_at.localeCompare(b.created_at))) {
    const ids = OPEN.includes(r.status) ? r.item_ids : r.status === 'in_candidate' || r.status === 'released' ? keptIds(r) : [];
    for (const id of ids) out[id] ??= { id: r.id, title: r.title, sent: r.created_at };
  }
  return out;
}

/** The outlines a draft started from (its untouched glyphs ride the font). */
export function startSvgs(draft: Bundle, fontSvgs: SvgMap): SvgMap {
  const svgs: SvgMap = { ...fontSvgs, ...draft.base.svgs };
  for (const n of draft.manifest.svgs.added) delete svgs[n];
  return svgs;
}

/** The draft's changes, item by item, against what it started from (Your changes). */
export function draftItems(draft: Bundle, fontSvgs: SvgMap): Item[] {
  return diffBundle(draft, { design: draft.base.design, typing: draft.base.typing, svgs: startSvgs(draft, fontSvgs) });
}

/** A bundle with only the chosen changes of a draft, on the same base: what a request carries. */
export function snapshot(draft: Bundle, fontSvgs: SvgMap, chosen: string[]): { bundle: Bundle; itemIds: string[] } {
  const items = draftItems(draft, fontSvgs);
  const keep = Object.fromEntries(items.map((i) => [i.id, chosen.includes(i.id)]));
  const start = startSvgs(draft, fontSvgs);
  const m = applyMerge(items, keep, { design: draft.base.design, typing: draft.base.typing, svgs: start });
  const svgs: SvgMap = { ...start, ...m.svgWrites };
  for (const n of m.svgDeletes) delete svgs[n];
  const bundle = makeBundle({
    design: m.design, typing: m.typing, svgs, baseDesign: draft.base.design, baseTyping: draft.base.typing,
    baseSvgs: { ...fontSvgs, ...draft.base.svgs }, base: draft.manifest.base, author: draft.manifest.author
  });
  return { bundle, itemIds: m.applied.map((i) => i.id) };
}

/** What a build of a request's changes needs (POST /api/build): the font plus only those changes. */
export function buildInputs(b: Bundle, fontSvgs: SvgMap): BuildInputs {
  const svgs: SvgMap = { ...fontSvgs, ...b.svgs };
  for (const n of b.manifest.svgs.deleted) delete svgs[n];
  const d = diffSvgs(fontSvgs, svgs);
  return { design: b.design, rows: T.toRecords(b.typing), svgs: Object.fromEntries([...d.added, ...d.changed].map((n) => [n, svgs[n]])), deleted: d.deleted };
}

type Row = Omit<ChangeRequest, 'bundle'> & { bundle: unknown };
const fromRow = (r: Row): ChangeRequest => ({ ...r, decisions: (r.decisions ?? {}) as ChangeRequest['decisions'], bundle: fromStored(r.bundle) });

export async function sendRequest(c: SupabaseClient, r: { title: string; notes: string; credit: string; bundle: Bundle; itemIds: string[] }): Promise<ChangeRequest> {
  const { data, error } = await c.from(TABLE).insert({
    title: r.title.trim(), notes: r.notes.trim(), credit: r.credit.trim(), bundle: JSON.parse(toJson(r.bundle)),
    item_ids: r.itemIds, base_commit: r.bundle.manifest.base.commit ?? null
  }).select().single();
  if (error) throw new Error(error.message);
  return fromRow(data as Row);
}

/** The signed-in tester's own requests, newest first. */
export async function myRequests(c: SupabaseClient, uid: string): Promise<ChangeRequest[]> {
  const { data, error } = await c.from(TABLE).select('*').eq('author', uid).order('created_at', { ascending: false });
  if (error) throw new Error(error.message);
  return (data as Row[]).map(fromRow);
}

/** Every request with who sent it (admin only), newest first. */
export async function allRequests(c: SupabaseClient): Promise<ChangeRequest[]> {
  const { data, error } = await c.from(TABLE).select('*').order('created_at', { ascending: false });
  if (error) throw new Error(error.message);
  const { data: people } = await c.from('profiles').select('id, name, email');
  const who = new Map((people ?? []).map((p: { id: string; name: string | null; email: string | null }) => [p.id, p]));
  return (data as Row[]).map((r) => {
    const p = who.get(r.author);
    return { ...fromRow(r), author_name: p?.name || p?.email || 'someone', author_email: p?.email ?? '' };
  });
}

/** Take a request back; false when it can no longer be (an admin kept a change meanwhile). */
export async function withdraw(c: SupabaseClient, id: string): Promise<boolean> {
  const { data, error } = await c.rpc('withdraw_change_request', { p_id: id });
  if (error) throw new Error(error.message);
  return data === true;
}

/** Admin: save the Keep / Skip decisions and the reply. All skipped declines the request. */
export async function saveDecisions(c: SupabaseClient, r: ChangeRequest, decisions: Record<string, Decision>, reply: string) {
  const all = r.item_ids.every((id) => decisions[id] === 'skip');
  const { error } = await c.from(TABLE).update({
    decisions, reply: reply.trim(), status: all ? 'declined' : 'in_review', reviewed_at: new Date().toISOString()
  }).eq('id', r.id);
  if (error) throw new Error(error.message);
}

/** Admin: move requests on (into a release candidate, released). */
export async function setStatus(c: SupabaseClient, ids: string[], status: RequestStatus, release?: string) {
  if (!ids.length) return;
  const patch: Record<string, unknown> = { status };
  if (release) patch.release = release;
  if (status === 'released') patch.released_at = new Date().toISOString();
  const { error } = await c.from(TABLE).update(patch).in('id', ids);
  if (error) throw new Error(error.message);
}

export async function myCredit(c: SupabaseClient, uid: string): Promise<string> {
  const { data } = await c.from('profiles').select('credit').eq('id', uid).maybeSingle();
  return (data as { credit: string | null } | null)?.credit ?? '';
}
export async function setCredit(c: SupabaseClient, credit: string) {
  const { error } = await c.rpc('set_my_credit', { p_credit: credit });
  if (error) throw new Error(error.message);
}
