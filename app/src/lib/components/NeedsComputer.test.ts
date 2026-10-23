// The note a phone shows in place of a tool that needs a computer.
import { describe, it, expect, vi, afterEach } from 'vitest';
import { flushSync, mount, unmount } from 'svelte';
import NeedsComputer from './NeedsComputer.svelte';
import { openedAnyway } from '$lib/phone.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = ''; });
const button = (label: string) => [...document.querySelectorAll('button')].find((b) => b.textContent?.trim() === label)!;

describe('NeedsComputer', () => {
  it('names the tool, copies the link, and opens anyway for this visit', async () => {
    const writeText = vi.fn(async () => {});
    vi.stubGlobal('navigator', { clipboard: { writeText } });
    const onanyway = vi.fn();
    const c = mount(NeedsComputer, { target: document.body, props: { tool: 'The glyph editor', key: '/glyphs/[name]/edit', onanyway } });
    flushSync();
    expect(document.body.textContent).toContain('The glyph editor needs a computer.');
    button('Copy link').click();
    await Promise.resolve();
    expect(writeText).toHaveBeenCalledWith(location.href);
    expect(button('Back')).toBeTruthy();
    button('Open anyway').click();
    expect(openedAnyway['/glyphs/[name]/edit']).toBe(true);
    expect(onanyway).toHaveBeenCalled();
    unmount(c);
  });
  it('in a dialog, Close takes the place of Back', () => {
    const onclose = vi.fn();
    const c = mount(NeedsComputer, { target: document.body, props: { tool: 'Importing and exporting the design', key: 'import-export', onclose } });
    flushSync();
    expect(button('Back')).toBeUndefined();
    button('Close').click();
    expect(onclose).toHaveBeenCalled();
    unmount(c);
  });
});
