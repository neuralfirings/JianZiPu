// The email each new piece of feedback sends to the admins: what it's about, the message, who sent
// it, and how many pictures (attached by index.ts). The same look as the Change Request emails.
import { mail, type Mail } from '../notify/templates.ts';
import type { Entry } from './check.ts';

export type FeedbackContext = {
  entry: Entry;
  pictures: number;
  /** The message in the Builder's Review › Feedback, where its status, ticket and note are set. */
  reviewUrl: string;
};

/** "2 · 中 · d · zhōng (1.1. Which Finger to Use)" → "中 (row 2)". */
export function rowName(row: string): string {
  const [n, zh] = row.split(' · ');
  return zh ? `${zh} (row ${n})` : `row ${n}`;
}

/** A requested character with its pinyin: "不动 (bù dòng)". */
function requested(e: Entry): string {
  const d = e.details ?? {};
  return d.pinyin ? `${d.zh} (${d.pinyin})` : d.zh ?? 'a character';
}

function subjectOf(e: Entry): string {
  if (e.kind === 'contact') return `Message from ${e.name || e.email} (the font page's Contact me)`;   // a note to you
  if (e.kind === 'request') return `Request: ${requested(e)}`;
  if (e.kind === 'comment') return `Comment on ${e.details?.about || e.upcoming_id} (coming next)`;
  return `Feedback on ${e.glossary_row ? rowName(e.glossary_row) : 'the font page'}`;
}

export function feedbackMail(c: FeedbackContext): Mail {
  const e = c.entry;
  const who = e.name && e.email ? `${e.name} (${e.email})` : e.name || e.email || 'Someone who left no name or email';
  const pics = c.pictures ? ` with ${c.pictures === 1 ? 'a picture' : `${c.pictures} pictures`}, attached` : '';
  const subject = subjectOf(e);
  const wrote = e.kind === 'request' ? `${who} asked for ${requested(e)}${pics}.`
    : e.kind === 'comment' ? `${who} commented on the coming character ${e.details?.about ? `${e.details.about} (${e.upcoming_id})` : e.upcoming_id}${pics}.`
    : `${who} wrote${pics}.`;
  return mail({
    brand: 'JianZiPu font page',
    subject,
    heading: e.kind === 'contact' ? `A message from ${e.name || e.email}` : subject,
    paras: [
      wrote,
      ...(e.details?.seen ? [`Where they saw it: ${e.details.seen}.`] : []),
      ...(e.glossary_row ? [`The row: ${e.glossary_row}.`] : []),
      ...(e.link ? [`On the page: ${e.link}`] : []),
      e.email ? 'Reply to this email to answer them.' : 'They left no email, so there is no one to reply to.',
    ],
    quote: [{ label: e.kind === 'request' ? 'What it means, or how it’s played' : 'Their message', text: e.message }],
    button: { label: 'Open it in Review', url: c.reviewUrl },
    footer: 'You get this email because you are an admin of the JianZiPu font. Every message is in the Builder’s Review › Feedback (signed in as an admin), with its pictures, where you set its status, a ticket link and your own note.',
  });
}
