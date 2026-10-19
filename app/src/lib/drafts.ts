// Testers' drafts in Supabase Storage: one private bucket, one folder per person
// (drafts/<user id>/draft.json, a bundle as JSON). Storage rules let each person read and write
// only their own folder; the admin can read all of them (supabase/001_setup.sql).
import type { SupabaseClient } from '@supabase/supabase-js';
import { fromJson, toJson, type Bundle } from './bundle';

export const BUCKET = 'drafts';
const FILE = 'draft.json';
export const draftPath = (uid: string) => `${uid}/${FILE}`;

/** When the stored draft was last written (null: none yet). */
export async function draftStamp(c: SupabaseClient, uid: string): Promise<string | null> {
  const { data, error } = await c.storage.from(BUCKET).list(uid, { limit: 10, search: FILE });
  if (error) throw new Error(error.message);
  return data?.find((f) => f.name === FILE)?.updated_at ?? null;
}

export async function loadDraft(c: SupabaseClient, uid: string): Promise<{ bundle: Bundle; stamp: string | null } | null> {
  const stamp = await draftStamp(c, uid);
  if (!stamp) return null;
  const { data, error } = await c.storage.from(BUCKET).download(`${draftPath(uid)}?t=${Date.parse(stamp) || Date.now()}`);
  if (error || !data) throw new Error(error?.message ?? 'could not read the draft');
  return { bundle: fromJson(await data.text()), stamp };
}

/** Write the draft; returns its new stamp. */
export async function saveDraft(c: SupabaseClient, uid: string, b: Bundle): Promise<string | null> {
  const body = new Blob([toJson(b)], { type: 'application/json' });
  const { error } = await c.storage.from(BUCKET).upload(draftPath(uid), body, { upsert: true, contentType: 'application/json', cacheControl: '0' });
  if (error) throw new Error(error.message);
  return draftStamp(c, uid);
}

export async function deleteDraft(c: SupabaseClient, uid: string) {
  const { error } = await c.storage.from(BUCKET).remove([draftPath(uid)]);
  if (error) throw new Error(error.message);
}

export type DraftRow = { uid: string; name: string; email: string; stamp: string };

/** Every tester's draft (admin only): who, and when it was last saved. */
export async function listDrafts(c: SupabaseClient): Promise<DraftRow[]> {
  const { data: folders, error } = await c.storage.from(BUCKET).list('', { limit: 1000 });
  if (error) throw new Error(error.message);
  const { data: people } = await c.from('profiles').select('id, name, email');
  const who = new Map((people ?? []).map((p: { id: string; name: string | null; email: string | null }) => [p.id, p]));
  const rows: DraftRow[] = [];
  for (const f of folders ?? []) {
    const stamp = await draftStamp(c, f.name).catch(() => null);
    if (!stamp) continue;
    const p = who.get(f.name);
    rows.push({ uid: f.name, name: p?.name || p?.email || f.name, email: p?.email ?? '', stamp });
  }
  return rows.sort((a, b) => b.stamp.localeCompare(a.stamp));
}

export async function loadDraftOf(c: SupabaseClient, uid: string) {
  return loadDraft(c, uid);
}
