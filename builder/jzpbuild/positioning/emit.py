"""GPOS feature text from a Design: one chained-context rule per word shape.

Two lookups hold the rules, `pos_y` (centering + cursive chain) and `pos_x`
(plain x adjustments), with identical contexts, so both consume the same
glyph runs. Within a lookup a longer rule is tried before a shorter one at
the same position; once a rule matches, its glyphs are consumed and no other
rule can reposition them. That ordering is the only scoping mechanism and it
is the same one the classic single-lookup build relied on.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

from .. import config
from .resolve import Unresolvable, pins_needed, resolve
from .schema import Design, Layout
from .shapes import Shape, enumerate_shapes

WILD = "@area_wild"


def _ident(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.]", "_", text)


def _fmt(v: float) -> str:
    return str(int(round(v)))


@dataclass
class Rule:
    layout: str
    shape: Shape
    bucket: tuple
    tokens: list[str]
    y_lookups: list[list[str]]     # per token
    x_lookups: list[list[str]]

    def render(self, which: str) -> str:
        lks = self.y_lookups if which == "y" else self.x_lookups
        parts = [t + "'" + "".join(f" lookup {n}" for n in names) for t, names in zip(self.tokens, lks)]
        return "  pos " + " ".join(parts) + ";"


@dataclass
class Emission:
    lines: list[str]
    rules: list[Rule]
    skipped: list[tuple[str, Shape, dict]]
    pair_lookups: int
    other_classes: dict[str, list[str]] = field(default_factory=dict)


class _Registry:
    """Lookup definitions shared by every rule, named by content."""

    def __init__(self, design: Design):
        self.design = design
        self.pairs: dict[tuple[str, str, int], str] = {}
        self.cens: dict[int, str] = {}
        self.xs: dict[int, str] = {}
        self.other: dict[str, list[str]] = {}

    def glyphs_of(self, token: str) -> list[str]:
        if token.startswith("@area_"):
            return self.design.areas[token[len("@area_"):]].glyphs
        if token.startswith("@"):
            return self.other[token]
        return [token]

    def pair(self, tok_a: str, tok_b: str, dy: int) -> str:
        return self.pairs.setdefault((tok_a, tok_b, dy), f"cur{len(self.pairs)}")

    def cen(self, y: int) -> str:
        return self.cens.setdefault(y, "cen_" + _fmt(y).replace("-", "m"))

    def x(self, v: int) -> str:
        return self.xs.setdefault(v, "x_" + _fmt(v).replace("-", "m"))

    def render(self) -> list[str]:
        out = []
        for name, glyphs in self.other.items():
            out.append(f"{name} = [ {' '.join(glyphs)} ];")
        for (a, b, dy), name in self.pairs.items():
            ga, gb = self.glyphs_of(a), self.glyphs_of(b)
            both = set(ga) & set(gb)
            out.append(f"lookup {name} {{")
            # child.y = parent.y + exit(parent) - entry(child): exit 0, entry -dy
            if both:
                for g in ga:
                    out.append(f"  pos cursive {g} <anchor 0 {-dy}> <anchor 0 0>;" if g in both
                               else f"  pos cursive {g} <anchor NULL> <anchor 0 0>;")
                for g in gb:
                    if g not in both:
                        out.append(f"  pos cursive {g} <anchor 0 {-dy}> <anchor NULL>;")
            else:
                out.append(f"  pos cursive {a} <anchor NULL> <anchor 0 0>;")
                out.append(f"  pos cursive {b} <anchor 0 {-dy}> <anchor NULL>;")
            out.append(f"}} {name};")
        for y, name in self.cens.items():
            out += [f"lookup {name} {{", f"  pos {WILD} <0 {y} 0 0>;", f"}} {name};"]
        for v, name in self.xs.items():
            out += [f"lookup {name} {{", f"  pos {WILD} <{v} 0 0 0>;", f"}} {name};"]
        return out


def _buckets(design: Design, layout: Layout, shape: Shape, reg: _Registry) -> list[dict[str, str | None]]:
    """Every combination of pinned glyph identities this shape needs: for
    each element some conditional gap names, one option per named glyph plus
    an "other" option (None) when the area holds glyphs no entry names."""
    pins = pins_needed(layout, shape, design)
    if not pins:
        return [{}]
    axes = []
    for name, glyphs in pins.items():
        area = design.areas[shape.element(name).area]
        options: list[str | None] = list(glyphs)
        rest = [g for g in area.glyphs if g not in glyphs]
        if rest:
            cls = f"@pos_{_ident(layout.name)}__{_ident(name)}__other"
            reg.other[cls] = rest
            options.append(None)
        axes.append((name, options))
    return [dict(zip((n for n, _ in axes), combo))
            for combo in itertools.product(*(opts for _, opts in axes))]


def _token(design: Design, layout: Layout, shape: Shape, name: str, pinned: dict[str, str | None]) -> str:
    e = shape.element(name)
    if name in pinned:
        g = pinned[name]
        return g if g else f"@pos_{_ident(layout.name)}__{_ident(name)}__other"
    return f"@area_{e.area}"


def build_rules(design: Design) -> tuple[list[Rule], list, _Registry]:
    reg = _Registry(design)
    rules: list[Rule] = []
    skipped = []
    for li, layout in enumerate(design.layouts):
        for shape in enumerate_shapes(layout):
            for pinned in _buckets(design, layout, shape, reg):
                try:
                    pos = resolve(design, layout, shape, {n: g for n, g in pinned.items() if g})
                except Unresolvable as err:
                    skipped.append((layout.name, shape, pinned, str(err), err.info))
                    continue
                tokens = [_token(design, layout, shape, e.name, pinned) for e in shape.elements]
                y_lk: list[list[str]] = []
                x_lk: list[list[str]] = []
                pen = 0
                root = True
                prev_tok = prev_y = None
                for e, tok in zip(shape.elements, tokens):
                    x, y = pos[e.name]
                    adv = design.areas[e.area].advance
                    xoff = int(round(x)) - pen
                    x_lk.append([reg.x(xoff)] if xoff else [])
                    if adv:                      # chain breaker: consumed, never attached
                        y_lk.append([])
                        pen += adv
                        root = True
                        continue
                    if root:
                        y_lk.append([reg.cen(int(round(y)))])
                        root = False
                    else:
                        dy = int(round(y)) - prev_y
                        y_lk.append([reg.pair(prev_tok, tok, dy)])
                    prev_tok, prev_y = tok, int(round(y))
                if not any(x_lk):
                    x_lk[0] = [reg.x(0)]
                rules.append(Rule(layout.name, shape, tuple(sorted(pinned.items())), tokens, y_lk, x_lk))
    order = {l.name: i for i, l in enumerate(design.layouts)}
    rules.sort(key=lambda r: (-len(r.tokens), order[r.layout], r.shape.sort_key(), str(r.bucket)))
    return rules, skipped, reg


# fontTools compiles each run of rules between `subtable;` breaks as one block and gives up when a
# block passes the 64 KB offset limit ("All candidates overflowed"), which a big design reaches at
# ~1,600 rules. Breaking the run every so many rules keeps each block small; matching is unchanged,
# because subtables are tried in order, just as the rules are within one.
RULES_PER_SUBTABLE = 300


def _with_breaks(lines: list[str]) -> list[str]:
    out: list[str] = []
    for i, line in enumerate(lines):
        if i and i % RULES_PER_SUBTABLE == 0:
            out.append("  subtable;")
        out.append(line)
    return out


CLEANUP_RULES = (
    # hide stray glyphs of half-formed words (up to 10 deep), and give space
    # its advance back at word boundaries -- carried over from the classic build
    ("numbersign", WILD, "<-1000 0 0 0>"),
    ("@new_word_char", "@space_char", "<0 0 -1000 0>"),
)


def gen_gpos(design: Design) -> Emission:
    rules, skipped, reg = build_rules(design)
    lines = ["# --- positioning (jzpbuild.positioning): one rule per word shape, cursive chains ---"]
    lines += reg.render()
    lines.append("lookup pos_y {")
    lines += _with_breaks([r.render("y") for r in rules])
    lines.append("} pos_y;")
    lines.append("lookup pos_x {")
    lines += _with_breaks([r.render("x") for r in rules])
    lines.append("} pos_x;")
    lines += ["", "feature kern {", "  lookup pos_y;", "  lookup pos_x;"]
    for context, marked, value in CLEANUP_RULES:
        for n in range(10, -1, -1):
            tokens = " ".join([context] + [WILD] * n + [f"{marked}'"])
            lines.append(f"  pos {tokens} {value};")
    lines.append("} kern;")
    return Emission(lines=lines, rules=rules, skipped=skipped, pair_lookups=len(reg.pairs),
                    other_classes=dict(reg.other))


# ---------------------------------------------------------------- statistics

_BYTES_PER_TOKEN = 2
_BYTES_PER_LOOKUP_RECORD = 4
_BYTES_PER_RULE = 14


def stats(design: Design) -> dict:
    """Shape/rule counts and a byte estimate, for the editor's badge."""
    rules, skipped, reg = build_rules(design)
    per_layout: dict[str, dict] = {}
    for l in design.layouts:
        mine = [r for r in rules if r.layout == l.name]
        per_layout[l.name] = {
            "shapes": len(enumerate_shapes(l)),
            "rules": len(mine),
            "skipped": sum(1 for s in skipped if s[0] == l.name),
            "est_bytes": sum(_BYTES_PER_RULE + _BYTES_PER_TOKEN * len(r.tokens)
                             + _BYTES_PER_LOOKUP_RECORD * sum(len(x) for x in r.y_lookups) for r in mine),
        }
    total = sum(v["est_bytes"] for v in per_layout.values())
    return {"rules": len(rules), "skipped": len(skipped), "pair_lookups": len(reg.pairs),
            "centering_lookups": len(reg.cens), "x_lookups": len(reg.xs),
            "est_bytes": total, "per_layout": per_layout,
            "skipped_by_layout": skipped_groups(skipped)}


def skipped_groups(skipped, max_examples: int = 8) -> dict[str, list[dict]]:
    """Skipped shape/glyph combinations grouped by cause, per layout, for the
    editor: {layout: [{kind, elem, axis, base, count, glyphs, examples}]}."""
    groups: dict[str, dict[tuple, dict]] = {}
    for lname, shape, pinned, msg, info in skipped:
        kind = info.get("kind", "other")
        key = (kind, info.get("elem") or ",".join(info.get("elems", [])), str(info.get("axis")), str(info.get("base")))
        g = groups.setdefault(lname, {}).setdefault(key, {
            "kind": kind, "elem": info.get("elem"), "elems": info.get("elems"), "axis": info.get("axis"),
            "base": info.get("base"), "count": 0, "base_glyphs": set(), "elem_glyphs": set(), "examples": []})
        g["count"] += 1
        if info.get("base_glyph"):
            g["base_glyphs"].add(info["base_glyph"])
        if info.get("elem_glyph"):
            g["elem_glyphs"].add(info["elem_glyph"])
        if len(g["examples"]) < max_examples:
            g["examples"].append({"names": list(shape.names), "pinned": {k: v for k, v in pinned.items() if v}, "message": msg})
    out: dict[str, list[dict]] = {}
    for lname, by_key in groups.items():
        lst = []
        for g in by_key.values():
            g["base_glyphs"] = sorted(g["base_glyphs"])
            g["elem_glyphs"] = sorted(g["elem_glyphs"])
            lst.append(g)
        out[lname] = sorted(lst, key=lambda g: -g["count"])
    return out
