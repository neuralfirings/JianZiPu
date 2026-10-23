// Vitest setup: what jsdom lacks and the components expect.
import { vi } from 'vitest';

if (!(globalThis as any).ResizeObserver) {
  (globalThis as any).ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
}
// localStorage exists in jsdom; make sure each test file starts clean
try { localStorage.clear(); } catch {}
vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('no network in unit tests'))));
// jsdom has no matchMedia: a wide window with a mouse (lib/phone.svelte.ts)
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = ((q: string) => ({ matches: false, media: q, onchange: null, addEventListener() {}, removeEventListener() {},
    addListener() {}, removeListener() {}, dispatchEvent: () => false })) as typeof window.matchMedia;
}
