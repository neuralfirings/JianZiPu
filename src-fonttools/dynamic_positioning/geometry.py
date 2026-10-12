"""Layout data for dynamic_positioning: area sizes, the centering target,
and one spatial-adjacency graph ("topology") per LAYOUTS entry.

Everything here is loaded from config.DYNAMIC_LAYOUTS_JSON (edited by
tools/jzpbuilder-dynamic.html); this module just exposes it. No fontTools
imports on purpose -- the geometry stays reviewable independent of feaLib.

Each layout carries two orderings that are deliberately kept separate:

- `order`: the real typed/glyph-sequence order -- a fact about the shaped
  text, which build.py uses to construct correct backtrack/lookahead
  context. Exactly one entry is the `pivot` (the element whose glyph IS the
  signifier); `optional` entries may be absent from a word.
- `relationships`: which element's POSITION each element is computed
  relative to -- a pure authoring choice, with no assumption that `base`
  was typed before `elem`. chain.py resolves it as a small dependency
  graph, not a sequential walk.

Relationship shape:
    {"axis": "x"|"y", "elem": <area>, "base": <area>|None,
     "base_edge": <edge>|omitted, "elem_edge": <edge>|omitted, "gap": Gap}

`elem`'s `elem_edge` is placed at `base`'s `base_edge` position plus `gap`,
in `base`'s own local coordinates (origin at its bottom-left corner). For
axis="y" the edges are "top"|"bottom" (base_edge default "bottom",
elem_edge default "top"); for axis="x" they're "left"|"right" (defaults
"left"/"right"). So by default elem's far edge is measured from base's near
edge -- "elem's top touches base's bottom plus gap"; spell the edges out
only when a relationship genuinely needs the other pairing (anchors.py).
`base=None` means no dependency: `gap` is then the literal absolute value.

Gap shape: a plain number, OR an ordered list of override entries
`{"base_signifiers": [...], "elem_signifiers": [...], "value": N}` (either
key omittable), evaluated FIRST-MATCH-WINS in list order
(anchors.resolve_gap) -- put any catch-all entry last yourself, nothing
enforces it. Signifiers are glyph names (e.g. "lg_gou", "md_5"), matched
against the relationship's `base` / `elem` area's glyph respectively. This
is what lets lg_gou and lg_da (same classic family) get independently
tuned values, and lets a gap depend on either side's identity or both.

`vertical_center_order`: visual top-to-bottom rank groups, used ONLY for
the whole-stack centering shift onto CENTER_Y (chain._centering_bounds).
Same-rank siblings (e.g. left/hui) sit side by side; either may define that
rank's box. There is no X-axis equivalent yet: CENTER_X is loaded but
nothing recenters on it.
"""

import json

from jzpbuild import config

# RIGHT_SELECTORS families this module positions; classic gpos.py's rules
# for them are zeroed under --dynamic_pos. Distinct from config.RIGHT_KEYS,
# which is classic's own "six standard families" list.
FAMILIES = ("gou", "io", "li")

_data = json.loads(config.DYNAMIC_LAYOUTS_JSON.read_text())

CENTER_X = _data["center_x"]
CENTER_Y = _data["center_y"]

# Per-area box sizes (w, h) in font units, shared by reference across every
# LAYOUTS entry (see below) -- not derived from glyph outlines, since
# positions are computed before outlines exist in this pipeline's build
# order. See README.md "Known simplifications".
AREA_SIZES = {k: tuple(v) for k, v in _data["area_sizes"].items()}

# One entry per topology; gou/io/li share "default_jzp" (differently
# proportioned signifiers within one shape). `selector.contains` lists the
# ASCII keys (signifiers.py) routed to each entry -- see
# build._engine_for_key. Every entry's "areas" is the same shared AREA_SIZES
# object, so editing one area's size affects every layout that uses it.
LAYOUTS = _data["layouts"]
for _layout in LAYOUTS:
    _layout["areas"] = AREA_SIZES
