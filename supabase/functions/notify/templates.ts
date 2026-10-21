// The Change Request emails: subject, plain text and HTML, filled in from the request. Same look
// as the auth emails in supabase/emails/ (tables, inline styles, the Builder's colours as hex,
// Georgia as the fallback); same voice: sentence case, no exclamation marks.
import type { RequestRow } from './events.ts';

export type Mail = { subject: string; text: string; html: string };
export type Context = {
  request: RequestRow;
  /** Who sent it, as the admins know them. */
  authorName: string;
  /** The online Builder (testers' links) and the Builder where requests are reviewed (admins). */
  builderUrl: string;
  reviewUrl: string;
};

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;
const day = (iso: string) => new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
const kept = (r: RequestRow) => r.item_ids.filter((id) => r.decisions?.[id] === 'keep').length;

/** One email: a heading, paragraphs (plain text, escaped here), an optional quote, a button. */
function mail(o: { subject: string; heading: string; paras: string[]; quote?: { label: string; text: string }[]; button: { label: string; url: string }; footer: string }): Mail {
  const quotes = (o.quote ?? []).filter((q) => q.text.trim());
  const text = [
    o.heading, '', ...o.paras.flatMap((p) => [p, '']),
    ...quotes.flatMap((q) => [`${q.label}:`, q.text.trim(), '']),
    `${o.button.label}: ${o.button.url}`, '', o.footer
  ].join('\n');
  const td = (style: string, inner: string) => `<tr><td style="${style}">${inner}</td></tr>`;
  const body = "font-family:Literata,Georgia,serif;font-size:15px;line-height:1.6;color:#2a2a2a;";
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>${esc(o.subject)}</title>
</head>
<body style="margin:0;padding:0;background:#eeeeee;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#eeeeee;">
  <tr>
    <td align="center" style="padding:32px 16px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;background:#fafafa;border:1px solid #c4c4c4;border-radius:6px;">
        ${td("padding:28px 32px 0 32px;font-family:'EB Garamond',Garamond,Georgia,serif;font-size:15px;line-height:1.4;color:#595959;", 'JZP Font Builder')}
        ${td("padding:8px 32px 0 32px;font-family:'EB Garamond',Garamond,Georgia,serif;font-size:26px;line-height:1.25;font-weight:500;color:#2a2a2a;", esc(o.heading))}
        ${o.paras.map((p) => td(`padding:16px 32px 0 32px;${body}`, esc(p))).join('\n        ')}
        ${quotes.map((q) => td(`padding:16px 32px 0 32px;${body}`, `<div style="font-size:13px;color:#595959;">${esc(q.label)}</div><div style="margin-top:4px;padding:8px 12px;border-left:2px solid #0a5cbf;background:#f0f0f0;white-space:pre-wrap;">${esc(q.text.trim())}</div>`)).join('\n        ')}
        <tr>
          <td style="padding:24px 32px 0 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0" border="0">
              <tr>
                <td style="background:#2a2a2a;border-radius:4px;">
                  <a href="${esc(o.button.url)}" style="display:inline-block;padding:11px 22px;font-family:Literata,Georgia,serif;font-size:15px;line-height:1.2;color:#fafafa;text-decoration:none;">${esc(o.button.label)}</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        ${td('padding:24px 32px 28px 32px;font-family:Literata,Georgia,serif;font-size:13px;line-height:1.6;color:#767676;', esc(o.footer))}
      </table>
    </td>
  </tr>
</table>
</body>
</html>
`;
  return { subject: o.subject, text, html };
}

/** To the admins: a tester sent a Change Request. */
export function newRequest(c: Context): Mail {
  const r = c.request;
  return mail({
    subject: `Change Request from ${c.authorName}: ${r.title}`,
    heading: r.title,
    paras: [`${c.authorName} sent a Change Request on ${day(r.created_at)} with ${plural(r.item_ids.length, 'change')}.`,
      r.credit ? `Credit them as: ${r.credit}.` : 'They asked not to be credited.'],
    quote: [{ label: 'What they changed and why', text: r.notes }],
    button: { label: 'Review it', url: `${c.reviewUrl}/review?request=${r.id}` },
    footer: 'You get this email because you are an admin of the JZP Font Builder. Review opens in the Builder on your own computer.'
  });
}

/** To the admins: a tester took a Change Request back. */
export function withdrawn(c: Context): Mail {
  const r = c.request;
  return mail({
    subject: `Withdrawn: ${r.title}`,
    heading: `${c.authorName} withdrew a Change Request`,
    paras: [`"${r.title}" (${plural(r.item_ids.length, 'change')}, sent ${day(r.created_at)}) was withdrawn. Nothing in it needs reviewing any more.`],
    button: { label: 'Open Review', url: `${c.reviewUrl}/review` },
    footer: 'You get this email because you are an admin of the JZP Font Builder.'
  });
}

/** To the tester: their Change Request moved on. */
export function statusChanged(c: Context): Mail {
  const r = c.request, n = r.item_ids.length, k = kept(r);
  const of = `${k} of ${plural(n, 'change')}`;
  const what: Record<string, { subject: string; heading: string; paras: string[] }> = {
    in_review: { subject: `Reviewed: ${r.title}`, heading: 'Your Change Request has been reviewed',
      paras: [`The maintainer looked at "${r.title}" and kept ${of} so far. Its changes stay locked in your draft while it goes on.`] },
    declined: { subject: `Not taken this time: ${r.title}`, heading: 'Your Change Request was not taken',
      paras: [`The maintainer decided not to take the changes in "${r.title}" this time. They are unlocked in your draft, so you can keep working on them and send them again.`] },
    in_candidate: { subject: `In the v${r.release} release candidate: ${r.title}`, heading: `Your changes are in the v${r.release} release candidate`,
      paras: [`${of} from "${r.title}" are in the release candidate for JianZiPu v${r.release}, a test version of the next font. If you try it and something looks wrong, say so with Feedback in the Builder.`] },
    released: { subject: `Released in v${r.release}: ${r.title}`, heading: `Your changes are in JianZiPu v${r.release}`,
      paras: [`${of} from "${r.title}" are in JianZiPu v${r.release}, released today${r.credit ? `, credited to ${r.credit}` : ''}. Thank you.`,
        'Next time you open the Builder, Update my draft brings the new font into your draft.'] },
  };
  const w = what[r.status] ?? { subject: `Updated: ${r.title}`, heading: 'Your Change Request was updated', paras: [`"${r.title}" is now ${r.status.replace('_', ' ')}.`] };
  return mail({
    ...w,
    quote: [{ label: "The maintainer's reply", text: r.reply }],
    button: { label: 'See your Change Requests', url: `${c.builderUrl}/requests#${r.id}` },
    footer: 'You get this email because you sent this Change Request from the JZP Font Builder.'
  });
}

export const TEMPLATES = { new_request: newRequest, withdrawn, status_changed: statusChanged };
