// Instant tooltips. A browser's own `title` tooltip waits about a second and can't be hurried, so
// icon-only buttons say what they do with `data-tip="Pen (P)"` instead (plus `data-tip-side="right"`
// to put it beside rather than below). One listener on the document shows a single tooltip at
// once, for disabled buttons too; installTooltips() runs once in routes/+layout.svelte.

export type Side = 'below' | 'right';
type Box = { left: number; top: number; right: number; bottom: number; width: number; height: number };

const GAP = 6, EDGE = 4;
/** How long a tapped tip stays: long enough to read it. */
export const tapTipMs = (text: string) => Math.min(6000, 1500 + 40 * text.length);

/** Where the tooltip goes: beside or below `anchor`, kept inside the window. */
export function placeTip(anchor: Box, tip: { width: number; height: number }, side: Side, view: { width: number; height: number }) {
  let x: number, y: number;
  if (side === 'right') {
    x = anchor.right + GAP; y = anchor.top + (anchor.height - tip.height) / 2;
    if (x + tip.width > view.width - EDGE) x = anchor.left - GAP - tip.width;
  } else {
    x = anchor.left + (anchor.width - tip.width) / 2; y = anchor.bottom + GAP;
    if (y + tip.height > view.height - EDGE) y = anchor.top - GAP - tip.height;
  }
  const clamp = (v: number, max: number) => Math.round(Math.max(EDGE, Math.min(v, max - EDGE)));
  return { x: clamp(x, view.width - tip.width), y: clamp(y, view.height - tip.height) };
}

/** Show `data-tip` on hover and keyboard focus. Returns a function that removes it all. */
export function installTooltips(doc: Document = document): () => void {
  const el = doc.createElement('div');
  el.className = 'tip';
  el.setAttribute('role', 'tooltip');
  el.hidden = true;
  doc.body.append(el);
  let on: HTMLElement | null = null;
  let touchAt = -Infinity, timer: ReturnType<typeof setTimeout> | null = null;

  const show = (t: HTMLElement) => {
    const text = t.dataset.tip;
    if (!text) return hide();
    on = t;
    el.textContent = text;
    el.hidden = false;
    const r = t.getBoundingClientRect();
    const p = placeTip(r, el.getBoundingClientRect(), t.dataset.tipSide === 'right' ? 'right' : 'below', { width: innerWidth, height: innerHeight });
    el.style.transform = `translate(${p.x}px, ${p.y}px)`;
  };
  const hide = () => { on = null; el.hidden = true; if (timer) { clearTimeout(timer); timer = null; } };
  const target = (e: Event) => (e.target instanceof Element ? e.target.closest<HTMLElement>('[data-tip]') : null);

  const touch = (e: Event) => (e as PointerEvent).pointerType === 'touch';
  const over = (e: Event) => {
    if (touch(e) || (e.type === 'focusin' && performance.now() - touchAt < 1000)) return;   // a finger: see tapped
    const t = target(e); if (t) { if (t !== on) show(t); } else if (on) hide();
  };
  const down = (e: Event) => { hide(); if (touch(e)) touchAt = performance.now(); };
  const tapped = (e: Event) => {
    const t = touch(e) ? target(e) : null;
    if (!t?.dataset.tip) return;
    show(t);
    timer = setTimeout(hide, tapTipMs(t.dataset.tip));
  };
  const out = (e: PointerEvent | FocusEvent) => {
    if (touch(e)) return;   // a finger leaves as it lifts; a tapped tip keeps its time
    const to = e.relatedTarget instanceof Element ? e.relatedTarget.closest('[data-tip]') : null;
    if (on && to !== on) hide();
  };
  const key = (e: KeyboardEvent) => { if (e.key === 'Escape') hide(); };
  const L: [string, EventListener][] = [['pointerover', over], ['focusin', over], ['pointerout', out as EventListener], ['focusout', out as EventListener],
    ['pointerdown', down], ['pointerup', tapped], ['keydown', key as EventListener], ['scroll', hide]];
  for (const [n, f] of L) doc.addEventListener(n, f, true);
  return () => { for (const [n, f] of L) doc.removeEventListener(n, f, true); el.remove(); };
}
