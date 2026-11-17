// Supabase Edge Function: feedback from the font page (jianzipufont.com). The form posts here as
// multipart (the message, the row it's about, an optional name and email, up to 5 pictures);
// check.ts decides what's acceptable, this stores the pictures in the private `feedback` bucket and
// the message in public.feedback (status 'new'), then emails FEEDBACK_TO (or the Builder's admins)
// through Resend with the pictures attached. Setup and secrets: README.md in this folder.
import { LIMITS, older, originAllowed, parse, senderHash } from './check.ts';
import { feedbackMail } from './mail.ts';
import { GHOSTS_QUERY, ghostOf, type UpcomingRow } from './ghosts.ts';

const env = (k: string, fallback = '') => Deno.env.get(k) ?? fallback;
const SUPABASE_URL = env('SUPABASE_URL');
const SERVICE_KEY = env('SUPABASE_SERVICE_ROLE_KEY');   // provided to every Edge Function
const service = { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` };

function cors(origin: string | null): Record<string, string> {
  const extra = env('FEEDBACK_ORIGINS').split(',').map((s) => s.trim()).filter(Boolean);
  return originAllowed(origin, extra)
    ? { 'Access-Control-Allow-Origin': origin!, 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'content-type', Vary: 'Origin' }
    : { Vary: 'Origin' };
}

async function recent(sender: string): Promise<number> {
  const since = new Date(Date.now() - 3600_000).toISOString();
  const r = await fetch(`${SUPABASE_URL}/rest/v1/feedback?select=id&sender=eq.${sender}&created_at=gte.${encodeURIComponent(since)}`, { headers: service });
  if (!r.ok) throw new Error(`feedback count: HTTP ${r.status}`);
  return (await r.json()).length;
}

async function upload(path: string, file: File) {
  const r = await fetch(`${SUPABASE_URL}/storage/v1/object/feedback/${path}`, {
    method: 'POST', headers: { ...service, 'Content-Type': file.type, 'x-upsert': 'false' }, body: file,
  });
  if (!r.ok) throw new Error(`storage ${path}: HTTP ${r.status} ${await r.text()}`);
}

/** Who gets the email: FEEDBACK_TO (comma-separated), else the Builder's admins, in its project. */
async function recipients(): Promise<string[]> {
  const to = env('FEEDBACK_TO').split(',').map((s) => s.trim()).filter(Boolean);
  if (to.length) return to;
  const r = await fetch(`${SUPABASE_URL}/rest/v1/profiles?select=email&role=eq.admin`, { headers: service });
  if (!r.ok) throw new Error(`no FEEDBACK_TO, and no admins to send to (profiles: HTTP ${r.status})`);
  return (await r.json() as { email: string | null }[]).map((p) => p.email).filter((e): e is string => !!e);
}

/** The coming characters the page shows (GET): public, so any page may read them; kept a minute. */
let ghostCache: { at: number; body: string } | null = null;
async function ghosts(): Promise<Response> {
  const headers = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' };
  if (ghostCache && Date.now() - ghostCache.at < 60_000) return new Response(ghostCache.body, { headers });
  const r = await fetch(`${SUPABASE_URL}/rest/v1/upcoming?${GHOSTS_QUERY}`, { headers: service });
  if (!r.ok) {
    // a project without supabase/009 has no upcoming table: no ghosts, rather than an error on the page
    console.error(`upcoming: HTTP ${r.status} ${await r.text()}`);
    return new Response(JSON.stringify({ ghosts: [] }), { headers: { ...headers, 'Cache-Control': 'no-store' } });
  }
  const rows = await r.json() as UpcomingRow[];
  const body = JSON.stringify({ ghosts: rows.map((x) => ghostOf(x, SUPABASE_URL)).filter(Boolean) });
  ghostCache = { at: Date.now(), body };
  return new Response(body, { headers });
}

/** Cloudflare Turnstile: whether the page's spam check passed. Off (always passes) until the
 *  TURNSTILE_SECRET secret is set, so the function can be deployed before the page has the widget. */
async function human(token: string, address: string): Promise<boolean> {
  const secret = env('TURNSTILE_SECRET');
  if (!secret) return true;
  if (!token) return false;
  const form = new FormData();
  form.append('secret', secret); form.append('response', token);
  if (address !== 'unknown') form.append('remoteip', address);
  try {
    const r = await fetch(env('TURNSTILE_URL', 'https://challenges.cloudflare.com/turnstile/v0/siteverify'), { method: 'POST', body: form });
    return !!(await r.json()).success;
  } catch (e) {
    console.error('turnstile:', e);
    return false;
  }
}

function base64(bytes: Uint8Array): string {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

Deno.serve(async (req) => {
  const origin = req.headers.get('origin'), headers = cors(origin);
  if (req.method === 'GET') {
    try { return await ghosts(); } catch (e) {
      console.error(e);
      return Response.json({ ghosts: [] }, { headers: { 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'no-store' } });
    }
  }
  if (req.method === 'OPTIONS') return new Response(null, { status: headers['Access-Control-Allow-Origin'] ? 204 : 403, headers });
  const answer = (body: unknown, status = 200) => Response.json(body, { status, headers });
  // a page that may not post is told so in words it can show (with no CORS header the browser hides
  // the answer, and the page could only say it couldn't reach the form); nothing of it is kept
  if (!headers['Access-Control-Allow-Origin']) {
    return Response.json({ error: `This form only takes messages from the JianZiPu font page, not ${origin ?? 'this page'}.` },
      { status: 403, headers: origin ? { 'Access-Control-Allow-Origin': origin, Vary: 'Origin' } : { Vary: 'Origin' } });
  }
  if (req.method !== 'POST') return answer({ error: 'Send the form with POST.' }, 405);

  let fd: FormData;
  try { fd = await req.formData(); } catch { return answer({ error: "The form didn't arrive whole. Try again." }, 400); }
  const p = parse(fd);
  if (!p.ok) return answer({ error: p.error }, p.status);
  if (p.spam) return answer({ ok: true });

  try {
    const address = (req.headers.get('x-forwarded-for') ?? '').split(',')[0].trim() || 'unknown';
    if (!await human(String(fd.get('cf-turnstile-response') ?? ''), address)) {
      return answer({ error: "The page's spam check didn't pass. Wait a few seconds and send again, or reload the page." }, 403);
    }
    const sender = await senderHash(address, env('FEEDBACK_SALT'));
    if (await recent(sender) >= LIMITS.perHour) {
      return answer({ error: "You've sent several messages in the last hour. Try again later, or write to me through the contact page." }, 429);
    }
    const id = crypto.randomUUID();
    const paths = p.pictures.map((pic, i) => `${id}/picture-${i + 1}.${pic.ext}`);
    for (let i = 0; i < paths.length; i++) await upload(paths[i], p.pictures[i].file);
    const insert = (row: Record<string, unknown>) => fetch(`${SUPABASE_URL}/rest/v1/feedback`, {
      method: 'POST', headers: { ...service, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
      body: JSON.stringify(row),
    });
    // a project behind on its migrations still keeps the message: without 008 a request or comment
    // goes in as feedback on the page with its details written into the message (older()), and
    // without 007 also without its kind. The 008 columns go only when they hold something, so plain
    // feedback never needs 008.
    const e = p.entry, plain = older(e);
    const full = { ...plain, kind: e.kind, message: e.message,
      ...(e.upcoming_id ? { upcoming_id: e.upcoming_id } : {}), ...(e.details ? { details: e.details } : {}) };
    const { kind: _, ...kindless } = plain;
    const tries = [full, plain, kindless].filter((t, i, all) => all.findIndex((u) => JSON.stringify(u) === JSON.stringify(t)) === i);
    let r: Response | null = null, why = '';
    for (const row of tries) {
      r = await insert({ id, ...row, pictures: paths, sender });
      if (r.ok) {
        if (row !== full) console.error('feedback: saved in an older form; run supabase/007_feedback_kind.sql and 008_feedback_requests.sql');
        break;
      }
      why = await r.text();
      if (!/kind|upcoming_id|details/.test(why)) break;
    }
    if (!r?.ok) throw new Error(`feedback insert: HTTP ${r?.status} ${why}`);

    // the message is kept; the email is a courtesy, so a failed send is logged, not the visitor's problem
    try {
      const to = await recipients();
      if (to.length) {
        const ref = new URL(SUPABASE_URL).hostname.split('.')[0];
        const m = feedbackMail({ entry: p.entry, pictures: paths.length, tableUrl: `https://supabase.com/dashboard/project/${ref}/editor` });
        const attachments = await Promise.all(p.pictures.map(async (pic, i) => ({
          filename: paths[i].split('/')[1], content: base64(new Uint8Array(await pic.file.arrayBuffer())),
        })));
        const sent = await fetch(env('RESEND_URL', 'https://api.resend.com/emails'), {   // RESEND_URL: a stand-in, for testing
          method: 'POST',
          headers: { Authorization: `Bearer ${env('RESEND_API_KEY')}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            from: env('FEEDBACK_FROM', env('MAIL_FROM')), to, subject: m.subject, text: m.text, html: m.html,
            ...(p.entry.email ? { reply_to: p.entry.email } : {}), ...(attachments.length ? { attachments } : {}),
          }),
        });
        if (!sent.ok) console.error(`Resend: HTTP ${sent.status} ${await sent.text()}`);
      }
    } catch (e) { console.error('feedback email:', e); }
    return answer({ ok: true, id });
  } catch (e) {
    console.error(e);
    return answer({ error: "Your message couldn't be saved just now. Try again in a minute." }, 500);
  }
});
