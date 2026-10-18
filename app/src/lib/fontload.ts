// Load a TTF into the page under a family name of its own, so what renders is that
// file and nothing else: no fallback to an installed JianZiPu, no stale cache.
let n = 0;
const loaded = new Map<string, FontFace>();

export type LoadedFont = { family: string; label: string; bytes: number; source: 'build' | 'file'; id?: string };

export async function loadFontFrom(source: string | Blob, label: string, kind: 'build' | 'file', id?: string): Promise<LoadedFont> {
  const key = typeof source === 'string' ? source : `${label}:${(source as File).lastModified ?? ''}:${source.size}`;
  const buf = typeof source === 'string' ? await (await fetch(source, { cache: 'no-store' })).arrayBuffer() : await source.arrayBuffer();
  if (!buf.byteLength) throw new Error('empty font file');
  const family = `JZP-${kind}-${id ?? ++n}`;
  const prev = loaded.get(key);
  if (prev) document.fonts.delete(prev);
  const ff = new FontFace(family, buf);
  await ff.load();
  document.fonts.add(ff);
  loaded.set(key, ff);
  return { family, label, bytes: buf.byteLength, source: kind, id };
}

export const fmtBytes = (b: number) => (b >= 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.round(b / 1024)} KB`);
export const fmtTime = (t: number) => new Date(t * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
