// Glyph renames (builder/inputs/glyph_ids.json, "renamed"): a draft, Change Request or .zip made
// before a rename still says the old name. Every bundle the app opens goes through bundle.validate,
// which hands it to translateBundle, so the rest of the app (Review, Update my draft, the locks on
// sent changes) only ever sees the names the font has now. The app sets the list once it has
// loaded the glyph catalog (GET /api/glyphs).
import type { Design } from './api';
import type * as T from './typing';

export type Rename = { from: string; to: string; date?: string };

let list: Rename[] = [];
export function setRenames(r: Rename[] | undefined) { list = r ?? []; }
export const renames = () => list;

/** A name as the glyph is called now (renames apply in order, so a → b → c gives c). */
export function current(name: string, r: Rename[] = list): string {
  for (const x of r) if (name === x.from) name = x.to;
  return name;
}

/** The same map with old names translated; an old name whose new name is already a key stays. */
function keys<V>(m: Record<string, V>, r: Rename[]): Record<string, V> {
  const out: Record<string, V> = {};
  for (const [k, v] of Object.entries(m)) {
    const n = current(k, r);
    if (n !== k && n in m) out[k] = v;
    else out[n] = v;
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
