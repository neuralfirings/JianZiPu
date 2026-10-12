"""One-shot converter: seed a NEW dynamic_positioning LAYOUTS entry with
absolute positions read straight from one classic builder/inputs/layouts.json
snapshot (the format jzpbuild/gpos.py reads -- {"layout_name": {"area_x":
{"x","y","w","h","yd"}, ...}}), so tools/jzpbuilder-dynamic.html has real
starting numbers to edit instead of a blank slate.

Deliberately NOT a faithful port: classic keeps one complete static frame per
presence-combination (layout_vertjzp1 for 1 row, ..vertjzp4 for 4 rows, each
with its own already-centered absolute y values), while dynamic_positioning
resolves ONE topology across every combination via relationships + a
whole-stack centering shift that's ALWAYS applied (even the default "exact"
centering_mode has no true off-switch at build time -- see chain.resolve).
This script only reads ONE chosen classic variant and writes every area's x
(axis="x") and yd (axis="y" -- the value gpos.py's fill_rule actually uses,
not the raw Figma "y") as a plain root relationship (base=None, i.e. classic
jzpbuild/gpos.py's "same value regardless of anything else"). Two real
consequences of that shortcut, both expected, not bugs:

1. Only the ONE row-count you converted from is seeded correctly. Import a
   different classic variant to reseed with a different row count's numbers.
2. dynamic_positioning's centering shift will apply ON TOP of these already-
   centered absolute values, likely shifting the whole word further than
   intended -- open the result in tools/jzpbuilder-dynamic.html and use its
   "vertically center character" toggle (raw, center=False view) to see the
   un-shifted numbers directly, then nudge each area to compensate, or add
   a `"centering": {"mode": "additive", "per_rank": [...]}` block once
   you've picked which classic variant's centering you want to match.

Usage:
    python3 -m dynamic_positioning.convert_classic_layout \\
        /path/to/classic/layouts.json layout_vertjzp4 \\
        --topology-name vertjzp_seed --pivot-area colon --key : \\
        -o /path/to/output/seed.layouts_data.json

Import the output file via tools/jzpbuilder-dynamic.html's "Import
layouts.json" button (it merges wholesale -- Save from there to actually
write it into the real config.DYNAMIC_LAYOUTS_JSON).
"""

import argparse
import json
import re
from pathlib import Path

from jzpbuild import config

_TRAILING_DIGITS_NO_UNDERSCORE = re.compile(r"^([a-zA-Z]+)(\d+)$")


def _normalize_area(area: str) -> str:
    """Classic layouts.json's own repeated-slot naming is inconsistent --
    "hui_1"/"left_1" (underscore) vs "char1"/"char2" (no underscore) even
    within the SAME layout_vertjzpN snapshot. dynamic_positioning's own
    convention (signifiers.csv_column_for's "_N" stripping, see README's
    "Repeated-slot areas") only recognizes the underscore form, so normalize
    every "wordN" area to "word_N" here rather than passing classic's
    naming through verbatim -- otherwise an area like "char1" would come
    through unrecognized (KeyError from csv_column_for) instead of
    resolving to components.csv's real "char" column."""
    m = _TRAILING_DIGITS_NO_UNDERSCORE.match(area)
    return f"{m.group(1)}_{m.group(2)}" if m else area


def convert(classic_layouts: dict, layout_name: str, topology_name: str,
            pivot_area: str, selector_keys: list[str],
            required_areas: set[str] = frozenset()) -> dict:
    """Build one dynamic_positioning LAYOUTS entry (plus its area_sizes
    contributions) from ONE classic `layout_name` snapshot. Every non-pivot
    area in the snapshot becomes a plain root (base=None) relationship pair
    (axis x -> its "x", axis y -> its "yd" -- see module docstring for why
    yd, not the raw Figma y). `pivot_area` is added separately as a
    zero-position root default (classic layouts.json has no entry for
    control-glyph pivots like vert-mode's colon -- see AREA_TO_CSV_COLUMN's
    own "chord"/"bar"/pivot areas for the general pattern this mirrors).
    `required_areas` marks which non-pivot areas are NOT optional (e.g. the
    first row's own character slot, since a word can't exist without it);
    everything else defaults to optional.
    """
    frame = classic_layouts[layout_name]
    areas = {_normalize_area(k[len("area_"):]): (v["w"], v["h"])
             for k, v in frame.items() if k.startswith("area_")}
    areas[pivot_area] = (0, 0)

    relationships = [
        {"axis": "x", "elem": pivot_area, "base": None, "gap": 0},
        {"axis": "y", "elem": pivot_area, "base": None, "gap": 0},
    ]
    order = [{"area": pivot_area, "optional": False, "pivot": True}]
    vc_rows: dict[str, list[str]] = {}
    for key, v in frame.items():
        if not key.startswith("area_"):
            continue
        area = _normalize_area(key[len("area_"):])
        relationships.append({"axis": "x", "elem": area, "base": None, "gap": v["x"]})
        relationships.append({"axis": "y", "elem": area, "base": None, "gap": v["yd"]})
        order.append({"area": area, "optional": area not in required_areas})
        # Group same-numbered-slot areas (char_1/hui_1/left_1, ...) into one
        # vertical_center_order rank, same-row convention -- see geometry.py.
        row = area.rsplit("_", 1)[-1] if "_" in area else area
        vc_rows.setdefault(row, []).append(area)

    layout = {
        "name": topology_name,
        "selector": {"contains": selector_keys},
        "vertical_center_order": list(vc_rows.values()),
        "relationships": relationships,
        "order": order,
    }
    return {"areas": areas, "layout": layout}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("classic_layouts_json", type=Path,
                    help="path to a classic builder/inputs/layouts.json-shaped file")
    p.add_argument("layout_name", help='key inside it to convert, e.g. "layout_vertjzp4"')
    p.add_argument("--topology-name", required=True, help="new LAYOUTS entry's own name")
    p.add_argument("--pivot-area", required=True,
                    help='the always-present pivot area (e.g. "colon" for vert-mode)')
    p.add_argument("--key", action="append", required=True, dest="selector_keys",
                    help="ASCII key routed to this topology (repeatable)")
    p.add_argument("--required", action="append", default=[], dest="required_areas",
                    help="a non-pivot area that's NOT optional (repeatable, e.g. --required char_1)")
    p.add_argument("-o", "--output", type=Path, required=True,
                    help="where to write the importable layouts_data.json-shaped file")
    args = p.parse_args()

    classic = json.loads(args.classic_layouts_json.read_text())
    if args.layout_name not in classic:
        raise SystemExit(f"{args.layout_name!r} not found in {args.classic_layouts_json} -- "
                          f"available: {sorted(classic)}")

    result = convert(classic, args.layout_name, args.topology_name, args.pivot_area,
                      args.selector_keys, set(args.required_areas))

    real = json.loads(config.DYNAMIC_LAYOUTS_JSON.read_text())
    existing_names = {layout["name"] for layout in real["layouts"]}
    if result["layout"]["name"] in existing_names:
        raise SystemExit(f"a LAYOUTS entry named {result['layout']['name']!r} already exists in "
                          f"{config.DYNAMIC_LAYOUTS_JSON} -- pick a different --topology-name")

    out = {
        "center_x": real["center_x"],
        "center_y": real["center_y"],
        "area_sizes": {**real["area_sizes"], **result["areas"]},
        "layouts": real["layouts"] + [result["layout"]],
        "area_to_csv_column": real["area_to_csv_column"],
    }
    args.output.write_text(json.dumps(out, indent=2))
    print(f"wrote {args.output} -- {len(out['layouts'])} layouts "
          f"(added {result['layout']['name']!r} seeded from {args.layout_name!r})")
    print("Import it in tools/jzpbuilder-dynamic.html (Import layouts.json button), "
          "review/retune, then Save to persist into the real layouts_data.json.")


if __name__ == "__main__":
    main()
