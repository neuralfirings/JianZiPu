// Thin client for the Python dev server (python3 -m jzpbuild.devserver).
export type Design = {
  version: 2;
  center: { x: number; y: number };
  areas: Record<string, Area>;
  layouts: Layout[];
  test_sets?: Record<string, string[]>;
  /** Reference stroke weight in SVG/font units: the thickness every glyph should sit around (glyph editor). */
  glyph_weight?: number;
};
export type SvgCheck = { ok: boolean; error?: string; d?: string; contours?: number; points?: number; bounds?: [number, number, number, number] | null; viewBox?: [number, number, number, number] };
export type Area = { label?: string; size: [number, number]; glyphs: string[]; advance?: number };
export type Slot = {
  name: string;
  optional?: boolean;
  alternatives: string[][];
  repeat?: [number, number];
  requires?: string[];
};
export type GapEntry = { when_base?: string[]; when_elem?: string[]; value: number };
export type Relationship = {
  axis: 'x' | 'y';
  elem: string;
  base: string | null;
  base_edge?: string;
  elem_edge?: string;
  gap: number | GapEntry[];
};
export type Layout = {
  name: string;
  label?: string;
  slots: Slot[];
  requires_any?: string[];
  priority?: string[];
  relationships: Relationship[];
  center: { y?: string[] | null; x?: string[] | null; y_phantom?: string[]; x_phantom?: string[]; y_target?: number; x_target?: number };
};
export type Stats = {
  rules: number; skipped: number; pair_lookups: number; est_bytes: number;
  per_layout: Record<string, { shapes: number; rules: number; skipped: number; est_bytes: number }>;
  skipped_by_layout: Record<string, SkipGroup[]>;
};
/** Why a set of word shapes could not be positioned (from the resolver). */
export type SkipGroup = {
  kind: 'no_gap' | 'no_rule' | 'base_absent' | 'self' | 'circular' | 'other';
  elem: string | null; elems?: string[] | null; axis: 'x' | 'y' | string[] | null; base: string | null;
  count: number; base_glyphs: string[]; elem_glyphs: string[];
  examples: { names: string[]; pinned: Record<string, string>; message: string }[];
};
export type DesignPayload = { design: Design; hash: string; warnings: string[]; stats: Stats };
export type ResolvedElement = {
  name: string; el: string; area: string; slot: string; instance: number;
  size: [number, number]; x: number | null; y: number | null;
};
export type ResolvePayload = {
  ok: boolean; error: string | null; elements: ResolvedElement[];
  chosen: Record<string, Relationship | null>; pins: Record<string, string[]>;
};
export type WordPiece = {
  glyphs: string[]; layout: string | null; shape?: string[]; choice?: (number | number[] | null)[];
  pinned?: Record<string, string>; pen: number;
  elements: { name: string; area: string; glyph: string; x: number; y: number; size: [number, number] }[];
};
export type WordPayload = { ok: boolean; words: { word: string; glyphs: string[]; pieces: WordPiece[]; advance: number }[] };
/** A glyph the app knows about: its SVG and the areas it is in. Its spellings live in `app.typing`. */
export type GlyphRow = { glyph: string; svg: boolean; areas: string[]; row?: boolean };
/** What the server sends per glyph: the catalog row plus its components.csv spelling fields. */
export type CatalogRow = GlyphRow & Record<string, unknown>;
export type TypingIssue = import('./typing').Issue;
export type RoundTrip = { glyph: string; field: string; value: string; got: string[]; texts: string[]; message: string };
export type TypingPreview = {
  ok: boolean; error?: string; errors: TypingIssue[]; seconds?: number;
  not_built?: string[]; missing_chars?: Record<string, string[]>; roundtrip?: RoundTrip[];
  words?: (WordPayload['words'][number] & { texts: string[] })[];
  changed?: { word: string; before: string[]; after: string[]; after_texts: string[] }[];
};
/** One finished build: its exact TTF lives in a temp dir on the server while it runs. */
export type Build = { id: string; time: number; bytes: number; ok: boolean; seconds: number | null; url: string; file: string };
export type BuildStatus = {
  state: 'idle' | 'running' | 'done'; log: string[]; started: number | null; finished: number | null;
  ok: boolean | null; font_exists: boolean; font_mtime: number | null;
  build: Build | null;      // the latest finished build
  builds: Build[];          // newest first
};

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json();
  if (!res.ok && !(data && typeof data === 'object' && 'error' in data)) {
    throw new Error(`${method} ${url}: HTTP ${res.status}`);
  }
  return data as T;
}

export const api = {
  design: () => call<DesignPayload>('GET', '/api/design'),
  saveDesign: (design: Design, base_hash: string) =>
    call<{ ok: boolean; error?: string; conflict?: boolean; hash?: string; warnings?: string[]; stats?: Stats }>(
      'PUT', '/api/design', { design, base_hash }),
  check: (design: Design) => call<{ ok: boolean; error?: string; warnings?: string[]; stats?: Stats; hash?: string }>(
    'POST', '/api/design/check', { design }),
  resolve: (design: Design, layout: string, choice: (number | number[] | null)[], pinned: Record<string, string>, center = true) =>
    call<ResolvePayload>('POST', '/api/resolve', { design, layout, choice, pinned, center }),
  words: (design: Design, words: string[]) => call<WordPayload & { error?: string }>('POST', '/api/words', { design, words }),
  glyphs: () => call<{ fields: string[]; glyphs: CatalogRow[]; control: string[]; order: string[]; hash: string }>('GET', '/api/glyphs'),
  /** Rewrite components.csv. 409 `conflict` if it changed on disk since `base_hash`; 400 `errors` on a clash. */
  saveGlyphs: (rows: Record<string, string>[], base_hash: string, design?: Design) =>
    call<{ ok: boolean; rows?: number; hash?: string; error?: string; conflict?: boolean; errors?: TypingIssue[] }>('PUT', '/api/glyphs', { rows, base_hash, design }),
  /** Unsaved spellings compiled into the last build (GSUB only): typed words, round trip, words that change. */
  typingPreview: (body: { design?: Design; rows: Record<string, string>[]; words?: string[]; base_rows?: Record<string, string>[]; compare_words?: string[]; roundtrip?: boolean }) =>
    call<TypingPreview>('POST', '/api/typing/preview', body),
  svgs: () => call<Record<string, string>>('GET', '/api/svgs'),
  /** What the font build makes of an SVG: the flattened outline (`d`, SVG coordinates), counts, bounds. */
  checkSvg: (svg: string) => call<SvgCheck>('POST', '/api/svg/check', { svg }),
  /** Write inputs/svg/<name>.svg. A new file must not exist; an existing one must still match `baseHash` (else 409 conflict) unless `overwrite`. */
  saveSvg: (name: string, svg: string, baseHash: string | null, overwrite = false) =>
    call<{ ok: boolean; error?: string; exists?: boolean; conflict?: boolean; disk?: string; file?: string; bytes?: number; existed?: boolean; hash?: string; contours?: number; points?: number }>(
      'PUT', `/api/svg/${encodeURIComponent(name)}`, { svg, base_hash: baseHash, overwrite }),
  build: () => call<{ ok: boolean; error: string | null; status: BuildStatus }>('POST', '/api/build'),
  buildStatus: () => call<BuildStatus>('GET', '/api/build/status')
};
