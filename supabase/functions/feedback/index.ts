// Supabase Edge Function: feedback from the font page (jianzipufont.com). The form posts here as
// multipart (the message, the row it's about, an optional name and email, up to 5 pictures);
// check.ts decides what's acceptable, this stores the pictures in the private `feedback` bucket and
// the message in public.feedback (status 'new'), then emails FEEDBACK_TO (or the Builder's admins)
// through Resend with the pictures attached. Setup and secrets: README.md in this folder.
import { LIMITS, originAllowed, parse, senderHash } from './check.ts';
import { feedbackMail } from './mail.ts';

const env = (k: string, fallback = '') => Deno.env.get(k) ?? fallback;
const SUPABASE_URL = env('SUPABASE_URL');
const SERVICE_KEY = env('SUPABASE_SERVICE_ROLE_KEY');   // provided to every Edge Function
const service = { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` };

function cors(origin: string | null): Record<string, string> {
  const extra = env('FEEDBACK_ORIGINS').split(',').map((s) => s.trim()).filter(Boolean);
  return originAllowed(origin, extra)
    ? { 'Access-Control-Allow-Origin': origin!, 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Access-Control-Allow-Headers': 'content-type', Vary: 'Origin' }
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

function base64(bytes: Uint8Array): string {
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

Deno.serve(async (req) => {
  const origin = req.headers.get('origin'), headers = cors(origin);
  if (req.method === 'OPTIONS') return new Response(null, { status: headers['Access-Control-Allow-Origin'] ? 204 : 403, headers });
  const answer = (body: unknown, status = 200) => Response.json(body, { status, headers });
  if (!headers['Access-Control-Allow-Origin']) return answer({ error: 'This form only takes messages from the JianZiPu font page.' }, 403);
  if (req.method !== 'POST') return answer({ error: 'Send the form with POST.' }, 405);

  let fd: FormData;
  try { fd = await req.formData(); } catch { return answer({ error: "The form didn't arrive whole. Try again." }, 400); }
  const p = parse(fd);
  if (!p.ok) return answer({ error: p.error }, p.status);
  if (p.spam) return answer({ ok: true });

  try {
    const address = (req.headers.get('x-forwarded-for') ?? '').split(',')[0].trim() || 'unknown';
    const sender = await senderHash(address, env('FEEDBACK_SALT'));
    if (await recent(sender) >= LIMITS.perHour) {
      return answer({ error: "You've sent several messages in the last hour. Try again later, or write to me through the contact page." }, 429);
    }
    const id = crypto.randomUUID();
    const paths = p.pictures.map((pic, i) => `${id}/picture-${i + 1}.${pic.ext}`);
    for (let i = 0; i < paths.length; i++) await upload(paths[i], p.pictures[i].file);
    const r = await fetch(`${SUPABASE_URL}/rest/v1/feedback`, {
      method: 'POST', headers: { ...service, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
      body: JSON.stringify({ id, ...p.entry, pictures: paths, sender }),
    });
    if (!r.ok) throw new Error(`feedback insert: HTTP ${r.status} ${await r.text()}`);

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
