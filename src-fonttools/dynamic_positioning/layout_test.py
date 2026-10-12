"""Standalone demo of the dynamic_positioning mechanism, NOT wired into the
real font build (no components.csv/signifiers.py/layouts_data.json
changes) -- see README.md "Adding a genuinely new topology" and "cuo:
current status" (chord_left/chord_right) for the real-pipeline shape this
mirrors.

Routing rule being demonstrated: three boxes, [left] [middle] [right].

- If the first typed character is one of LEFT_TRIGGER_KEYS ("s", "d",
  "f"), it's assigned to the `left` area, and the SECOND typed character
  (whatever it is) is assigned to `right`. `middle` is absent.
- Otherwise, the first typed character alone is assigned to `middle`.
  `left`/`right` are absent.

Because left+right and middle never co-occur, this needs two topologies
(exactly like chord_left/chord_right split for cuo) rather than one, since
anchors.AnchorEngine requires exactly one `pivot` per topology and a
single topology can't have two different "which area is the signifier"
answers depending on the word.

Run directly: `python3 -m dynamic_positioning.layout_test`
"""

from . import anchors, chain, geometry

LEFT_TRIGGER_KEYS = {"s", "d", "f"}

AREAS = {
    "left": (800, 800),
    "right": (600, 800),
    "middle": (1000, 900),
}

# left+right: left is the pivot (its glyph is the s/d/f signifier that
# selects this topology); right is a required leaf, positioned flush
# against left's right edge plus a fixed gap. Explicit base_edge/elem_edge
# on the x relationship below, since the *default* edge pairing (base's
# near edge, elem's far edge -- see README's "gap" section) places elem
# mostly to the LEFT of base, not the right; overriding both edges to
# "elem starts right after base ends" is what actually produces a
# left-then-right layout.
LAYOUT_TEST_LR = {
    "name": "layout_test_lr",
    "areas": AREAS,
    "vertical_center_order": [["left", "right"]],
    "relationships": [
        {"axis": "x", "elem": "left", "base": None, "gap": 0},
        {"axis": "x", "elem": "right", "base": "left",
         "base_edge": "right", "elem_edge": "left", "gap": 100},
        {"axis": "y", "elem": "left", "base": None, "gap": 0},
        {"axis": "y", "elem": "right", "base": "left",
         "base_edge": "bottom", "elem_edge": "bottom", "gap": 0},
    ],
    "order": [
        {"area": "left", "optional": False, "pivot": True},
        {"area": "right", "optional": False},
    ],
}

# middle alone: middle is its own pivot, no left/right relationships at all.
LAYOUT_TEST_MID = {
    "name": "layout_test_mid",
    "areas": AREAS,
    "vertical_center_order": [["middle"]],
    "relationships": [
        {"axis": "x", "elem": "middle", "base": None, "gap": 0},
        {"axis": "y", "elem": "middle", "base": None, "gap": 0},
    ],
    "order": [
        {"area": "middle", "optional": False, "pivot": True},
    ],
}

ENGINE_LR = anchors.AnchorEngine(LAYOUT_TEST_LR)
ENGINE_MID = anchors.AnchorEngine(LAYOUT_TEST_MID)


def route(word: str) -> dict[str, tuple[float, float]]:
    """Apply the [left][middle][right] routing rule to a typed `word`
    (a short string of placeholder ASCII "glyph names" -- not real
    components.csv keys) and resolve absolute (x, y) positions."""
    first, rest = word[0], word[1:]
    if first in LEFT_TRIGGER_KEYS:
        if not rest:
            raise ValueError(f"{word!r}: an s/d/f trigger needs a following character for `right`")
        present = {"left": True, "right": True}
        present_glyphs = {"left": first, "right": rest[0]}
        return chain.resolve(ENGINE_LR, present, present_glyphs)
    present = {"middle": True}
    present_glyphs = {"middle": first}
    return chain.resolve(ENGINE_MID, present, present_glyphs)


def _demo() -> None:
    for word in ("sX", "dY", "fZ", "q", "m"):
        positions = route(word)
        print(f"{word!r:>6} -> " + ", ".join(f"{area}=({x:.0f}, {y:.0f})" for area, (x, y) in positions.items()))


if __name__ == "__main__":
    _demo()
