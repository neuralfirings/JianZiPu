// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { installTooltips, placeTip } from './tooltip';

const box = (left: number, top: number, width: number, height: number) => ({ left, top, width, height, right: left + width, bottom: top + height });
const view = { width: 800, height: 600 };

describe('placeTip', () => {
  it('centres below, or sits beside on the right', () => {
    expect(placeTip(box(100, 100, 40, 40), { width: 60, height: 20 }, 'below', view)).toEqual({ x: 90, y: 146 });
    expect(placeTip(box(0, 100, 40, 40), { width: 60, height: 20 }, 'right', view)).toEqual({ x: 46, y: 110 });
  });
  it('flips or clamps to stay in the window', () => {
    expect(placeTip(box(100, 570, 40, 24), { width: 60, height: 20 }, 'below', view).y).toBe(544);   // above instead
    expect(placeTip(box(770, 100, 24, 24), { width: 60, height: 20 }, 'right', view).x).toBe(704);   // left instead
    expect(placeTip(box(0, 10, 20, 20), { width: 200, height: 20 }, 'below', view).x).toBe(4);       // not off the left edge
  });
});

describe('installTooltips', () => {
  it('shows data-tip on pointer over and focus, hides on leave, press and Escape', () => {
    document.body.innerHTML = '<button id="a" data-tip="Pen (P)"><svg></svg></button><button id="b">plain</button>';
    const off = installTooltips();
    const tip = document.querySelector<HTMLElement>('.tip')!;
    const a = document.getElementById('a')!, b = document.getElementById('b')!;
    a.querySelector('svg')!.dispatchEvent(new Event('pointerover', { bubbles: true }));
    expect(tip.hidden).toBe(false);
    expect(tip.textContent).toBe('Pen (P)');
    b.dispatchEvent(new Event('pointerover', { bubbles: true }));
    expect(tip.hidden).toBe(true);
    a.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    expect(tip.hidden).toBe(false);
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(tip.hidden).toBe(true);
    a.dispatchEvent(new Event('pointerover', { bubbles: true }));
    a.dispatchEvent(new Event('pointerdown', { bubbles: true }));
    expect(tip.hidden).toBe(true);
    off();
    expect(document.querySelector('.tip')).toBeNull();
  });
  it('on touch, a tap shows the tip for a moment instead of hover', () => {
    vi.useFakeTimers();
    document.body.innerHTML = '<button id="a" data-tip="Undo"><svg></svg></button>';
    const off = installTooltips();
    const tip = document.querySelector<HTMLElement>('.tip')!;
    const a = document.getElementById('a')!;
    const finger = (type: string) => Object.assign(new Event(type, { bubbles: true }), { pointerType: 'touch' });
    a.dispatchEvent(finger('pointerover'));
    expect(tip.hidden).toBe(true);                    // no hover on a phone
    a.dispatchEvent(finger('pointerdown'));
    a.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    expect(tip.hidden).toBe(true);                    // the focus a tap brings doesn't show it either
    a.dispatchEvent(finger('pointerup'));
    a.dispatchEvent(finger('pointerout'));
    expect(tip.hidden).toBe(false);
    expect(tip.textContent).toBe('Undo');
    vi.advanceTimersByTime(3000);
    expect(tip.hidden).toBe(true);
    off();
    vi.useRealTimers();
  });
});
