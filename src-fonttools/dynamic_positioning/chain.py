"""Resolve absolute (x, y) positions for one word combination, for a
specific right-hand signifier (an ASCII key, e.g. "k" for lg_gou), using
one anchors.AnchorEngine (i.e. one geometry.LAYOUTS entry / topology).

Fully generic dependency-graph resolver -- no hardcoded element names
anywhere. Given the engine's own `flat_optional` (which elements are
optional, derived from `order`, see geometry.py's LAYOUTS comment) and
which of those are present in this word, plus every OTHER element the
layout's `relationships` declare (always resolved, whether or not it's
optional), resolves each element's (x, y) in dependency order:
whichever relationship candidate's base is either root (None) or itself
going to be resolved is the one used, picking the first such candidate in
declaration order when more than one qualifies (same "first-declared /
most-specific wins" convention used elsewhere in this codebase, e.g.
anchors.resolve_gap's signifier matching and build.py's own rule
ordering).

An always-present element (not in flat_optional) is allowed to fail to
resolve for a given signifier -- e.g. string_top/string_bottom have no
catch-all gap, so KeyError is expected for every signifier but li's; that
gets silently treated as "this element doesn't apply here," not an error
(see build.py, which uses exactly this to decide whether a signifier is
double-string, with no separate flag). An OPTIONAL element that's marked
present must resolve, or it's a real authoring bug (missing relationship
or gap coverage) -- that's allowed to raise.

After resolving, the whole composed word is shifted so it's centered on
geometry.CENTER_Y, per the engine's vertical_center_order, regardless of
which optional elements are present -- rather than hanging from one
element's fixed default Y and only growing in one direction. See
README.md.
"""

from . import anchors, geometry


def _choose_relationships(engine: "anchors.AnchorEngine", present: dict[str, bool],
                           to_resolve: set[str]) -> dict[str, dict[str, dict]]:
    """For each element in `to_resolve`, per axis, the relationship
    candidate to use -- purely from presence, no values needed yet.

    Preference order (most to least specific), NOT declaration order (a
    root/base=None default is typically declared before its overrides, so
    "first candidate whose base qualifies" would pick root every time --
    that's a real bug this function exists to avoid):
    1. Among candidates whose base is a ranked (engine.optional_order)
       element that's actually present, the one with the HIGHEST rank
       (latest typed) -- reconstructs "attach to whichever optional
       element was typed most recently" without a sequential walk.
       Only ever considers bases THIS element's own relationships
       actually declare, not every ranked element typed before it --
       e.g. area_right has no base="zhu" candidate at all (deliberately,
       to avoid a cycle with zhu depending on area_right), so zhu typed
       present never makes it a candidate for area_right here either,
       with no special-casing needed.
    2. A candidate whose base is a guaranteed-resolvable, non-ranked
       (always-present) element, e.g. zhu's base="right".
    3. The root (base=None) default, as a last resort.
    """
    rank = {elem: i for i, elem in enumerate(engine.flat_optional)}
    chosen: dict[str, dict[str, dict]] = {}
    for elem in to_resolve:
        chosen[elem] = {}
        for axis in ("x", "y"):
            candidates = engine.relationships_for(axis, elem)
            if not candidates:
                continue
            ranked = [c for c in candidates if c["base"] in rank and present.get(c["base"])]
            if ranked:
                chosen[elem][axis] = max(ranked, key=lambda c: rank[c["base"]])
                continue
            always = [c for c in candidates if c["base"] is not None and c["base"] not in rank]
            if always:
                chosen[elem][axis] = always[0]
                continue
            root = next((c for c in candidates if c["base"] is None), None)
            if root is None:
                raise KeyError(
                    f"no relationship for elem={elem!r} axis={axis!r} in layout {engine.name!r} "
                    f"resolvable given present={present!r}")
            chosen[elem][axis] = root
    return chosen


def resolve(engine: "anchors.AnchorEngine", present: dict[str, bool],
            present_glyphs: dict[str, str]) -> dict[str, tuple[float, float]]:
    """Absolute (x, y) origin for every element this word resolves.

    `present`: presence flags for engine.optional_order's elements
    (missing/False = absent). Everything else engine.relationships
    declares is resolved unconditionally. `present_glyphs` is {area: glyph}
    for every area whose specific glyph identity is pinned down in this
    word/rule variant (the pivot's own area -> its own glyph, plus
    whichever other areas' specific glyph this variant pins down -- see
    build.py's identity-sensitive-area branching); an area missing from
    this dict is "unpinned" for this variant. Used to resolve any gap that
    varies by a relationship's base and/or elem area's own glyph identity
    (anchors.resolve_gap's base_signifiers/elem_signifiers).
    """
    flat_optional = set(engine.flat_optional)
    always_present = engine.declared_elems - flat_optional
    to_resolve = {e for e in flat_optional if present.get(e)} | always_present

    chosen = _choose_relationships(engine, present, to_resolve)

    resolved: dict[str, dict[str, float]] = {}
    # Elements that permanently failed to resolve (an always_present element
    # whose own gap/candidate lookup raised KeyError -- "doesn't apply to
    # this word", see module docstring). Tracked separately from `resolved`
    # so a dependent of a failed base can be recognized as itself
    # permanently unresolvable, rather than waiting forever for a base that
    # will never show up in `resolved` -- that starvation used to surface as
    # a misleading "cyclic dependency?" ValueError even though there was no
    # cycle, just a base that legitimately opted out.
    failed: set[str] = set()
    remaining = set(to_resolve)
    while remaining:
        progressed = False
        for elem in list(remaining):
            bases = {rel["base"] for rel in chosen[elem].values() if rel["base"] is not None}
            if bases & failed:
                # A dependency permanently failed -- this elem can never
                # resolve either. Cascade the same always_present/optional
                # distinction the KeyError handler below applies directly.
                if elem in always_present:
                    remaining.discard(elem)
                    failed.add(elem)
                    progressed = True
                    continue
                raise KeyError(
                    f"elem={elem!r} in layout {engine.name!r} depends on "
                    f"{bases & failed!r}, which failed to resolve for "
                    f"present_glyphs={present_glyphs!r}")
            if not bases <= resolved.keys():
                continue  # a dependency isn't resolved yet -- try again next pass
            try:
                values = {}
                elem_glyph = present_glyphs.get(elem)
                for axis, rel in chosen[elem].items():
                    if rel["base"] is None:
                        values[axis] = anchors.resolve_gap(rel["gap"], None, elem_glyph)
                    else:
                        base_glyph = present_glyphs.get(rel["base"])
                        values[axis] = (resolved[rel["base"]][axis]
                                         + engine.anchor(rel, base_glyph, elem_glyph))
            except KeyError:
                if elem in always_present:
                    remaining.discard(elem)
                    failed.add(elem)
                    progressed = True
                    continue
                raise
            if values:
                resolved[elem] = values
            remaining.discard(elem)
            progressed = True
        if not progressed:
            raise ValueError(
                f"can't make progress resolving {remaining!r} in layout {engine.name!r} "
                "-- cyclic dependency?")

    present_for_centering = {**present, **{e: True for e in always_present}}
    top, bottom = _centering_bounds(engine, resolved, present_for_centering)
    shift = geometry.CENTER_Y - (top + bottom) / 2

    return {elem: (v["x"], v["y"] + shift) for elem, v in resolved.items()}


def _rank_box(engine: "anchors.AnchorEngine", rank_group: list[str],
              resolved: dict[str, dict[str, float]],
              present: dict[str, bool]) -> tuple[float, float] | None:
    """(top_y, bottom_y) of whichever element in this rank group is
    present and resolved, or None if none of them are."""
    for elem in rank_group:
        if present.get(elem) and elem in resolved:
            y = resolved[elem]["y"]
            return (y + engine.areas[elem][1], y)
    return None


def _centering_bounds(engine: "anchors.AnchorEngine", resolved: dict[str, dict[str, float]],
                       present: dict[str, bool]) -> tuple[float, float]:
    boxes = [box for rank in engine.vertical_center_order
             if (box := _rank_box(engine, rank, resolved, present)) is not None]
    if not boxes:
        raise ValueError(f"no present element found in layout {engine.name!r}'s vertical_center_order")
    return boxes[0][0], boxes[-1][1]


def bare_fy(engine: "anchors.AnchorEngine") -> tuple[float, float]:
    """The one case with no right-hand glyph at all: just area_fy, centered
    on its own height alone (top == bottom == fy's own span)."""
    x = engine.default("x", "fy", None)
    y = engine.default("y", "fy", None)
    top = y + engine.areas["fy"][1]
    bottom = y
    shift = geometry.CENTER_Y - (top + bottom) / 2
    return (x, y + shift)
