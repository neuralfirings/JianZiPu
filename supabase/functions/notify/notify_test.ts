// deno test supabase/functions/notify
import { assert, assertEquals, assertStringIncludes } from 'jsr:@std/assert@1';
import { decide, type RequestRow } from './events.ts';
import { newRequest, statusChanged, withdrawn } from './templates.ts';

const row = (o: Partial<RequestRow> = {}): RequestRow => ({
  id: 'r1', author: 'u1', title: 'Hui spacing', notes: 'Tighter <b>gaps</b> & more', credit: 'Mei Chen',
  item_ids: ['design:area:hui', 'spelling:md_7', 'glyph:md_7'], status: 'sent', decisions: {}, reply: '', release: null,
  created_at: '2026-10-20T10:00:00Z', ...o
});
const ctx = (r: RequestRow) => ({ request: r, authorName: 'Mei', builderUrl: 'https://builder.example', reviewUrl: 'http://127.0.0.1:5713' });

Deno.test('a new request mails the admins; a status change the author; withdrawing the admins', () => {
  assertEquals(decide({ type: 'INSERT', table: 'change_requests', record: row(), old_record: null }), { template: 'new_request', to: 'admins' });
  const up = (from: RequestRow['status'], to: RequestRow['status']) => decide({ type: 'UPDATE', table: 'change_requests', record: row({ status: to }), old_record: row({ status: from }) });
  assertEquals(up('sent', 'withdrawn'), { template: 'withdrawn', to: 'admins' });
  assertEquals(up('sent', 'in_review'), { template: 'status_changed', to: 'author' });
  assertEquals(up('in_review', 'released'), { template: 'status_changed', to: 'author' });
  assertEquals(up('in_review', 'in_review'), null);   // decisions saved again: no email
  assertEquals(decide({ type: 'INSERT', table: 'drafts', record: row(), old_record: null }), null);
});

Deno.test('the new-request email escapes what the tester wrote and links to Review', () => {
  const m = newRequest(ctx(row()));
  assertEquals(m.subject, 'Change Request from Mei: Hui spacing');
  assertStringIncludes(m.html, 'Tighter &lt;b&gt;gaps&lt;/b&gt; &amp; more');
  assert(!m.html.includes('<b>gaps'));
  assertStringIncludes(m.html, 'href="http://127.0.0.1:5713/review?request=r1"');
  assertStringIncludes(m.text, 'Credit them as: Mei Chen.');
  assertStringIncludes(m.text, '3 changes');
});

Deno.test('status emails say how much was kept and where it went', () => {
  const decided = { 'design:area:hui': 'keep', 'spelling:md_7': 'keep', 'glyph:md_7': 'skip' } as const;
  const rel = statusChanged(ctx(row({ status: 'released', release: '3.200', decisions: decided, reply: 'Lovely, thank you' })));
  assertEquals(rel.subject, 'Released in v3.200: Hui spacing');
  assertStringIncludes(rel.text, '2 of 3 changes');
  assertStringIncludes(rel.text, "The maintainer's reply:\nLovely, thank you");
  assertStringIncludes(rel.html, 'href="https://builder.example/requests#r1"');
  assertEquals(statusChanged(ctx(row({ status: 'declined' }))).subject, 'Not taken this time: Hui spacing');
  assertEquals(withdrawn(ctx(row({ status: 'withdrawn' }))).subject, 'Withdrawn: Hui spacing');
  for (const m of [rel, newRequest(ctx(row()))]) assert(!/!/.test(m.subject + m.text), 'no exclamation marks');
});
