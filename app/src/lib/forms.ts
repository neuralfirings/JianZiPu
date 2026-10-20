// The pilot's two forms, "Ask for an invite" (sign-in page) and "Feedback" (header), sent to
// Formspree as JSON so the page stays put. Formspree uses the `email` field as the reply-to
// address and `_subject` as the subject; `_gotcha` is its honeypot (left empty by people).
export const FORM_ENDPOINT = 'https://formspree.io/f/mjygdlbq';

export type FormKind = 'invite' | 'feedback';

const SUBJECT: Record<FormKind, string> = {
  invite: 'JianZiPu Font Builder: invite request',
  feedback: 'JianZiPu Font Builder: feedback'
};

export type FormResult = { ok: true } | { ok: false; error: string };

/** Post one form. Empty fields are dropped; never throws. */
export async function sendForm(kind: FormKind, fields: Record<string, string>, fetchFn: typeof fetch = fetch): Promise<FormResult> {
  const body: Record<string, string> = { _subject: SUBJECT[kind], form: kind };
  for (const [k, v] of Object.entries(fields)) if (v.trim()) body[k] = v.trim();
  let r: Response;
  try {
    r = await fetchFn(FORM_ENDPOINT, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body) });
  } catch {
    return { ok: false, error: "Couldn't reach the form service. Check your connection and try again." };
  }
  if (r.ok) return { ok: true };
  const j = (await r.json().catch(() => null)) as { error?: string; errors?: { message: string }[] } | null;
  const why = j?.errors?.map((e) => e.message).join(' ') || j?.error;
  return { ok: false, error: why ? `Not sent: ${why}` : `Not sent: the form service answered ${r.status}. Try again in a minute.` };
}

