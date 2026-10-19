# jzpbuild.positioning

Geometry-derived GPOS from `inputs/design.json`. The model and the file
format are documented in `builder/README.md` ("`jzpbuild/positioning/`
and `inputs/design.json`") and in `schema.py`'s docstring; this file is the
short map.

| Module | Does |
|---|---|
| `schema.py` | parse + validate the design file (`load_design`, `parse_design`, `validate`, `dump_design`) |
| `shapes.py` | enumerate concrete word shapes per layout (`enumerate_shapes`), sorted longest first with `priority` tie-breaks |
| `resolve.py` | absolute x/y per part for one shape and one set of pinned glyphs (`resolve`, `plan`, `pins_needed`) |
| `emit.py` | the feature text (`gen_gpos`), per-shape rules with glyph buckets (`build_rules`), and `stats` for the app's budget badge |

Why cursive attachment: one chained-context rule per word shape, every
glyph marked; the first glyph gets the word's absolute centred y, each
later glyph a cursive pair lookup whose entry anchor is its delta to the
previous glyph. That gives "anchor + marks" layout for standard words,
`:` vertical stacks and `|` chords with the same mechanism, shapes the same
on HarfBuzz and CoreText, and keeps rule counts proportional to the number
of word shapes rather than to the number of glyph combinations. x is a
separate pass (`pos_x`) because cursive attachment rewrites x offsets.

Tests: `tests/test_positioning.py` (toy design, runs without pytest),
`tests/parity_report.py` (vs the classic build), `tests/shaper_parity.py`
(HarfBuzz vs CoreText).
