// App state: the editable design and the spellings (components.csv), with one
// undo/redo history and one browser draft for both, the glyph catalog and SVG
// sources, and save/budget status. Save writes design.json and components.csv,
// each hash-checked; a spelling clash pauses Save (the build would fail).
import { api, type Design, type GlyphRow, type Stats } from './api';
import * as T from './typing';

const DRAFT_KEY = 'jzp-builder-draft';

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

  undoStack: { label: string; json: string; typing: string }[] = $state([]);
  redoStack: { label: string; json: string; typing: string }[] = $state([]);
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
  svgs = $state<Record<string, string>>({});
  /** Unsaved outlines from the glyph editor, shown in place of the file wherever glyphs render. */
  preview = $state<Record<string, string>>({});

  get designDirty() {
    return this.design !== null && JSON.stringify(this.design) !== this.savedJson;
  }
  get typingDirty() {
    return JSON.stringify(this.typing) !== this.savedTypingJson;
  }
  get dirty() {
    return this.designDirty || this.typingDirty;
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

  async load() {
    this.loading = true;
    try {
      const [d, g] = await Promise.all([api.design(), api.glyphs()]);
      this.diskHash = d.hash;
      this.savedJson = JSON.stringify(d.design);
      this.warnings = d.warnings;
      this.stats = d.stats;
      this.glyphs = g.glyphs.map((r) => ({ glyph: r.glyph, svg: r.svg, areas: r.areas, row: r.row }));
      const typing = T.fromCatalog(g.glyphs);
      this.savedTypingJson = JSON.stringify(typing);
      this.csvHash = g.hash;
      this.csvOrder = g.order;
      this.control = g.control;
      let draft: { hash: string; design: Design; changes: string[]; csvHash?: string; typing?: T.Typing } | null = null;
      try {
        const raw = localStorage.getItem(DRAFT_KEY);
        draft = raw ? JSON.parse(raw) : null;
      } catch {
        draft = null;
      }
      const draftTyping = draft?.typing && draft.csvHash === g.hash ? draft.typing : null;
      if (draft && draft.hash === d.hash && (JSON.stringify(draft.design) !== this.savedJson || (draftTyping && JSON.stringify(draftTyping) !== this.savedTypingJson))) {
        this.design = draft.design;
        this.typing = draftTyping ?? typing;
        this.changes = draft.changes ?? [];
        this.draftRestored = true;
      } else {
        this.design = d.design;
        this.typing = typing;
        this.changes = [];
      }
      this.error = null;
      api.svgs().then((s) => (this.svgs = s)).catch(() => {});
    } catch (e) {
      this.error = `Can't reach the dev server. Run: cd src-fonttools && python3 -m jzpbuild.devserver  (${(e as Error).message})`;
    } finally {
      this.loading = false;
    }
  }

  /** Apply an edit: `fn` mutates a working copy; one undo step. */
  edit(label: string, fn: (d: Design) => void) {
    if (!this.design) return;
    const before = JSON.stringify(this.design);
    const next = clone(this.design);
    fn(next);
    const after = JSON.stringify(next);
    if (after === before) return;
    this.undoStack = [...this.undoStack.slice(-199), { label, json: before, typing: JSON.stringify(this.typing) }];
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
    this.undoStack = [...this.undoStack.slice(-199), { label, json: JSON.stringify(this.design), typing: before }];
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

  undo() {
    const step = this.undoStack.at(-1);
    if (!step || !this.design) return;
    this.undoStack = this.undoStack.slice(0, -1);
    this.redoStack = [...this.redoStack, { label: step.label, json: JSON.stringify(this.design), typing: JSON.stringify(this.typing) }];
    this.design = JSON.parse(step.json);
    this.typing = JSON.parse(step.typing);
    this.changes = this.changes.slice(0, -1);
    this.paused = null;
    this.persistDraft();
    this.recheck();
  }

  redo() {
    const step = this.redoStack.at(-1);
    if (!step || !this.design) return;
    this.redoStack = this.redoStack.slice(0, -1);
    this.undoStack = [...this.undoStack, { label: step.label, json: JSON.stringify(this.design), typing: JSON.stringify(this.typing) }];
    this.design = JSON.parse(step.json);
    this.typing = JSON.parse(step.typing);
    this.changes = [...this.changes, step.label];
    this.persistDraft();
    this.recheck();
  }

  discard() {
    this.design = JSON.parse(this.savedJson);
    this.typing = JSON.parse(this.savedTypingJson);
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
        localStorage.setItem(DRAFT_KEY, JSON.stringify({ hash: this.diskHash, design: this.design, changes: this.changes, csvHash: this.csvHash, typing: this.typing }));
      } else {
        localStorage.removeItem(DRAFT_KEY);
      }
    } catch {
      /* private mode etc. */
    }
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

  /** Write design.json and components.csv (whichever changed). A spelling clash pauses Save:
   *  the font build would fail on it. `force` overwrites a file that changed on disk. */
  async save(force = false): Promise<boolean> {
    if (!this.design) return false;
    if (this.typingDirty) {
      const errs = this.typingErrors;
      if (errs.length) { this.paused = errs; return false; }
    }
    this.saving = true;
    try {
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

  async reloadFromDisk() {
    this.undoStack = [];
    this.redoStack = [];
    localStorage.removeItem(DRAFT_KEY);
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
