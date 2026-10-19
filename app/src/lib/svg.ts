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

// ---------------------------------------------------------------- untrusted SVGs

const SAFE_ELEMENTS = new Set(['svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'title', 'desc', 'defs', 'clipPath']);
const SAFE_ATTRS = new Set([
  'xmlns', 'version', 'viewBox', 'width', 'height', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'd', 'points',
  'transform', 'fill', 'fill-rule', 'clip-rule', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-linecap', 'stroke-linejoin',
  'stroke-miterlimit', 'stroke-opacity', 'opacity', 'id', 'class', 'clip-path', 'clipPathUnits', 'preserveAspectRatio'
]);

/** An SVG from someone else (a tester's draft, an imported .zip) reduced to plain shapes, so it
 *  is safe to inline: no scripts, event handlers, links, external references or foreign markup.
 *  A file with nothing to remove comes back unchanged (byte for byte, so a merge can compare it
 *  with the file on disk); anything else is rebuilt from the cleaned tree. Throws when the text
 *  isn't an SVG. */
export function sanitizeSvg(text: string): string {
  const doc = new DOMParser().parseFromString(text, 'image/svg+xml');
  const root = doc.documentElement;
  if (!root || root.localName !== 'svg' || doc.getElementsByTagName('parsererror').length) throw new Error('not an SVG');
  // comments, CDATA, doctypes and processing instructions parse differently once inlined in HTML
  let dirty = /<!|<\?/.test(text.replace(/^\s*<\?xml[^>]*\?>/, ''));
  const walk = (el: Element) => {
    for (const n of [...el.childNodes]) {
      // CDATA, processing instruction, comment
      if (n.nodeType === 4 || n.nodeType === 7 || n.nodeType === 8) { n.remove(); dirty = true; }
    }
    for (const child of [...el.children]) {
      if (!SAFE_ELEMENTS.has(child.localName)) { child.remove(); dirty = true; }
      else walk(child);
    }
    for (const a of [...el.attributes]) {
      const name = a.name, v = a.value;
      const ok = SAFE_ATTRS.has(name)
        && !/javascript:|data:|expression\(/i.test(v)
        && (!/url\(/i.test(v) || /^url\(#[\w-]+\)$/.test(v.trim()));
      if (!ok) { el.removeAttribute(name); dirty = true; }
    }
  };
  walk(root);
  if (!root.getAttribute('xmlns')) { root.setAttribute('xmlns', 'http://www.w3.org/2000/svg'); dirty = true; }
  return dirty ? new XMLSerializer().serializeToString(root) : text;
}
