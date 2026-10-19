"""Enumerate the concrete word shapes a layout can produce.

A *shape* is the ordered list of concrete elements of one word: which slots
are present, which alternative each holds, and how many instances a repeated
slot has. Every shape becomes exactly one GPOS rule (per glyph-identity
bucket, see emit.py), so the number of shapes is the number of rules.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from .schema import Layout, Slot


@dataclass(frozen=True)
class Element:
    name: str       # concrete name: "hui", or "char@2" for instance 2 of a repeated slot
    el: str         # element name as written in the layout ("char")
    area: str
    slot: str
    instance: int   # 0 for a non-repeated slot, 1.. for a repeated one


@dataclass(frozen=True)
class Shape:
    layout_name: str
    elements: tuple[Element, ...]
    choice: tuple               # per slot: None | alt index | tuple of alt indices (repeated)
    rank: tuple = ()            # per slot: sort rank (layout.priority first, then slot order)

    @property
    def names(self) -> list[str]:
        return [e.name for e in self.elements]

    def has(self, name: str) -> bool:
        """Present-ness of an element or slot name (any instance)."""
        return any(e.el == name or e.slot == name or e.name == name for e in self.elements)

    def instance_elements(self, slot: str, instance: int) -> list[Element]:
        return [e for e in self.elements if e.slot == slot and e.instance == instance]

    def element(self, name: str) -> Element:
        for e in self.elements:
            if e.name == name:
                return e
        raise KeyError(name)

    def sort_key(self) -> tuple:
        """Longer shapes first. Among equal lengths the shape whose present
        slots rank earlier wins, where the rank is the slot's position in the
        layout's `priority` list, then its typed order -- so a lone digit is
        read as hui in a standard word (hui slot before string slot) but as a
        string after a chord glyph (priority: string first), as classic did."""
        ranks = tuple(sorted(self.rank[i] for i, c in enumerate(self.choice) if c is not None))
        # fewer instances of a repeated slot first: ":大八" is one finger+position
        # row, not two character rows, when both readings fit
        instances = tuple(len(c) for c in self.choice if isinstance(c, tuple))
        return (-len(self.elements), ranks, instances, self.choice)


def _instances(slot: Slot, instance: int) -> list[list[Element]]:
    """Every alternative of `slot` as a list of concrete elements."""
    suffix = f"@{instance}" if instance else ""
    return [[Element(name=e.name + suffix, el=e.name, area=e.area, slot=slot.name, instance=instance)
             for e in alt] for alt in slot.alternatives]


def enumerate_shapes(layout: Layout) -> list[Shape]:
    per_slot: list[list[tuple[object, list[Element]]]] = []
    for s in layout.slots:
        options: list[tuple[object, list[Element]]] = []
        if s.optional:
            options.append((None, []))
        if s.repeat:
            lo, hi = s.repeat
            for n in range(lo, hi + 1):
                alts_per_instance = [_instances(s, i) for i in range(1, n + 1)]
                for combo in itertools.product(*(range(len(s.alternatives)) for _ in range(n))):
                    elems = [e for i, k in enumerate(combo) for e in alts_per_instance[i][k]]
                    options.append((combo, elems))
        else:
            for k, elems in enumerate(_instances(s, 0)):
                options.append((k, elems))
        per_slot.append(options)

    shapes = []
    slot_names = [s.name for s in layout.slots]
    rank = tuple((layout.priority.index(n) if n in layout.priority else len(layout.priority) + i)
                 for i, n in enumerate(slot_names))
    for combo in itertools.product(*per_slot):
        present = {slot_names[i] for i, (c, _) in enumerate(combo) if c is not None}
        if not present:
            continue
        ok = True
        for i, s in enumerate(layout.slots):
            if combo[i][0] is not None and any(req not in present for req in s.requires):
                ok = False
                break
        if not ok:
            continue
        elements = tuple(e for _, elems in combo for e in elems)
        shape = Shape(layout.name, elements, tuple(c for c, _ in combo), rank)
        if layout.requires_any and not any(shape.has(n) for n in layout.requires_any):
            continue
        shapes.append(shape)
    shapes.sort(key=Shape.sort_key)
    return shapes
