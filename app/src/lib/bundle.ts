// A draft bundle: everything one person changed, in one portable piece. The same shape is a
// tester's draft in Supabase (as JSON), "Export my changes" (as a .zip) and what the Review
// screen opens. It carries the whole design and spellings (small), only the glyph files that
// were added or changed, the names of deleted ones, and the base copies a three-way merge needs
// (the design and spellings it started from, the original of every changed or deleted glyph).
import { strFromU8, strToU8, unzipSync, zipSync } from 'fflate';
import type { Design } from './api';
import { sanitizeSvg } from './svg';
import * as T from './typing';

export const BUNDLE_FORMAT = 1;
/** Same rule as the server's SVG_NAME (webserver.py). */
export const GLYPH_NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;

export type SvgMap = Record<string, string>;
/** The font version a draft is based on. `date`: when the font's files last changed ("the font of 18 Oct"). */
export type BaseVersion = { commit: string | null; date?: string | null; design_hash: string; csv_hash: string };
export type Manifest = {
  format: number;
  kind: 'jzp-draft';
  base: BaseVersion;
  author: { id?: string; name?: string };
  updated: string;
  note?: string;
  svgs: { added: string[]; changed: string[]; deleted: string[] };
};
export type Bundle = {
  manifest: Manifest;
  design: Design;
  typing: T.Typing;
  /** Added and changed glyphs only. */
  svgs: SvgMap;
  base: { design: Design; typing: T.Typing; svgs: SvgMap };
};

/** Which glyph files differ between the base set and the current set. */
export function diffSvgs(base: SvgMap, cur: SvgMap) {
  const added: string[] = [], changed: string[] = [], deleted: string[] = [];
  for (const [n, t] of Object.entries(cur)) {
    if (!(n in base)) added.push(n);
    else if (norm(base[n]) !== norm(t)) changed.push(n);
  }
  for (const n of Object.keys(base)) if (!(n in cur)) deleted.push(n);
  return { added: added.sort(), changed: changed.sort(), deleted: deleted.sort() };
}
/** The server appends a final newline on write; don't count that as a change. */
const norm = (t: string) => t.replace(/\s+$/, '');

export function makeBundle(o: {
  design: Design; typing: T.Typing; svgs: SvgMap;
  baseDesign: Design; baseTyping: T.Typing; baseSvgs: SvgMap; base: BaseVersion;
  author?: Manifest['author']; note?: string; now?: Date;
}): Bundle {
  const d = diffSvgs(o.baseSvgs, o.svgs);
  const pick = (m: SvgMap, names: string[]) => Object.fromEntries(names.map((n) => [n, m[n]]));
  return {
    manifest: {
      format: BUNDLE_FORMAT, kind: 'jzp-draft', base: o.base, author: o.author ?? {},
      updated: (o.now ?? new Date()).toISOString(), ...(o.note ? { note: o.note } : {}), svgs: d
    },
    design: clone(o.design),
    typing: clone(o.typing),
    svgs: pick(o.svgs, [...d.added, ...d.changed]),
    base: { design: clone(o.baseDesign), typing: clone(o.baseTyping), svgs: pick(o.baseSvgs, [...d.changed, ...d.deleted]) }
  };
}

/** The full glyph set a bundle describes, on top of some current set (e.g. the server's). */
export function applySvgs(cur: SvgMap, b: Pick<Bundle, 'svgs' | 'manifest'>): SvgMap {
  const out = { ...cur, ...b.svgs };
  for (const n of b.manifest.svgs.deleted) delete out[n];
  return out;
}

export function isEmptyBundle(b: Bundle): boolean {
  const s = b.manifest.svgs;
  return !s.added.length && !s.changed.length && !s.deleted.length
    && JSON.stringify(b.design) === JSON.stringify(b.base.design)
    && T.changedGlyphs(b.base.typing, b.typing).length === 0;
}

// ---------------------------------------------------------------- checks

export class BundleError extends Error {}

/** Throws a readable BundleError when `x` is not a draft this version of the app can open. */
export function validate(x: unknown): Bundle {
  const b = x as Bundle;
  const m = b?.manifest;
  if (!m || m.kind !== 'jzp-draft') throw new BundleError('This is not a JZP draft (no manifest).');
  if (m.format > BUNDLE_FORMAT) throw new BundleError(`This draft was made by a newer Builder (format ${m.format}); update the app to open it.`);
  if (!b.design || b.design.version !== 2 || !b.design.areas || !Array.isArray(b.design.layouts)) throw new BundleError('The draft has no usable design.json.');
  if (!b.base?.design) throw new BundleError('The draft is missing the version it started from.');
  for (const n of [...Object.keys(b.svgs ?? {}), ...m.svgs.deleted]) {
    if (!GLYPH_NAME.test(n) || n.endsWith('.')) throw new BundleError(`Bad glyph name in the draft: ${n}`);
  }
  for (const n of [...m.svgs.added, ...m.svgs.changed]) {
    if (typeof b.svgs[n] !== 'string') throw new BundleError(`The draft lists ${n} but has no file for it.`);
  }
  return { ...b, typing: b.typing ?? {}, svgs: cleanAll(b.svgs ?? {}), base: { design: b.base.design, typing: b.base.typing ?? {}, svgs: cleanAll(b.base.svgs ?? {}) } };
}

/** Glyph files from someone else are inlined in the page: keep only plain shapes (svg.ts).
 *  Outside a browser (the unit tests run under Node) there is nothing to inline into. */
function cleanAll(m: SvgMap): SvgMap {
  if (typeof DOMParser === 'undefined') return m;
  const out: SvgMap = {};
  for (const [n, t] of Object.entries(m)) {
    try { out[n] = sanitizeSvg(t); } catch { throw new BundleError(`${n}.svg in the draft is not an SVG.`); }
  }
  return out;
}

// ---------------------------------------------------------------- JSON (storage) and zip (export)

export const toJson = (b: Bundle) => JSON.stringify(b);
export const fromJson = (text: string) => validate(JSON.parse(text));
/** A bundle as Supabase hands back a jsonb column: normally the object, but a row pasted in by
 *  hand can hold the same JSON as one string (jsonb_typeof = 'string'); read both. */
export const fromStored = (v: unknown) => (typeof v === 'string' ? fromJson(v) : validate(JSON.parse(JSON.stringify(v))));

/** Zip layout = the repo's inputs/ layout, plus manifest.json and the base copies under base/. */
export function toZip(b: Bundle): Uint8Array {
  const files: Record<string, Uint8Array> = {
    'manifest.json': strToU8(JSON.stringify(b.manifest, null, 2) + '\n'),
    'design.json': strToU8(JSON.stringify(b.design, null, 2) + '\n'),
    'components.csv': strToU8(T.toCsv(b.typing)),
    'base/design.json': strToU8(JSON.stringify(b.base.design, null, 2) + '\n'),
    'base/components.csv': strToU8(T.toCsv(b.base.typing))
  };
  for (const [n, t] of Object.entries(b.svgs)) files[`svg/${n}.svg`] = strToU8(t);
  for (const [n, t] of Object.entries(b.base.svgs)) files[`base/svg/${n}.svg`] = strToU8(t);
  return zipSync(files, { level: 6 });
}

export function fromZip(bytes: Uint8Array): Bundle {
  let files: Record<string, Uint8Array>;
  try { files = unzipSync(bytes); } catch { throw new BundleError('That file is not a .zip.'); }
  // a zip made by re-zipping the folder may have everything under one top folder
  const names = Object.keys(files);
  const top = names.find((n) => n.endsWith('manifest.json'))?.slice(0, -'manifest.json'.length) ?? '';
  const text = (n: string) => (files[top + n] ? strFromU8(files[top + n]) : null);
  const json = (n: string) => { const t = text(n); try { return t == null ? null : JSON.parse(t); } catch { throw new BundleError(`${n} in the zip is not valid JSON.`); } };
  const svgsUnder = (dir: string) => Object.fromEntries(names
    .filter((n) => n.startsWith(top + dir) && n.endsWith('.svg') && !n.slice((top + dir).length).includes('/'))
    .map((n) => [n.slice((top + dir).length, -4), strFromU8(files[n])]));
  return validate({
    manifest: json('manifest.json'),
    design: json('design.json'),
    typing: T.fromCsv(text('components.csv') ?? ''),
    svgs: svgsUnder('svg/'),
    base: { design: json('base/design.json'), typing: T.fromCsv(text('base/components.csv') ?? ''), svgs: svgsUnder('base/svg/') }
  });
}

/** "jzp-draft-mei-2026-10-18.zip" */
export function zipName(b: Bundle): string {
  const who = (b.manifest.author.name ?? 'draft').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'draft';
  return `jzp-draft-${who}-${b.manifest.updated.slice(0, 10)}.zip`;
}

function clone<T>(x: T): T {
  return JSON.parse(JSON.stringify(x));
}
