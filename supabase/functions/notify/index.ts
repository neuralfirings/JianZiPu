// Supabase Edge Function: emails about Change Requests, sent through Resend. A Database Webhook on
// public.change_requests (insert and update) posts here; events.ts decides which email, and
// templates.ts writes it. Setup and secrets: README.md in this folder.
import { decide, type Payload, type RequestRow } from './events.ts';
import { TEMPLATES, type Mail } from './templates.ts';

const env = (k: string, fallback = '') => Deno.env.get(k) ?? fallback;
const SUPABASE_URL = env('SUPABASE_URL');
const SERVICE_KEY = env('SUPABASE_SERVICE_ROLE_KEY');   // provided to every Edge Function

async function people(query: string): Promise<{ id: string; email: string | null; name: string | null }[]> {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/profiles?select=id,email,name&${query}`, {
    headers: { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` }
  });
  if (!r.ok) throw new Error(`profiles: HTTP ${r.status}`);
  return await r.json();
}

async function send(to: string[], m: Mail) {
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env('RESEND_API_KEY')}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: env('MAIL_FROM'), to, subject: m.subject, text: m.text, html: m.html })
  });
  if (!r.ok) throw new Error(`Resend: HTTP ${r.status} ${await r.text()}`);
}

Deno.serve(async (req) => {
  // the webhook sends this header (README.md); anything else is turned away
  if (!env('NOTIFY_WEBHOOK_SECRET') || req.headers.get('x-webhook-secret') !== env('NOTIFY_WEBHOOK_SECRET')) {
    return new Response('forbidden', { status: 403 });
  }
  let payload: Payload;
  try { payload = await req.json(); } catch { return new Response('bad json', { status: 400 }); }
  const email = decide(payload);
  if (!email) return Response.json({ sent: 0 });
  const request = payload.record as RequestRow;
  try {
    const [author] = await people(`id=eq.${encodeURIComponent(request.author)}`);
    const to = email.to === 'admins'
      ? (await people('role=eq.admin')).map((p) => p.email).filter((e): e is string => !!e)
      : author?.email ? [author.email] : [];
    if (!to.length) return Response.json({ sent: 0, why: 'no address' });
    const mail = TEMPLATES[email.template]({
      request, authorName: author?.name || author?.email || 'A tester',
      builderUrl: env('BUILDER_URL', 'https://builder.jianzipufont.com').replace(/\/$/, ''),
      reviewUrl: env('REVIEW_URL', 'http://127.0.0.1:5713').replace(/\/$/, '')
    });
    await send(to, mail);
    return Response.json({ sent: to.length, template: email.template });
  } catch (e) {
    console.error(e);
    return Response.json({ error: (e as Error).message }, { status: 500 });
  }
});
