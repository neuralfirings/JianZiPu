"""Generic engine turning one geometry.LAYOUTS entry's relationships into
resolved coordinates.

No hardcoded per-area-pair formulas, and no hardcoded assumption about
which area is anyone's "base" -- every relationship has the same shape,
for either axis, whether or not `base` is null, so one engine resolves
all of them for whichever LAYOUTS entry it's built from. `chain.py`
decides, per word, which relationship applies to which element; this
module only knows how to turn one relationship dict into a number.

One AnchorEngine per geometry.LAYOUTS entry -- see build.py's
`_engine_for_key`, which is the only place that picks which engine
applies to a given word.
"""

# axis -> which edge is the box's own local origin ("near") vs the far side
# ("far"), and which index into an areas dict's (w, h) tuple is that
# axis's size.
_AXIS_INFO = {
    "y": {"size_index": 1, "near_edge": "bottom", "far_edge": "top"},
    "x": {"size_index": 0, "near_edge": "left", "far_edge": "right"},
}


def resolve_gap(gap, base_glyph: str | None, elem_glyph: str | None) -> float:
    """`gap` is either a plain number (same regardless of glyph identity), or
    an ordered list of override entries, each shaped
    {"base_signifiers": [...], "elem_signifiers": [...], "value": N} (either
    or both keys omittable), evaluated FIRST-MATCH-WINS in list order (not
    "most specific wins" -- authoring is responsible for ordering specific
    entries before any catch-all, same as everywhere else in this codebase
    that says "first-declared wins"). An entry matches if every signifier
    key it declares is satisfied: `base_glyph in entry["base_signifiers"]`
    (if that key is present) AND `elem_glyph in entry["elem_signifiers"]`
    (if that key is present) -- so an entry can condition on the
    relationship's `base` area's own glyph identity, its `elem` area's own
    glyph identity, both at once (a genuine conjunction, e.g. "only when
    base is md_9 AND elem is md_bar"), or neither (an unconditional
    catch-all, matches regardless of base_glyph/elem_glyph -- put these
    last in the list, nothing enforces the ordering for you).

    `base_glyph`/`elem_glyph` are the literal glyph names (components.csv's
    glyph_name column) actually present for the relationship's `base`/`elem`
    areas in this specific word/rule variant, or None if that area's
    identity isn't pinned down in this variant (e.g. axis has no base, or
    the area isn't glyph-identity-sensitive here) -- an entry that declares
    a signifier key for an unpinned side simply never matches."""
    if isinstance(gap, (int, float)):
        return gap
    if not isinstance(gap, list):
        raise TypeError(f"unrecognized gap shape: {gap!r}")
    for entry in gap:
        base_sigs = entry.get("base_signifiers")
        if base_sigs is not None and base_glyph not in base_sigs:
            continue
        elem_sigs = entry.get("elem_signifiers")
        if elem_sigs is not None and elem_glyph not in elem_sigs:
            continue
        return entry["value"]
    raise KeyError(
        f"no gap override matches base_glyph={base_glyph!r} elem_glyph={elem_glyph!r} in {gap!r}")


class AnchorEngine:
    """Resolves relationships for one geometry.LAYOUTS entry (one spatial-
    adjacency graph / "topology")."""

    def __init__(self, layout: dict):
        self.name = layout["name"]
        self.areas = layout["areas"]
        self.vertical_center_order = layout["vertical_center_order"]
        self.relationships = layout["relationships"]
        # the real typed/glyph-sequence order (flat -- see geometry.py's
        # LAYOUTS comment for why no sibling grouping is needed here,
        # unlike vertical_center_order) -- can't be derived from
        # `relationships` at all, it's a fact about the input, not the
        # geometry.
        self.order = layout["order"]
        self.flat_optional = [e["area"] for e in self.order if e["optional"]]
        # every always-present (non-optional) element -- resolved
        # unconditionally, whether or not it's this word's pivot.
        self.always_present = {e["area"] for e in self.order if not e["optional"]}
        # the one always-present element whose glyph IS the signifier
        # itself (gets classes.signifier_token(...) instead of a generic
        # "@area_{elem}" token) -- see build.py. Exactly one entry should
        # have pivot=True.
        pivots = [e["area"] for e in self.order if e.get("pivot")]
        if len(pivots) != 1:
            raise ValueError(
                f"layout {self.name!r}'s order must mark exactly one area pivot=True, "
                f"found {pivots!r}")
        self.pivot = pivots[0]
        # Optional per-layout approximation of chain.py's whole-stack
        # vertical centering shift: instead of the exact topmost/bottommost
        # `vertical_center_order` span calculation (chain._centering_bounds),
        # sum a fixed contribution per RANK that has at least one present
        # member (OR-then-sum, not one contribution per present element --
        # same-rank siblings like default_jzp's ["left", "hui"] sit side by
        # side, not stacked, so a second present member of an already-
        # counted rank adds no additional height). Absent `centering` key ->
        # "exact" mode, today's behavior, byte-for-byte unchanged -- this is
        # what keeps every layout that doesn't opt in guaranteed untouched.
        # See dynamic_positioning/README.md's "Approximate additive
        # centering" section and build.py's `optional_lookahead`, which
        # relies on `centering_mode`/`centering_per_rank` to shrink rule
        # count once a layout opts in.
        centering = layout.get("centering")
        self.centering_mode = centering["mode"] if centering else "exact"
        self.centering_per_rank = centering.get("per_rank") if centering else None
        # "additive_lookups" is the same OR-then-sum model as "additive",
        # but realized as separate accumulating GPOS lookups (one per rank)
        # instead of one literal pre-summed total per presence-combination
        # -- see build.py's _signifier_rules_lookups and
        # ACCUM_LOOKUPS_PLAN.md. Shares "additive"'s per_rank shape/
        # validation exactly; only build.py's rule-generation path differs.
        if self.centering_mode in ("additive", "additive_lookups"):
            if len(self.centering_per_rank) != len(self.vertical_center_order):
                raise ValueError(
                    f"layout {self.name!r}'s centering.per_rank must have one entry per "
                    f"vertical_center_order rank ({len(self.vertical_center_order)}), "
                    f"got {len(self.centering_per_rank)}")
        self.declared_elems = {rel["elem"] for rel in self.relationships}
        self._by_axis_elem: dict[tuple[str, str], list[dict]] = {}
        for rel in self.relationships:
            self._by_axis_elem.setdefault((rel["axis"], rel["elem"]), []).append(rel)

    def relationships_for(self, axis: str, elem: str) -> list[dict]:
        """Every relationship declared for (axis, elem), in geometry.py order."""
        return self._by_axis_elem.get((axis, elem), [])

    def root_relationship(self, axis: str, elem: str) -> dict:
        """The base=None (root default) relationship for (axis, elem)."""
        for rel in self.relationships_for(axis, elem):
            if rel["base"] is None:
                return rel
        raise KeyError(f"no root relationship for axis={axis!r} elem={elem!r} in layout {self.name!r}")

    def override_relationship(self, axis: str, elem: str, base: str) -> dict:
        """The relationship for (axis, elem) whose base is exactly `base`."""
        for rel in self.relationships_for(axis, elem):
            if rel["base"] == base:
                return rel
        raise KeyError(
            f"no relationship for axis={axis!r} elem={elem!r} base={base!r} in layout {self.name!r}")

    def declared_relationship(self, axis: str, elem: str) -> dict:
        """The single relationship for (axis, elem) -- for elements with no
        predecessor ambiguity (leaves: zhu, string, string_top,
        string_bottom), where exactly one relationship should exist per
        axis, whatever its base is. Raises if that assumption doesn't
        hold, rather than silently picking one -- geometry.py authoring
        should keep leaves unambiguous."""
        rels = self.relationships_for(axis, elem)
        if len(rels) != 1:
            raise ValueError(
                f"expected exactly one {axis}-relationship for elem={elem!r} in layout "
                f"{self.name!r}, found {len(rels)} -- use override_relationship/"
                f"root_relationship directly if {elem!r} genuinely has multiple candidate bases")
        return rels[0]

    def edge_span(self, axis: str, area: str, edge: str | None) -> float:
        """Distance from `area`'s own near-edge origin to `edge` of its box.
        `edge=None` (or the axis's near edge) -> 0 (that IS the origin);
        the axis's far edge -> the box's full size along this axis."""
        info = _AXIS_INFO[axis]
        return self.areas[area][info["size_index"]] if edge == info["far_edge"] else 0

    def anchor(self, rel: dict, base_glyph: str | None = None, elem_glyph: str | None = None) -> float:
        """The offset (along rel['axis']) from `base`'s own near-edge
        origin to `elem`'s own near-edge origin, such that `elem`'s
        `elem_edge` (default: the axis's FAR edge -- top for y, right for
        x) lands at `base`'s `base_edge` (default: the axis's NEAR edge --
        bottom for y, left for x) position plus `gap`. Both `elem_edge`
        and `base_edge` accept the axis-appropriate edge names explicitly
        ("top"/"bottom" for y, "left"/"right" for x) if you want to write
        the default out instead of relying on it. Meaningless when
        rel['base'] is None -- use `default` on the root relationship
        directly for that case (see chain.py). `base_glyph`/`elem_glyph`
        are this relationship's `base`/`elem` areas' own specific glyph in
        the current word/rule variant, or None if unpinned -- see
        resolve_gap."""
        axis = rel["axis"]
        info = _AXIS_INFO[axis]
        elem, base = rel["elem"], rel["base"]
        base_edge = rel.get("base_edge", info["near_edge"])
        elem_edge = rel.get("elem_edge", info["far_edge"])
        base_span = self.edge_span(axis, base, base_edge)
        gap = resolve_gap(rel["gap"], base_glyph, elem_glyph)
        target_local = base_span + gap  # position of elem's chosen edge, in base's local coords
        elem_size = self.areas[elem][info["size_index"]]
        # convert from "elem's chosen edge position" to "elem's own
        # near-edge-origin position"
        return target_local - elem_size if elem_edge == info["far_edge"] else target_local

    def default(self, axis: str, elem: str, elem_glyph: str | None = None) -> float:
        """elem's own near-edge-origin position along `axis` when it has no
        base at all (root default) -- a literal absolute value, not an
        offset. No `base_glyph` parameter -- a root relationship has no
        base, so a "base_signifiers" entry on one would never match
        anything; only `elem_signifiers` makes sense here."""
        rel = self.root_relationship(axis, elem)
        return resolve_gap(rel["gap"], None, elem_glyph)
