// Vitest setup: what jsdom lacks and the components expect.
import { vi } from 'vitest';

if (!(globalThis as any).ResizeObserver) {
  (globalThis as any).ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
}
// localStorage exists in jsdom; make sure each test file starts clean
try { localStorage.clear(); } catch {}
vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('no network in unit tests'))));
