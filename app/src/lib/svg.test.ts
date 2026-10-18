import { describe, expect, it } from 'vitest';
import { parseSvg } from './svg';

describe('parseSvg', () => {
  it('extracts the viewBox and inner markup, recolouring black to currentColor', () => {
    const r = parseSvg('<svg width="350" height="350" viewBox="0 0 350 350" xmlns="x"><path d="M0 0" fill="black"/><path stroke="#000"/></svg>');
    expect(r?.viewBox).toBe('0 0 350 350');
    expect(r?.inner).toBe('<path d="M0 0" fill="currentColor"/><path stroke="currentColor"/>');
  });
  it('falls back to width/height, then 1000', () => {
    expect(parseSvg('<svg width="200" height="100"></svg>')?.viewBox).toBe('0 0 200 100');
    expect(parseSvg('<svg></svg>')?.viewBox).toBe('0 0 1000 1000');
  });
  it('returns null for missing or non-SVG text and caches', () => {
    expect(parseSvg(undefined)).toBeNull();
    expect(parseSvg('nope')).toBeNull();
    const t = '<svg viewBox="0 0 1 1"></svg>';
    expect(parseSvg(t)).toBe(parseSvg(t));
  });
});
