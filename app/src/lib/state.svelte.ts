// App state: the editable design and the spellings (components.csv), with one
// undo/redo history and one browser draft for both, the glyph catalog and SVG
// sources, and save/budget status. Save writes design.json and components.csv,
// each hash-checked; a spelling clash pauses Save (the build would fail).
// Glyph files from a merge (Review → Apply) wait in `pendingSvgs` until Save too.
// Hosted (pilot) mode: everything above is the signed-in tester's draft; Save uploads it
// to Supabase (drafts.ts) instead of writing files, and saves itself every 30 s.
import { api, type BaseInfo, type BuildInputs, type Design, type GlyphRow, type Stats } from './api';
import { diffSvgs, isEmptyBundle, makeBundle, type BaseVersion, type Bundle, type SvgMap } from './bundle';
import { deleteDraft, draftStamp, loadDraft, saveDraft } from './drafts';
import { hosted } from './hosted.svelte';
import { applyMerge, fontUpdateItems, type Item } from './merge';
import * as T from './typing';

const DRAFT_KEY = 'jzp-builder-draft';
export const AUTOSAVE_MS = 30_000;

/** Unsaved glyph files: text to write, or null to delete. */
export type PendingSvgs = Record<string, string | null>;
/** What a merge puts into the unsaved changes (merge.ts applyMerge). */
export type Changes = { design: Design; typing: T.Typing; svgWrites: SvgMap; svgDeletes: string[] };
/** The font version a hosted draft started from, and the originals a merge needs. */
export type DraftBase = { version: BaseVersion; design: Design; typing: T.Typing; svgs: SvgMap };
type Step = { label: string; json: string; typing: string; svgs: string; base?: string };

export function withPending(saved: SvgMap, pending: PendingSvgs): SvgMap {
  const out = { ...saved };
  for (const [n, t] of Object.entries(pending)) if (t == null) delete out[n]; else out[n] = t;
  return out;
}

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v));
}

class DesignState {
  design = $state<Design | null>(null);
  diskHash = $state('');
  savedJson = $state('');
  warnings = $state<string[]>([]);
  stats = $state<Stats | null>(null);
  error = $state<string | null>(null);
  loading = $state(true);
  saving = $state(false);
  conflict = $state<string | null>(null);
  lastSaved = $state<Date | null>(null);
  draftRestored = $state(false);

  undoStack: Step[] = $state([]);
  redoStack: Step[] = $state([]);
  changes = $state<string[]>([]);

  /** Spellings by glyph (components.csv), the saved copy, and the file's hash/order on disk. */
  typing = $state<T.Typing>({});
  savedTypingJson = $state('{}');
  csvHash = $state('');
  csvOrder = $state<string[]>([]);
  /** Set when Save was refused because spellings clash or are malformed. */
  paused = $state<T.Issue[] | null>(null);
  /** Which file a hash conflict is about. */
  conflictFile = $state<'design.json' | 'components.csv'>('design.json');

  glyphs = $state<GlyphRow[]>([]);
  /** Built-in glyphs typed by symbols (blank, blank_colon…): never need a spelling. */
  control = $state<string[]>([]);
  /** Every glyph outline as the app shows it: saved files plus `pendingSvgs`. */
  svgs = $state<Record<string, string>>({});
  /** The saved outlines (local: the files; hosted: the font plus the saved draft). */
  savedSvgs = $state<SvgMap>({});
  /** The font's own outlines as the server has them (main). */
  mainSvgs = $state<SvgMap>({});
  pendingSvgs = $state<PendingSvgs>({});
  /** Unsaved outlines from the glyph editor, shown in place of the file wherever glyphs render. */
  preview = $state<Record<string, string>>({});

  // ---- hosted draft
  /** The font version on the server now (hashes per file), and its design and spellings. */
  main = $state<BaseInfo | null>(null);
  mainDesign = $state<Design | null>(null);
  mainTyping = $state<T.Typing>({});
  /** What the draft started from; null until loaded (and in local mode). */
  draftBase = $state<DraftBase | null>(null);
  /** Storage timestamp of the draft as last loaded or saved here (null: no draft yet). */
  draftStamp = $state<string | null>(null);
  /** Save could not reach Supabase: the edits wait in this browser. */
  offline = $state(false);
  /** Someone saved the draft elsewhere after it was loaded here: their timestamp. */
  savedElsewhere = $state<string | null>(null);

  get designDirty() {
    return this.design !== null && JSON.stringify(this.design) !== this.savedJson;
  }
  get typingDirty() {
    return JSON.stringify(this.typing) !== this.savedTypingJson;
  }
  get svgsDirty() {
    return Object.keys(this.pendingSvgs).length > 0;
  }
  get dirty() {
    return this.designDirty || this.typingDirty || this.svgsDirty;
  }
  /** Number of unsaved edits for the header chip. */
  get unsavedCount() {
    return Math.max(this.changes.length, this.dirty ? 1 : 0);
  }
  /** Glyphs the app has that the server's font files don't (draft-added): the server's spelling
   *  checks need their names. */
  get extraGlyphs(): string[] {
    return Object.keys(this.svgs).filter((n) => !(n in this.mainSvgs));
  }
  /** The font has moved since the draft started (hosted). */
  get fontMoved(): boolean {
    const b = this.draftBase, m = this.main;
    if (!b || !m) return false;
    if (b.version.design_hash !== m.design_hash || b.version.csv_hash !== m.csv_hash) return true;
    return Object.entries(b.svgs).some(([n, t]) => (this.mainSvgs[n] ?? null) !== t);
  }
  get savedTyping(): T.Typing {
    return JSON.parse(this.savedTypingJson);
  }
  /** Every glyph that exists: SVG files and design area members. */
  get known(): Set<string> {
    const k = new Set(this.glyphs.map((g) => g.glyph));
    for (const a of Object.values(this.design?.areas ?? {})) for (const g of a.glyphs) k.add(g);
    return k;
  }
  /** Spelling problems that pause Save. */
  get typingErrors(): T.Issue[] {
    return T.issues(this.typing, this.known);
  }
  /** The 简体 (else 繁體) of a glyph, for messages. */
  charOf(g: string): string {
    const s = this.typing[g];
    return s?.simplified || s?.traditional || '';
  }

  private get draftKey() {
    return hosted.isHosted ? `${DRAFT_KEY}:${hosted.user?.id ?? 'anon'}` : DRAFT_KEY;
  }

  async load() {
    this.loading = true;
    try {
      const [d, g, svgs] = await Promise.all([api.design(), api.glyphs(), api.svgs()]);
      this.diskHash = d.hash;
      this.warnings = d.warnings;
      this.stats = d.stats;
      this.glyphs = g.glyphs.map((r) => ({ glyph: r.glyph, svg: r.svg, areas: r.areas, row: r.row }));
      const typing = T.fromCatalog(g.glyphs);
      this.csvHash = g.hash;
      this.csvOrder = g.order;
      this.control = g.control;
      this.mainSvgs = svgs;
      this.mainDesign = d.design;
      this.mainTyping = typing;
      this.savedElsewhere = null;
      this.offline = false;
      if (hosted.isHosted) {
        this.main = await api.base();
        await this.loadDraft(d.design, typing);
      } else {
        this.main = null;
        this.draftBase = null;
        this.setSaved(d.design, typing, svgs);
      }
      this.restoreBuffer();
      this.syncGlyphRows();
      this.error = null;
    } catch (e) {
      this.error = hosted.isHosted
        ? `The Builder is taking a break: we can't reach it right now. Your saved draft is safe. (${(e as Error).message})`
        : `Can't reach the web server. Run: cd src-fonttools && python3 -m jzpbuild.webserver  (${(e as Error).message})`;
    } finally {
      this.loading = false;
    }
  }

  /** Make (design, typing, svgs) the saved state and the current one, with no history. */
  private setSaved(design: Design, typing: T.Typing, svgs: SvgMap) {
    this.savedJson = JSON.stringify(design);
    this.savedTypingJson = JSON.stringify(typing);
    this.savedSvgs = svgs;
    this.design = clone(design);
    this.typing = clone(typing);
    this.svgs = svgs;
    this.pendingSvgs = {};
    this.changes = [];
    this.undoStack = [];
    this.redoStack = [];
    this.paused = null;
  }

  /** Hosted: the tester's draft on top of the font, or the font itself if there is no draft yet. */
  private async loadDraft(mainDesign: Design, mainTyping: T.Typing) {
    const c = hosted.client, uid = hosted.user?.id;
    const fresh = (): DraftBase => ({
      version: { commit: this.main?.commit ?? null, date: this.main?.date ?? null, design_hash: this.main?.design_hash ?? this.diskHash, csv_hash: this.main?.csv_hash ?? this.csvHash },
      design: clone(mainDesign), typing: clone(mainTyping), svgs: {}
    });
    const got = c && uid ? await loadDraft(c, uid) : null;
    if (!got) {
      this.draftBase = fresh();
      this.draftStamp = null;
      this.setSaved(mainDesign, mainTyping, this.mainSvgs);
      return;
    }
    const b = got.bundle;
    this.draftBase = { version: b.manifest.base, design: b.base.design, typing: b.base.typing, svgs: b.base.svgs };
    this.draftStamp = got.stamp;
    const svgs = { ...this.mainSvgs, ...b.svgs };
    for (const n of b.manifest.svgs.deleted) delete svgs[n];
    this.setSaved(b.design, b.typing, svgs);
  }

  /** Edits that never reached the files or the draft (crash, offline, closed tab). */
  private restoreBuffer() {
    let buf: { hash?: string; stamp?: string | null; design: Design; changes: string[]; csvHash?: string; typing?: T.Typing; svgs?: PendingSvgs } | null = null;
    try {
      const raw = localStorage.getItem(this.draftKey);
      buf = raw ? JSON.parse(raw) : null;
    } catch {
      buf = null;
    }
    if (!buf) return;
    // local: on top of the same files; hosted: on top of the same saved draft
    const same = hosted.isHosted ? (buf.stamp ?? null) === this.draftStamp : buf.hash === this.diskHash;
    if (!same) return;
    const typing = buf.typing && (hosted.isHosted || buf.csvHash === this.csvHash) ? buf.typing : null;
    const svgs = buf.svgs ?? {};
    const differs = JSON.stringify(buf.design) !== this.savedJson
      || (typing && JSON.stringify(typing) !== this.savedTypingJson) || Object.keys(svgs).length > 0;
    if (!differs) return;
    this.design = buf.design;
    if (typing) this.typing = typing;
    this.pendingSvgs = svgs;
    this.svgs = withPending(this.savedSvgs, svgs);
    this.changes = buf.changes ?? [];
    this.draftRestored = true;
  }

  /** Catalog rows for glyph files that exist only in the draft or a pending merge, and not for deleted ones. */
  syncGlyphRows() {
    const have = new Set(this.glyphs.map((g) => g.glyph));
    const inArea = new Set(Object.values(this.design?.areas ?? {}).flatMap((a) => a.glyphs));
    let rows = this.glyphs.map((g) => (!!this.svgs[g.glyph] === g.svg ? g : { ...g, svg: !!this.svgs[g.glyph] }));
    rows = rows.filter((g) => g.svg || g.row || inArea.has(g.glyph));
    for (const n of Object.keys(this.svgs)) if (!have.has(n)) rows.push({ glyph: n, svg: true, areas: [] });
    this.glyphs = rows;
    this.syncCatalog();
  }

  /** Apply an edit: `fn` mutates a working copy; one undo step. */
  edit(label: string, fn: (d: Design) => void) {
    if (!this.design) return;
    const before = JSON.stringify(this.design);
    const next = clone(this.design);
    fn(next);
    const after = JSON.stringify(next);
    if (after === before) return;
    this.undoStack = [...this.undoStack.slice(-199), { label, json: before, typing: JSON.stringify(this.typing), svgs: JSON.stringify(this.pendingSvgs) }];
    this.redoStack = [];
    this.design = next;
    this.changes = [...this.changes, label];
    this.persistDraft();
    this.recheck();
  }

  /** Apply a spelling edit: `fn` mutates a working copy of the spellings; one undo step. */
  editTyping(label: string, fn: (t: T.Typing) => void) {
    if (!this.design) return;
    const before = JSON.stringify(this.typing);
    const next: T.Typing = JSON.parse(before);
    fn(next);
    for (const [g, sp] of Object.entries(next)) if (T.isEmpty(sp)) delete next[g];
    if (JSON.stringify(next) === before) return;
    this.undoStack = [...this.undoStack.slice(-199), { label, json: JSON.stringify(this.design), typing: before, svgs: JSON.stringify(this.pendingSvgs) }];
    this.redoStack = [];
    this.typing = next;
    this.changes = [...this.changes, label];
    this.paused = null;
    this.persistDraft();
  }

  /** Set one spelling field (one undo step). */
  setSpelling(g: string, f: T.SpellField, value: string) {
    const v = value.trim();
    const old = T.get(this.typing, g)[f];
    if (v === old) return;
    this.editTyping(`${g} · ${T.LABEL[f]} ${old || '—'} → ${v || '—'}`, (t) => { (t[g] ??= T.empty())[f] = v; });
  }

  /** One undo step that replaces design, spellings and glyph files at once (Review → Apply,
   *  Update my draft, the hosted glyph editor). Glyph files wait for Save like the rest. */
  applyChanges(label: string, c: Partial<Changes> & { draftBase?: DraftBase }) {
    if (!this.design) return;
    this.undoStack = [...this.undoStack.slice(-199), this.snapshot(label, !!c.draftBase)];
    this.redoStack = [];
    if (c.draftBase) this.draftBase = clone(c.draftBase);
    if (c.design) this.design = clone(c.design);
    if (c.typing) {
      const t = clone(c.typing);
      for (const [g, sp] of Object.entries(t)) if (T.isEmpty(sp)) delete t[g];
      this.typing = t;
    }
    const pending = { ...this.pendingSvgs };
    const set = (n: string, t: string | null) => {
      const saved = this.savedSvgs[n] ?? null;
      if (t === saved) delete pending[n]; else pending[n] = t;
    };
    for (const [n, t] of Object.entries(c.svgWrites ?? {})) set(n, t);
    for (const n of c.svgDeletes ?? []) set(n, null);
    this.setPending(pending);
    this.changes = [...this.changes, label];
    this.paused = null;
    this.persistDraft();
    this.recheck();
  }

  /** `withBase`: the step also changes what the draft is based on (Update my draft). */
  private snapshot(label: string, withBase = false): Step {
    return {
      label, json: JSON.stringify(this.design), typing: JSON.stringify(this.typing), svgs: JSON.stringify(this.pendingSvgs),
      ...(withBase ? { base: JSON.stringify(this.draftBase) } : {})
    };
  }
  private restore(step: Step) {
    if (step.base) this.draftBase = JSON.parse(step.base);
    this.design = JSON.parse(step.json);
    this.typing = JSON.parse(step.typing);
    this.setPending(JSON.parse(step.svgs ?? '{}'));
  }
  private setPending(p: PendingSvgs) {
    const changed = JSON.stringify(p) !== JSON.stringify(this.pendingSvgs);
    this.pendingSvgs = p;
    if (changed) {
      this.svgs = withPending(this.savedSvgs, p);
      this.syncGlyphRows();
    }
  }

  undo() {
    const step = this.undoStack.at(-1);
    if (!step || !this.design) return;
    this.undoStack = this.undoStack.slice(0, -1);
    this.redoStack = [...this.redoStack, this.snapshot(step.label, !!step.base)];
    this.restore(step);
    this.changes = this.changes.slice(0, -1);
    this.paused = null;
    this.persistDraft();
    this.recheck();
  }

  redo() {
    const step = this.redoStack.at(-1);
    if (!step || !this.design) return;
    this.redoStack = this.redoStack.slice(0, -1);
    this.undoStack = [...this.undoStack, this.snapshot(step.label, !!step.base)];
    this.restore(step);
    this.changes = [...this.changes, step.label];
    this.persistDraft();
    this.recheck();
  }

  discard() {
    this.design = JSON.parse(this.savedJson);
    this.typing = JSON.parse(this.savedTypingJson);
    this.setPending({});
    this.paused = null;
    this.changes = [];
    this.undoStack = [];
    this.redoStack = [];
    this.persistDraft();
    this.recheck();
  }

  persistDraft() {
    try {
      if (this.dirty) {
        localStorage.setItem(this.draftKey, JSON.stringify({
          hash: this.diskHash, stamp: this.draftStamp, design: this.design, changes: this.changes,
          csvHash: this.csvHash, typing: this.typing, svgs: this.pendingSvgs
        }));
      } else {
        localStorage.removeItem(this.draftKey);
      }
    } catch {
      /* private mode etc. */
    }
    this.scheduleAutosave();
  }

  private autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  /** Hosted: save the draft ~30 s after an edit (and retry while offline). */
  scheduleAutosave(ms = AUTOSAVE_MS) {
    if (!hosted.isHosted) return;
    if (this.autosaveTimer) clearTimeout(this.autosaveTimer);
    if (!this.dirty) return;
    this.autosaveTimer = setTimeout(() => { this.autosaveTimer = null; void this.save(); }, ms);
  }
  /** Save now if there is anything to save (screen change, tab hidden). */
  flush() {
    if (hosted.isHosted && this.dirty && !this.saving) void this.save();
  }

  private checkTimer: ReturnType<typeof setTimeout> | null = null;
  recheck() {
    if (this.checkTimer) clearTimeout(this.checkTimer);
    this.checkTimer = setTimeout(async () => {
      if (!this.design) return;
      try {
        const r = await api.check(this.design);
        if (r.ok) {
          this.warnings = r.warnings ?? [];
          this.stats = r.stats ?? this.stats;
          this.error = null;
        } else {
          this.error = r.error ?? 'invalid design';
        }
      } catch (e) {
        this.error = (e as Error).message;
      }
    }, 300);
  }

  /** Write design.json, components.csv and pending glyph files (whichever changed). A spelling
   *  clash pauses Save: the font build would fail on it. `force` overwrites a file that changed on
   *  disk. Hosted: saves the draft instead (`force` keeps this one over one saved elsewhere). */
  async save(force = false): Promise<boolean> {
    if (!this.design || this.saving) return false;
    if (this.typingDirty) {
      const errs = this.typingErrors;
      if (errs.length) { this.paused = errs; return false; }
    }
    if (hosted.isHosted) return this.saveDraft(force);
    this.saving = true;
    try {
      // glyph files first: the design and spellings checks look for them
      for (const [n, t] of Object.entries(this.pendingSvgs)) {
        const r = t == null ? await api.deleteSvg(n) : await api.saveSvg(n, t, null, true);
        if (!r.ok) { this.error = `${n}.svg: ${r.error ?? 'save failed'}`; return false; }
        const { [n]: _, ...rest } = this.pendingSvgs;
        this.pendingSvgs = rest;
        const saved = { ...this.savedSvgs };
        if (t == null) delete saved[n]; else saved[n] = t;
        this.savedSvgs = saved;
        this.mainSvgs = saved;
      }
      if (this.designDirty) {
        const r = await api.saveDesign(this.design, force ? '' : this.diskHash);
        if (!r.ok) {
          if (r.conflict) { this.conflictFile = 'design.json'; this.conflict = r.error ?? 'conflict'; return false; }
          this.error = r.error ?? 'save failed';
          return false;
        }
        this.diskHash = r.hash ?? this.diskHash;
        this.savedJson = JSON.stringify(this.design);
        this.warnings = r.warnings ?? [];
        this.stats = r.stats ?? this.stats;
      }
      if (this.typingDirty) {
        const r = await api.saveGlyphs(T.toRecords(this.typing), force ? '' : this.csvHash, this.design);
        if (!r.ok) {
          if (r.conflict) { this.conflictFile = 'components.csv'; this.conflict = r.error ?? 'conflict'; return false; }
          if (r.errors?.length) { this.paused = r.errors; return false; }
          this.error = r.error ?? 'save failed';
          return false;
        }
        this.csvHash = r.hash ?? this.csvHash;
        this.savedTypingJson = JSON.stringify(this.typing);
        this.csvOrder = [...this.csvOrder, ...Object.keys(this.typing).filter((g) => !this.csvOrder.includes(g))];
      }
      this.changes = [];
      this.lastSaved = new Date();
      this.conflict = null;
      this.paused = null;
      this.persistDraft();
      return true;
    } finally {
      this.saving = false;
    }
  }

  /** The draft as a bundle (also what Export downloads): unsaved edits included. */
  bundle(note?: string): Bundle {
    const b = this.draftBase ?? {
      version: { commit: null, design_hash: this.diskHash, csv_hash: this.csvHash },
      design: JSON.parse(this.savedJson), typing: this.savedTyping, svgs: {}
    };
    return makeBundle({
      design: this.design!, typing: this.typing, svgs: this.svgs,
      baseDesign: b.design, baseTyping: b.typing,
      // glyphs the draft never touched ride the font: their base is the font's current file
      baseSvgs: { ...this.mainSvgs, ...b.svgs }, base: b.version,
      author: hosted.user ? { id: hosted.user.id, name: hosted.user.name || hosted.firstName } : {}, note
    });
  }

  /** Counts for "Your changes" (popover, Discard): against what the draft started from. */
  get draftCounts() {
    if (!this.design) return { glyphs: 0, spellings: 0, design: 0 };
    const b = this.bundle(), s = b.manifest.svgs;
    const units = (d: Design) => ({ center: d.center, glyph_weight: d.glyph_weight, test_sets: d.test_sets, ...Object.fromEntries(Object.entries(d.areas).map(([k, v]) => ['area:' + k, v])), ...Object.fromEntries(d.layouts.map((l) => ['layout:' + l.name, l])) } as Record<string, unknown>);
    const a = units(b.base.design), c = units(b.design);
    const design = [...new Set([...Object.keys(a), ...Object.keys(c)])].filter((k) => JSON.stringify(a[k]) !== JSON.stringify(c[k])).length;
    return { glyphs: s.added.length + s.changed.length + s.deleted.length, spellings: T.changedGlyphs(b.base.typing, b.typing).length, design };
  }

  private async saveDraft(force: boolean): Promise<boolean> {
    const c = hosted.client, uid = hosted.user?.id;
    if (!c || !uid || hosted.signedOut) return false;
    this.saving = true;
    try {
      const remote = await draftStamp(c, uid);
      if (!force && remote !== this.draftStamp) { this.savedElsewhere = remote ?? 'deleted'; return false; }
      const b = this.bundle();
      if (isEmptyBundle(b) && !remote) {
        this.draftStamp = null;
      } else {
        this.draftStamp = await saveDraft(c, uid, b);
      }
      this.savedJson = JSON.stringify(this.design);
      this.savedTypingJson = JSON.stringify(this.typing);
      this.savedSvgs = this.svgs;
      this.pendingSvgs = {};
      this.changes = [];
      this.lastSaved = new Date();
      this.offline = false;
      this.savedElsewhere = null;
      this.paused = null;
      this.persistDraft();
      return true;
    } catch (e) {
      this.offline = true;
      this.error = null;
      console.warn('draft save failed', e);
      this.persistDraft();
      return false;
    } finally {
      this.saving = false;
    }
  }

  /** "Saved elsewhere" → Load that version: drop the edits here, take the stored draft. */
  async takeStoredDraft() {
    this.savedElsewhere = null;
    try { localStorage.removeItem(this.draftKey); } catch {}
    await this.load();
  }

  /** Hosted: delete the stored draft and start again from the font. */
  async discardDraft() {
    const c = hosted.client, uid = hosted.user?.id;
    if (c && uid) await deleteDraft(c, uid).catch(() => {});
    try { localStorage.removeItem(this.draftKey); } catch {}
    this.draftStamp = null;
    await this.load();
  }

  /** The font's changes since the draft started, as items for "Update my draft" (merge.ts). */
  fontUpdate(): Item[] {
    if (!this.design || !this.mainDesign) return [];
    const b = this.bundle();
    return fontUpdateItems(
      { design: b.base.design, typing: b.base.typing, svgs: b.base.svgs },
      { design: this.mainDesign, typing: this.mainTyping, svgs: this.mainSvgs },
      { design: this.design, typing: this.typing, svgs: this.svgs }
    );
  }

  /** Bring the font's changes into the draft (kept items), rebase it on the font now, and save.
   *  One undo step. Returns how many of the font's changes came in and how many of mine were kept. */
  async updateToFont(items: Item[], keep: Record<string, boolean>, label: string) {
    if (!this.design || !this.mainDesign || !this.main) return { came: 0, kept: 0 };
    const m = applyMerge(items, keep, { design: this.design, typing: this.typing, svgs: this.svgs });
    this.applyChanges(label, {
      ...m,
      draftBase: {
        version: { commit: this.main.commit, date: this.main.date, design_hash: this.main.design_hash, csv_hash: this.main.csv_hash },
        design: this.mainDesign, typing: this.mainTyping, svgs: {}
      }
    });
    await this.save();
    return { came: m.applied.length, kept: items.filter((i) => i.conflict && !keep[i.id]).length };
  }

  /** What a build needs to make the draft's font (hosted), or nothing (local: the files). */
  buildInputs(): BuildInputs | undefined {
    if (!hosted.isHosted || !this.design) return undefined;
    const d = diffSvgs(this.mainSvgs, this.svgs);
    return {
      design: this.design, rows: T.toRecords(this.typing),
      svgs: Object.fromEntries([...d.added, ...d.changed].map((n) => [n, this.svgs[n]])), deleted: d.deleted
    };
  }

  async reloadFromDisk() {
    this.undoStack = [];
    this.redoStack = [];
    try { localStorage.removeItem(this.draftKey); } catch {}
    await this.load();
    this.draftRestored = false;
  }

  /** Import a design file: becomes unsaved changes. */
  importDesign(d: Design, label = 'Import design file') {
    this.edit(label, (cur) => {
      cur.center = d.center;
      cur.areas = d.areas;
      cur.layouts = d.layouts;
      if (d.test_sets) cur.test_sets = d.test_sets;
    });
  }

  areaLabel(area: string) {
    return this.design?.areas[area]?.label || area;
  }

  /** How many spacing exception rows name this glyph (any word type). */
  referenced(g: string): number {
    let n = 0;
    for (const l of this.design?.layouts ?? [])
      for (const r of l.relationships)
        if (Array.isArray(r.gap)) for (const e of r.gap) if (e.when_base?.includes(g) || e.when_elem?.includes(g)) n++;
    return n;
  }

  /** Recompute the glyph catalog's area membership from the design. */
  syncCatalog() {
    const map: Record<string, string[]> = {};
    for (const [n, a] of Object.entries(this.design?.areas ?? {})) for (const g of a.glyphs) (map[g] ??= []).push(n);
    this.glyphs = this.glyphs.map((r) => ({ ...r, areas: map[r.glyph] ?? [] }));
  }

  addToArea(area: string, glyphs: string[]) {
    const add = glyphs.filter((g) => !this.design?.areas[area]?.glyphs.includes(g));
    if (!add.length) return;
    this.edit(`Area ${area}: add ${add.length === 1 ? add[0] : add.length + ' glyphs'}`, (d) => { for (const g of add) d.areas[area].glyphs.push(g); });
    this.syncCatalog();
  }

  /** Remove a glyph from an area; returns false if the user declined. */
  removeFromArea(area: string, g: string): boolean {
    const n = this.referenced(g);
    if (n && !confirm(`${g} is named in ${n} spacing exception rows. Remove it from "${area}" anyway? Those rows keep the name but will never match.`)) return false;
    this.edit(`Area ${area}: remove ${g}`, (d) => { d.areas[area].glyphs = d.areas[area].glyphs.filter((x) => x !== g); });
    this.syncCatalog();
    return true;
  }
}

export const app = new DesignState();

/** Area label for a slot/element name in a layout ("string_top" -> String). */
export function elementArea(layout: { slots: { alternatives: string[][] }[] }, el: string): string | null {
  for (const s of layout.slots)
    for (const alt of s.alternatives)
      for (const t of alt) {
        const [name, area] = t.includes(':') ? t.split(':') : [t, t];
        if (name === el) return area;
      }
  return null;
}

export function parseElement(t: string): { name: string; area: string } {
  if (t.includes(':')) {
    const [name, area] = t.split(':');
    return { name: name.trim(), area: area.trim() };
  }
  return { name: t, area: t };
}
