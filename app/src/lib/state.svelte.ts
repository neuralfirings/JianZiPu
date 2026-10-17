// App state: the editable design (with undo/redo and a browser draft),
// the glyph catalog and SVG sources, and save/budget status.
import { api, type Design, type GlyphRow, type Stats } from './api';

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

  undoStack: { label: string; json: string }[] = $state([]);
  redoStack: { label: string; json: string }[] = $state([]);
  changes = $state<string[]>([]);

  glyphs = $state<GlyphRow[]>([]);
  svgs = $state<Record<string, string>>({});

  get dirty() {
    return this.design !== null && JSON.stringify(this.design) !== this.savedJson;
  }

  async load() {
    this.loading = true;
    try {
      const [d, g] = await Promise.all([api.design(), api.glyphs()]);
      this.diskHash = d.hash;
      this.savedJson = JSON.stringify(d.design);
      this.warnings = d.warnings;
      this.stats = d.stats;
      this.glyphs = g.glyphs;
      let draft: { hash: string; design: Design; changes: string[] } | null = null;
      try {
        const raw = localStorage.getItem(DRAFT_KEY);
        draft = raw ? JSON.parse(raw) : null;
      } catch {
        draft = null;
      }
      if (draft && draft.hash === d.hash && JSON.stringify(draft.design) !== this.savedJson) {
        this.design = draft.design;
        this.changes = draft.changes ?? [];
        this.draftRestored = true;
      } else {
        this.design = d.design;
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
    this.undoStack = [...this.undoStack.slice(-199), { label, json: before }];
    this.redoStack = [];
    this.design = next;
    this.changes = [...this.changes, label];
    this.persistDraft();
    this.recheck();
  }

  undo() {
    const step = this.undoStack.at(-1);
    if (!step || !this.design) return;
    this.undoStack = this.undoStack.slice(0, -1);
    this.redoStack = [...this.redoStack, { label: step.label, json: JSON.stringify(this.design) }];
    this.design = JSON.parse(step.json);
    this.changes = this.changes.slice(0, -1);
    this.persistDraft();
    this.recheck();
  }

  redo() {
    const step = this.redoStack.at(-1);
    if (!step || !this.design) return;
    this.redoStack = this.redoStack.slice(0, -1);
    this.undoStack = [...this.undoStack, { label: step.label, json: JSON.stringify(this.design) }];
    this.design = JSON.parse(step.json);
    this.changes = [...this.changes, step.label];
    this.persistDraft();
    this.recheck();
  }

  discard() {
    this.design = JSON.parse(this.savedJson);
    this.changes = [];
    this.undoStack = [];
    this.redoStack = [];
    this.persistDraft();
    this.recheck();
  }

  persistDraft() {
    try {
      if (this.dirty) {
        localStorage.setItem(DRAFT_KEY, JSON.stringify({ hash: this.diskHash, design: this.design, changes: this.changes }));
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

  async save(force = false): Promise<boolean> {
    if (!this.design) return false;
    this.saving = true;
    try {
      const r = await api.saveDesign(this.design, force ? '' : this.diskHash);
      if (!r.ok) {
        if (r.conflict) {
          this.conflict = r.error ?? 'conflict';
          return false;
        }
        this.error = r.error ?? 'save failed';
        return false;
      }
      this.diskHash = r.hash ?? this.diskHash;
      this.savedJson = JSON.stringify(this.design);
      this.warnings = r.warnings ?? [];
      this.stats = r.stats ?? this.stats;
      this.changes = [];
      this.lastSaved = new Date();
      this.conflict = null;
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
