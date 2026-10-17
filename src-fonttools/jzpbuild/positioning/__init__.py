"""Glyph positioning for JianZiPu: the design file (inputs/design.json) in,
GPOS feature text out.

The model is "anchor + marks" implemented with OpenType cursive attachment:

- A *design* declares reusable **areas** (a box size plus the glyphs that
  may fill it), and **layouts** (a typed sequence of *slots*, each holding
  one of a few area alternatives, optional or not, possibly repeated), with
  **relationships** that say where each element sits relative to another
  element's edge plus a gap, and what the word is centered on.
- `shapes.enumerate_shapes` lists every concrete word shape a layout can
  produce (which slots are present, which alternative, how many repeats).
- `resolve.resolve` turns one shape into absolute (x, y) per element,
  honouring glyph-conditional gaps and centering.
- `emit.gen_gpos` writes one chained-context rule per shape (every element
  marked). The first glyph of each chain dispatches a single adjustment
  carrying the word's absolute y; every later glyph dispatches a tiny cursive
  lookup carrying its y-delta to the previous glyph. x is a second pass of
  identical rules dispatching plain x adjustments, because cursive attachment
  destroys any x offset already on the glyphs. No lookupflag RightToLeft is
  used anywhere: CoreText ignores it in left-to-right runs.

Glyphs whose area carries an `advance` (the vertical-mode colon, the chord
bar) are chain breakers: they are matched and consumed by the rule but never
attached to, and the element after them starts a fresh chain.
"""
