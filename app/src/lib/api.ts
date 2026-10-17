// Thin client for the Python dev server (python3 -m jzpbuild.devserver).
export type Design = {
  version: 2;
  center: { x: number; y: number };
  areas: Record<string, Area>;
  layouts: Layout[];
  test_sets?: Record<string, string[]>;
};
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
export type GlyphRow = {
  glyph: string; svg: boolean; areas: string[]; ID: string; keys: string; filename: string; vert_variant: string;
  common: string; latin: string; latin_alt: string; simplified: string; traditional: string; pinyin: string;
};
export type BuildStatus = {
  state: 'idle' | 'running' | 'done'; log: string[]; started: number | null; finished: number | null;
  ok: boolean | null; font_exists: boolean; font_mtime: number | null;
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
  glyphs: () => call<{ fields: string[]; glyphs: GlyphRow[]; control: string[] }>('GET', '/api/glyphs'),
  saveGlyphs: (rows: Record<string, unknown>[]) => call<{ ok: boolean; rows: number; error?: string }>('PUT', '/api/glyphs', { rows }),
  svgs: () => call<Record<string, string>>('GET', '/api/svgs'),
  build: () => call<{ ok: boolean; error: string | null; status: BuildStatus }>('POST', '/api/build'),
  buildStatus: () => call<BuildStatus>('GET', '/api/build/status')
};
