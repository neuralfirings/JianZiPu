"""Pure-data spatial-adjacency graph for the gou/io/li GPOS prototype.

No fontTools/feaLib imports here on purpose — this module is the literal,
reviewable translation of the composition's geometry into Python, checkable
independent of feaLib syntax. See README.md for background.

This is a rewrite of an earlier version of this module that modeled
positioning as a strict "typed order" chain (each element attaches to
whichever optional element was typed immediately before it). That
conflated two things that don't actually have to match: the ORDER GLYPHS
APPEAR IN THE SHAPED SEQUENCE (a real fact about the font, still used by
build.py to construct correct backtrack/lookahead context) and WHICH
ELEMENT'S POSITION A GIVEN ELEMENT IS COMPUTED RELATIVE TO (a pure
geometry/authoring choice). RELATIONSHIPS below is a spatial adjacency
graph -- "elem is positioned relative to base" -- with no assumption that
base was typed before elem. `chain.py` resolves it as a small dependency
graph, not a fixed sequential walk.

Stacking template (bottom to top, visual), area_left/area_hui side by side:

    [area_fy]
    [area_left][area_hui]
    [area_jc]
    [area_right]

area_fy, area_left+area_hui, area_jc are each independently optional and
form the "core chain" (chain.py's `_walk_core`) -- each attaches to
whichever of them is actually present in this word (still typed-order
recency among themselves, since that's a real ambiguity: which of several
possibly-present predecessors does a given element sit against).

area_right is always present for the families this module covers. Its own
Y attaches to whichever of jc/hui/left/fy precedes it, same recency rule,
or its own root default when none do.

area_zhu, area_string, area_string_top, area_string_bottom are LEAVES: each
is positioned purely as an offset from area_right's already-resolved
position (both axes), regardless of typed order. area_zhu is typed before
area_right but visually sits right up against the technique glyph, so its
position is authored that way -- see RELATIONSHIPS' area_zhu rows.

Relationship shape (see RELATIONSHIPS):
    {"axis": "x"|"y", "elem": <area>, "base": <area>|None,
     "base_edge": <edge>|omitted, "elem_edge": <edge>|omitted, "gap": Gap}

For axis="y", edges are "top"|"bottom" (base_edge default "bottom",
elem_edge default "top"). For axis="x", edges are "left"|"right"
(base_edge default "left", elem_edge default "right"). `elem`'s
`elem_edge` is placed at `base`'s `base_edge` position plus `gap` (both
expressed in `base`'s own local coordinates, base's own origin at its own
near corner -- bottom-left). Both edge fields are almost always left at
their default (elem's far edge measured from base's near edge -- e.g.
"elem's top touches base's bottom plus gap") -- write them out explicitly
only when a relationship genuinely needs the other edge (see anchors.py's
`anchor()`). `base=None` means "no dependency" -- `gap` is then the literal absolute
default value directly, not a relative offset.

Gap shape: a plain number (same value regardless of which specific
right-hand glyph/signifier is in play), OR an ordered list of
`{"signifiers": [<glyph name>, ...], "value": <number>}` overrides, with
an optional trailing entry that omits "signifiers" as a catch-all. A
specific signifier match always wins over the catch-all, regardless of
declaration order (see anchors.resolve_gap). "signifier" = an actual
right-hand PUA glyph name from config.RIGHT_SELECTORS (e.g. "lg_gou",
"lg_da"), the finest-grained unit this module can address -- this is what
lets e.g. lg_gou and lg_da (both family "gou") get independently-tuned
values instead of being forced to share one, unlike the classic pipeline's
own per-family (not per-glyph) granularity.

Many of the numeric gap values below are placeholders (per an explicit
decision this round to prioritize getting the new engine's shape right
over re-deriving exact classic-matching numbers) -- expect to retune them
against tests/test_shaping.py and font_tester.html.
"""

import json

from jzpbuild import config

from . import signifiers

RIGHT_KEYS = ("gou", "io", "li")

# Whether a signifier's word shape uses two string areas (area_string_top
# + area_string_bottom) instead of one is no longer a separate table --
# it's derived directly from whether a string_top/string_bottom
# relationship's gap actually resolves for that signifier (see the "U"-only
# gap lists below, and build.py's try/except around
# chain.resolve_double_string).

# All of AREA_SIZES/CENTER_X/CENTER_Y/LAYOUTS below are loaded from
# config.DYNAMIC_LAYOUTS_JSON rather than declared as Python literals here,
# so tools/jzpbuilder-dynamic.html can edit and save them directly. The
# schema (per-layout selector/vertical_center_order/relationships/order,
# a shared area_sizes map) matches what used to be hand-authored in this
# file 1:1 -- see dynamic_positioning/layouts_data.json.
_data = json.loads(config.DYNAMIC_LAYOUTS_JSON.read_text())

CENTER_X = _data["center_x"]
CENTER_Y = _data["center_y"]

# Generic per-area box sizes (w, h), in font design units. Shared by
# reference across every LAYOUTS entry below (see the "areas" assignment
# after LAYOUTS) -- not derived from real glyph outlines, since anchors are
# computed before glyph outlines exist in this pipeline's build order. See
# README.md "Known simplifications".
AREA_SIZES = {k: tuple(v) for k, v in _data["area_sizes"].items()}

# Visual top-to-bottom rank order, used ONLY for the whole-stack Y-axis
# centering shift (chain.py's _centering_bounds, which feeds CENTER_Y --
# there's no X-axis equivalent, nothing recenters on CENTER_X today). At
# resolve time: "top" = the topmost box among whichever ranks are
# actually present in this word, "bottom" = the bottommost. Same-rank
# groups (left/hui) sit side by side; either may define that rank's box.
# area_right is always present, so it's always eligible to be "bottom" --
# it's listed last for that reason, not because it's part of the core
# chain (it isn't; see module docstring). NOT the same as typed/glyph-
# sequence order (build.py's _ORDER) or attachment/dependency order
# (RELATIONSHIPS' own "base" pointers) -- three separate orderings that
# happen to agree for this topology, but aren't guaranteed to.
VERTICAL_CENTER_ORDER = [["fy"], ["left", "hui"], ["jc"], ["zhu"], ["right"]]

# One entry per distinct spatial-adjacency graph ("topology"). gou/io/li
# all share the one below -- they're differently-proportioned SIGNIFIERS
# within the same fy/left/hui/jc/right/zhu/string shape, not different
# shapes. A genuinely different shape (no area_right at all, or a repeated
# structure) needs its own entry here with its own areas/
# vertical_center_order/relationships -- e.g. cuo_left/cuo_right, added
# once dynamic_positioning
# actually covers cuo. `selector.contains` lists ASCII keys (see
# signifiers.py); anchors.AnchorEngine + chain.py are built against
# whichever entry a given key's `contains` list matches -- see build.py's
# `_engine_for_key`.
#
# Loaded from config.DYNAMIC_LAYOUTS_JSON (see AREA_SIZES above) rather
# than a Python literal -- each entry's "areas" is re-attached here as the
# same shared AREA_SIZES dict object every other entry uses, exactly as
# when this was hand-authored, so editing one area's size in
# tools/jzpbuilder-dynamic.html affects every layout that references it.
LAYOUTS = _data["layouts"]
for _layout in LAYOUTS:
    _layout["areas"] = AREA_SIZES
