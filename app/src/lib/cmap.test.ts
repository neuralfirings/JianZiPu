import { describe, it, expect } from 'vitest';
import { cmapCodepoints, segments } from './cmap';

// The tracked golden font: 425 mapped code points per fontTools. Node's fs exists under Vitest;
// the app has no @types/node, so it is typed loosely here.
const { readFileSync } = (await import(/* @vite-ignore */ 'node:' + 'fs')) as { readFileSync: (p: string) => Uint8Array };
const cwd = (globalThis as unknown as { process: { cwd(): string } }).process.cwd();   // app/ (vitest runs there)
const font = readFileSync(`${cwd}/../src-fonttools/tests/JianZiPu.ttf`);
const buf = font.buffer.slice(font.byteOffset, font.byteOffset + font.byteLength) as ArrayBuffer;

describe('cmapCodepoints', () => {
  const chars = cmapCodepoints(buf);
  it('reads every mapped code point', () => expect(chars.size).toBe(425));
  it('knows what the font carries and what it lacks', () => {
    expect(chars.has('名'.codePointAt(0)!)).toBe(true);
    expect(chars.has('s'.codePointAt(0)!)).toBe(true);
    expect(chars.has('往'.codePointAt(0)!)).toBe(false);
  });
});

describe('segments', () => {
  const has = new Set([...'s7k5 名七'].map((c) => c.codePointAt(0)!));
  it('splits present and missing runs, keeping whitespace present', () => {
    expect(segments('s7k5 往x名', has)).toEqual([
      { text: 's7k5 ', missing: false }, { text: '往x', missing: true }, { text: '名', missing: false }
    ]);
  });
  it('marks nothing without a character map', () => expect(segments('往', null)).toEqual([{ text: '往', missing: false }]));
});
