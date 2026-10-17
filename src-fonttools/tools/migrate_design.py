"""One-off migration to the v2 design file (inputs/design.json).

Sources:
- dynamic_positioning/layouts_data.json  -> the standard word layout (gaps as
  tuned there), re-expressed in the slot model with `right` optional so words
  without a right-hand glyph are covered too;
- inputs/layouts.json (classic Figma frames) -> the vertical and chord layouts
  and the no-right-hand roots;
- inputs/components.csv area_* columns -> area glyph membership (then the
  columns are dropped from the CSV: the design file is the only source).

Run from src-fonttools:  python3 tools/migrate_design.py [--write]
"""

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from jzpbuild import config  # noqa: E402

OLD_DYN = HERE / "dynamic_positioning" / "layouts_data.json"
CLASSIC = json.loads((HERE / "inputs" / "layouts.json").read_text())
OUT = config.INPUTS_DIR / "design.json"

AREA_COLUMNS = {
    "area_fy": "fy", "area_left": "left", "area_hui": "hui", "area_mod_jc": "jc",
    "area_mod_zhu": "zhu", "area_right": "right", "area_string": "string",
    "area_char": "char", "area_chord": "chord",
}
LABELS = {
    "fy": "泛音 harmonic", "left": "Left hand", "hui": "徽 position", "jc": "急/绰 modifier",
    "zhu": "注 modifier", "right": "Right hand", "string": "String", "char": "Character",
    "chord": "Chord", "colon": "Vertical marker", "bar": "Chord divider",
}


def convert_gap(gap):
    if not isinstance(gap, list):
        return gap
    out = []
    for e in gap:
        n = {}
        if e.get("base_signifiers") is not None:
            n["when_base"] = list(e["base_signifiers"])
        if e.get("elem_signifiers") is not None:
            n["when_elem"] = list(e["elem_signifiers"])
        n["value"] = e["value"]
        out.append(n)
    return out


def rel(axis, elem, base, gap, base_edge=None, elem_edge=None):
    r = {"axis": axis, "elem": elem, "base": base}
    if base_edge:
        r["base_edge"] = base_edge
    if elem_edge:
        r["elem_edge"] = elem_edge
    r["gap"] = gap
    return r


def standard_layout(old):
    lay = next(l for l in old["layouts"] if l["name"] == "default_jzp")
    order = [e["area"] for e in lay["order"]]
    optional = [e["area"] for e in lay["order"] if e["optional"]]
    rank = {a: i for i, a in enumerate(optional)}
    # old engine priority: optional base with the highest rank, then
    # always-present base, then root -> declaration order here
    rels = []
    by_key = {}
    for r in lay["relationships"]:
        by_key.setdefault((r["axis"], r["elem"]), []).append(r)
    for key, cands in by_key.items():
        def prio(r):
            b = r["base"]
            if b is None:
                return (2, 0)
            if b in rank:
                return (0, -rank[b])
            return (1, 0)
        for r in sorted(cands, key=prio):
            gap = convert_gap(r["gap"])
            if r["axis"] == "y" and r["base"] == "fy" and gap == 0:
                # classic frames: fy sits 30 above hui/left, but overlaps a jc
                # box by 47 (the 急 glyph's ink is small)
                gap = 47 if r["elem"] == "jc" else -30
            if r["axis"] == "y" and r["base"] == "fy" and r["elem"] == "right":
                # fy directly over the right-hand glyph (no left/hui): seed the
                # families the old data left at 0 from the classic *3 frames
                gap = [e for e in gap if not (e.get("when_elem") is None)]
                for fam, frame in (("gou", "layout_gou3"), ("io", "layout_io3"), ("li", "layout_li3")):
                    fr = CLASSIC[frame]
                    v = (fr["area_right"]["yd"] + fr["area_right"]["h"]) - fr["area_fy"]["yd"]
                    gap.append({"when_elem": config.RIGHT_SELECTORS[fam], "value": v})
                gap.append({"value": 0})
            rels.append(rel(r["axis"], r["elem"], r["base"], gap,
                            r.get("base_edge"), r.get("elem_edge")))
    # Re-seed every per-family gap from the classic frames (layout_<fam>,
    # <fam>2 = with jc, <fam>3 = no left/hui) so the migrated font matches the
    # released one as closely as the chain model allows.
    fams = config.RIGHT_SELECTORS
    def frame(fam, suffix=""):
        return CLASSIC[f"layout_{fam}{suffix}"]
    def top(a):
        return a["yd"] + a["h"]
    def per_family(fn, key):
        return [{key: list(glyphs), "value": int(round(fn(fam)))} for fam, glyphs in fams.items()]
    seeded = {
        ("y", "right", "hui"): per_family(lambda f: top(frame(f)["area_right"]) - frame(f)["area_hui"]["yd"], "when_elem"),
        ("y", "right", "left"): per_family(lambda f: top(frame(f)["area_right"]) - frame(f)["area_left"]["yd"], "when_elem"),
        ("y", "right", "jc"): per_family(lambda f: top(frame(f, "2")["area_right"]) - frame(f, "2")["area_jc"]["yd"], "when_elem"),
        ("y", "right", "fy"): per_family(lambda f: top(frame(f, "3")["area_right"]) - frame(f, "3")["area_fy"]["yd"], "when_elem"),
        ("y", "zhu", "right"): per_family(lambda f: frame(f)["area_zhu"]["yd"] + 470 - top(frame(f)["area_right"]), "when_base"),
        ("y", "string", "right"): per_family(lambda f: top(frame(f)["area_string"]) - top(frame(f)["area_right"]), "when_base"),
        ("x", "string", "right"): per_family(lambda f: frame(f)["area_string"]["x"] - frame(f)["area_right"]["x"], "when_base"),
        ("x", "zhu", "right"): per_family(lambda f: frame(f)["area_zhu"]["x"] + 115 - frame(f)["area_right"]["x"], "when_base"),
        ("y", "string_top", "right"): [{"when_base": fams["li"], "value": int(round(top(frame("li")["area_string_top"]) - top(frame("li")["area_right"])))}],
        ("y", "string_bottom", "right"): [{"when_base": fams["li"], "value": int(round(top(frame("li")["area_string_bottom"]) - top(frame("li")["area_right"])))}],
    }
    for r in rels:
        key = (r["axis"], r["elem"], r["base"])
        if key in seeded:
            r["gap"] = seeded[key]
    # roots and gaps for words without a right-hand glyph (classic layout_blank*)
    rels += [
        rel("y", "string", "jc", 0, base_edge="bottom"),
        rel("y", "string", "hui", -35, base_edge="bottom"),
        rel("y", "string", "left", -35, base_edge="bottom"),
        rel("y", "string", None, 125),
        rel("y", "zhu", "jc", 6, base_edge="bottom"),
        rel("y", "zhu", "hui", -32, base_edge="bottom"),
        rel("y", "zhu", "left", -32, base_edge="bottom"),
        rel("y", "zhu", None, 125),
        rel("x", "zhu", None, 209),
    ]
    # the per-signifier x rules reference `right` first, then the roots
    rels.sort(key=lambda r: 0 if r["base"] is not None else 1)
    slots = []
    for a in order:
        if a == "string":
            slots.append({"name": "string", "optional": True,
                          "alternatives": [["string"], ["string_top:string", "string_bottom:string"]]})
        else:
            slots.append({"name": a, "optional": True, "alternatives": [[a]]})
    return {
        "name": "standard", "label": "Standard word",
        "slots": slots,
        "requires_any": ["fy", "left", "hui", "jc", "zhu", "right"],
        "relationships": rels,
        # classic never re-centers for fy (it just stacks on top) and keeps
        # hui/left at the same height with or without a string below
        "center": {"y": [g for grp in lay["vertical_center_order"] for g in grp if g != "fy"] + ["string"],
                   "y_phantom": ["string"], "x": None},
    }


def vertical_layout():
    return {
        "name": "vertical", "label": "Vertical (after :)",
        "slots": [
            {"name": "colon", "alternatives": [["colon"]]},
            {"name": "row", "repeat": [1, 4], "alternatives": [["char"], ["left", "hui"]]},
        ],
        "relationships": [
            rel("x", "colon", None, 0), rel("y", "colon", None, 0),
            rel("x", "char", None, 325), rel("x", "left", None, 150),
            rel("x", "hui", "left", 0, base_edge="right", elem_edge="left"),
            rel("y", "char", "prev", -35, base_edge="bottom"),
            rel("y", "left", "prev", -35, base_edge="bottom"),
            rel("y", "char", None, 0), rel("y", "left", None, 0),
            rel("y", "hui", "left", 0, base_edge="top", elem_edge="top"),
        ],
        "center": {"y": ["row"], "x": None},
    }


def chord_layout():
    # classic layout_cuo_left/2/3 frames; right segment = same + 1300 in x
    def segment(prefix, dx, with_left=True):
        p = (lambda n: n) if not prefix else (lambda n: f"{prefix}{n}:{n}")
        name = (lambda n: n) if not prefix else (lambda n: f"{prefix}{n}")
        slots = []
        if with_left:
            slots.append({"name": name("left"), "optional": True, "alternatives": [[p("left")]]})
        slots += [
            {"name": name("hui"), "optional": True, "alternatives": [[p("hui")]]},
            {"name": name("jc"), "optional": True, "alternatives": [[p("jc")]]},
            {"name": name("zhu"), "optional": True, "alternatives": [[p("zhu")]]},
            {"name": name("string"), "optional": True, "alternatives": [[p("string")]]},
        ]
        n = name
        rels = [
            rel("x", n("left"), None, 0 + dx), rel("y", n("left"), None, 220),
            rel("x", n("hui"), n("left"), 0, base_edge="right", elem_edge="left"),
            rel("x", n("hui"), None, 350 + dx),
            rel("y", n("hui"), n("left"), 0, base_edge="top", elem_edge="top"),
            rel("y", n("hui"), None, 220),
            rel("x", n("jc"), None, 250 + dx),
            rel("y", n("jc"), n("hui"), -28, base_edge="bottom"),
            rel("y", n("jc"), n("left"), -28, base_edge="bottom"),
            rel("y", n("jc"), None, 365),
            rel("x", n("string"), n("hui"), -175, base_edge="left", elem_edge="left"),
            rel("x", n("string"), n("left"), 175, base_edge="left", elem_edge="left"),
            rel("x", n("string"), None, 215 + dx),
            rel("y", n("string"), n("jc"), 3, base_edge="bottom"),
            rel("y", n("string"), n("hui"), -35, base_edge="bottom"),
            rel("y", n("string"), n("left"), -35, base_edge="bottom"),
            rel("y", n("string"), None, 15),
            rel("x", n("zhu"), n("string"), -116, base_edge="left", elem_edge="left"),
            rel("x", n("zhu"), None, 99 + dx),
            rel("y", n("zhu"), n("string"), 0, base_edge="bottom", elem_edge="bottom"),
            rel("y", n("zhu"), n("jc"), 6, base_edge="bottom"),
            rel("y", n("zhu"), n("hui"), -32, base_edge="bottom"),
            rel("y", n("zhu"), n("left"), -32, base_edge="bottom"),
            rel("y", n("zhu"), None, 15),
        ]
        return slots, rels

    lslots, lrels = segment("", 0)
    rslots, rrels = segment("", 1300)
    # Two layouts, so the rule count is the SUM of the two segments' shapes,
    # not the product: the chord glyph anchors the left segment, the bar
    # (which advances the pen by one cell) anchors the right one.
    left = {
        "name": "chord", "label": "Chord (left of |)",
        "slots": [
            {"name": "fy", "optional": True, "alternatives": [["fy"]]},
            {"name": "chord", "alternatives": [["chord"]]},
            *lslots,
        ],
        "relationships": [
            rel("x", "chord", None, 250), rel("y", "chord", None, -200),
            rel("x", "fy", None, 575), rel("y", "fy", None, 1050),
            *lrels,
        ],
        "priority": ["string"],
        "center": {},
    }
    right = {
        "name": "chord_right", "label": "Chord (right of |)",
        "slots": [{"name": "bar", "alternatives": [["bar"]]}, *rslots],
        "relationships": [rel("x", "bar", None, 0), rel("y", "bar", None, 0), *rrels],
        "priority": ["string"],
        "center": {},
    }
    return [left, right]


def areas_from_csv(old):
    sizes = {k: list(v) for k, v in old["area_sizes"].items()}
    glyphs = {a: [] for a in AREA_COLUMNS.values()}
    with open(config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    for r in rows:
        for col, area in AREA_COLUMNS.items():
            if r.get(col, "").strip():
                glyphs[area].append(r["glyph_name"].strip())
    # hui decimals + blank (as features.py's hui_class_glyphs did)
    for n in range(1, 14):
        glyphs["hui"].append(f"md_{n}.blank")
        glyphs["hui"] += [f"md_{n}.{d}" for d in range(1, 10)]
    glyphs["hui"].append("blank")
    # a left-hand glyph can also be a plain character row in vertical mode
    # (classic special-cased ":大息"); the shape sort prefers the finger+position
    # reading whenever a position number follows
    glyphs["char"] += [g for g in glyphs["left"] if g not in glyphs["char"]]
    areas = {}
    for name in ["fy", "left", "hui", "jc", "zhu", "right", "string", "char", "chord", "colon", "bar"]:
        size = sizes.get(name) or {"char": [350, 350], "colon": [1000, 1000], "bar": [1000, 1000]}.get(name)
        a = {"label": LABELS[name], "size": size, "glyphs": glyphs.get(name, [])}
        if name == "colon":
            a["glyphs"], a["advance"] = ["blank_colon"], 1000
        if name == "bar":
            a["glyphs"], a["advance"] = ["blank_bar"], 1000
        areas[name] = a
    return areas, rows, fieldnames


def main(write: bool):
    old = json.loads(OLD_DYN.read_text())
    areas, rows, fieldnames = areas_from_csv(old)
    design = {
        "version": 2,
        "center": {"x": 500, "y": 300},
        "areas": areas,
        "layouts": [standard_layout(old), vertical_layout(), *chord_layout()],
    }
    text = json.dumps(design, ensure_ascii=False, indent=2) + "\n"
    if not write:
        print(text[:3000] + "\n...")
        return
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
    keep = [c for c in fieldnames if c not in AREA_COLUMNS and c != "area_hui_deci"]
    with open(config.COMPONENTS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keep)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in keep})
    print(f"rewrote {config.COMPONENTS_CSV} without area columns")


if __name__ == "__main__":
    main("--write" in sys.argv)
