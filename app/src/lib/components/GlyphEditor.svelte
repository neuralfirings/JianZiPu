<script lang="ts">
  import * as TY from '$lib/typing';
  // The glyph editor screen (docs/GLYPH-EDITOR-UX.md): glyph bar, tool rail, action bar,
  // canvas and status line in the center; everything else in dockable panels (Selection,
  // Compare, Glyph, Typing, Try it, Checks, Tester, Trace while tracing) arranged like the
  // Layouts screen's, kept per browser. Owns ⌘Z/⌘S while mounted.
  import { onMount } from 'svelte';
  import { beforeNavigate, goto } from '$app/navigation';
  import { app } from '$lib/state.svelte';
  import { hosted } from '$lib/hosted.svelte';
  import { glyphEditor as ed } from '$lib/glyphed/editor.svelte';
  import type { Mode } from '$lib/glyphed/tools';
  import * as I from '$lib/icons';
  import Glyph from './Glyph.svelte';
  import GlyphPopover from './GlyphPopover.svelte';
  import PanelWorkspace from './PanelWorkspace.svelte';
  import GlyphFacts from './GlyphFacts.svelte';
  import TypingFields from './TypingFields.svelte';
  import TryIt from './TryIt.svelte';
  import WordTester from './WordTester.svelte';
  import { editorPanels, type EditorPanelId, type Meta } from '$lib/panels.svelte';
  import { EDITOR_HELP } from '$lib/help';

  let { name, isNew = false, area = null, from = null, back = null }: {
    name: string; isNew?: boolean; area?: string | null; from?: 'file' | 'image' | null;
    /** Where "←" returns to (an app path, e.g. the Layouts screen it was opened from). */
    back?: string | null;
  } = $props();
  let backHref = $derived(back && /^\/(?!\/)/.test(back) ? back : `/glyphs?g=${encodeURIComponent(name)}`);
  let backLabel = $derived(backHref.startsWith('/layouts') ? 'Layouts' : 'Glyphs');
  let canvas: HTMLCanvasElement;
  let wrap: HTMLDivElement;
  let svgInput: HTMLInputElement;
  let imgInput: HTMLInputElement;

  // ui state
  let popover = $state<null | 'simplify' | 'thicken' | 'import'>(null);
  let simplifyTol = $state(2);
  let thickTotal = $state(4);
  let thickSharp = $state(false);
  let ghostPick = $state<{ x: number; y: number } | null>(null);
  let leave = $state<null | { to: string }>(null);
  let importAsk = $state<null | { text: string; box: [number, number] | null; dropped: string[]; strokes: number; fit: boolean; replace: boolean }>(null);
  let shortcuts = $state(false);
  let toast = $state<string | null>(null);
  let starting = $state<'file' | 'image' | null>(from);
  let toastTimer: ReturnType<typeof setTimeout> | null = null;
  function say(t: string) { toast = t; if (toastTimer) clearTimeout(toastTimer); toastTimer = setTimeout(() => (toast = null), 4000); }

  let row = $derived(app.glyphs.find((g) => g.glyph === name) ?? null);
  let typedAs = $derived(TY.TYPED.map((f) => TY.shown(app.typing, name, f).value).filter(Boolean).join(' · '));
  let areaName = $derived(isNew && area ? area : (Object.entries(app.design?.areas ?? {}).find(([, a]) => a.glyphs.includes(name))?.[0] ?? row?.areas[0] ?? null));
  let areaObj = $derived(areaName ? app.design?.areas[areaName] ?? null : null);
  let sameArea = $derived((areaObj?.glyphs ?? []).filter((g) => g !== name && app.svgs[g]).slice(0, 8));
  let ghostGlyphs = $derived(app.glyphs.filter((g) => g.svg && g.glyph !== name).map((g) => g.glyph));
  let sel = $derived(ed.selection);
  let canCombine = $derived(ed.preview?.kind === 'combine' || (sel.kind === 'shapes' && sel.n >= 2));

  // ---- panels: header of each (the frame is PanelWorkspace, the bodies the `body` snippet)
  let glyphErrors = $derived(app.typingErrors.filter((e) => (e.kind === 'clash' ? e.glyphs.includes(name) : e.glyph === name)).length);
  let checkWarnings = $derived((ed.stats.paths === 0 ? 1 : 0) + (ed.stats.outside ? 1 : 0) + (ed.stats.open ? 1 : 0) + (ed.stats.specks ? 1 : 0));
  function meta(id: EditorPanelId): Meta {
    switch (id) {
      case 'trace': return { title: ed.trace ? `Trace ${ed.trace.file.name}` : 'Trace', hidden: !ed.trace, summary: ed.trace ? `${ed.trace.img.width} × ${ed.trace.img.height}px` : '' };
      case 'selection': return { title: 'Selection', summary: sel.kind === 'points' ? `${sel.n} point${sel.n === 1 ? '' : 's'}` : sel.kind === 'shapes' ? `${sel.n} shape${sel.n === 1 ? '' : 's'}` : sel.kind === 'overlay' ? 'compare overlay' : `${ed.stats.paths} shapes · ${ed.stats.nodes} points` };
      case 'compare': return { title: 'Compare', summary: [ed.dot && 'dot', ed.ghostName, ed.ghostSaved && 'last saved'].filter(Boolean).join(' · ') || 'off' };
      case 'glyph': return { title: 'Glyph', summary: `${areaName ? app.areaLabel(areaName) : 'no area'} · ${ed.box[0]} × ${ed.box[1]}` };
      case 'typing': return { title: 'Typing', badge: glyphErrors || null, warn: !!glyphErrors, summary: typedAs || 'no spelling yet' };
      case 'tryit': return { title: 'Try it', summary: 'live, saved or not' };
      case 'checks': return { title: 'Checks', badge: checkWarnings || null, warn: !!checkWarnings, summary: checkWarnings ? `${checkWarnings} to look at` : 'all fine' };
      case 'tester': return { title: 'Tester', summary: 'words with this glyph' };
    }
  }
  // tracing opens the Trace panel, wherever it sits
  $effect(() => {
    if (!ed.trace) return;
    if (editorPanels.isFolded('trace')) editorPanels.setFolded('trace', false);
    const dock = editorPanels.dockOf('trace');
    if (editorPanels.a.hidden[dock]) editorPanels.show(dock);
  });

  function boxFor(): [number, number] {
    const d = app.design!;
    const a = areaName ? d.areas[areaName] : Object.values(d.areas).find((x) => x.glyphs.includes(name));
    return a ? [a.size[0], a.size[1]] : [350, 350];
  }

  onMount(() => {
    const ro = new ResizeObserver(() => { const r = wrap.getBoundingClientRect(); ed.resize(r.width, r.height); });
    ro.observe(wrap);
    const r = wrap.getBoundingClientRect();
    canvas.width = r.width; canvas.height = r.height;
    ed.mount(canvas, name, isNew ? null : app.svgs[name] ?? null, boxFor(), { isNew, area }).then(() => {
      ed.resize(r.width, r.height); ed.fit();
      const ps = ed.pendingStart; ed.pendingStart = null;
      if (ps?.kind === 'svg') ps.file.text().then((t) => askImport(t));
      else if (ps?.kind === 'image') void trace(ps.file);
    });
    const onKey = (e: KeyboardEvent) => key(e);
    const onKeyUp = (e: KeyboardEvent) => { if (e.code === 'Space') ed.holdHand(false); };
    const onUnload = (e: BeforeUnloadEvent) => { if (ed.dirty) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('keydown', onKey); window.addEventListener('keyup', onKeyUp); window.addEventListener('beforeunload', onUnload);
    return () => { ro.disconnect(); window.removeEventListener('keydown', onKey); window.removeEventListener('keyup', onKeyUp); window.removeEventListener('beforeunload', onUnload); ed.unmount(); };
  });
  // the SVG texts load after the design: pick ours up when it arrives
  $effect(() => {
    const text = app.svgs[name];
    if (!isNew && text && ed.scene && ed.savedText == null && !ed.dirty) ed.setSource(text);
  });
  // a new glyph opens with a sibling from its area ghosted, once the SVG texts are in
  let ghosted = false;
  $effect(() => {
    const sib = sameArea[0];
    if (isNew && sib && ed.scene && !ghosted && !ed.ghostName) { ghosted = true; ed.setGhost(sib); }
  });
  beforeNavigate((nav) => {
    if (!ed.dirty || leaving) return;
    nav.cancel();
    leave = { to: nav.to?.url.pathname + (nav.to?.url.search ?? '') };
  });
  let leaving = false;
  async function doLeave(how: 'discard' | 'save') {
    if (!leave) return;
    if (how === 'save') { const r = await ed.save(); if (!r.ok) { if (!r.conflict) say(r.error ?? 'could not save'); return; } }
    else ed.dropDraft();
    leaving = true; const to = leave.to; leave = null;
    goto(to);
  }

  function typing(e: KeyboardEvent) { const t = e.target as HTMLElement | null; return !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable); }
  function key(e: KeyboardEvent) {
    if (leave || importAsk || ed.conflictDisk != null) return;
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key.toLowerCase() === 's') { e.preventDefault(); save(); return; }
    if (typing(e)) return;
    if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); if (e.shiftKey) ed.redo(); else ed.undo(); return; }
    if (mod && e.key.toLowerCase() === 'a') { e.preventDefault(); ed.selectAll(); return; }
    if (mod && e.altKey && e.key.toLowerCase() === 'o') { e.preventDefault(); ed.outlineLines(); return; }
    if (e.altKey && e.shiftKey) {
      const op = ({ u: 'unite', s: 'subtract', i: 'intersect', e: 'exclude' } as const)[e.key.toLowerCase()];
      if (op && canCombine) { e.preventDefault(); ed.previewCombine(op, false); ed.applyPreview(); return; }
    }
    if (mod) return;
    if (ed.trace) { if (e.key === 'Escape') ed.endTrace(); return; }
    switch (e.key) {
      case 'Escape': if (popover) cancelPopover(); else if (ghostPick) ghostPick = null; else if (ed.drawing) ed.finishPen(); else ed.clearSelection(); return;
      case 'Enter': if (popover) applyPopover(); else if (ed.drawing) ed.finishPen(); return;
      case 'Delete': case 'Backspace': e.preventDefault(); ed.deleteSelection(); return;
      case 'ArrowLeft': e.preventDefault(); ed.nudge(e.shiftKey ? -10 : -1, 0); return;
      case 'ArrowRight': e.preventDefault(); ed.nudge(e.shiftKey ? 10 : 1, 0); return;
      case 'ArrowUp': e.preventDefault(); ed.nudge(0, e.shiftKey ? -10 : -1); return;
      case 'ArrowDown': e.preventDefault(); ed.nudge(0, e.shiftKey ? 10 : 1); return;
      case ' ': e.preventDefault(); ed.holdHand(true); return;
      case '?': shortcuts = !shortcuts; return;
    }
    if (e.shiftKey) {
      switch (e.key) {
        case '!': case '1': ed.fit(); return;
        case ')': case '0': ed.zoom100(); return;
        case '@': case '2': ed.fitSelection(); return;
        case 'H': ed.flip('h'); return;
        case 'V': ed.flip('v'); return;
        case 'P': ed.setMode('pencil'); return;
        case 'G': ed.setGrid(!ed.grid); return;
      }
      return;
    }
    const modes: Record<string, Mode> = { v: 'select', p: 'pen', r: 'rect', o: 'ellipse', h: 'hand', z: 'zoom', a: 'select' };
    if (modes[e.key]) { ed.setMode(modes[e.key]); return; }
    if (e.key === 'd') ed.setDot(!ed.dot);
    else if (e.key === 'l') ed.setGhostSaved(!ed.ghostSaved);
    else if (e.key === 'g') ghostPick = ghostPick ? null : { x: window.innerWidth - 300, y: 120 };
  }

  // ---- popover ops (live preview, Apply = one undo step)
  function openPopover(p: 'simplify' | 'thicken') {
    if (popover) cancelPopover();
    popover = p;
    if (p === 'simplify') ed.previewSimplify(simplifyTol); else ed.previewThicken(thickTotal, thickSharp);
  }
  function applyPopover() { if (ed.preview) ed.applyPreview(); popover = null; }
  function cancelPopover() { ed.cancelPreview(); popover = null; }
  let hoverOp = $state<string | null>(null);
  function combineHover(op: 'unite' | 'subtract' | 'intersect' | 'exclude', e: MouseEvent) { if (!canCombine) return; hoverOp = op; ed.previewCombine(op, e.shiftKey); }
  function combineLeave() { if (hoverOp) { ed.cancelPreview(); hoverOp = null; } }
  function combineClick(op: 'unite' | 'subtract' | 'intersect' | 'exclude', e: MouseEvent) { if (!canCombine) return; ed.previewCombine(op, e.shiftKey); ed.applyPreview(); hoverOp = null; }

  // ---- import
  function askImport(text: string) {
    const info = ed.inspectSvg(text);
    const differs = !!info.box && (Math.abs(info.box[0] - ed.box[0]) > 0.5 || Math.abs(info.box[1] - ed.box[1]) > 0.5);
    const hasPaths = ed.stats.paths > 0;
    if (!differs && !info.dropped.length && !info.strokes && !hasPaths) { ed.importSvg(text, { fit: false, replace: false }); return; }
    importAsk = { text, box: info.box, dropped: info.dropped, strokes: info.strokes, fit: differs, replace: hasPaths && from === 'file' };
  }
  async function onSvgFile(e: Event) { const f = (e.target as HTMLInputElement).files?.[0]; (e.target as HTMLInputElement).value = ''; starting = null; if (f) askImport(await f.text()); }
  async function trace(f: File) { if (!(await ed.startTrace(f)) && ed.error) say(ed.error); }
  async function onImgFile(e: Event) { const f = (e.target as HTMLInputElement).files?.[0]; (e.target as HTMLInputElement).value = ''; starting = null; if (f) void trace(f); }
  async function onDrop(e: DragEvent) {
    e.preventDefault();
    const f = e.dataTransfer?.files?.[0]; if (!f) return;
    if (f.type === 'image/svg+xml' || f.name.endsWith('.svg')) askImport(await f.text()); else if (f.type.startsWith('image/')) void trace(f);
  }
  async function onPaste(e: ClipboardEvent) {
    if (typing(e as unknown as KeyboardEvent)) return;
    const t = e.clipboardData?.getData('text') ?? '';
    if (/<svg[\s>]/.test(t)) { e.preventDefault(); askImport(t); }
  }

  // ---- save
  async function save(overwrite = false) {
    const r = await ed.save(overwrite);
    if (r.ok) {
      if (r.waiting) say(`${name} is in your draft, not saved yet: ${r.waiting}. It's kept in this browser meanwhile.`);
      else if (r.draft) say(`Saved ${name} to your draft · Layouts and the Tester use it now; the font needs a Build.`);
      else say(`Saved inputs/svg/${name}.svg · Layouts and the Tester use it now; the font needs a Build.`);
      if (isNew) { isNew = false; goto(`/glyphs/${encodeURIComponent(name)}/edit`, { replaceState: true }); }
    } else if (r.exists) say(`${name}.svg already exists on disk.`);
    else if (!r.conflict) say(r.error ?? 'could not save');
  }
  function autoThreshold() {
    const t = ed.trace; if (!t) return;
    const c = document.createElement('canvas'); const s = Math.min(1, 200 / Math.max(t.img.width, t.img.height));
    c.width = Math.max(1, Math.round(t.img.width * s)); c.height = Math.max(1, Math.round(t.img.height * s));
    const ctx = c.getContext('2d')!; ctx.drawImage(t.img, 0, 0, c.width, c.height);
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    const hist = new Array(256).fill(0);
    for (let i = 0; i < d.length; i += 4) hist[Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2])]++;
    // Otsu
    const total = c.width * c.height; let sum = 0; for (let i = 0; i < 256; i++) sum += i * hist[i];
    let sumB = 0, wB = 0, best = 0, thr = 128;
    for (let i = 0; i < 256; i++) { wB += hist[i]; if (!wB) continue; const wF = total - wB; if (!wF) break; sumB += i * hist[i]; const mB = sumB / wB, mF = (sum - sumB) / wF; const v = wB * wF * (mB - mF) ** 2; if (v > best) { best = v; thr = i; } }
    ed.updateTrace({ threshold: thr });
  }
  const r1 = (v: number) => Math.round(v * 10) / 10;
  const num = (e: Event) => +(e.target as HTMLInputElement).value;
  const TOOLS: [Mode, string, string][] = [['select', 'V', 'Select'], ['pen', 'P', 'Pen'], ['pencil', '⇧P', 'Pencil'], ['rect', 'R', 'Rectangle'], ['ellipse', 'O', 'Ellipse'], ['hand', 'H', 'Hand'], ['zoom', 'Z', 'Zoom']];
  const ICON = { select: I.ToolSelect, pen: I.ToolPen, pencil: I.ToolPencil, rect: I.ToolRect, ellipse: I.ToolEllipse, hand: I.ToolHand, zoom: I.ToolZoom } satisfies Record<Mode, unknown>;
</script>

{#snippet body(id: EditorPanelId)}
  <div class="sec">
  {#if id === 'trace' && ed.trace}
    {@const t = ed.trace}
    <label class="f"><span>Threshold</span><input type="range" min="0" max="255" value={t.opts.threshold} oninput={(e) => ed.updateTrace({ threshold: num(e) })} /><span class="mono">{t.opts.threshold}</span><button class="sm" onclick={autoThreshold}>Auto</button></label>
    <label class="f"><span>Clean specks</span><input type="range" min="0" max="50" value={t.opts.despeckle} oninput={(e) => ed.updateTrace({ despeckle: num(e) })} /><span class="mono">{t.opts.despeckle}px</span></label>
    <label class="f"><span>Corners</span><input type="range" min="0" max="1.34" step="0.02" value={t.opts.smoothing} oninput={(e) => ed.updateTrace({ smoothing: num(e) })} /><span class="muted">{t.opts.smoothing < 0.5 ? 'sharp' : t.opts.smoothing < 1 ? 'mixed' : 'round'}</span></label>
    <label class="f"><span>Simplify</span><input type="range" min="0" max="2" step="0.05" value={t.opts.tolerance} oninput={(e) => ed.updateTrace({ tolerance: num(e) })} /><span class="mono">{t.opts.tolerance}</span></label>
    <label><input type="checkbox" checked={t.opts.invert} onchange={(e) => ed.updateTrace({ invert: (e.target as HTMLInputElement).checked })} /> light on dark</label>
    <label><input type="checkbox" checked={t.showImage} onchange={(e) => ed.updateTrace({ showImage: (e.target as HTMLInputElement).checked })} /> show image</label>
    <div class="f"><span>Place</span><label>scale <input type="number" step="1" value={Math.round(t.scale * 100)} onchange={(e) => ed.updateTrace({ scale: num(e) / 100 })} style="width:64px" />%</label></div>
    <div class="f"><span></span><label>x <input type="number" value={Math.round(t.dx)} onchange={(e) => ed.updateTrace({ dx: num(e) })} style="width:64px" /></label><label>y <input type="number" value={Math.round(t.dy)} onchange={(e) => ed.updateTrace({ dy: num(e) })} style="width:64px" /></label></div>
    <div class="row" style="margin-top: 8px">
      {#if ed.stats.paths}<button class="primary" disabled={!t.svg || t.busy} onclick={() => ed.useTrace(true)}>Use: replace</button><button disabled={!t.svg || t.busy} onclick={() => ed.useTrace(false)}>Use: add</button>
      {:else}<button class="primary" disabled={!t.svg || t.busy} onclick={() => ed.useTrace(true)}>Use this outline</button>{/if}
      <button onclick={() => ed.endTrace()}>Cancel</button>
    </div>
    <p class="muted small">{t.busy ? 'tracing…' : 'The image stays in this browser only; it is not written to the repo.'}</p>
  {:else if id === 'selection'}
    {#if sel.kind === 'points'}
      <div class="f"><span>{sel.n} point{sel.n === 1 ? '' : 's'}</span>
        <label>x <input type="number" value={sel.x} onchange={(e) => ed.setPointPos(num(e), sel.kind === 'points' ? sel.y : 0)} /></label>
        <label>y <input type="number" value={sel.y} onchange={(e) => ed.setPointPos(sel.kind === 'points' ? sel.x : 0, num(e))} /></label></div>
      <div class="f"><span>Kind</span>
        <span class="seg"><button class:on={sel.pointKind === 'corner'} onclick={() => ed.setPointKind('corner')}>Corner</button><button class:on={sel.pointKind === 'smooth'} onclick={() => ed.setPointKind('smooth')}>Smooth</button><button class:on={sel.pointKind === 'free'} disabled title="Drag a handle with ⌥ to free it">Free</button></span></div>
      <p class="muted small">Drag a handle to bend the curve; ⌥-drag moves one handle alone. Double-click a point to toggle corner / smooth. Pen over the shape adds a point; pen over a point removes it.</p>
    {:else if sel.kind === 'shapes'}
      <div class="f"><span>{sel.n} shape{sel.n === 1 ? '' : 's'}</span>
        <label>x <input type="number" value={sel.x} onchange={(e) => ed.transform({ dx: num(e) - (sel.kind === 'shapes' ? sel.x : 0) }, 'move')} /></label>
        <label>y <input type="number" value={sel.y} onchange={(e) => ed.transform({ dy: num(e) - (sel.kind === 'shapes' ? sel.y : 0) }, 'move')} /></label></div>
      <div class="f"><span>Size</span>
        <label>w <input type="number" value={sel.w} onchange={(e) => sel.kind === 'shapes' && sel.w && ed.transform({ sx: num(e) / sel.w }, 'resize')} /></label>
        <label>h <input type="number" value={sel.h} onchange={(e) => sel.kind === 'shapes' && sel.h && ed.transform({ sy: num(e) / sel.h }, 'resize')} /></label></div>
      <div class="f"><span>Scale</span><label><input type="number" value={100} onchange={(e) => { const v = num(e); if (v > 0) ed.transform({ sx: v / 100, sy: v / 100 }, 'scale'); (e.target as HTMLInputElement).value = '100'; }} />%</label>
        <label>rotate <input type="number" value={0} onchange={(e) => { ed.transform({ rotate: num(e) }, 'rotate'); (e.target as HTMLInputElement).value = '0'; }} />°</label></div>
      {#if sel.lines}<div class="f"><span>{sel.lines} line{sel.lines === 1 ? '' : 's'}</span><span class="muted small">drawn at {ed.referenceWeight} units, round ends</span><button class="sm" onclick={() => ed.outlineLines()}>Outline line</button></div>{/if}
      <div class="row"><button class="sm" onclick={() => ed.center()}>Center in box</button><button class="sm" onclick={() => ed.deleteSelection()}>Delete</button></div>
    {:else if sel.kind === 'overlay'}
      <div class="f"><span>Compare</span><span>{[sel.dot && 'reference dot', sel.ghost && `${ed.ghostName ?? 'glyph'}`].filter(Boolean).join(' + ')}</span></div>
      <p class="muted small">Drag to move, arrows nudge (⇧ 10). ⇧-click the other to move both. Never saved; Esc lets go.</p>
    {:else}
      <div class="f"><span>Glyph</span><span>{ed.stats.paths} shape{ed.stats.paths === 1 ? '' : 's'} · {ed.stats.nodes} points</span></div>
      <div class="f"><span>Weight</span><span title="2 × area ÷ perimeter of the filled outline: right for long strokes, rough for blobs">≈ {ed.weightEstimate?.toFixed(0) ?? '—'} units <span class="muted">(reference {ed.referenceWeight})</span></span></div>
      <div class="row"><button class="sm" disabled={!ed.stats.paths} onclick={() => ed.fitToBox()}>Fit to box</button><button class="sm" disabled={!ed.stats.paths} onclick={() => ed.center()}>Center</button></div>
      <p class="muted small">Click a shape to see its points. Drag the fill to move it, a point to move the point.</p>
    {/if}
  {:else if id === 'compare'}
    <label><input type="checkbox" checked={ed.dot} onchange={(e) => ed.setDot((e.target as HTMLInputElement).checked)} /> Reference dot <span class="muted">(D) · drag it over a stroke</span></label>
    <div class="f"><span>Line weight</span><input type="number" min="1" max="200" value={ed.referenceWeight} onchange={(e) => ed.setSessionWeight(num(e))} />
      {#if ed.sessionWeight != null}<button class="sm" onclick={() => ed.setSessionWeight(null)} title="Back to the design's reference weight">Reset</button>{:else}<span class="muted small">design's reference</span>{/if}</div>
    <p class="muted small">Match the body of main strokes to the reference, not the tapers.</p>
    <div class="f"><span>Glyph</span>
      <button class="sm" data-gpop-anchor onclick={(e) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); ghostPick = ghostPick ? null : { x: r.left, y: r.bottom + 4 }; }}>{ed.ghostName ?? 'choose…'} <I.Dropdown /></button>
      {#if ed.ghostName}<button class="sm" onclick={() => ed.setGhost(null)} data-tip="No comparison glyph" aria-label="Clear"><I.Close /></button>{/if}
    </div>
    {#if ed.ghostName}<p class="muted small">Drag the blue glyph to move it; the outline stays editable where they overlap.</p>{/if}
    {#if sameArea.length}<div class="chips">{#each sameArea as g}<button class="gchip" class:on={ed.ghostName === g} onclick={() => ed.setGhost(ed.ghostName === g ? null : g)} title={g}><Glyph name={g} size={22} /></button>{/each}</div>{/if}
    {#if ed.ghostName}<div class="f"><span>Line up</span><span class="seg"><button class:on={!ed.ghostMoved && ed.ghostAlign === 'origin'} onclick={() => ed.setGhost(ed.ghostName, 'origin')}>box top-left</button><button class:on={!ed.ghostMoved && ed.ghostAlign === 'center'} onclick={() => ed.setGhost(ed.ghostName, 'center')}>centred</button></span>{#if ed.ghostMoved}<span class="muted small">moved · click to put back</span>{/if}</div>{/if}
    <label><input type="checkbox" checked={ed.ghostSaved} disabled={!ed.savedText} onchange={(e) => ed.setGhostSaved((e.target as HTMLInputElement).checked)} /> Last saved <span class="muted">(L) · dashed outline</span></label>
  {:else if id === 'glyph'}
    {#if ed.isNew}
      <div class="f"><span>File</span><span class="mono small">inputs/svg/{name}.svg <span class="muted">(new)</span></span></div>
      {#if areaName}<p class="muted small">Joins the area <strong>{app.areaLabel(areaName)}</strong> on the first save (a design change: save the design too).</p>{/if}
    {:else}
      <GlyphFacts glyph={name} showName={false} showBox={false}
        busy={ed.dirty ? 'Save or discard your edits to the outline first.' : null}
        onrenamed={(to) => goto(`/glyphs/${encodeURIComponent(to)}/edit${back ? `?back=${encodeURIComponent(back)}` : ''}`, { replaceState: true })}
        ondeleted={() => goto('/glyphs', { replaceState: true })} />
    {/if}
    <div class="f"><span>Box</span><span>{ed.box[0]} × {ed.box[1]} units{#if areaName} · from area <a href="/layouts?area={areaName}&g={encodeURIComponent(name)}" title="Area Properties on the Layouts screen (box size)">{app.areaLabel(areaName)}</a>{/if}</span></div>
  {:else if id === 'typing'}
    <TypingFields glyph={name} />
  {:else if id === 'tryit'}
    <TryIt glyph={name} />
  {:else if id === 'checks'}
    <ul class="checks">
      <li class:bad={ed.stats.paths === 0}>{ed.stats.paths === 0 ? 'Empty: nothing to save yet' : 'Has an outline'}</li>
      <li class:warn={ed.stats.outside}>{ed.stats.outside ? 'Sticks out of the box (the Layouts screen positions by the box)' : 'Inside the box'}</li>
      <li class:warn={ed.stats.open > 0}>{ed.stats.open ? `${ed.stats.open} open line${ed.stats.open === 1 ? '' : 's'}: outlined on save` : 'No open lines'} {#if ed.stats.open}<button class="sm" onclick={() => ed.outlineLines()}>Outline now</button>{/if}</li>
      <li class:warn={ed.stats.specks > 0}>{ed.stats.specks ? `${ed.stats.specks} speck${ed.stats.specks === 1 ? '' : 's'} under 6 units` : 'No specks'} {#if ed.stats.specks}<button class="sm" onclick={() => ed.removeSpecks()}>Remove them</button>{/if}</li>
    </ul>
    <div class="row"><button class="sm" disabled={!ed.stats.paths} onclick={() => ed.check()}>Check as built</button>
      {#if ed.built}<span class="small">{ed.built.ok ? `${ed.built.contours} contours · ${ed.built.points} points` : ed.built.error}</span>{/if}</div>
    {#if ed.error}<p class="error small">{ed.error}</p>{/if}
  {:else if id === 'tester'}
    <WordTester glyph={name} size={72} />
  {/if}
  </div>
{/snippet}

<div class="ge" ondrop={onDrop} ondragover={(e) => e.preventDefault()} onpaste={onPaste}>
  <!-- glyph bar -->
  <div class="gbar">
    <a href={backHref} class="back"><I.Back />{backLabel}</a>
    <span class="thumb"><Glyph name={name} size={28} /></span>
    <strong class="mono">{name}</strong>
    {#if app.charOf(name)}<span class="char">{app.charOf(name)}</span>{/if}
    {#if areaName}<a class="chip" href="/layouts?area={areaName}&g={encodeURIComponent(name)}" title="Area (sets the box): open it on the Layouts screen">{app.areaLabel(areaName)} · {ed.box[0]} × {ed.box[1]}</a>{:else}<span class="chip" title="No area yet: default box">no area · {ed.box[0]} × {ed.box[1]}</span>{/if}
    <span class="state">
      {#if ed.saving}<span class="chip">Saving…</span>
      {:else if ed.isNew && !ed.dirty}<span class="chip">new · not saved yet</span>
      {:else if ed.dirty}<span class="chip accent"><I.Unsaved size={14} />Edited · {ed.changeCount} change{ed.changeCount === 1 ? '' : 's'}</span>
      {:else if ed.savedAt}<span class="chip">Saved {ed.savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      {:else}<span class="chip">Saved</span>{/if}
    </span>
    <span class="spacer"></span>
    <button class="ghost" onclick={() => ed.undo()} disabled={!ed.canUndo} data-tip={ed.canUndo ? `Undo ${ed.undoLabel} (⌘Z)` : 'Nothing to undo'} aria-label="Undo"><I.Undo /></button>
    <button class="ghost" onclick={() => ed.redo()} disabled={!ed.canRedo} data-tip="Redo (⇧⌘Z)" aria-label="Redo"><I.Redo /></button>
    <button onclick={() => ed.discard()} disabled={!ed.dirty} title="Back to the file as loaded (can be undone)">Discard</button>
    <button class="primary" onclick={() => save()} disabled={ed.saving || !!ed.trace || (!ed.dirty && !ed.isNew) || !!app.lockOf(`glyph:${name}`)} title="Write inputs/svg/{name}.svg (⌘S)">Save glyph</button>
  </div>
  {#if app.lockOf(`glyph:${name}`)}
    <div class="banner info locked"><span class="ic"><I.Lock /></span>{app.lockMessage(`glyph:${name}`)} You can still draw here to try ideas; Save stays off.</div>
  {/if}

  <div class="body">
    <!-- tool rail -->
    <div class="rail">
      {#each TOOLS as [m, k, label]}
        {@const Ic = ICON[m]}
        <button class:on={ed.mode === m} onclick={() => ed.setMode(m)} data-tip="{label} ({k})" data-tip-side="right" aria-label={label} disabled={!!ed.trace && m !== 'hand' && m !== 'zoom'}><Ic /><span class="k">{k}</span></button>
      {/each}
      <span class="spacer"></span>
      <button class:on={ed.grid} onclick={() => ed.setGrid(!ed.grid)} data-tip="Grid (⇧G)" data-tip-side="right" aria-label="Grid"><I.Grid /></button>
      <button onclick={() => (shortcuts = true)} data-tip="Keyboard shortcuts (?)" data-tip-side="right" aria-label="Keyboard shortcuts"><I.Shortcuts /></button>
    </div>

    <PanelWorkspace store={editorPanels} {meta} {body} centerMin={320} help={EDITOR_HELP}>
      <!-- action bar -->
      <div class="actions">
        <span class="grp">
          <button disabled={!canCombine} onmouseenter={(e) => combineHover('unite', e)} onmouseleave={combineLeave} onclick={(e) => combineClick('unite', e)} data-tip={canCombine ? 'Union (⌥⇧U)' : 'Union: select 2 shapes first'} aria-label="Union"><I.Union /></button>
          <button disabled={!canCombine} onmouseenter={(e) => combineHover('subtract', e)} onmouseleave={combineLeave} onclick={(e) => combineClick('subtract', e)} data-tip={canCombine ? 'Subtract: the newest shape cuts the others; ⇧ swaps (⌥⇧S)' : 'Subtract: select 2 shapes first'} aria-label="Subtract"><I.Subtract /></button>
          <button disabled={!canCombine} onmouseenter={(e) => combineHover('intersect', e)} onmouseleave={combineLeave} onclick={(e) => combineClick('intersect', e)} data-tip={canCombine ? 'Intersect (⌥⇧I)' : 'Intersect: select 2 shapes first'} aria-label="Intersect"><I.Intersect /></button>
          <button disabled={!canCombine} onmouseenter={(e) => combineHover('exclude', e)} onmouseleave={combineLeave} onclick={(e) => combineClick('exclude', e)} data-tip={canCombine ? 'Exclude (⌥⇧E)' : 'Exclude: select 2 shapes first'} aria-label="Exclude"><I.Exclude /></button>
        </span>
        <button class:on={popover === 'simplify'} disabled={!ed.stats.paths || !!ed.trace} onclick={() => (popover === 'simplify' ? cancelPopover() : openPopover('simplify'))} title="Fewer points, same shape">Simplify…</button>
        <button class:on={popover === 'thicken'} disabled={!ed.stats.paths || !!ed.trace} onclick={() => (popover === 'thicken' ? cancelPopover() : openPopover('thicken'))} title="Make the outline heavier or lighter">Thicken…</button>
        <button disabled={!ed.stats.open} onclick={() => ed.outlineLines()} title="Turn open lines into filled outlines at the line weight (⌥⌘O); Save does this too">Outline line{ed.stats.open > 1 ? 's' : ''}</button>
        <button disabled={!ed.stats.paths} onclick={() => ed.cleanUp()} title="Remove self-overlaps and fix winding (what the font build does)">Clean up</button>
        <span class="grp">
          <button disabled={!ed.stats.paths} onclick={() => ed.flip('h')} data-tip="Flip horizontal (⇧H)" aria-label="Flip horizontal"><I.FlipH /></button>
          <button disabled={!ed.stats.paths} onclick={() => ed.flip('v')} data-tip="Flip vertical (⇧V)" aria-label="Flip vertical"><I.FlipV /></button>
        </span>
        <span class="grp" title="Import">
          <button onclick={() => svgInput.click()} title="Add the shapes of an SVG file (or drop it on the canvas, or paste SVG text)">SVG file…</button>
          <button onclick={() => imgInput.click()} title="Trace a JPG / PNG (or drop it on the canvas)">Image to trace…</button>
        </span>
        <input type="file" accept=".svg,image/svg+xml" bind:this={svgInput} onchange={onSvgFile} hidden />
        <input type="file" accept="image/png,image/jpeg,image/webp,image/gif,image/bmp" bind:this={imgInput} onchange={onImgFile} hidden />
        <span class="spacer"></span>
        <span class="zoom"><button class="ghost" onclick={() => ed.zoomBy(1 / 1.25)} data-tip="Zoom out (−)" aria-label="Zoom out"><I.Minus /></button><button class="ghost" onclick={() => ed.fit()} data-tip="Fit (⇧1)">{Math.round(ed.zoom * 100)}%</button><button class="ghost" onclick={() => ed.zoomBy(1.25)} data-tip="Zoom in (+)" aria-label="Zoom in"><I.Plus /></button></span>
      </div>

      {#if popover === 'simplify' && ed.preview?.kind === 'simplify'}
        <div class="pop">
          <strong>Simplify</strong>
          <input type="range" min="0.5" max="10" step="0.5" bind:value={simplifyTol} oninput={() => ed.previewSimplify(simplifyTol)} />
          <span class="mono">{simplifyTol}</span>
          <span class="muted">points {ed.preview.from} → {ed.preview.to}{sel.kind === 'shapes' ? ' · selection' : ' · whole glyph'}</span>
          <span class="spacer"></span><button onclick={cancelPopover}>Cancel</button><button class="primary" onclick={applyPopover}>Apply</button>
        </div>
      {:else if popover === 'thicken' && ed.preview?.kind === 'thicken'}
        <div class="pop">
          <strong>Thicken / thin</strong>
          <input type="range" min="-40" max="40" step="1" bind:value={thickTotal} oninput={() => ed.previewThicken(thickTotal, thickSharp)} />
          <input type="number" bind:value={thickTotal} onchange={() => ed.previewThicken(thickTotal, thickSharp)} style="width: 64px" />
          <span class="muted">units of total width ({thickTotal >= 0 ? '+' : ''}{thickTotal / 2} each side){sel.kind === 'shapes' ? ' · selection' : ' · whole glyph'}</span>
          <label><input type="checkbox" bind:checked={thickSharp} onchange={() => ed.previewThicken(thickTotal, thickSharp)} /> sharp corners</label>
          {#if ed.stats.paths === 0}<span class="badge-warn">everything vanished: thin less</span>{/if}
          <span class="spacer"></span><button onclick={cancelPopover}>Cancel</button><button class="primary" onclick={applyPopover}>Apply</button>
        </div>
      {/if}
      {#if starting}
        <div class="pop">
          {#if starting === 'file'}<span>Choose the SVG file that replaces <strong class="mono">{name}</strong> (nothing is written until you save).</span><button class="primary" onclick={() => svgInput.click()}>Choose SVG…</button>
          {:else}<span>Choose the image to trace for <strong class="mono">{name}</strong>.</span><button class="primary" onclick={() => imgInput.click()}>Choose image…</button>{/if}
          <span class="spacer"></span><button onclick={() => (starting = null)}>Not now</button>
        </div>
      {/if}
      {#if ed.draftRestored}
        <div class="pop">Restored unsaved edits to this glyph from your last session. <button onclick={() => (ed.draftRestored = false)}>Keep</button> <button onclick={() => { ed.discard(); ed.draftRestored = false; }}>Discard</button></div>
      {/if}

      <div class="wrap" bind:this={wrap}>
        <canvas bind:this={canvas} class="m-{ed.mode}" onwheel={(e) => ed.wheel(e)} ondblclick={(e) => ed.doubleClick(e)}></canvas>
        {#if toast}<div class="toast">{toast}</div>{/if}
        {#if ed.trace}<div class="tracehint">Trace mode · adjust in the Trace panel, then <strong>Use this outline</strong></div>{/if}
      </div>

      <div class="status">
        <span class="mono">{ed.cursor ? `${ed.cursor.x}, ${ed.cursor.y}` : '—'}</span>
        <span>{ed.stats.paths} shape{ed.stats.paths === 1 ? '' : 's'} · {ed.stats.nodes} points{ed.stats.selPaths ? ` · ${ed.stats.selPaths} selected` : ''}{ed.stats.selNodes ? ` · ${ed.stats.selNodes} point${ed.stats.selNodes === 1 ? '' : 's'}` : ''}</span>
        {#if ed.stats.outside}<span class="badge-warn">outside the box</span>{/if}
        {#if ed.drawing}<span class="muted">pen: click to add points, click the first point to close, Enter for a line, Esc to stop</span>{/if}
        <span class="spacer"></span>
        <span class="muted">{Math.round(ed.zoom * 100)}%</span>
      </div>
    </PanelWorkspace>
  </div>
</div>

{#if ghostPick}
  <GlyphPopover title="Compare with" glyphs={ghostGlyphs} current={ed.ghostName} anchor={ghostPick} onpick={(g) => { ed.setGhost(g); ghostPick = null; }} onclose={() => (ghostPick = null)} />
{/if}

{#if importAsk}
  {@const a = importAsk}
  <div class="modal-bg" role="presentation">
    <div class="modal" role="dialog" tabindex="-1">
      <h3 style="margin:0">Import SVG</h3>
      {#if a.box && (Math.abs(a.box[0] - ed.box[0]) > 0.5 || Math.abs(a.box[1] - ed.box[1]) > 0.5)}
        <p>The file is {a.box[0]} × {a.box[1]}; this glyph's box is {ed.box[0]} × {ed.box[1]}.</p>
        <label><input type="radio" bind:group={a.fit} value={true} /> Fit to the box (keeps proportions)</label>
        <label><input type="radio" bind:group={a.fit} value={false} /> Keep its size (units are units)</label>
      {/if}
      {#if ed.stats.paths}
        <label><input type="radio" bind:group={a.replace} value={true} /> Replace the current outline</label>
        <label><input type="radio" bind:group={a.replace} value={false} /> Add to it</label>
      {/if}
      {#if a.strokes}<p class="muted small">{a.strokes} stroked path{a.strokes === 1 ? '' : 's'} will be outlined at their width (the font keeps fills only).</p>{/if}
      {#if a.dropped.length}<p class="muted small">Dropped: {a.dropped.join(', ')}. The file holds shapes only.</p>{/if}
      <div class="row"><span class="spacer"></span><button onclick={() => (importAsk = null)}>Cancel</button><button class="primary" onclick={() => { ed.importSvg(a.text, { fit: a.fit, replace: a.replace }); importAsk = null; }}>Import</button></div>
    </div>
  </div>
{/if}

{#if ed.conflictDisk != null}
  <div class="modal-bg" role="presentation">
    <div class="modal" role="dialog" tabindex="-1">
      <h3 style="margin:0">{name}.svg changed on disk</h3>
      <p>Someone (or another tab) wrote this file since you loaded it.</p>
      <div class="row">
        <button onclick={() => { ed.scene?.setGhostSaved(ed.conflictDisk); ed.ghostSaved = true; ed.conflictDisk = null; say('Disk version shown as a dashed outline'); }}>Compare</button>
        <button onclick={() => ed.loadDiskVersion()}>Load disk version (lose mine)</button>
        <button class="primary" onclick={() => save(true)}>Overwrite with mine</button>
      </div>
    </div>
  </div>
{/if}

{#if leave}
  <div class="modal-bg" role="presentation">
    <div class="modal" role="dialog" tabindex="-1">
      <h3 style="margin:0">Unsaved edits to {name}</h3>
      <p>{ed.changeCount} change{ed.changeCount === 1 ? '' : 's'} {hosted.isHosted ? 'not saved to your draft yet' : 'not written to the file yet'}.</p>
      <div class="row"><button onclick={() => (leave = null)}>Keep editing</button><button onclick={() => doLeave('discard')}>Discard and leave</button><button class="primary" onclick={() => doLeave('save')}>Save and leave</button></div>
    </div>
  </div>
{/if}

{#if shortcuts}
  <div class="modal-bg" role="presentation" onclick={() => (shortcuts = false)}>
    <div class="modal" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()}>
      <h3 style="margin:0">Keyboard shortcuts</h3>
      <table class="keys"><tbody>
        <tr><td><kbd>V</kbd></td><td>Select</td><td><kbd>P</kbd> / <kbd>⇧P</kbd></td><td>Pen / Pencil</td></tr>
        <tr><td><kbd>R</kbd> / <kbd>O</kbd></td><td>Rectangle / Ellipse</td><td><kbd>H</kbd> / <kbd>Space</kbd></td><td>Hand (pan)</td></tr>
        <tr><td><kbd>Z</kbd></td><td>Zoom (⌥ out)</td><td><kbd>⌘</kbd> + wheel</td><td>Zoom at the pointer</td></tr>
        <tr><td><kbd>⇧1</kbd> / <kbd>⇧0</kbd> / <kbd>⇧2</kbd></td><td>Fit / 100% / fit selection</td><td><kbd>⇧G</kbd></td><td>Grid</td></tr>
        <tr><td><kbd>Enter</kbd></td><td>Finish the pen path as a line · apply a popover</td><td><kbd>Esc</kbd></td><td>Cancel popover · stop the pen · deselect</td></tr>
        <tr><td><kbd>⌫</kbd></td><td>Delete points or shapes</td><td>arrows</td><td>Nudge 1 unit (⇧ 10)</td></tr>
        <tr><td><kbd>⇧H</kbd> / <kbd>⇧V</kbd></td><td>Flip</td><td><kbd>⌥⇧U S I E</kbd></td><td>Union · Subtract · Intersect · Exclude</td></tr>
        <tr><td><kbd>⌥⌘O</kbd></td><td>Outline lines</td><td><kbd>D</kbd> / <kbd>G</kbd> / <kbd>L</kbd></td><td>Dot · compare glyph · last saved</td></tr>
        <tr><td><kbd>⌘Z</kbd> / <kbd>⇧⌘Z</kbd></td><td>Undo / redo (the glyph)</td><td><kbd>⌘S</kbd></td><td>Save glyph</td></tr>
        <tr><td>double-click a point</td><td>Corner ↔ smooth</td><td><kbd>⌥</kbd>-drag a handle</td><td>Move one handle alone</td></tr>
      </tbody></table>
      <div class="row"><span class="spacer"></span><button onclick={() => (shortcuts = false)}>Close</button></div>
    </div>
  </div>
{/if}

<style>
  .ge { display: flex; flex-direction: column; height: 100%; min-height: 0; }
  .gbar { display: flex; align-items: center; gap: var(--space-4); padding: 6px var(--space-6); border-bottom: 1px solid var(--border); background: var(--bg-panel); }
  .back { display: inline-flex; align-items: center; gap: var(--space-2); text-decoration: none; margin-right: var(--space-4); }
  .thumb { display: inline-flex; width: 30px; height: 30px; align-items: center; justify-content: center; border: 1px solid var(--border); border-radius: 4px; background: var(--bg-field); }
  .mono { font-family: var(--font-mono); }
  .char { font-size: var(--t-panel); }
  .chip.accent { text-decoration: none; }
  a.chip { text-decoration: none; color: inherit; }
  .spacer { flex: 1; }
  .body { display: flex; flex: 1; min-height: 0; }
  .rail { display: flex; flex-direction: column; gap: 4px; padding: var(--space-4) 6px; border-right: 1px solid var(--border); background: var(--bg-panel); }
  .rail button { width: 40px; height: 40px; padding: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0; }
  .rail button.on { background: var(--sel-bg); border-color: var(--link); color: var(--link); }
  .rail .k { font-size: 9px; color: var(--ink-muted); }
  .actions { display: flex; align-items: center; gap: var(--space-4); padding: 6px var(--space-5); border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  .actions button { height: 26px; padding: 0 8px; font-size: var(--t-small); }
  .actions button.on { background: var(--sel-bg); border-color: var(--link); color: var(--link); }
  .grp { display: inline-flex; }
  .grp button { border-radius: 0; margin-left: -1px; min-width: 30px; }
  .grp button:first-child { border-radius: var(--radius-md) 0 0 var(--radius-md); margin-left: 0; }
  .grp button:last-child { border-radius: 0 var(--radius-md) var(--radius-md) 0; }
  .zoom { display: inline-flex; align-items: center; gap: 2px; }
  .zoom button { min-width: 28px; }
  .pop { display: flex; align-items: center; gap: var(--space-4); padding: 6px var(--space-5); background: var(--sel-bg); border-bottom: 1px solid var(--border); font-size: var(--t-small); flex-wrap: wrap; }
  .pop input[type=range] { width: 180px; }
  .wrap { flex: 1; min-height: 240px; background: var(--bg-canvas); position: relative; }
  canvas { display: block; width: 100%; height: 100%; touch-action: none; }
  canvas.m-hand { cursor: grab; } canvas.m-zoom { cursor: zoom-in; } canvas.m-pen, canvas.m-pencil, canvas.m-rect, canvas.m-ellipse { cursor: crosshair; }
  .toast { position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%); padding: 6px 12px; font-size: var(--t-small); max-width: 80%; }
  .tracehint { position: absolute; left: 50%; top: 10px; transform: translateX(-50%); background: var(--sel-bg); color: var(--ink); padding: 4px 10px; border-radius: 6px; font-size: var(--t-small); }
  .status { display: flex; gap: var(--space-5); align-items: center; padding: 4px var(--space-5); border-top: 1px solid var(--border); font-size: var(--t-caption); color: var(--ink-muted); }
  .sec { display: flex; flex-direction: column; gap: 6px; font-size: var(--t-small); min-width: 0; }
  .f { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .f > span:first-child { width: 72px; color: var(--ink-muted); flex-shrink: 0; }
  .f input[type=number] { width: 64px; height: 24px; }
  .f input[type=range] { flex: 1; min-width: 80px; }
  .small { font-size: var(--t-caption); }
  button.sm { height: 22px; padding: 0 8px; font-size: var(--t-caption); }
  .seg { display: inline-flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
  .seg button { height: 22px; padding: 0 8px; border: 0; border-radius: 0; font-size: var(--t-caption); }
  .seg button.on { background: var(--sel-bg); color: var(--ink); }
  .chips { display: flex; gap: 4px; flex-wrap: wrap; }
  .gchip { height: 28px; width: 28px; padding: 2px; }
  .gchip.on { border-color: var(--link); background: var(--sel-bg); }
  .checks { margin: 0; padding-left: 18px; }
  .checks li.warn { color: var(--status-draft); } .checks li.bad { color: var(--status-danger); }

  .modal { padding: var(--space-6); width: min(560px, 92vw); display: flex; flex-direction: column; gap: var(--space-5); }
  .modal p { margin: 0; }
  .keys td { padding: 3px 10px 3px 0; font-size: var(--t-small); vertical-align: top; }
</style>
