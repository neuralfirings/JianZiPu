// deno test supabase/functions/feedback
import { assert, assertEquals, assertMatch, assertStringIncludes } from 'jsr:@std/assert@1';
import { LIMITS, originAllowed, parse, senderHash } from './check.ts';
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
  assertEquals(p.entry, { glossary_row: '2 · 中 · d · zhōng (1.1. Which Finger to Use)', link: 'https://jianzipufont.com/#2',
    message: 'The pinyin should be zhòng.', name: 'Lin', email: 'lin@example.com' });
  assertEquals(p.pictures.map((x) => x.ext), ['png', 'jpg']);
});

Deno.test('feedback on the page has no row; empty fields are null', () => {
  const p = parse(form({ message: 'The font has no 猱.' }));
  assert(p.ok && !p.spam);
  assertEquals(p.entry, { glossary_row: null, link: null, message: 'The font has no 猱.', name: null, email: null });
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
    'https://claude-practical-goldberg-t0.jianzipu.pages.dev', 'http://127.0.0.1:8765', 'http://localhost:5173']) assert(originAllowed(o), o);
  for (const o of [null, 'https://evil.example', 'https://jianzipufont.com.evil.example', 'https://jianzipu.pages.dev.evil.example', 'http://jianzipufont.com'])
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
    entry: { glossary_row: '2 · 中 · d · zhōng (1.1. Which Finger to Use)', link: 'https://jianzipufont.com/#2', message: 'Should be <b>zhòng</b>.', name: 'Lin', email: 'lin@example.com' },
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
  const m = feedbackMail({ entry: { glossary_row: null, link: null, message: 'Lovely font.', name: null, email: null }, pictures: 0, tableUrl: 'u' });
  assertEquals(m.subject, 'Feedback on the font page');
  assertStringIncludes(m.text, 'Someone who left no name or email wrote.');
  assertStringIncludes(m.text, 'no one to reply to');
});
