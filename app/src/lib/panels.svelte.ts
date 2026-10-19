// Dockable panels: which dock each panel sits in, its order, folded state, dock
// sizes and hidden docks. Two arrangements (wide / narrow windows), kept in
// localStorage; never part of the design. One store per screen: `panels` for
// Layouts, `editorPanels` for the glyph editor.

export type PanelId = 'types' | 'structure' | 'pagecenter' | 'budget' | 'spacing' | 'centering' | 'glyphs' | 'tester';
export type EditorPanelId = 'trace' | 'selection' | 'compare' | 'glyph' | 'typing' | 'tryit' | 'checks' | 'tester';
export type Dock = 'left' | 'right' | 'bottom';
export const PANEL_IDS: PanelId[] = ['types', 'structure', 'pagecenter', 'budget', 'spacing', 'centering', 'glyphs', 'tester'];
export const EDITOR_PANEL_IDS: EditorPanelId[] = ['trace', 'selection', 'compare', 'glyph', 'typing', 'tryit', 'checks', 'tester'];
export const DOCKS: Dock[] = ['left', 'right', 'bottom'];
/** What a screen tells the panel frame about one panel. `hidden`: nothing to show right now, takes no room. */
export type Meta = { title: string; badge?: string | number | null; warn?: boolean; summary?: string; tag?: string; hidden?: boolean };
export const DOCK_LABEL: Record<Dock, string> = { left: 'left column', right: 'right column', bottom: 'bottom strip' };

export type Arrangement<Id extends string = string> = {
  docks: Record<Dock, Id[]>;
  folded: Partial<Record<Id, boolean>>;
  size: Record<Dock, number>;             // column width (px) or strip height (px)
  hidden: Partial<Record<Dock, boolean>>; // dragged shut by the user
};
type Mode = 'wide' | 'narrow';
export type Defaults<Id extends string> = Record<Mode, Arrangement<Id>>;
export const WIDE_MIN = 1280;
export const DOCK_MIN: Record<Dock, number> = { left: 160, right: 160, bottom: 60 };
export const DOCK_HIDE_BELOW: Record<Dock, number> = { left: 110, right: 110, bottom: 40 };

const LAYOUTS_DEFAULTS: Defaults<PanelId> = {
  wide: {
    docks: { left: ['types', 'structure', 'pagecenter', 'budget'], right: ['spacing', 'centering'], bottom: ['glyphs', 'tester'] },
    folded: { pagecenter: true, budget: true, centering: true },
    size: { left: 280, right: 420, bottom: 230 },
    hidden: {}
  },
  narrow: {
    docks: { left: [], right: ['types', 'structure', 'pagecenter', 'budget', 'spacing', 'centering'], bottom: ['glyphs', 'tester'] },
    folded: { types: true, structure: true, pagecenter: true, budget: true, centering: true, tester: true },
    size: { left: 260, right: 380, bottom: 200 },
    hidden: {}
  }
};
const clone = <T>(x: T): T => JSON.parse(JSON.stringify(x));

function sane<Id extends string>(a: Partial<Arrangement<Id>> | null, d0: Arrangement<Id>, ids: readonly Id[]): Arrangement<Id> {
  const d = clone(d0);
  if (!a || !a.docks) return d;
  const seen = new Set<Id>();
  const docks: Record<Dock, Id[]> = { left: [], right: [], bottom: [] };
  for (const dock of DOCKS) for (const id of a.docks[dock] ?? []) if (ids.includes(id) && !seen.has(id)) { docks[dock].push(id); seen.add(id); }
  for (const dock of DOCKS) for (const id of d.docks[dock]) if (!seen.has(id)) { docks[dock].push(id); seen.add(id); }
  return { docks, folded: { ...(a.folded ?? {}) }, size: { ...d.size, ...(a.size ?? {}) }, hidden: { ...(a.hidden ?? {}) } };
}

export class PanelStore<Id extends string> {
  readonly key: string;
  readonly ids: readonly Id[];
  readonly defaults: Defaults<Id>;
  mode = $state<Mode>('wide');
  arr = $state<Record<Mode, Arrangement<Id>>>() as Record<Mode, Arrangement<Id>>;
  dragging = $state<Id | null>(null);
  over = $state<{ dock: Dock; index: number } | null>(null);
  pointer = $state({ x: 0, y: 0 });
  loaded = false;

  constructor(key: string, ids: readonly Id[], defaults: Defaults<Id>) {
    this.key = key; this.ids = ids; this.defaults = defaults;
    this.arr = clone(defaults);
  }

  get a(): Arrangement<Id> { return this.arr[this.mode]; }

  load() {
    if (this.loaded) return;
    this.loaded = true;
    try {
      const raw = localStorage.getItem(this.key);
      if (raw) { const j = JSON.parse(raw); this.arr = { wide: sane(j.wide, this.defaults.wide, this.ids), narrow: sane(j.narrow, this.defaults.narrow, this.ids) }; }
    } catch { /* ignore */ }
    this.syncMode();
  }
  syncMode() { this.mode = window.innerWidth >= WIDE_MIN ? 'wide' : 'narrow'; }
  persist() { try { localStorage.setItem(this.key, JSON.stringify($state.snapshot(this.arr))); } catch { /* ignore */ } }
  get isDefault() { return JSON.stringify($state.snapshot(this.arr)) === JSON.stringify(this.defaults); }
  reset() { this.arr = clone(this.defaults); this.persist(); }

  dockOf(id: Id): Dock { return DOCKS.find((d) => this.a.docks[d].includes(id)) ?? 'right'; }
  isFolded(id: Id) { return !!this.a.folded[id]; }
  setFolded(id: Id, v: boolean) { this.a.folded[id] = v; this.persist(); }
  toggle(id: Id) { this.setFolded(id, !this.isFolded(id)); }
  /** Move a panel to `dock` at `index` (index counted in the target list before removal). */
  move(id: Id, dock: Dock, index: number) {
    const from = this.dockOf(id);
    const src = this.a.docks[from];
    const i = src.indexOf(id);
    if (i >= 0) src.splice(i, 1);
    const dst = this.a.docks[dock];
    let at = index;
    if (from === dock && i >= 0 && i < index) at = index - 1;
    dst.splice(Math.max(0, Math.min(at, dst.length)), 0, id);
    this.a.hidden[dock] = false;
    this.persist();
  }
  nudge(id: Id, dir: -1 | 1) {
    const dock = this.dockOf(id), list = this.a.docks[dock], i = list.indexOf(id), j = i + dir;
    if (j < 0 || j >= list.length) return;
    [list[i], list[j]] = [list[j], list[i]];
    this.persist();
  }
  /** Resize a dock; dragging it below the hide threshold hides it and keeps `restore` as its size for when it is shown again. */
  setSize(dock: Dock, px: number, restore: number | null = null) {
    if (px < DOCK_HIDE_BELOW[dock]) { this.a.hidden[dock] = true; if (restore != null && restore >= DOCK_MIN[dock]) this.a.size[dock] = restore; }
    else { this.a.hidden[dock] = false; this.a.size[dock] = Math.round(Math.max(DOCK_MIN[dock], px)); }
    this.persist();
  }
  show(dock: Dock) { this.a.hidden[dock] = false; if (this.a.size[dock] < DOCK_MIN[dock]) this.a.size[dock] = this.defaults[this.mode].size[dock]; this.persist(); }
  hide(dock: Dock) { this.a.hidden[dock] = true; this.persist(); }
  /** A dock shows as a column/strip when it has panels and is not hidden. */
  visible(dock: Dock) { return this.a.docks[dock].length > 0 && !this.a.hidden[dock]; }
}

export const panels = new PanelStore<PanelId>('jzp-panels-v1', PANEL_IDS, LAYOUTS_DEFAULTS);

const EDITOR_DEFAULTS: Defaults<EditorPanelId> = {
  wide: {
    docks: { left: [], right: ['trace', 'selection', 'compare', 'glyph', 'typing', 'checks'], bottom: ['tester', 'tryit'] },
    folded: { checks: true },
    size: { left: 300, right: 320, bottom: 210 },
    hidden: {}
  },
  narrow: {
    docks: { left: [], right: ['trace', 'selection', 'compare', 'glyph', 'typing', 'checks'], bottom: ['tester', 'tryit'] },
    folded: { compare: true, glyph: true, typing: true, checks: true, tryit: true },
    size: { left: 260, right: 300, bottom: 180 },
    hidden: {}
  }
};
export const editorPanels = new PanelStore<EditorPanelId>('jzp-editor-panels-v1', EDITOR_PANEL_IDS, EDITOR_DEFAULTS);

/** Any screen's store, as the shared panel components see it. */
export type AnyPanels = PanelStore<string>;
