// The Send Change Request dialog needs a signed-in tester in the app, so its ticks are checked here.
import { describe, it, expect, afterEach } from 'vitest';
import { flushSync, mount, unmount } from 'svelte';
import SendRequestDialog from './SendRequestDialog.svelte';
import type { Item } from '$lib/merge';

afterEach(() => { document.body.innerHTML = ''; });

const items: Item[] = [
  { id: 'glyph:fei1_md', kind: 'glyph', key: 'fei1_md', status: 'added', conflict: false, theirs: '<svg/>' },
  { id: 'glyph:md_nao', kind: 'glyph', key: 'md_nao', status: 'changed', conflict: false, base: '<svg/>', theirs: '<svg></svg>' },
  { id: 'spelling:fei1_md', kind: 'spelling', key: 'fei1_md', status: 'added', conflict: false, fields: [] }
];

describe('SendRequestDialog', () => {
  it('Select all and Clear all tick and untick every change', () => {
    const c = mount(SendRequestDialog, { target: document.body, props: { items, onclose: () => {} } });
    flushSync();
    const button = (t: string) => [...document.querySelectorAll('button')].find((b) => b.textContent?.trim() === t)!;
    const ticked = () => [...document.querySelectorAll<HTMLInputElement>('.pick input')].filter((i) => i.checked).length;
    const count = () => document.querySelector('legend')!.textContent;
    expect(ticked()).toBe(3);
    expect(button('Select all').disabled).toBe(true);       // everything's ticked to start with
    button('Clear all').click(); flushSync();
    expect(ticked()).toBe(0);
    expect(count()).toContain('0 of 3');
    expect(button('Clear all').disabled).toBe(true);
    expect(button('Send').disabled).toBe(true);             // nothing to send
    button('Select all').click(); flushSync();
    expect(ticked()).toBe(3);
    expect(count()).toContain('3 of 3');
    unmount(c);
  });
});
