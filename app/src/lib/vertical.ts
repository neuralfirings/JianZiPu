// Which glyphs the font sets vertically without the colon typed (kept free of app state, so anything can use it).
import type { Design } from './api';

/** Glyphs only a vertical word can place: in an area a word type opening with the colon uses, and in no
 *  area any other word type uses (上, 下, 退…). The font sets a word holding one vertically without its
 *  colon. As `vertical_only_glyphs()` in builder/jzpbuild/features.py, but from the design being edited,
 *  so a glyph just put in such an area needs no colon at once. */
export function verticalOnlyGlyphs(d: Design | null): Set<string> {
  if (!d) return new Set();
  const colonAreas = new Set(Object.entries(d.areas).filter(([, a]) => a.glyphs.includes('blank_colon')).map(([n]) => n));
  const areaOf = (spec: string) => (spec.includes(':') ? spec.split(':')[1] : spec);
  const vertical: string[] = [], other = new Set<string>();
  for (const l of d.layouts) {
    const first = l.slots[0];
    const opens = colonAreas.size > 0 && !!first && !first.optional && first.alternatives.flat().every((s) => colonAreas.has(areaOf(s)));
    const used = new Set(l.slots.flatMap((s) => s.alternatives.flat().map(areaOf)));
    for (const name of Object.keys(d.areas).filter((n) => used.has(n))) {
      for (const g of d.areas[name].glyphs) {
        if (opens) { if (!vertical.includes(g)) vertical.push(g); } else other.add(g);
      }
    }
  }
  return new Set(vertical.filter((g) => !other.has(g) && g !== 'blank_colon'));
}
