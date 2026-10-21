"""Unit tests for jzpbuild.positioning: shapes, resolver, emitter.

Run:  cd builder && python3 -m pytest tests/test_positioning.py
  or  python3 tests/test_positioning.py   (no pytest needed)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import pytest
except ImportError:          # plain `python3 tests/test_positioning.py` works too
    class _Approx:
        def __init__(self, v, tol=1e-6):
            self.v, self.tol = v, tol

        def __eq__(self, other):
            return abs(other - self.v) <= self.tol

    class pytest:  # noqa: N801
        @staticmethod
        def fixture(f):
            return f

        approx = _Approx

from jzpbuild.positioning import emit, resolve, schema, shapes  # noqa: E402

TOY = {
    "version": 2,
    "center": {"x": 500, "y": 300},
    "areas": {
        "a": {"size": [100, 100], "glyphs": ["g_a1", "g_a2"]},
        "b": {"size": [100, 50], "glyphs": ["g_b"]},
        "c": {"size": [100, 100], "glyphs": ["g_c", "g_a1"]},
        "col": {"size": [1000, 1000], "glyphs": ["blank_colon"], "advance": 1000},
    },
    "layouts": [
        {
            "name": "word",
            "slots": [
                {"name": "a", "optional": True, "alternatives": [["a"]]},
                {"name": "b", "alternatives": [["b"]]},
                {"name": "c", "optional": True, "alternatives": [["c"], ["c1:c", "c2:c"]]},
            ],
            "relationships": [
                {"axis": "x", "elem": "a", "base": None, "gap": 0},
                {"axis": "x", "elem": "b", "base": None, "gap": 10},
                {"axis": "x", "elem": "c", "base": None, "gap": 20},
                {"axis": "x", "elem": "c1", "base": None, "gap": 20},
                {"axis": "x", "elem": "c2", "base": None, "gap": 20},
                {"axis": "y", "elem": "a", "base": None, "gap": 0},
                {"axis": "y", "elem": "b", "base": "a", "base_edge": "bottom",
                 "gap": [{"when_base": ["g_a1"], "value": -10}, {"value": 0}]},
                {"axis": "y", "elem": "b", "base": None, "gap": 500},
                {"axis": "y", "elem": "c", "base": "b", "gap": -5},
                {"axis": "y", "elem": "c1", "base": "b", "gap": -5},
                {"axis": "y", "elem": "c2", "base": "c1", "gap": 0},
            ],
            "center": {"y": ["a", "b"], "y_phantom": ["c"]},
        },
        {
            "name": "vert",
            "slots": [
                {"name": "col", "alternatives": [["col"]]},
                {"name": "row", "repeat": [1, 3], "alternatives": [["c"], ["a", "b"]]},
            ],
            "relationships": [
                {"axis": "x", "elem": "col", "base": None, "gap": 0},
                {"axis": "y", "elem": "col", "base": None, "gap": 0},
                {"axis": "x", "elem": "c", "base": None, "gap": 300},
                {"axis": "x", "elem": "a", "base": None, "gap": 200},
                {"axis": "x", "elem": "b", "base": "a", "base_edge": "right", "elem_edge": "left", "gap": 0},
                {"axis": "y", "elem": "c", "base": "prev", "base_edge": "bottom", "gap": -20},
                {"axis": "y", "elem": "a", "base": "prev", "base_edge": "bottom", "gap": -20},
                {"axis": "y", "elem": "c", "base": None, "gap": 0},
                {"axis": "y", "elem": "a", "base": None, "gap": 0},
                {"axis": "y", "elem": "b", "base": "a", "base_edge": "top", "elem_edge": "top", "gap": 0},
            ],
            "center": {"y": ["row"]},
        },
    ],
}


@pytest.fixture
def design():
    return schema.parse_design(TOY)


def test_shapes_word(design):
    L = design.layout("word")
    names = [s.names for s in shapes.enumerate_shapes(L)]
    assert ["a", "b", "c1", "c2"] in names and ["b"] in names
    assert names[0] == ["a", "b", "c1", "c2"]          # longest first
    assert len(names) == 2 * 3                           # a? x (none | c | c1+c2)


def test_shapes_vert_repeat(design):
    L = design.layout("vert")
    ss = shapes.enumerate_shapes(L)
    assert len(ss) == 2 + 4 + 8
    one_row_pair = next(s for s in ss if s.names == ["col", "a@1", "b@1"])
    two_rows = next(s for s in ss if s.names == ["col", "c@1", "c@2"])
    # same length: the single finger+position row sorts before two char rows
    assert ss.index(one_row_pair) < ss.index(two_rows)


def test_resolve_chain_and_conditional_gap(design):
    L = design.layout("word")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["a", "b"])
    pos = resolve.resolve(design, L, sh, {"a": "g_a1"}, center=False)
    assert pos["a"] == (0, 0) and pos["b"] == (10, -60)       # b.top = a.bottom - 10
    pos = resolve.resolve(design, L, sh, {"a": "g_a2"}, center=False)
    assert pos["b"] == (10, -50)


def test_resolve_first_present_base_wins(design):
    L = design.layout("word")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["b"])
    assert resolve.resolve(design, L, sh, center=False)["b"] == (10, 500)


def test_centering_with_phantom(design):
    L = design.layout("word")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["a", "b"])
    pos = resolve.resolve(design, L, sh, {"a": "g_a2"})
    # a 0..100, b -50..0, phantom c (b.bottom-5 - 100) -155..-55 -> mid -27.5 -> shift 327.5
    assert pos["a"][1] == pytest.approx(327.5)
    sh2 = next(s for s in shapes.enumerate_shapes(L) if s.names == ["a", "b", "c"])
    assert resolve.resolve(design, L, sh2, {"a": "g_a2"})["a"][1] == pytest.approx(327.5)


def _without_b_page_rule():
    import copy
    toy = copy.deepcopy(TOY)
    word = toy["layouts"][0]
    word["relationships"] = [r for r in word["relationships"] if not (r["axis"] == "y" and r["elem"] == "b" and r["base"] is None)]
    return schema.parse_design(toy)


def test_resolve_lenient_parks_the_unplaceable_part():
    d = _without_b_page_rule()
    L = d.layout("word")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["b", "c"])
    try:
        resolve.resolve(d, L, sh, center=False)
        raise AssertionError("strict resolve should fail: b has no y rule without a")
    except resolve.Unresolvable:
        pass
    missing = {}
    pos = resolve.resolve(d, L, sh, center=False, missing=missing)
    assert list(missing) == ["b"] and list(missing["b"]) == ["y"]
    assert "no relationship positions b on y" in missing["b"]["y"]
    assert pos["b"] == (10, 0)                    # x from its rule, y parked at 0
    assert pos["c"] == (20, -105)                 # c still hangs off b: top = b.bottom - 5


def test_resolve_payload_reports_unplaced():
    from jzpbuild import webserver
    d = _without_b_page_rule()
    L = d.layout("word")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["b"])
    r = webserver.resolve_payload(d, "word", [list(c) if isinstance(c, tuple) else c for c in sh.choice], None, center=False)
    assert r["ok"] is False and "b on y" in r["error"]
    assert list(r["unplaced"]) == ["b"]
    assert r["elements"][0]["x"] == 10 and r["elements"][0]["y"] == 0
    ok = webserver.resolve_payload(schema.parse_design(TOY), "word", [list(c) if isinstance(c, tuple) else c for c in sh.choice], None)
    assert ok["ok"] and ok["unplaced"] == {}


def test_resolve_vert_prev(design):
    L = design.layout("vert")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["col", "c@1", "a@2", "b@2"])
    pos = resolve.resolve(design, L, sh, center=False)
    assert pos["c@1"] == (300, 0) and pos["a@2"] == (200, -120) and pos["b@2"] == (300, -70)


def test_pins_only_for_conditional_gaps(design):
    L = design.layout("word")
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["a", "b"])
    assert resolve.pins_needed(L, sh, design) == {"a": ["g_a1"]}
    sh = next(s for s in shapes.enumerate_shapes(L) if s.names == ["b"])
    assert resolve.pins_needed(L, sh, design) == {}


def test_emit_structure(design):
    em = emit.gen_gpos(design)
    text = "\n".join(em.lines)
    assert "lookup pos_y {" in text and "lookup pos_x {" in text
    # the colon is a breaker: it gets no lookup, the row after it gets a centering lookup
    row_rule = next(r for r in em.rules if r.shape.names == ["col", "c@1", "c@2"])
    assert row_rule.y_lookups[0] == [] and row_rule.y_lookups[1][0].startswith("cen_")
    assert row_rule.y_lookups[2][0].startswith("cur")
    # x after a 1000-advance breaker is pen-relative
    assert row_rule.x_lookups[1] == ["x_m700"]
    # glyph on both sides of a pair (g_a1 is in a and c) gets both anchors
    pair = next(l for l in em.lines if l.startswith("  pos cursive g_a1 <anchor 0 ") and "<anchor 0 0>;" in l)
    assert pair
    # bucket "other" class for the a area
    assert "@pos_word__a__other = [ g_a2 ];" in text


def test_big_lookups_are_broken_into_subtables(monkeypatch):
    """Over ~1,600 rules in one run, fontTools gives up ("All candidates overflowed"); a break every
    RULES_PER_SUBTABLE rules keeps each run small, in the same order."""
    rules = [f"  pos r{i}' lookup x;" for i in range(7)]
    monkeypatch.setattr(emit, "RULES_PER_SUBTABLE", 3)
    out = emit._with_breaks(rules)
    assert out == rules[:3] + ["  subtable;"] + rules[3:6] + ["  subtable;"] + rules[6:]
    assert emit._with_breaks(rules[:3]) == rules[:3]


def test_emitted_fea_compiles_with_real_design():
    """The real design file compiles through feaLib (no font needed: parse only)."""
    from fontTools.feaLib.parser import Parser
    from io import StringIO
    from jzpbuild.genfea import generate
    text = generate()
    Parser(StringIO(text), glyphNames=()).parse()


if __name__ == "__main__":
    import inspect
    failed = 0
    d = design()
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(d) if inspect.signature(fn).parameters else fn()
                print("ok  ", name)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print("FAIL", name, repr(e))
    sys.exit(1 if failed else 0)
