import { describe, it, expect, vi } from 'vitest';
import { SCREENS, screenOnPhone, installPhone, phone, PHONE_MEDIA } from './phone.svelte';

// every route the app has: src/routes/**/+page.svelte and +page.ts (a page that only redirects)
const routes = [...new Set(Object.keys(import.meta.glob(['/src/routes/**/+page.svelte', '/src/routes/**/+page.ts']))
  .map((f) => f.replace(/^\/src\/routes/, '').replace(/\/\+page\.(svelte|ts)$/, '') || '/'))];

describe('screens on a phone', () => {
  it('every route says what it is on a phone', () => {
    expect(routes.length).toBeGreaterThan(5);
    for (const r of routes) expect(SCREENS, r).toHaveProperty([r]);
    for (const r of Object.keys(SCREENS)) expect(routes, `${r} is in SCREENS but not a route`).toContain(r);
  });
  it('a screen not in the list needs a computer', () => {
    expect(screenOnPhone('/somewhere-new')).toEqual({ computer: 'This screen' });
    expect(screenOnPhone(null)).toEqual({ computer: 'This screen' });
  });
  it('the glyph editor and Release need a computer; Glyphs, Layouts and Help work on a phone', () => {
    expect(screenOnPhone('/glyphs/[name]/edit')).toEqual({ computer: 'The glyph editor' });
    expect(screenOnPhone('/release')).toHaveProperty('computer');
    for (const r of ['/glyphs', '/layouts', '/help', '/test', '/requests']) expect(screenOnPhone(r)).toBe('phone');
  });
  it('Review works on a phone only for your own changes', () => {
    expect(screenOnPhone('/review', new URLSearchParams('mine'))).toBe('phone');
    expect(screenOnPhone('/review', new URLSearchParams('mine&send'))).toBe('phone');
    expect(screenOnPhone('/review')).toEqual({ computer: 'Review' });
    expect(screenOnPhone('/review', new URLSearchParams('request=r1'))).toEqual({ computer: 'Review' });
  });
});

describe('installPhone', () => {
  it('follows the breakpoint and the pointer', () => {
    const qs = new Map<string, { matches: boolean; fire?: () => void }>();
    const win = {
      matchMedia: (q: string) => {
        const m = { matches: q === PHONE_MEDIA, addEventListener: (_: string, f: () => void) => { (qs.get(q) as any).fire = f; }, removeEventListener: vi.fn() };
        qs.set(q, m);
        return m;
      }
    } as unknown as Window;
    const off = installPhone(win);
    expect(phone).toEqual({ on: true, coarse: false });
    qs.get(PHONE_MEDIA)!.matches = false;
    qs.get(PHONE_MEDIA)!.fire!();
    expect(phone.on).toBe(false);
    off();
  });
});
