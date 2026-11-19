// The font page's feedback (supabase/006–009): one row per message in the `feedback` table, its
// pictures in the private `feedback` bucket. Admins read and update them from Review › Feedback;
// messages come in only through the feedback Edge Function.
import type { SupabaseClient } from '@supabase/supabase-js';

export type FeedbackStatus = 'new' | 'read' | 'wip' | 'need_info' | 'ticket' | 'wont_do' | 'done';
export type FeedbackKind = 'row' | 'page' | 'contact' | 'request' | 'comment';
export type Feedback = {
  id: string; created_at: string; updated_at: string; status: FeedbackStatus; kind: FeedbackKind;
  glossary_row: string | null; link: string | null; message: string; name: string | null; email: string | null;
  pictures: string[]; ticket: string | null; note: string | null;
  upcoming_id: string | null; details: Record<string, unknown> | null;
};

export const TABLE = 'feedback';
export const BUCKET = 'feedback';

/** In the order the status menu lists them. A ticket is a link of its own, whatever the status: `ticket`
 *  stays in the database's list (006) for messages set to it before, but the menu doesn't offer it. */
export const STATUSES: FeedbackStatus[] = ['new', 'read', 'need_info', 'wip', 'done', 'wont_do'];
export const STATUS_LABEL: Record<FeedbackStatus, string> = {
  new: 'New', read: 'Read', need_info: 'Need info', wip: 'WIP', ticket: 'Ticket (old status)', done: 'Done', wont_do: "Won't do"
};
/** The pill each status shows (app.css .pill.*): colour + icon + word. */
export const STATUS_PILL: Record<FeedbackStatus, 'info' | 'draft' | 'saved' | ''> = {
  new: 'info', read: '', need_info: 'draft', wip: 'draft', ticket: 'saved', done: 'saved', wont_do: ''
};
/** Still yours to deal with: the Show menu's first choice, Open. */
export const OPEN: FeedbackStatus[] = ['new', 'read', 'need_info'];
export const KIND_LABEL: Record<FeedbackKind, string> = {
  row: 'Glossary row', page: 'The page', contact: 'Contact me', request: 'Character request', comment: 'Coming character'
};

/** What a message is about, in one line. */
export function aboutOf(f: Pick<Feedback, 'kind' | 'glossary_row' | 'details' | 'upcoming_id'>): string {
  const d = f.details ?? {};
  const s = (k: string) => (typeof d[k] === 'string' ? (d[k] as string).trim() : '');
  if (f.kind === 'row') return f.glossary_row ?? '';
  if (f.kind === 'request') return [s('zh'), s('pinyin')].filter(Boolean).join(' · ');
  if (f.kind === 'comment') return s('about') || f.upcoming_id || '';
  return '';
}

/** A request's details other than its 中文 and pinyin (where it was seen…), as label/value pairs. */
export function otherDetails(f: Pick<Feedback, 'details'>): [string, string][] {
  return Object.entries(f.details ?? {})
    .filter(([k, v]) => !['zh', 'pinyin', 'about'].includes(k) && v != null && String(v).trim())
    .map(([k, v]) => [k.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase()), typeof v === 'string' ? v : JSON.stringify(v)]);
}

/** Every message, newest first. */
export async function allFeedback(c: SupabaseClient): Promise<Feedback[]> {
  const { data, error } = await c.from(TABLE)
    .select('id, created_at, updated_at, status, kind, glossary_row, link, message, name, email, pictures, ticket, note, upcoming_id, details')
    .order('created_at', { ascending: false });
  if (error) throw new Error(/relation .*feedback.* does not exist|schema cache/.test(error.message) ? 'Supabase has no feedback table yet: run supabase/006_feedback.sql.' : error.message);
  return ((data ?? []) as Feedback[]).map((f) => ({ ...f, kind: f.kind ?? 'page', pictures: f.pictures ?? [] }));
}

/** Change its status, ticket link or your note; returns the row as saved (a request set to WIP
 *  gets its coming character's id from the database). */
export async function updateFeedback(c: SupabaseClient, id: string, patch: Partial<Pick<Feedback, 'status' | 'ticket' | 'note'>>): Promise<Feedback> {
  const { data, error } = await c.from(TABLE).update(patch).eq('id', id).select().single();
  if (error) throw new Error(error.message);
  return data as Feedback;
}

/** A message's pictures as local blob: URLs, path → URL (the bucket is private, and the Builder's
 *  content policy loads images only from itself, so they come down through the Supabase client).
 *  A picture that can't be read is left out. Revoke the URLs (URL.revokeObjectURL) when done. */
export async function pictureBlobs(c: SupabaseClient, paths: string[]): Promise<Record<string, string>> {
  const got = await Promise.all(paths.map(async (p) => {
    const { data, error } = await c.storage.from(BUCKET).download(p);
    return error || !data ? null : ([p, URL.createObjectURL(data)] as const);
  }));
  if (paths.length && got.every((g) => !g)) throw new Error('none of them could be read');
  return Object.fromEntries(got.filter((g) => !!g));
}
