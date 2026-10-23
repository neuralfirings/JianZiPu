import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Hold, HOLD_MS, HOLD_SLOP } from './hold';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());
const make = () => { const ev = { onlift: vi.fn(), ontap: vi.fn() }; return { ev, h: new Hold(ev) }; };

describe('press and hold', () => {
  it('a quick tap selects and never lifts', () => {
    const { ev, h } = make();
    h.down(10, 10);
    vi.advanceTimersByTime(HOLD_MS - 100);
    expect(h.up()).toBe(false);
    expect(ev.ontap).toHaveBeenCalledOnce();
    vi.advanceTimersByTime(1000);
    expect(ev.onlift).not.toHaveBeenCalled();
  });
  it('holding still lifts, then the finger drags until it comes up', () => {
    const { ev, h } = make();
    h.down(10, 10);
    h.move(12, 11);                          // a finger is never quite still
    vi.advanceTimersByTime(HOLD_MS);
    expect(ev.onlift).toHaveBeenCalledOnce();
    expect(h.move(80, 10)).toBe(true);
    expect(h.up()).toBe(true);
    expect(ev.ontap).not.toHaveBeenCalled();
  });
  it('moving before the lift is a scroll: nothing lifts, nothing is tapped', () => {
    const { ev, h } = make();
    h.down(10, 10);
    expect(h.move(10, 10 + HOLD_SLOP + 1)).toBe(false);
    vi.advanceTimersByTime(HOLD_MS * 2);
    expect(ev.onlift).not.toHaveBeenCalled();
    expect(h.up()).toBe(false);
    expect(ev.ontap).not.toHaveBeenCalled();
  });
  it('a cancel (the browser scrolled) ends a lifted drag', () => {
    const { h } = make();
    h.down(0, 0);
    vi.advanceTimersByTime(HOLD_MS);
    expect(h.cancel()).toBe(true);
    expect(h.state).toBe('idle');
  });
});
