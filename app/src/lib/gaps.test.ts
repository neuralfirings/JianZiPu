import { describe, expect, it } from 'vitest';
import { bumpGap, bumpGapOwn, gapEntryIndex, gapKeySide, gapValue, hitsOtherwise } from './editor.svelte';
import type { Relationship } from './api';

const list = [{ when_base: ['b1'], value: 10 }, { when_elem: ['e1'], value: 20 }, { value: 30 }];

describe('gap lookups', () => {
  it('first match wins; a number is not a list', () => {
    expect(gapEntryIndex(list, 'b1', 'e1')).toBe(0);
    expect(gapEntryIndex(list, 'b2', 'e1')).toBe(1);
    expect(gapEntryIndex(list, 'b2', 'e2')).toBe(2);
    expect(gapEntryIndex(5, 'b1', 'e1')).toBe(-1);
    expect(gapValue(5, null, null)).toBe(5);
    expect(gapValue([{ when_base: ['b1'], value: 1 }], 'b2', null)).toBeNull();
    expect(hitsOtherwise(list, 'b2', 'e2')).toBe(true);
    expect(hitsOtherwise(list, 'b1', 'e1')).toBe(false);
  });
  it('gapKeySide: existing conditions decide, else the side with choices', () => {
    expect(gapKeySide(list, 1, 1)).toBe('base');
    expect(gapKeySide([{ when_elem: ['x'], value: 1 }], 1, 1)).toBe('elem');
    expect(gapKeySide(5, 3, 1)).toBe('elem');
    expect(gapKeySide(5, 1, 3)).toBe('base');
  });
});

describe('bumpGap', () => {
  it('adds to the matching entry (rounded) or to a plain number', () => {
    const rel: Relationship = { axis: 'y', elem: 'a', base: 'b', gap: [{ when_base: ['b1'], value: 10 }, { value: 30 }] };
    expect(bumpGap(rel, 2.4, 'b1', null)).toBe(12);
    expect(bumpGap(rel, -1, 'zz', null)).toBe(29);
    const num: Relationship = { axis: 'y', elem: 'a', base: 'b', gap: 7 };
    expect(bumpGap(num, 0.6, null, null)).toBe(8);
    expect(num.gap).toBe(8);
  });
  it('returns null when nothing matches', () => {
    expect(bumpGap({ axis: 'y', elem: 'a', base: 'b', gap: [{ when_base: ['b1'], value: 1 }] }, 1, 'b2', null)).toBeNull();
  });
});

describe('bumpGapOwn', () => {
  it('splits a number into an exception row plus otherwise', () => {
    const rel: Relationship = { axis: 'y', elem: 'a', base: 'b', gap: 10 };
    expect(bumpGapOwn(rel, 5, 'elem', 'e1', null, 'e1')).toBe(15);
    expect(rel.gap).toEqual([{ when_elem: ['e1'], value: 15 }, { value: 10 }]);
  });
  it('widens an existing single-glyph row in place, otherwise inserts before the shared one', () => {
    const rel: Relationship = { axis: 'y', elem: 'a', base: 'b', gap: [{ when_elem: ['e1'], value: 15 }, { when_elem: ['e2', 'e3'], value: 20 }, { value: 10 }] };
    expect(bumpGapOwn(rel, 1, 'elem', 'e1', null, 'e1')).toBe(16);
    expect(rel.gap).toHaveLength(3);
    expect(bumpGapOwn(rel, 2, 'elem', 'e2', null, 'e2')).toBe(22);
    expect(rel.gap).toEqual([{ when_elem: ['e1'], value: 16 }, { when_elem: ['e2'], value: 22 }, { when_elem: ['e2', 'e3'], value: 20 }, { value: 10 }]);
  });
});

describe('else gaps toggle', () => {
  it('is off by default and remembered in this browser', async () => {
    const { editor } = await import('./editor.svelte');
    expect(editor.showElse).toBe(false);
    editor.showElse = true;
    expect(localStorage.getItem('jzp-show-else')).toBe('1');
    editor.showElse = false;
    expect(localStorage.getItem('jzp-show-else')).toBe('0');
  });
});
