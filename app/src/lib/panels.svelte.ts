// Dockable panels of the Layouts screen: which dock each panel sits in, its
// order, folded state, dock sizes and hidden docks. Two arrangements (wide /
// narrow windows), kept in localStorage; never part of the design.

export type PanelId = 'types' | 'structure' | 'pagecenter' | 'budget' | 'spacing' | 'centering' | 'glyphs' | 'tester';
export type Dock = 'left' | 'right' | 'bottom';
export const PANEL_IDS: PanelId[] = ['types', 'structure', 'pagecenter', 'budget', 'spacing', 'centering', 'glyphs', 'tester'];
export const DOCKS: Dock[] = ['left', 'right', 'bottom'];
export const DOCK_LABEL: Record<Dock, string> = { left: 'left column', right: 'right column', bottom: 'bottom strip' };

export type Arrangement = {
  docks: Record<Dock, PanelId[]>;
  folded: Partial<Record<PanelId, boolean>>;
  size: Record<Dock, number>;             // column width (px) or strip height (px)
  hidden: Partial<Record<Dock, boolean>>; // dragged shut by the user
};
type Mode = 'wide' | 'narrow';
const KEY = 'jzp-panels-v1';
export const WIDE_MIN = 1280;
export const DOCK_MIN: Record<Dock, number> = { left: 160, right: 160, bottom: 60 };
export const DOCK_HIDE_BELOW: Record<Dock, number> = { left: 110, right: 110, bottom: 40 };

const DEFAULTS: Record<Mode, Arrangement> = {
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

function sane(a: Partial<Arrangement> | null, mode: Mode): Arrangement {
  const d = clone(DEFAULTS[mode]);
  if (!a || !a.docks) return d;
  const seen = new Set<PanelId>();
  const docks: Record<Dock, PanelId[]> = { left: [], right: [], bottom: [] };
  for (const dock of DOCKS) for (const id of a.docks[dock] ?? []) if (PANEL_IDS.includes(id) && !seen.has(id)) { docks[dock].push(id); seen.add(id); }
  for (const dock of DOCKS) for (const id of d.docks[dock]) if (!seen.has(id)) { docks[dock].push(id); seen.add(id); }
  return { docks, folded: { ...(a.folded ?? {}) }, size: { ...d.size, ...(a.size ?? {}) }, hidden: { ...(a.hidden ?? {}) } };
}

class Panels {
  mode = $state<Mode>('wide');
  arr = $state<Record<Mode, Arrangement>>(clone(DEFAULTS));
  dragging = $state<PanelId | null>(null);
  over = $state<{ dock: Dock; index: number } | null>(null);
  pointer = $state({ x: 0, y: 0 });
  loaded = false;

  get a(): Arrangement { return this.arr[this.mode]; }

  load() {
    if (this.loaded) return;
    this.loaded = true;
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) { const j = JSON.parse(raw); this.arr = { wide: sane(j.wide, 'wide'), narrow: sane(j.narrow, 'narrow') }; }
    } catch { /* ignore */ }
    this.syncMode();
  }
  syncMode() { this.mode = window.innerWidth >= WIDE_MIN ? 'wide' : 'narrow'; }
  persist() { try { localStorage.setItem(KEY, JSON.stringify($state.snapshot(this.arr))); } catch { /* ignore */ } }
  get isDefault() { return JSON.stringify($state.snapshot(this.arr)) === JSON.stringify(DEFAULTS); }
  reset() { this.arr = clone(DEFAULTS); this.persist(); }

  dockOf(id: PanelId): Dock { return DOCKS.find((d) => this.a.docks[d].includes(id)) ?? 'right'; }
  isFolded(id: PanelId) { return !!this.a.folded[id]; }
  setFolded(id: PanelId, v: boolean) { this.a.folded[id] = v; this.persist(); }
  toggle(id: PanelId) { this.setFolded(id, !this.isFolded(id)); }
  /** Move a panel to `dock` at `index` (index counted in the target list before removal). */
  move(id: PanelId, dock: Dock, index: number) {
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
  nudge(id: PanelId, dir: -1 | 1) {
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
  show(dock: Dock) { this.a.hidden[dock] = false; if (this.a.size[dock] < DOCK_MIN[dock]) this.a.size[dock] = DEFAULTS[this.mode].size[dock]; this.persist(); }
  hide(dock: Dock) { this.a.hidden[dock] = true; this.persist(); }
  /** A dock shows as a column/strip when it has panels and is not hidden. */
  visible(dock: Dock) { return this.a.docks[dock].length > 0 && !this.a.hidden[dock]; }
}

export const panels = new Panels();
