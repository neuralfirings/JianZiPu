// Areas as the Area Properties panel and the Glyphs screen see them: which word
// types use one, the position-decimal grid, and making a new one.
import type { Design, Layout } from './api';
import { layoutUsesArea } from './editor.svelte';
import { isDecimal } from './typing';

export { layoutUsesArea };

/** The word types with a part that can hold `area`. */
export function usedIn(d: Design, area: string): Layout[] {
  return d.layouts.filter((l) => layoutUsesArea(l, area));
}

export const HUI = Array.from({ length: 13 }, (_, i) => i + 1);
export const DECIMALS = ['blank', '1', '2', '3', '4', '5', '6', '7', '8', '9'] as const;

export type DecimalCell = { glyph: string; label: string; hui: number; decimal: string; member: boolean; exists: boolean };

/** The position decimals as a grid: one row per hui (1–13), one cell per decimal (`7.`, `7.1` … `7.9`).
 *  `member`: in the area; `exists`: has an SVG (so it can be added). */
export function decimalGrid(members: readonly string[], exists: (g: string) => boolean): DecimalCell[][] {
  const mine = new Set(members);
  return HUI.map((h) => DECIMALS.map((dd) => {
    const glyph = `md_${h}.${dd}`;
    return { glyph, label: dd === 'blank' ? `${h}.` : `${h}.${dd}`, hui: h, decimal: dd, member: mine.has(glyph), exists: exists(glyph) };
  }));
}

/** Split an area's members into ordinary glyphs (chips) and position decimals (the grid). */
export function splitMembers(members: readonly string[]): { chips: string[]; decimals: string[] } {
  const chips: string[] = [], decimals: string[] = [];
  for (const g of members) (isDecimal(g) ? decimals : chips).push(g);
  return { chips, decimals };
}

/** Why `id` can't name a new area, or null when it can. */
export function areaIdProblem(d: Design, id: string): string | null {
  if (!id) return 'Give it an id';
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(id)) return 'Letters, digits and _ only, starting with a letter';
  if (d.areas[id]) return `"${id}" is already an area`;
  return null;
}

/** Why `id` can't name a new word type (layout), or null when it can. */
export function wordTypeIdProblem(d: Design, id: string): string | null {
  if (!id) return 'Give the word type an id.';
  if (!/^[A-Za-z][A-Za-z0-9_]*$/.test(id)) return `"${id}" can't be an id: use letters, digits and _ only, starting with a letter.`;
  if (d.layouts.some((l) => l.name === id)) return `"${id}" is already a word type.`;
  return null;
}

/** Add an empty area to a design (in place). */
export function addArea(d: Design, id: string, label: string, size: [number, number]) {
  d.areas[id] = { label: label.trim() || id, size: [size[0], size[1]], glyphs: [] };
}

/** Why `id` can't be deleted, one sentence per reason (empty when it can): it still holds glyphs,
 *  or a word type has a part that uses it. */
export function deleteAreaProblems(d: Design, id: string): string[] {
  const a = d.areas[id];
  if (!a) return [`There is no area "${id}".`];
  const out: string[] = [];
  const n = a.glyphs.length;
  if (n) out.push(`It still has ${n} glyph${n === 1 ? '' : 's'}. Remove ${n === 1 ? 'it' : 'them'} first: Manage, then × on each.`);
  const uses = usedIn(d, id).map((l) => l.label ?? l.name);
  if (uses.length) out.push(`${uses.join(', ')} ${uses.length === 1 ? 'uses' : 'use'} it. Take it out of ${uses.length === 1 ? 'that word type' : 'those word types'} in Structure (Advanced) first.`);
  return out;
}
