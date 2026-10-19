"""The design file: loading, light validation, and the typed view the rest
of the package works from.

File shape (inputs/design.json, version 2):

    {
      "version": 2,
      "center": {"x": 500, "y": 300},            # default centering targets
      "areas": {
        "left": {"label": "Left hand", "size": [350, 350],
                 "glyphs": ["md_ming", ...], "advance": 0}
      },
      "layouts": [
        {
          "name": "standard", "label": "Standard word",
          "slots": [
            {"name": "fy", "optional": true, "alternatives": [["fy"]]},
            {"name": "string", "optional": true,
             "alternatives": [["string"], ["string_top:string", "string_bottom:string"]]},
            {"name": "row", "repeat": [1, 4], "alternatives": [["char"], ["left", "hui"]]}
          ],
          "requires_any": ["left", "hui", ...],   # a shape must contain one of these
          "priority": ["string", "hui"],          # tie-break for equal-length shapes (see shapes.py)
          "relationships": [
            {"axis": "y", "elem": "hui", "base": "left",
             "base_edge": "top", "elem_edge": "top", "gap": 0},
            {"axis": "y", "elem": "right", "base": "jc",
             "gap": [{"when_elem": ["lg_gou"], "value": 100}, {"value": 30}]}
          ],
          "center": {"y": ["left", "hui", ...], "y_phantom": ["string"], "x": null, "y_target": 300}
        }
      ]
    }

Alternatives list *element* names; "el:area" names an element whose area
differs from its name (so one area can appear twice in a word, like li's two
strings, or hui on both sides of a chord). A bare name is both element and
area. A repeated slot's elements exist once per instance; relationships
written against the element name apply to every instance, and `base: "prev"`
means the previous instance's bounding box.

`center.y` lists the elements the vertical centering spans; `y_phantom`
lists elements that always count for the centering, even when the word
lacks them, positioned where they would sit (so a finger+position pair keeps
the same height with or without a string below it, as the classic frames
did). `y_target`/`x_target` override the design-wide centers.

Relationship semantics (unchanged from the previous engine): `elem`'s
`elem_edge` (default: the far edge, top/right) lands at `base`'s `base_edge`
(default: the near edge, bottom/left) plus `gap`, in font units. `base: null`
makes `gap` an absolute position. `gap` is a number or an ordered list of
`{"when_base": [...glyphs], "when_elem": [...glyphs], "value": N}` entries,
first match wins, so put the unconditional entry last. Among several
relationships for the same (axis, elem), the first whose base is present in
the word wins.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import config

AXIS_INFO = {
    "y": {"size_index": 1, "near_edge": "bottom", "far_edge": "top"},
    "x": {"size_index": 0, "near_edge": "left", "far_edge": "right"},
}


class DesignError(ValueError):
    pass


@dataclass
class Area:
    name: str
    size: tuple[float, float]
    glyphs: list[str]
    label: str = ""
    advance: int = 0


@dataclass(frozen=True)
class ElementSpec:
    """One entry of a slot alternative: an element name and the area it draws."""
    name: str
    area: str

    @classmethod
    def parse(cls, text: str) -> "ElementSpec":
        if ":" in text:
            name, area = text.split(":", 1)
            return cls(name.strip(), area.strip())
        return cls(text.strip(), text.strip())


@dataclass
class Slot:
    name: str
    alternatives: list[list[ElementSpec]]
    optional: bool = False
    repeat: tuple[int, int] | None = None     # (min, max) instances, or None
    requires: list[str] = field(default_factory=list)   # slot names that must be present

    @property
    def element_names(self) -> set[str]:
        return {e.name for alt in self.alternatives for e in alt}


@dataclass
class Relationship:
    axis: str
    elem: str
    base: str | None
    gap: object
    base_edge: str | None = None
    elem_edge: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class Layout:
    name: str
    slots: list[Slot]
    relationships: list[Relationship]
    center_y: list[str] | None          # element/slot names the vertical centering spans, or None
    center_x: list[str] | None
    center_y_phantom: list[str] = field(default_factory=list)
    center_x_phantom: list[str] = field(default_factory=list)
    y_target: float = 0.0
    x_target: float = 0.0
    requires_any: list[str] = field(default_factory=list)
    priority: list[str] = field(default_factory=list)
    label: str = ""
    raw: dict = field(default_factory=dict)

    def slot(self, name: str) -> Slot:
        for s in self.slots:
            if s.name == name:
                return s
        raise KeyError(name)

    def element_area(self, el: str) -> str:
        for s in self.slots:
            for alt in s.alternatives:
                for e in alt:
                    if e.name == el:
                        return e.area
        raise KeyError(f"layout {self.name!r} has no element {el!r}")

    def element_slot(self, el: str) -> Slot:
        for s in self.slots:
            if el in s.element_names:
                return s
        raise KeyError(f"layout {self.name!r} has no element {el!r}")

    def relationships_for(self, axis: str, el: str) -> list[Relationship]:
        return [r for r in self.relationships if r.axis == axis and r.elem == el]


@dataclass
class Design:
    areas: dict[str, Area]
    layouts: list[Layout]
    center_x: float
    center_y: float
    raw: dict

    def layout(self, name: str) -> Layout:
        for l in self.layouts:
            if l.name == name:
                return l
        raise KeyError(name)

    def all_glyphs(self) -> list[str]:
        seen: dict[str, None] = {}
        for a in self.areas.values():
            for g in a.glyphs:
                seen.setdefault(g, None)
        return list(seen)


# ---------------------------------------------------------------- parsing

def parse_design(d: dict) -> Design:
    if d.get("version") != 2:
        raise DesignError(f"design.json version must be 2, got {d.get('version')!r}")
    areas = {}
    for name, a in d["areas"].items():
        size = a["size"]
        areas[name] = Area(name=name, size=(float(size[0]), float(size[1])),
                           glyphs=list(a.get("glyphs", [])), label=a.get("label", ""),
                           advance=int(a.get("advance", 0)))
    center = d.get("center", {})
    cx, cy = float(center.get("x", 500)), float(center.get("y", 500))
    layouts = [parse_layout(l, areas, cx, cy) for l in d["layouts"]]
    design = Design(areas=areas, layouts=layouts, center_x=cx, center_y=cy, raw=d)
    validate(design)
    return design


def parse_layout(l: dict, areas: dict[str, Area], cx: float, cy: float) -> Layout:
    slots = []
    for s in l["slots"]:
        alts = [[ElementSpec.parse(t) for t in alt] for alt in s["alternatives"]]
        rep = s.get("repeat")
        slots.append(Slot(name=s["name"], alternatives=alts, optional=bool(s.get("optional", False)),
                          repeat=(int(rep[0]), int(rep[1])) if rep else None,
                          requires=list(s.get("requires", []))))
    rels = [Relationship(axis=r["axis"], elem=r["elem"], base=r.get("base"), gap=r["gap"],
                         base_edge=r.get("base_edge"), elem_edge=r.get("elem_edge"), raw=r)
            for r in l.get("relationships", [])]
    c = l.get("center", {}) or {}
    return Layout(name=l["name"], label=l.get("label", l["name"]), slots=slots, relationships=rels,
                  center_y=list(c["y"]) if c.get("y") else None,
                  center_x=list(c["x"]) if c.get("x") else None,
                  center_y_phantom=list(c.get("y_phantom", [])), center_x_phantom=list(c.get("x_phantom", [])),
                  y_target=float(c.get("y_target", cy)), x_target=float(c.get("x_target", cx)),
                  requires_any=list(l.get("requires_any", [])),
                  priority=list(l.get("priority", [])), raw=l)


def validate(design: Design) -> list[str]:
    """Raise DesignError on structural problems; return non-fatal warnings."""
    warnings: list[str] = []
    names = set()
    for l in design.layouts:
        if l.name in names:
            raise DesignError(f"duplicate layout name {l.name!r}")
        names.add(l.name)
        slot_names, el_names = set(), set()
        for s in l.slots:
            if s.name in slot_names:
                raise DesignError(f"{l.name}: duplicate slot {s.name!r}")
            slot_names.add(s.name)
            if not s.alternatives or any(not alt for alt in s.alternatives):
                raise DesignError(f"{l.name}/{s.name}: every slot needs at least one non-empty alternative")
            for alt in s.alternatives:
                for e in alt:
                    if e.area not in design.areas:
                        raise DesignError(f"{l.name}/{s.name}: unknown area {e.area!r}")
                    if e.name in el_names and l.element_slot(e.name) is not s:
                        raise DesignError(f"{l.name}: element {e.name!r} appears in two slots")
                    el_names.add(e.name)
            if s.repeat and (s.repeat[0] < 1 or s.repeat[1] < s.repeat[0]):
                raise DesignError(f"{l.name}/{s.name}: repeat must be [min>=1, max>=min]")
        for s in l.slots:
            for req in s.requires:
                if req not in slot_names:
                    raise DesignError(f"{l.name}/{s.name}: requires unknown slot {req!r}")
        for r in l.relationships:
            if r.axis not in AXIS_INFO:
                raise DesignError(f"{l.name}: bad axis {r.axis!r}")
            if r.elem not in el_names and r.elem not in slot_names:
                raise DesignError(f"{l.name}: relationship for unknown element {r.elem!r}")
            if r.base not in (None, "prev") and r.base not in el_names and r.base not in slot_names:
                raise DesignError(f"{l.name}: relationship {r.elem!r} has unknown base {r.base!r}")
            if isinstance(r.gap, list):
                if not r.gap:
                    raise DesignError(f"{l.name}: empty gap list on {r.axis} {r.elem}")
                last = r.gap[-1]
                if last.get("when_base") or last.get("when_elem"):
                    warnings.append(f"{l.name}: {r.axis} {r.elem} <- {r.base}: no unconditional "
                                    "last entry; words whose glyphs match no entry are not positioned")
                for e in r.gap:
                    if "value" not in e:
                        raise DesignError(f"{l.name}: gap entry without value on {r.axis} {r.elem}")
        for names_ in (l.center_y or []) + (l.center_x or []) + l.requires_any + l.priority \
                + l.center_y_phantom + l.center_x_phantom:
            if names_ not in el_names and names_ not in slot_names:
                raise DesignError(f"{l.name}: center/requires_any names unknown element {names_!r}")
        for el in el_names:
            for axis in AXIS_INFO:
                if not any(r.base is None for r in l.relationships_for(axis, el)) and \
                        not any(r.base is None for r in l.relationships_for(axis, l.element_slot(el).name)):
                    warnings.append(f"{l.name}: element {el!r} has no absolute {axis} position; "
                                    "it is only positioned when one of its bases is present")
    return warnings


def load_design(path: Path | None = None) -> Design:
    path = Path(path) if path else config.DESIGN_JSON
    return parse_design(json.loads(path.read_text(encoding="utf-8")))


def dump_design(d: dict) -> str:
    """Canonical serialization: stable key order, 2-space indent, trailing newline."""
    return json.dumps(d, ensure_ascii=False, indent=2) + "\n"
