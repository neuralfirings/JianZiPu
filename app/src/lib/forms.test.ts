import { describe, it, expect, vi } from 'vitest';
import { FORM_ENDPOINT, sendForm } from './forms';

describe('sendForm', () => {
  it('posts JSON with a subject per form, dropping empty fields', async () => {
    const f = vi.fn(async () => new Response('{"ok":true}', { status: 200 }));
    const r = await sendForm('invite', { name: ' Mei ', email: 'mei@example.com', about: '', _gotcha: '' }, f);
    expect(r).toEqual({ ok: true });
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(FORM_ENDPOINT);
    expect((init.headers as Record<string, string>).Accept).toBe('application/json');
    expect(JSON.parse(init.body as string)).toEqual({ _subject: 'JianZiPu Font Builder: invite request', form: 'invite', name: 'Mei', email: 'mei@example.com' });
  });

  it("says why Formspree refused, and copes with no answer at all", async () => {
    const bad = vi.fn(async () => new Response(JSON.stringify({ errors: [{ message: 'should be an email' }] }), { status: 422 }));
    expect(await sendForm('feedback', { email: 'x' }, bad)).toEqual({ ok: false, error: 'Not sent: should be an email' });
    const down = vi.fn(async () => { throw new TypeError('Failed to fetch'); });
    const r = await sendForm('feedback', { message: 'hi' }, down);
    expect(r.ok).toBe(false);
    const odd = vi.fn(async () => new Response('oops', { status: 500 }));
    expect(await sendForm('feedback', { message: 'hi' }, odd)).toEqual({ ok: false, error: 'Not sent: the form service answered 500. Try again in a minute.' });
  });
});

