"""Turn one shape into absolute (x, y) per element.

Positions are in *word frame* units: x from the pen position where the word
starts (so an element after a 1000-unit colon can sit at x=325 and the
emitter turns that into an offset of -675), y from the baseline.
"""

from __future__ import annotations

from .schema import AXIS_INFO, Design, Layout, Relationship
from .shapes import Element, Shape


class Unresolvable(Exception):
    """This shape/glyph combination has no position (a conditional gap with
    no matching entry). The emitter skips such combinations. `info` carries
    the structured cause (kind, elem, axis, base, glyphs) for the editor."""

    def __init__(self, msg: str, **info):
        super().__init__(msg)
        self.info = info


def resolve_gap(gap, base_glyph: str | None, elem_glyph: str | None) -> float:
    if isinstance(gap, (int, float)):
        return float(gap)
    for entry in gap:
        wb = entry.get("when_base")
        if wb is not None and base_glyph not in wb:
            continue
        we = entry.get("when_elem")
        if we is not None and elem_glyph not in we:
            continue
        return float(entry["value"])
    raise Unresolvable(f"no gap entry matches base={base_glyph!r} elem={elem_glyph!r}")


# ---------------------------------------------------------------- planning

def _base_present(shape: Shape, e: Element, rel: Relationship, layout: Layout) -> bool:
    b = rel.base
    if b is None:
        return True
    if b == "prev":
        return e.instance > 1
    slot = layout.element_slot(e.el)
    if b in slot.element_names:                      # sibling in the same slot (same instance)
        return any(x.el == b and x.instance == e.instance for x in shape.elements)
    return shape.has(b)


def plan(layout: Layout, shape: Shape) -> dict[tuple[str, str], Relationship | None]:
    """Which relationship positions each element on each axis: the first
    declared one whose base is present. Slot-level relationships (elem = the
    slot's name) apply to the first element of each instance."""
    chosen: dict[tuple[str, str], Relationship | None] = {}
    for e in shape.elements:
        first_of_instance = shape.instance_elements(e.slot, e.instance)[0] is e
        for axis in AXIS_INFO:
            cands = layout.relationships_for(axis, e.el)
            if first_of_instance:
                cands = cands + layout.relationships_for(axis, e.slot)
            chosen[(axis, e.name)] = next((r for r in cands if _base_present(shape, e, r, layout)), None)
    return chosen


def pins_needed(layout: Layout, shape: Shape, design: Design) -> dict[str, list[str]]:
    """Elements whose glyph identity some chosen relationship conditions on,
    mapped to the glyphs those conditions name (restricted to the element's
    area). The emitter adds an "other" bucket when the area has more glyphs."""
    refs: dict[str, dict[str, None]] = {}
    for (axis, name), rel in plan(layout, shape).items():
        if rel is None or not isinstance(rel.gap, list):
            continue
        e = shape.element(name)
        base_name = _base_name(shape, e, rel, layout)
        for entry in rel.gap:
            if entry.get("when_elem"):
                refs.setdefault(name, {}).update(dict.fromkeys(entry["when_elem"]))
            if entry.get("when_base") and base_name:
                refs.setdefault(base_name, {}).update(dict.fromkeys(entry["when_base"]))
    out = {}
    for name, glyphs in refs.items():
        area = design.areas[shape.element(name).area]
        out[name] = [g for g in glyphs if g in area.glyphs]
    return out


def _base_name(shape: Shape, e: Element, rel: Relationship, layout: Layout) -> str | None:
    """Concrete element name the relationship's base refers to (None for
    roots and for `prev`, whose box has no single glyph)."""
    b = rel.base
    if b in (None, "prev"):
        return None
    slot = layout.element_slot(e.el)
    if b in slot.element_names:
        return next(x.name for x in shape.elements if x.el == b and x.instance == e.instance)
    for x in shape.elements:
        if x.el == b or x.name == b:
            return x.name
    inst = shape.instance_elements(b, 0) or shape.instance_elements(b, 1)   # a slot name
    return inst[0].name if inst else None


# ---------------------------------------------------------------- resolving

def resolve(design: Design, layout: Layout, shape: Shape, pinned: dict[str, str] | None = None,
            center: bool = True, missing: dict[str, dict[str, str]] | None = None) -> dict[str, tuple[float, float]]:
    """x/y of each element. Raises Unresolvable on the first part that can't be placed, unless
    `missing` is given: then such a part sits at 0 on that axis and `missing[name][axis]` says why
    (the editor still draws the shape and marks the part)."""
    pinned = pinned or {}
    chosen = plan(layout, shape)
    pos: dict[tuple[str, str], float] = {}          # (axis, name) -> near-edge origin
    pending = set(chosen)

    def size(e: Element, axis: str) -> float:
        return design.areas[e.area].size[AXIS_INFO[axis]["size_index"]]

    def box(names: list[str], axis: str) -> tuple[float, float] | None:
        """(lo, hi) extent of a set of resolved elements along axis, or None."""
        if not names:
            return None
        lo = hi = None
        for n in names:
            if (axis, n) not in pos:
                return None
            e = shape.element(n)
            a, b = pos[(axis, n)], pos[(axis, n)] + size(e, axis)
            lo = a if lo is None else min(lo, a)
            hi = b if hi is None else max(hi, b)
        return (lo, hi)

    def step(key: tuple[str, str]) -> bool:
        """Place one (axis, element); False while its base isn't placed yet."""
        axis, name = key
        e = shape.element(name)
        rel = chosen[key]
        if rel is None:
            raise Unresolvable(f"{layout.name}: no relationship positions {name} on {axis} in shape {shape.names}",
                               kind="no_rule", elem=name, axis=axis)
        info = AXIS_INFO[axis]
        elem_glyph = pinned.get(name)
        if rel.base is None:
            try:
                pos[key] = resolve_gap(rel.gap, None, elem_glyph)
            except Unresolvable as err:
                raise Unresolvable(f"{layout.name}: {err} ({name} on {axis}, page rule)",
                                   kind="no_gap", elem=name, axis=axis, base=None, base_glyph=None, elem_glyph=elem_glyph) from None
            return True
        # base extent along this axis
        if rel.base == "prev":
            prev = shape.instance_elements(e.slot, e.instance - 1)
            ext = box([p.name for p in prev], axis)
            base_glyph = None
        else:
            bname = _base_name(shape, e, rel, layout)
            if bname is None:
                raise Unresolvable(f"{layout.name}: base {rel.base!r} of {name} absent", kind="base_absent", elem=name, axis=axis, base=rel.base)
            if bname == name:
                raise Unresolvable(f"{layout.name}: {name} positioned relative to itself", kind="self", elem=name, axis=axis)
            ext = box([bname], axis)
            base_glyph = pinned.get(bname)
        if ext is None:
            return False
        base_edge = rel.base_edge or info["near_edge"]
        elem_edge = rel.elem_edge or info["far_edge"]
        try:
            gap = resolve_gap(rel.gap, base_glyph, elem_glyph)
        except Unresolvable as err:
            raise Unresolvable(f"{layout.name}: {err} ({name} on {axis} relative to {rel.base})",
                               kind="no_gap", elem=name, axis=axis, base=rel.base, base_glyph=base_glyph, elem_glyph=elem_glyph) from None
        target = (ext[1] if base_edge == info["far_edge"] else ext[0]) + gap
        pos[key] = target - size(e, axis) if elem_edge == info["far_edge"] else target
        return True

    def stuck(key: tuple[str, str], err: Unresolvable) -> None:
        """Lenient mode: park the part at 0 on this axis and say why."""
        if missing is None:
            raise err
        missing.setdefault(key[1], {})[key[0]] = str(err).removeprefix(f"{layout.name}: ")
        pos[key] = 0.0

    while pending:
        progressed = False
        for key in sorted(pending):
            try:
                placed = step(key)
            except Unresolvable as err:
                stuck(key, err)
                placed = True
            if placed:
                pending.discard(key)
                progressed = True
        if not progressed:
            err = Unresolvable(f"{layout.name}: circular or dangling relationships for {sorted(pending)}",
                               kind="circular", elems=sorted(n for _, n in pending), axis=sorted({a for a, _ in pending}))
            if missing is None:
                raise err
            key = min(pending)       # park one part; the rest may then place against it
            stuck(key, Unresolvable(f"{layout.name}: its rules on {key[0]} go round in a circle"))
            pending.discard(key)

    def phantom_extent(axis: str, el: str) -> tuple[float, float] | None:
        """Where an absent element would sit: first relationship whose base
        is a present element (or the root), evaluated against the resolved
        positions. Same-slot and `prev` bases can't be present, so they're skipped."""
        area = design.areas[layout.element_area(el)]
        sz = area.size[AXIS_INFO[axis]["size_index"]]
        info = AXIS_INFO[axis]
        for rel in layout.relationships_for(axis, el):
            if rel.base is None:
                p = resolve_gap(rel.gap, None, None)
                return (p, p + sz)
            if rel.base == "prev" or rel.base in layout.element_slot(el).element_names:
                continue
            bname = next((x.name for x in shape.elements if x.el == rel.base or x.name == rel.base), None)
            if bname is None:
                continue
            ext = box([bname], axis)
            base_edge = rel.base_edge or info["near_edge"]
            elem_edge = rel.elem_edge or info["far_edge"]
            try:
                g = resolve_gap(rel.gap, pinned.get(bname), None)
            except Unresolvable:
                return None
            target = (ext[1] if base_edge == info["far_edge"] else ext[0]) + g
            p = target - sz if elem_edge == info["far_edge"] else target
            return (p, p + sz)
        return None

    shift = {"x": 0.0, "y": 0.0}
    if center:
        for axis, names, phantoms in (("y", layout.center_y, layout.center_y_phantom),
                                      ("x", layout.center_x, layout.center_x_phantom)):
            if not names:
                continue
            included = [e.name for e in shape.elements
                        if e.el in names or e.slot in names or e.name in names or e.el in phantoms]
            ext = box(included, axis)
            for el in phantoms:
                if shape.has(el):
                    continue            # present: already in `included`
                pe = phantom_extent(axis, el)
                if pe:
                    ext = pe if ext is None else (min(ext[0], pe[0]), max(ext[1], pe[1]))
            if ext:
                target = layout.y_target if axis == "y" else layout.x_target
                shift[axis] = target - (ext[0] + ext[1]) / 2
    return {e.name: (pos[("x", e.name)] + shift["x"], pos[("y", e.name)] + shift["y"]) for e in shape.elements}
