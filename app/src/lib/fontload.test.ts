import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fmtBytes, loadFontFrom } from './fontload';

describe('fmtBytes', () => {
  it('shows KB under a megabyte and MB above', () => {
    expect(fmtBytes(2048)).toBe('2 KB');
    expect(fmtBytes(3.5 * 1024 * 1024)).toBe('3.5 MB');
  });
});

describe('loadFontFrom', () => {
  const added: unknown[] = [];
  beforeEach(() => {
    added.length = 0;
    class FakeFace { constructor(public family: string, public src: ArrayBuffer) {} load() { return Promise.resolve(this); } }
    vi.stubGlobal('FontFace', FakeFace);
    Object.defineProperty(document, 'fonts', { configurable: true, value: { add: (f: unknown) => added.push(f), delete: vi.fn() } });
  });

  it('loads a build URL under its own family, never a shared name', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new Uint8Array([0, 1, 0, 0, 9]))));
    const f = await loadFontFrom('/api/builds/b3/JianZiPu.ttf', 'build b3', 'build', 'b3');
    expect(f.family).toBe('JZP-build-b3');
    expect(f.bytes).toBe(5);
    expect(fetch).toHaveBeenCalledWith('/api/builds/b3/JianZiPu.ttf', { cache: 'no-store' });
    expect((added[0] as { family: string }).family).toBe('JZP-build-b3');
  });

  it('loads a chosen file without touching the server', async () => {
    vi.stubGlobal('fetch', vi.fn());
    const file = new File([new Uint8Array([1, 2, 3])], 'mine.ttf');
    const f = await loadFontFrom(file, 'mine.ttf', 'file');
    expect(f.family).toMatch(/^JZP-file-\d+$/);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('rejects an empty file', async () => {
    await expect(loadFontFrom(new File([], 'x.ttf'), 'x', 'file')).rejects.toThrow('empty');
  });
});
