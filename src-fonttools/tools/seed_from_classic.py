"""Seed per-signifier gap entries in dynamic_positioning/layouts_data.json
for right-hand families from the classic inputs/layouts.json frames.

    cd src-fonttools && python3 tools/seed_from_classic.py loki nc tiao mo
    python3 tools/seed_from_classic.py --dry-run loki     # print, don't write

For each family's signifier glyphs this adds the family's keys to
default_jzp's selector and, for every relationship whose value is
family-specific (the ones that reference `right`, the pivot), a gap entry
derived from the classic frame by inverting anchors.AnchorEngine.anchor():

    base_edge bottom, elem_edge top (default):  gap = E.y - B.y + E.h
    base_edge top,    elem_edge top:            gap = E.y - B.y - B.h + E.h
    base_edge left,   elem_edge left:           gap = E.x - B.x
    base_edge left,   elem_edge right (default): gap = E.x - B.x + E.w

Which classic frame supplies the numbers: `layout_<fam>` (left/hui
present) for everything, except right<-jc from `layout_<fam>2` (the jc
variant) and right<-fy from `layout_<fam>3` (the no-left variant -- the
only classic frame where fy sits directly above right).

Entries are inserted before the existing catch-all, so already-covered
signifiers (gou/io/li) resolve exactly as before; a scalar gap becomes a
list with the scalar as its catch-all. `x string` is re-expressed as
string <- right (left edges) with catch-all 155, which reproduces the old
root value 325 for every existing family. These are starting points for
the layout editor, not final values -- the dynamic model's boxes are
approximations of the classic frames, not copies.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jzpbuild import config  # noqa: E402
from dynamic_positioning import signifiers  # noqa: E402

LAYOUT = "default_jzp"


def classic_frame(classic: dict, fam: str, variant: str) -> dict[str, tuple[int, int]]:
    """{area: (x, yd)} for one classic frame, area names without `area_`."""
    frame = classic[f"layout_{fam}{variant}"]
    return {k[len("area_"):]: (v["x"], v["yd"]) for k, v in frame.items() if isinstance(v, dict)}


def derived_gaps(classic: dict, fam: str, sizes: dict[str, tuple[int, int]]) -> dict[tuple, int]:
    """{(axis, elem, base): gap} for the family-specific relationships."""
    L, L2, L3 = (classic_frame(classic, fam, v) for v in ("", "2", "3"))
    rw, rh = sizes["right"]

    def bottom_top(E, B, frame):   # elem's top at base's bottom + gap
        return frame[E][1] - frame[B][1] + sizes[E][1]

    def top_top(E, B, frame):      # elem's top at base's top + gap
        return frame[E][1] - frame[B][1] - sizes[B][1] + sizes[E][1]

    return {
        ("y", "right", "fy"): bottom_top("right", "fy", L3),
        ("y", "right", "hui"): bottom_top("right", "hui", L),
        ("y", "right", "left"): bottom_top("right", "left", L),
        ("y", "right", "jc"): bottom_top("right", "jc", L2),
        ("x", "zhu", "right"): L["zhu"][0] - L["right"][0] + sizes["zhu"][0],   # left/right edges
        ("y", "zhu", "right"): top_top("zhu", "right", L),
        ("x", "string", "right"): L["string"][0] - L["right"][0],              # left/left edges
        ("y", "string", "right"): top_top("string", "right", L),
    }


def ensure_string_x_relationship(layout: dict) -> dict:
    """The `x string <- right` relationship (left edges), creating it with
    the catch-all that reproduces the old root value if it doesn't exist."""
    for rel in layout["relationships"]:
        if (rel["axis"], rel["elem"], rel["base"]) == ("x", "string", "right"):
            return rel
    root = next(r for r in layout["relationships"] if (r["axis"], r["elem"], r["base"]) == ("x", "string", None))
    right_root = next(r for r in layout["relationships"] if (r["axis"], r["elem"], r["base"]) == ("x", "right", None))
    rel = {"axis": "x", "elem": "string", "base": "right", "base_edge": "left", "elem_edge": "left",
           "gap": [{"value": root["gap"] - right_root["gap"]}]}
    layout["relationships"].insert(layout["relationships"].index(root) + 1, rel)
    return rel


def add_entry(rel: dict, key: str, glyphs: list[str], value: int) -> None:
    """Insert {key: glyphs, value} before the catch-all (or convert a scalar
    gap into [entry, catch-all])."""
    if not isinstance(rel["gap"], list):
        rel["gap"] = [{"value": rel["gap"]}]
    gap = rel["gap"]
    catch_all = next((i for i, e in enumerate(gap)
                      if not e.get("base_signifiers") and not e.get("elem_signifiers")), len(gap))
    gap.insert(catch_all, {key: list(glyphs), "value": int(round(value))})


def seed(families: list[str], dry_run: bool) -> None:
    classic = json.loads(config.LAYOUTS_JSON.read_text())
    data = json.loads(config.DYNAMIC_LAYOUTS_JSON.read_text())
    sizes = {k: tuple(v) for k, v in data["area_sizes"].items()}
    layout = next(l for l in data["layouts"] if l["name"] == LAYOUT)
    by_key = {(r["axis"], r["elem"], r["base"]): r for r in layout["relationships"]}

    for fam in families:
        glyphs = config.RIGHT_SELECTORS[fam]
        keys = [k for k, g in signifiers.KEY_TO_GLYPH.items() if g in glyphs]
        print(f"== {fam}: glyphs {glyphs}, keys {keys}")
        for k in keys:
            if k not in layout["selector"]["contains"]:
                layout["selector"]["contains"].append(k)
        for (axis, elem, base), value in derived_gaps(classic, fam, sizes).items():
            rel = ensure_string_x_relationship(layout) if (axis, elem, base) == ("x", "string", "right") \
                else by_key[(axis, elem, base)]
            # the pivot's glyph is the condition: it's the elem when elem ==
            # right, the base otherwise
            key = "elem_signifiers" if elem == "right" else "base_signifiers"
            add_entry(rel, key, glyphs, value)
            print(f"   {axis} {elem:7} <- {base:6} {key.split('_')[0]:4} in {glyphs}: gap = {value}")

    if dry_run:
        print("(dry run, nothing written)")
        return
    config.DYNAMIC_LAYOUTS_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {config.DYNAMIC_LAYOUTS_JSON}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("families", nargs="+", choices=sorted(config.RIGHT_SELECTORS))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    seed(args.families, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
