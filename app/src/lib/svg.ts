// Turn an SVG file's text into something we can inline: its viewBox and its
// inner markup, with black fills swapped for currentColor so dark mode works.
const cache = new Map<string, { viewBox: string; inner: string } | null>();

export function parseSvg(text: string | undefined) {
  if (!text) return null;
  const hit = cache.get(text);
  if (hit !== undefined) return hit;
  const open = text.match(/<svg[^>]*>/i);
  if (!open) {
    cache.set(text, null);
    return null;
  }
  const vb = open[0].match(/viewBox="([^"]+)"/i)?.[1];
  const w = open[0].match(/\swidth="([\d.]+)/i)?.[1];
  const h = open[0].match(/\sheight="([\d.]+)/i)?.[1];
  const viewBox = vb ?? `0 0 ${w ?? 1000} ${h ?? 1000}`;
  const inner = text
    .slice(open.index! + open[0].length)
    .replace(/<\/svg>\s*$/i, '')
    .replace(/fill="(black|#000|#000000)"/gi, 'fill="currentColor"')
    .replace(/stroke="(black|#000|#000000)"/gi, 'stroke="currentColor"');
  const out = { viewBox, inner };
  cache.set(text, out);
  return out;
}
