// Press and hold to drag, for a finger on a canvas that also has to scroll (Layouts on a phone).
// A swipe scrolls; a tap selects; holding still for HOLD_MS lifts the part, and from then on the
// finger drags it. Moving more than HOLD_SLOP px before the lift gives the gesture to scrolling.
// Pure: the caller passes pointer positions and gets told what happened (WordCanvas.svelte).

export const HOLD_MS = 400;
export const HOLD_SLOP = 8;

export type HoldEvents = {
  /** The hold time passed with the finger still: lift the part. */
  onlift: () => void;
  /** Down and up without moving or lifting. */
  ontap: () => void;
};

export class Hold {
  /** idle → pressed (waiting) → lifted (dragging); `abandoned` after moving too soon (a scroll). */
  state: 'idle' | 'pressed' | 'lifted' | 'abandoned' = 'idle';
  private x = 0;
  private y = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  constructor(private ev: HoldEvents, private ms = HOLD_MS, private slop = HOLD_SLOP) {}

  get lifted() { return this.state === 'lifted'; }

  down(x: number, y: number) {
    this.clear();
    this.state = 'pressed'; this.x = x; this.y = y;
    this.timer = setTimeout(() => { this.timer = null; if (this.state === 'pressed') { this.state = 'lifted'; this.ev.onlift(); } }, this.ms);
  }
  /** True while the finger drags a lifted part (the caller moves it and stops the page scrolling). */
  move(x: number, y: number): boolean {
    if (this.state === 'pressed' && Math.hypot(x - this.x, y - this.y) > this.slop) { this.clear(); this.state = 'abandoned'; }
    return this.state === 'lifted';
  }
  /** The finger came up. Returns whether a lifted drag ended (the caller drops the part). */
  up(): boolean {
    const was = this.state;
    this.clear();
    this.state = 'idle';
    if (was === 'pressed') this.ev.ontap();
    return was === 'lifted';
  }
  /** The browser took the gesture (a scroll) or it was called off. Returns whether a drag was under way. */
  cancel(): boolean {
    const was = this.state;
    this.clear();
    this.state = 'idle';
    return was === 'lifted';
  }
  private clear() { if (this.timer) { clearTimeout(this.timer); this.timer = null; } }
}
