// What the font page's feedback form may send, checked before anything is stored: the fields, their
// lengths, the pictures (count, size, type), the spam trap, and which pages may post here at all.
// Pure functions, tested in feedback_test.ts; index.ts does the storing and the email.

export const LIMITS = {
  message: 5000, name: 100, email: 254, row: 300, link: 500,
  zh: 40, pinyin: 80, seen: 300, about: 200,
  pictures: 5,
  pictureBytes: 8 * 1024 * 1024,     // the page shrinks photos to ~2000 px first, so this is generous
  totalBytes: 25 * 1024 * 1024,
  perHour: 5,                        // messages from one network address in an hour
};

/** What a message is: about a glossary row, about the page, a note to me (Contact me), a request for
 *  a character the font lacks, or a comment on a coming character (its id: `upcoming`). */
export type Kind = 'row' | 'page' | 'contact' | 'request' | 'comment';
export const KINDS: Kind[] = ['row', 'page', 'contact', 'request', 'comment'];

/** A request's character (zh, its pinyin, where it was seen) or the coming character a comment is
 *  about (`about`: its name as the page shows it). Stored as `details` (supabase/008). */
export type Details = { zh?: string; pinyin?: string; seen?: string; about?: string };

/** One message as it's stored (public.feedback, supabase/006, 007 and 008), less what the server adds. */
export type Entry = {
  kind: Kind; glossary_row: string | null; link: string | null; message: string; name: string | null; email: string | null;
  upcoming_id: string | null; details: Details | null;
};
export type Picture = { file: File; ext: string };
export type Parsed =
  | { ok: true; spam: false; entry: Entry; pictures: Picture[] }
  | { ok: true; spam: true }
  | { ok: false; status: number; error: string };

const TYPES: Record<string, string> = {
  'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif', 'image/heic': 'heic', 'image/heif': 'heif',
};

const text = (fd: FormData, k: string): string => {
  const v = fd.get(k);
  return typeof v === 'string' ? v.trim() : '';
};

export function parse(fd: FormData): Parsed {
  // the spam trap: people never see the field, so anything in it came from a script. Pretend it
  // went through, so the script learns nothing.
  if (text(fd, '_gotcha')) return { ok: true, spam: true };
  const bad = (error: string, status = 400): Parsed => ({ ok: false, status, error });

  // the kind the page says, else what the fields show (a page from before kinds sends none)
  const said = text(fd, 'kind') as Kind, row = text(fd, 'row'), upcoming = text(fd, 'upcoming');
  const kind: Kind = KINDS.includes(said) && (said !== 'row' || row) && (said !== 'comment' || upcoming) ? said : row ? 'row' : 'page';

  const message = text(fd, 'message');
  if (!message) {
    return bad(kind === 'request' ? 'Say what it means or how it’s played, so I can find it.'
      : kind === 'comment' ? 'Write what you would change, so the drawing can follow it.'
      : 'Write what should change, so I know what to fix.');
  }
  if (message.length > LIMITS.message) return bad(`Your message is over ${LIMITS.message} characters. Shorten it, or send it in two.`);
  const name = text(fd, 'name'), email = text(fd, 'email'), link = text(fd, 'link');
  if (name.length > LIMITS.name) return bad(`Your name is over ${LIMITS.name} characters.`);
  if (email && (email.length > LIMITS.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) return bad("That email doesn't look right. Check it, or leave it empty.");
  if (row.length > LIMITS.row) return bad('The row it came from is too long to be one of the glossary’s.');
  if (kind === 'contact' && !email) return bad('Leave your email, so I can write back.');
  let details: Details | null = null, upcomingId: string | null = null;
  if (kind === 'request') {
    const zh = text(fd, 'zh'), pinyin = text(fd, 'pinyin'), seen = text(fd, 'seen');
    if (!zh) return bad('Write the character you would like, in Chinese.');
    if (!email) return bad('Leave your email, so I can ask about it and tell you when it’s in.');
    if (zh.length > LIMITS.zh) return bad(`The character is over ${LIMITS.zh} characters. Request one at a time.`);
    if (pinyin.length > LIMITS.pinyin) return bad(`The pinyin is over ${LIMITS.pinyin} characters.`);
    if (seen.length > LIMITS.seen) return bad(`Where you saw it is over ${LIMITS.seen} characters. Shorten it, or put it in your message.`);
    details = { zh, ...(pinyin ? { pinyin } : {}), ...(seen ? { seen } : {}) };
  }
  if (kind === 'comment') {
    // a coming character's id, as the page's list gives it (u12)
    if (!/^[a-z0-9][a-z0-9-]{0,39}$/.test(upcoming)) return bad('The character you are commenting on isn’t one of the coming ones. Reload the page and try again.');
    const about = text(fd, 'about').slice(0, LIMITS.about);
    upcomingId = upcoming;
    details = about ? { about } : null;
  }
  let goodLink: string | null = null;
  if (link) {
    try {
      const u = new URL(link);
      if ((u.protocol === 'https:' || u.protocol === 'http:') && link.length <= LIMITS.link) goodLink = u.href;
    } catch { /* not a link: leave it out */ }
  }

  const pictures: Picture[] = [];
  let total = 0;
  for (const [k, v] of fd.entries()) {
    if (!/^picture-\d+$/.test(k) || typeof v === 'string') continue;
    const ext = TYPES[v.type];
    if (!ext) return bad(`${v.name || 'A picture'} isn't a photo the form can take. Use a JPEG or PNG.`, 415);
    if (v.size > LIMITS.pictureBytes) return bad(`${v.name || 'A picture'} is over ${LIMITS.pictureBytes / 1024 / 1024} MB. Try a smaller photo.`, 413);
    total += v.size;
    pictures.push({ file: v, ext });
  }
  if (pictures.length > LIMITS.pictures) return bad(`Up to ${LIMITS.pictures} pictures, please.`, 413);
  if (total > LIMITS.totalBytes) return bad(`The pictures come to over ${LIMITS.totalBytes / 1024 / 1024} MB together. Send fewer, or smaller ones.`, 413);

  return {
    ok: true, spam: false, pictures,
    entry: { kind, glossary_row: kind === 'row' ? row : null, link: goodLink, message, name: name || null, email: email || null,
      upcoming_id: upcomingId, details },
  };
}

/** The pages that may post here: the font page, its Cloudflare previews, the Builder's copy of it
 *  (builder.jianzipufont.com/site and a pull request's Railway preview), and a page served on your
 *  own computer; `extra` adds more (the FEEDBACK_ORIGINS secret, comma-separated). */
export function originAllowed(origin: string | null, extra: string[] = []): boolean {
  if (!origin) return false;
  if (extra.includes(origin)) return true;
  return /^https:\/\/(www\.)?jianzipufont\.com$/.test(origin)
    || /^https:\/\/([a-z0-9-]+\.)?jianzipu\.pages\.dev$/.test(origin)
    || origin === 'https://builder.jianzipufont.com'
    || /^https:\/\/jianzipu-[a-z0-9-]+\.up\.railway\.app$/.test(origin)
    || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
}

/** A sender's network address as a hash (with a secret salt), so the hourly limit works without
 *  keeping anyone's address. */
export async function senderHash(address: string, salt: string): Promise<string> {
  const data = new TextEncoder().encode(`${salt}|${address}`);
  const hash = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
  return Array.from(hash.slice(0, 16), (b) => b.toString(16).padStart(2, '0')).join('');
}

/** The message as a project without supabase/008 can keep it: a request or comment becomes feedback
 *  on the page, its details written above the message, so nothing is lost. */
export function older(e: Entry): Omit<Entry, 'upcoming_id' | 'details'> {
  const { upcoming_id, details, ...rest } = e;
  if (e.kind !== 'request' && e.kind !== 'comment') return rest;
  const d = details ?? {};
  const head = e.kind === 'request'
    ? [`Request: ${d.zh}${d.pinyin ? ` (${d.pinyin})` : ''}`, ...(d.seen ? [`Seen in: ${d.seen}`] : [])]
    : [`Comment on ${d.about ? `${d.about} ` : ''}(${upcoming_id})`];
  return { ...rest, kind: 'page', message: `${head.join('\n')}\n\n${e.message}` };
}
