// Testers' drafts in Supabase: one row per person in the drafts table (supabase/002_drafts_table.sql),
// the bundle as JSON. Row rules let each person read and write only their own row; the admin can
// read all of them. A save goes through save_draft(), which writes only if the row is still the one
// this tab loaded (its updated_at, the "stamp"), so two tabs can't overwrite each other unseen.
import type { SupabaseClient } from '@supabase/supabase-js';
import { fromJson, toJson, type Bundle } from './bundle';

export const TABLE = 'drafts';

/** Someone saved (or deleted) the draft since this tab loaded it. */
export class DraftConflict extends Error {
  constructor() { super('Your draft was saved somewhere else.'); }
}

/** When the stored draft was last written (null: none yet). */
export async function draftStamp(c: SupabaseClient, uid: string): Promise<string | null> {
  const { data, error } = await c.from(TABLE).select('updated_at').eq('user_id', uid).maybeSingle();
  if (error) throw new Error(error.message);
  return (data as { updated_at: string } | null)?.updated_at ?? null;
}

export async function loadDraft(c: SupabaseClient, uid: string): Promise<{ bundle: Bundle; stamp: string | null } | null> {
  const { data, error } = await c.from(TABLE).select('bundle, updated_at').eq('user_id', uid).maybeSingle();
  if (error) throw new Error(error.message);
  if (!data) return null;
  const row = data as { bundle: unknown; updated_at: string };
  return { bundle: fromJson(JSON.stringify(row.bundle)), stamp: row.updated_at };
}

/** Write the draft over the one stamped `expected` (null: there was none); returns its new stamp.
 *  Throws DraftConflict when the stored draft is no longer that one. */
export async function saveDraft(c: SupabaseClient, _uid: string, b: Bundle, expected: string | null): Promise<string> {
  const { data, error } = await c.rpc('save_draft', { p_bundle: JSON.parse(toJson(b)), p_expected: expected });
  if (error) {
    if (/conflict/i.test(error.message)) throw new DraftConflict();
    throw new Error(error.message);
  }
  return data as string;
}

export async function deleteDraft(c: SupabaseClient, uid: string) {
  const { error } = await c.from(TABLE).delete().eq('user_id', uid);
  if (error) throw new Error(error.message);
}

export type DraftRow = { uid: string; name: string; email: string; stamp: string };

/** Every tester's draft (admin only): who, and when it was last saved. */
export async function listDrafts(c: SupabaseClient): Promise<DraftRow[]> {
  const { data, error } = await c.from(TABLE).select('user_id, updated_at').order('updated_at', { ascending: false });
  if (error) throw new Error(error.message);
  const { data: people } = await c.from('profiles').select('id, name, email');
  const who = new Map((people ?? []).map((p: { id: string; name: string | null; email: string | null }) => [p.id, p]));
  return ((data ?? []) as { user_id: string; updated_at: string }[]).map((r) => {
    const p = who.get(r.user_id);
    return { uid: r.user_id, name: p?.name || p?.email || r.user_id, email: p?.email ?? '', stamp: r.updated_at };
  });
}

export async function loadDraftOf(c: SupabaseClient, uid: string) {
  return loadDraft(c, uid);
}
