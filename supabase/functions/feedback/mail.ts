// The email each new piece of feedback sends to the admins: what it's about, the message, who sent
// it, and how many pictures (attached by index.ts). The same look as the Change Request emails.
import { mail, type Mail } from '../notify/templates.ts';
import type { Entry } from './check.ts';

export type FeedbackContext = {
  entry: Entry;
  pictures: number;
  /** The Supabase dashboard's table of feedback, where its status is set. */
  tableUrl: string;
};

/** "2 · 中 · d · zhōng (1.1. Which Finger to Use)" → "中 (row 2)". */
export function rowName(row: string): string {
  const [n, zh] = row.split(' · ');
  return zh ? `${zh} (row ${n})` : `row ${n}`;
}

export function feedbackMail(c: FeedbackContext): Mail {
  const e = c.entry;
  const about = e.glossary_row ? rowName(e.glossary_row) : 'the font page';
  const who = e.name && e.email ? `${e.name} (${e.email})` : e.name || e.email || 'Someone who left no name or email';
  const pics = c.pictures ? ` with ${c.pictures === 1 ? 'a picture' : `${c.pictures} pictures`}, attached` : '';
  return mail({
    brand: 'JianZiPu font page',
    subject: `Feedback on ${about}`,
    heading: `Feedback on ${about}`,
    paras: [
      `${who} wrote${pics}.`,
      ...(e.glossary_row ? [`The row: ${e.glossary_row}.`] : []),
      ...(e.link ? [`On the page: ${e.link}`] : []),
      e.email ? 'Reply to this email to answer them.' : 'They left no email, so there is no one to reply to.',
    ],
    quote: [{ label: 'Their message', text: e.message }],
    button: { label: 'Set its status', url: c.tableUrl },
    footer: 'You get this email because you are an admin of the JianZiPu font. Every message is kept in Supabase, in the feedback table, with its status: new, read, ticket, wont_do or need_info.',
  });
}
