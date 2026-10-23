// Glyph renames (builder/inputs/glyph_ids.json, "renamed"): one entry per rename, oldest first,
// each renaming all its names at once (a naming scheme, a swap). A draft, Change Request or .zip
// made before a rename still says the old names. Every bundle the app opens goes through
// bundle.validate, which hands it to translateBundle, so the rest of the app (Review, Update my
// draft, the locks on sent changes) only ever sees the names the font has now. The app's own
// name patterns (the position decimals, md_7.6) go through original()/current() the same way.
// The app sets the list once it has loaded the glyph catalog (GET /api/glyphs).
import type { Design } from './api';
import type * as T from './typing';

export type Rename = { date?: string; names: Record<string, string> };

let list: Rename[] = [];
export function setRenames(r: Rename[] | undefined) { list = r ?? []; }
export const renames = () => list;

/** A name as the glyph is called now (renames apply in order, so a → b → c gives c). */
export function current(name: string, r: Rename[] = list): string {
  for (const x of r) if (Object.hasOwn(x.names, name)) name = x.names[name];
  return name;
}

/** The name a glyph had before every recorded rename (what the build's code calls it: md_7.6). */
export function original(name: string, r: Rename[] = list): string {
  for (let i = r.length - 1; i >= 0; i--) {
    const back = Object.entries(r[i].names).find(([, to]) => to === name);
    if (back) name = back[0];
  }
  return name;
}

/** The same map with old names translated (all at once, so a swap swaps). When two keys would
 *  land on one name (a glyph a draft added under a name that later went to another glyph), the
 *  key that already has that name keeps it and the other stays as it was. */
function keys<V>(m: Record<string, V>, r: Rename[]): Record<string, V> {
  const to = Object.fromEntries(Object.keys(m).map((k) => [k, current(k, r)]));
  const claims: Record<string, number> = {};
  for (const n of Object.values(to)) claims[n] = (claims[n] ?? 0) + 1;
  const out: Record<string, V> = {};
  for (const [k, v] of Object.entries(m)) {
    const n = to[k];
    out[claims[n] > 1 && n !== k ? k : n] = v;
  }
  return out;
}

export function translateDesign(d: Design, r: Rename[] = list): Design {
  if (!r.length) return d;
  const n = (g: string) => current(g, r);
  return {
    ...d,
    areas: Object.fromEntries(Object.entries(d.areas).map(([k, a]) => [k, { ...a, glyphs: a.glyphs.map(n) }])),
    layouts: d.layouts.map((l) => ({
      ...l,
      relationships: l.relationships.map((rel) => (Array.isArray(rel.gap)
        ? { ...rel, gap: rel.gap.map((e) => ({ ...e, ...(e.when_base ? { when_base: e.when_base.map(n) } : {}), ...(e.when_elem ? { when_elem: e.when_elem.map(n) } : {}) })) }
        : rel))
    }))
  };
}

export function translateTyping(t: T.Typing, r: Rename[] = list): T.Typing {
  if (!r.length) return t;
  const out = keys(t, r);
  for (const [g, s] of Object.entries(out)) if (s.vert_variant) out[g] = { ...s, vert_variant: current(s.vert_variant, r) };
  return out;
}

export function translateSvgs<V>(m: Record<string, V>, r: Rename[] = list): Record<string, V> {
  return r.length ? keys(m, r) : m;
}

/** A Review item id (`glyph:<name>`, `spelling:<name>`) with the glyph's name now. */
export function translateId(id: string, r: Rename[] = list): string {
  const m = /^(glyph|spelling):(.+)$/.exec(id);
  return m ? `${m[1]}:${current(m[2], r)}` : id;
}
