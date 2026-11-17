// deno test supabase/functions/feedback
import { assert, assertEquals, assertMatch, assertStringIncludes } from 'jsr:@std/assert@1';
import { LIMITS, older, originAllowed, parse, senderHash } from './check.ts';
import { feedbackMail, rowName } from './mail.ts';

const form = (fields: Record<string, string>, files: [string, File][] = []) => {
  const fd = new FormData();
  for (const [k, v] of Object.entries(fields)) fd.append(k, v);
  for (const [k, f] of files) fd.append(k, f);
  return fd;
};
const png = (bytes = 10, name = 'drawing-1.png', type = 'image/png') => new File([new Uint8Array(bytes)], name, { type });

Deno.test('a row message is taken, trimmed, with its pictures', () => {
  const p = parse(form({ message: '  The pinyin should be zhòng.  ', row: '2 · 中 · d · zhōng (1.1. Which Finger to Use)',
    link: 'https://jianzipufont.com/#2', name: 'Lin', email: 'lin@example.com', _gotcha: '' }, [['picture-1', png()], ['picture-2', png(5, 'a.jpg', 'image/jpeg')]]));
  assert(p.ok && !p.spam);
  assertEquals(p.entry, { kind: 'row', glossary_row: '2 · 中 · d · zhōng (1.1. Which Finger to Use)', link: 'https://jianzipufont.com/#2',
    message: 'The pinyin should be zhòng.', name: 'Lin', email: 'lin@example.com', upcoming_id: null, details: null });
  assertEquals(p.pictures.map((x) => x.ext), ['png', 'jpg']);
});

Deno.test('feedback on the page has no row; empty fields are null', () => {
  const p = parse(form({ message: 'The font has no 猱.' }));
  assert(p.ok && !p.spam);
  assertEquals(p.entry, { kind: 'page', glossary_row: null, link: null, message: 'The font has no 猱.', name: null, email: null, upcoming_id: null, details: null });
});

Deno.test('the spam trap passes quietly and keeps nothing', () => {
  const p = parse(form({ message: 'buy now', _gotcha: 'http://spam' }));
  assert(p.ok && p.spam);
});

Deno.test('what is refused, and why', () => {
  const no = (fd: FormData, status: number, has: string) => {
    const p = parse(fd);
    assert(!p.ok, has);
    assertEquals(p.status, status);
    assertStringIncludes(p.error, has);
  };
  no(form({ message: '   ' }), 400, 'Write what should change');
  no(form({ message: 'x'.repeat(LIMITS.message + 1) }), 400, 'over 5000 characters');
  no(form({ message: 'hi', email: 'not-an-email' }), 400, "email doesn't look right");
  no(form({ message: 'hi' }, [['picture-1', png(10, 'notes.pdf', 'application/pdf')]]), 415, 'JPEG or PNG');
  no(form({ message: 'hi' }, [['picture-1', png(LIMITS.pictureBytes + 1)]]), 413, 'over 8 MB');
  no(form({ message: 'hi' }, Array.from({ length: 6 }, (_, i) => [`picture-${i + 1}`, png()] as [string, File])), 413, 'Up to 5');
});

Deno.test('a link that is not a web address is left out, not refused', () => {
  const p = parse(form({ message: 'hi', link: 'javascript:alert(1)' }));
  assert(p.ok && !p.spam);
  assertEquals(p.entry.link, null);
});

Deno.test('only the font page, its previews and your own computer may post', () => {
  for (const o of ['https://jianzipufont.com', 'https://www.jianzipufont.com', 'https://jianzipu.pages.dev',
    'https://claude-practical-goldberg-t0.jianzipu.pages.dev', 'https://builder.jianzipufont.com', 'https://jianzipu-jianzipu-pr-91.up.railway.app', 'https://jzpbuilder-jianzipu-pr-94.up.railway.app',
    'http://127.0.0.1:8765', 'http://localhost:5173']) assert(originAllowed(o), o);
  for (const o of [null, 'https://evil.example', 'https://jianzipufont.com.evil.example', 'https://jianzipu.pages.dev.evil.example', 'http://jianzipufont.com',
    'https://other.up.railway.app', 'https://evil-jianzipu-pr-94.up.railway.app', 'https://jianzipu-x.up.railway.app.evil.example'])
    assert(!originAllowed(o), String(o));
  assert(originAllowed('https://guqintabs.com', ['https://guqintabs.com']));
});

Deno.test('the sender is kept as a salted hash, the same each time', async () => {
  const a = await senderHash('203.0.113.7', 'salt'), b = await senderHash('203.0.113.7', 'salt');
  assertEquals(a, b);
  assertMatch(a, /^[0-9a-f]{32}$/);
  assert(a !== await senderHash('203.0.113.7', 'other salt'));
  assert(!a.includes('203'));
});

Deno.test('the email names the row, quotes the message, and says who to reply to', () => {
  assertEquals(rowName('2 · 中 · d · zhōng (1.1. Which Finger to Use)'), '中 (row 2)');
  const m = feedbackMail({
    entry: { kind: 'row', glossary_row: '2 · 中 · d · zhōng (1.1. Which Finger to Use)', link: 'https://jianzipufont.com/#2', message: 'Should be <b>zhòng</b>.', name: 'Lin', email: 'lin@example.com', upcoming_id: null, details: null },
    pictures: 2, tableUrl: 'https://supabase.com/dashboard/project/abc/editor',
  });
  assertEquals(m.subject, 'Feedback on 中 (row 2)');
  assertStringIncludes(m.text, 'Lin (lin@example.com) wrote with 2 pictures, attached.');
  assertStringIncludes(m.text, 'Reply to this email to answer them.');
  assertStringIncludes(m.html, 'Should be &lt;b&gt;zhòng&lt;/b&gt;.');
  assertStringIncludes(m.html, 'JianZiPu font page');
  assertStringIncludes(m.html, 'https://supabase.com/dashboard/project/abc/editor');
});

Deno.test('feedback on the page, from someone who left nothing', () => {
  const m = feedbackMail({ entry: { kind: 'page', glossary_row: null, link: null, message: 'Lovely font.', name: null, email: null, upcoming_id: null, details: null }, pictures: 0, tableUrl: 'u' });
  assertEquals(m.subject, 'Feedback on the font page');
  assertStringIncludes(m.text, 'Someone who left no name or email wrote.');
  assertStringIncludes(m.text, 'no one to reply to');
});

Deno.test('Contact me: kept as contact, needs an email, and its email says so', () => {
  assertEquals(parse(form({ message: 'Could I help?', kind: 'contact' })), { ok: false, status: 400, error: 'Leave your email, so I can write back.' });
  const p = parse(form({ message: 'Could I help?', kind: 'contact', name: 'Lin', email: 'lin@example.com', row: '2 · 中' }));
  assert(p.ok && !p.spam);
  assertEquals(p.entry.kind, 'contact');
  assertEquals(p.entry.glossary_row, null);                    // a note to you, not about a row
  const m = feedbackMail({ entry: p.entry, pictures: 0, tableUrl: 'u' });
  assertEquals(m.subject, "Message from Lin (the font page's Contact me)");
  assertStringIncludes(m.text, 'Reply to this email to answer them.');
});

Deno.test('the kind comes from the page, else from whether there is a row', () => {
  const kind = (f: Record<string, string>) => { const p = parse(form({ message: 'hi', ...f })); return p.ok && !p.spam ? p.entry.kind : null; };
  assertEquals(kind({ row: '2 · 中' }), 'row');                  // a page from before kinds sends none
  assertEquals(kind({}), 'page');
  assertEquals(kind({ kind: 'row' }), 'page');                   // a row kind with no row is about the page
  assertEquals(kind({ kind: 'nonsense', row: '2 · 中' }), 'row');
  assertEquals(kind({ kind: 'page' }), 'page');
});

Deno.test('a request: the character, its pinyin and where it was seen go in details', () => {
  const p = parse(form({ kind: 'request', zh: ' 不动 ', pinyin: 'bù dòng', seen: '《梅庵琴谱》, p. 4', message: 'Keep the left hand where it is.', email: 'lin@example.com' }));
  assert(p.ok && !p.spam);
  assertEquals([p.entry.kind, p.entry.glossary_row, p.entry.upcoming_id], ['request', null, null]);
  assertEquals(p.entry.details, { zh: '不动', pinyin: 'bù dòng', seen: '《梅庵琴谱》, p. 4' });
  const bare = parse(form({ kind: 'request', zh: '不动', message: 'x', email: 'lin@example.com' }));
  assertEquals(bare.ok && !bare.spam && bare.entry.details, { zh: '不动' });            // nothing empty is kept
  assertEquals(parse(form({ kind: 'request', message: 'Keep the hand still.' })), { ok: false, status: 400, error: 'Write the character you would like, in Chinese.' });
  assertEquals(parse(form({ kind: 'request', zh: '不动', message: 'Keep the hand still.' })), { ok: false, status: 400, error: 'Leave your email, so I can ask about it and tell you when it’s in.' });
  assertEquals(parse(form({ kind: 'request', zh: '不动' })), { ok: false, status: 400, error: 'Say what it means or how it’s played, so I can find it.' });
  assertEquals(parse(form({ kind: 'request', zh: '字'.repeat(LIMITS.zh + 1), message: 'x', email: 'lin@example.com' })).ok, false);
});

Deno.test('a comment names its coming character by id; without one it is feedback on the page', () => {
  const p = parse(form({ kind: 'comment', upcoming: 'u12', about: '不动 · bù dòng', message: 'The hook is too long.' }));
  assert(p.ok && !p.spam);
  assertEquals([p.entry.kind, p.entry.upcoming_id, p.entry.details], ['comment', 'u12', { about: '不动 · bù dòng' }]);
  const none = parse(form({ kind: 'comment', message: 'The hook is too long.' }));
  assert(none.ok && !none.spam);
  assertEquals([none.entry.kind, none.entry.upcoming_id], ['page', null]);
  assertEquals(parse(form({ kind: 'comment', upcoming: '../etc', message: 'x' })).ok, false);
  assertEquals(parse(form({ kind: 'comment', upcoming: 'u12', message: '' })), { ok: false, status: 400, error: 'Write what you would change, so the drawing can follow it.' });
});

Deno.test('before supabase/008: a request is kept as feedback on the page, its details in the message', () => {
  const p = parse(form({ kind: 'request', zh: '不动', pinyin: 'bù dòng', seen: 'p. 4', message: 'Keep the hand still.', email: 'lin@example.com' }));
  assert(p.ok && !p.spam);
  assertEquals(older(p.entry), { kind: 'page', glossary_row: null, link: null, name: null, email: 'lin@example.com',
    message: 'Request: 不动 (bù dòng)\nSeen in: p. 4\n\nKeep the hand still.' });
  const c = parse(form({ kind: 'comment', upcoming: 'u12', about: '不动', message: 'Too long.' }));
  assert(c.ok && !c.spam);
  assertEquals(older(c.entry).message, 'Comment on 不动 (u12)\n\nToo long.');
  const row = parse(form({ row: '2 · 中', message: 'hi' }));
  assert(row.ok && !row.spam);
  assertEquals(older(row.entry), { kind: 'row', glossary_row: '2 · 中', link: null, message: 'hi', name: null, email: null });
});

Deno.test('the emails for a request and a comment', () => {
  const req = feedbackMail({ entry: { kind: 'request', glossary_row: null, link: null, message: 'Keep the hand still.', name: 'Lin', email: 'lin@example.com',
    upcoming_id: null, details: { zh: '不动', pinyin: 'bù dòng', seen: '《梅庵琴谱》' } }, pictures: 1, tableUrl: 'u' });
  assertEquals(req.subject, 'Request: 不动 (bù dòng)');
  assertStringIncludes(req.text, 'Lin (lin@example.com) asked for 不动 (bù dòng) with a picture, attached.');
  assertStringIncludes(req.text, 'Where they saw it: 《梅庵琴谱》.');
  const com = feedbackMail({ entry: { kind: 'comment', glossary_row: null, link: null, message: 'Too long.', name: null, email: null,
    upcoming_id: 'u12', details: { about: '不动 · bù dòng' } }, pictures: 0, tableUrl: 'u' });
  assertEquals(com.subject, 'Comment on 不动 · bù dòng (coming next)');
  assertStringIncludes(com.text, 'commented on the coming character 不动 · bù dòng (u12).');
});
