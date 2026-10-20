// The feedback form needs a signed-in tester in the app, so it's checked here instead.
import { describe, it, expect, vi, afterEach } from 'vitest';
import { flushSync, mount, unmount } from 'svelte';
import ContactDialog from './ContactDialog.svelte';

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = ''; });

async function settle() { for (let i = 0; i < 5; i++) await Promise.resolve(); flushSync(); }

describe('ContactDialog', () => {
  it('feedback: prefilled from the tester, sends the message with page and version, then thanks', async () => {
    const f = vi.fn(async () => new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal('fetch', f);
    const onclose = vi.fn();
    const c = mount(ContactDialog, { target: document.body, props: { kind: 'feedback', name: 'Mei Chen', email: 'mei@example.com', context: { page: '/layouts', version: 'abc123' }, onclose } });
    flushSync();
    const send = [...document.querySelectorAll('button')].find((b) => b.textContent === 'Send feedback')!;
    expect(send.disabled).toBe(true);                       // no message yet
    const ta = document.querySelector('textarea')!;
    ta.value = 'The Spacing panel is lovely'; ta.dispatchEvent(new Event('input', { bubbles: true }));
    flushSync();
    expect(send.disabled).toBe(false);
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await settle();
    expect(JSON.parse((f.mock.calls[0] as unknown as [string, RequestInit])[1].body as string)).toEqual({
      _subject: 'JianZiPu Font Builder: feedback', form: 'feedback', name: 'Mei Chen', email: 'mei@example.com',
      page: '/layouts', version: 'abc123', message: 'The Spacing panel is lovely'
    });
    expect(document.body.textContent).toContain('Thank you, feedback sent');
    unmount(c);
  });

  it('invite: needs a name, a valid email and a few words about you, sent as "about"', async () => {
    const f = vi.fn(async () => new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal('fetch', f);
    const c = mount(ContactDialog, { target: document.body, props: { kind: 'invite', onclose: () => {} } });
    flushSync();
    expect(document.body.textContent).toContain('Tell me a bit about yourself');
    const send = [...document.querySelectorAll('button')].find((b) => b.textContent === 'Ask for an invite')!;
    const set = (el: HTMLInputElement | HTMLTextAreaElement, v: string) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); flushSync(); };
    const [name, email] = [...document.querySelectorAll('input')] as HTMLInputElement[];
    set(name, 'Mei'); set(email, 'not-an-email');
    expect(send.disabled).toBe(true);
    set(email, 'mei@example.com');
    expect(send.disabled).toBe(true);                       // nothing about yourself yet
    set(document.querySelector('textarea')!, 'I play guqin');
    expect(send.disabled).toBe(false);
    document.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await settle();
    expect(JSON.parse((f.mock.calls[0] as unknown as [string, RequestInit])[1].body as string)).toMatchObject({ form: 'invite', name: 'Mei', email: 'mei@example.com', about: 'I play guqin' });
    unmount(c);
  });
});
