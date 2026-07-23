"""Generate literal contextual `pos` rules per right-hand SIGNIFIER (an
ASCII key, e.g. "k" for lg_gou vs "l" for lg_da -- finer than family)
from geometry.LAYOUTS (via chain.py/anchors.py), instead of GPOS mark
attachment.

Why not mark attachment: an earlier version of this module used GPOS
mark-to-base/mark-to-mark anchors (types 4/6). Those anchors fire whenever
their glyph shapes match, with no way to require "and only within a
gou/io/li word" -- fy/hui/left/jc/zhu are the same shared glyphs across
every right-hand-technique family, so the mark rules also fired (and
additively stacked on top of) the classic pipeline's own positioning for
loki/nc/tiao/mo words. Literal contextual single-adjustment rules (this
module) can require the exact backtrack/lookahead glyph sequence --
including the specific per-signifier class from classes.py -- so they
only ever match words that actually contain that exact right-hand glyph,
same scoping mechanism jzpbuild/gpos.py::word_layout_rules already relies
on via its `R_` context.

Rule ORDER is load-bearing, same as jzpbuild/gpos.py: within the lookup,
the FIRST matching rule wins. Rules are emitted most-specific (longest
backtrack+lookahead) first, so e.g. a rule requiring "@area_fy" in the
backtrack is tried before the otherwise-identical rule that doesn't --
letting real fy-less sequences correctly fall through to it. See
README.md.

Backtrack/lookahead context reflects the real TYPED/glyph-sequence order
(engine.optional_order) -- a fact about the shaped text, unrelated to
which element's POSITION a given element is computed relative to
(chain.py's concern, see geometry.py's module docstring). area_zhu still
gets its own `pos` rule with correct backtrack/lookahead here even though
chain.py computes its value as an offset from area_right rather than
from whatever preceded it in typed order.

geometry.LAYOUTS is what actually drives this module's coverage: iterate
its entries, and each entry's own selector.contains gives the keys to
generate rules for -- adding a new LAYOUTS entry is picked up here
automatically, no separate registration needed. Every token except the
pivot (engine.pivot, e.g. "right"/"chord") is generic ("@area_{elem}");
the pivot gets classes.signifier_token(...) instead, since that's the one
element whose glyph IS the signifier.
"""

import itertools

from jzpbuild import config

from . import anchors, chain, classes, geometry, signifiers

_ENGINES = {layout["name"]: anchors.AnchorEngine(layout) for layout in geometry.LAYOUTS}


def _engine_for_key(key: str) -> anchors.AnchorEngine:
    for layout in geometry.LAYOUTS:
        if key in layout["selector"].get("contains", ()):
            return _ENGINES[layout["name"]]
    raise KeyError(f"no geometry.LAYOUTS entry selects key={key!r}")


class _Rule:
    def __init__(self, backtrack: list[str], marked: str, x: float, y: float,
                 lookahead: list[str]):
        self.backtrack = backtrack
        self.marked = marked
        self.x = x
        self.y = y
        self.lookahead = lookahead

    @property
    def specificity(self) -> int:
        return len(self.backtrack) + len(self.lookahead)

    def render(self) -> str:
        parts = list(self.backtrack)
        parts.append(f"{self.marked}' <{round(self.x)} {round(self.y)} 0 0>")
        parts += self.lookahead
        return "  pos " + " ".join(parts) + ";"


def _signifier_rules(family: str, key: str) -> list[_Rule]:
    engine = _engine_for_key(key)
    rules: list[_Rule] = []
    right_token = classes.signifier_token(family, key)
    flat_optional = engine.flat_optional

    def token(area: str) -> str:
        return right_token if area == engine.pivot else f"@area_{area}"

    for combo in itertools.product((True, False), repeat=len(flat_optional)):
        present = dict(zip(flat_optional, combo))
        # the real full sequence for this combo: every always-present
        # element (in its engine.order position -- the pivot might come
        # first, as for cuo's chord, or last, as for default_jzp's right;
        # nothing here assumes either) plus whichever optional elements
        # are present, all in engine.order's declared order.
        seq = [e["area"] for e in engine.order if not e["optional"] or present.get(e["area"])]
        positions = chain.resolve(engine, present, key)
        pivot_i = seq.index(engine.pivot)
        before, after = seq[:pivot_i], seq[pivot_i + 1:]

        # Elements BEFORE the pivot chain together (each attaches to
        # whichever preceded it), with lookahead always ending in
        # right_token -- that's the scoping mechanism (ensures these only
        # ever match words that actually contain THIS signifier, not some
        # other family's word that happens to share the same fy/left/hui/
        # jc glyphs -- see module docstring).
        for i, area in enumerate(before):
            backtrack = [token(e) for e in before[:i]]
            lookahead = [token(e) for e in before[i + 1:]] + [right_token]
            x, y = positions[area]
            rules.append(_Rule(backtrack, token(area), x, y, lookahead))

        # The pivot itself: backtrack is whatever preceded it in this
        # combo; NO lookahead requirement. Its own value never depends on
        # what (if anything) follows -- requiring something to follow
        # would wrongly exclude the valid "nothing after the pivot at
        # all" case (e.g. a bare right-hand glyph with no string).
        pivot_backtrack = [token(e) for e in before]
        x, y = positions[engine.pivot]
        rules.append(_Rule(pivot_backtrack, right_token, x, y, []))

        # Elements AFTER the pivot (leaves: string, and anything future
        # topologies add here) each independently attach right after
        # whatever precedes them. Scoping already comes from right_token
        # sitting in their backtrack (the pivot precedes them) -- no
        # lookahead requirement needed on top of that, so each one is
        # independent of whichever others do or don't follow it.
        running_backtrack = pivot_backtrack + [right_token]
        for area in after:
            x, y = positions[area]
            rules.append(_Rule(running_backtrack, token(area), x, y, []))

            # li's double-string case: string_top/string_bottom ride along
            # in the SAME sequence slot "string" occupies (variants of the
            # same leaf, deliberately not separate entries in `order` --
            # see geometry.py). Emitted alongside (not instead of) the
            # generic "string" rule above -- li words can use either.
            # Their own paired backtrack/lookahead (string_bottom requires
            # string_top immediately before it) is a real rule-matching
            # coordination between the two, not a generic independent-leaf
            # case, so it's special-cased here. Whether string_top/
            # string_bottom actually show up in `positions` for THIS
            # signifier at all IS the "is this signifier double-string"
            # signal (see chain.resolve's docstring) -- no separate flag.
            if area == "string" and "string_top" in positions and "string_bottom" in positions:
                top_x, top_y = positions["string_top"]
                bottom_x, bottom_y = positions["string_bottom"]
                rules.append(_Rule(running_backtrack, "@area_string_top", top_x, top_y,
                                    ["@area_string_bottom"]))
                rules.append(_Rule(running_backtrack + ["@area_string_top"], "@area_string_bottom",
                                    bottom_x, bottom_y, []))
            running_backtrack = running_backtrack + [token(area)]

    return rules


def gen_dynamic_gpos(layouts: dict, right_keys: tuple[str, ...] = geometry.RIGHT_KEYS) -> list[str]:
    """Entry point genfea.py calls. `layouts` is accepted for interface
    parity with jzpbuild.gpos.gen_gpos but unused -- this prototype's
    geometry lives entirely in geometry.py, not inputs/layouts.json.
    """
    del layouts  # unused, see docstring

    rules: list[_Rule] = []
    for layout in geometry.LAYOUTS:
        for key in layout["selector"].get("contains", ()):
            family = signifiers.family_for_key(key)
            if family is not None:
                # A RIGHT_SELECTORS family (gou/io/li/...) -- `right_keys`
                # is genfea.py's opt-in list for that specific system;
                # respect it same as always.
                if family not in right_keys:
                    continue
            # else: this key isn't part of the RIGHT_SELECTORS/family
            # system at all (e.g. cuo's chord keys) -- there's no
            # per-family opt-in/opt-out for it, presence in geometry.LAYOUTS
            # is what turns it on. Fall back to the layout's own name for
            # class-naming/scoping purposes (see _signifier_rules).
            rules += _signifier_rules(family or layout["name"], key)

    # The one case with no right-hand glyph at all: bare area_fy, nothing
    # else. Safe as a zero-context (always-matches) rule specifically
    # because it sorts last (specificity 0) -- every other rule that could
    # apply to an actual "fy + more" sequence, including the blocker
    # below, is strictly more specific and tried first. Resolved against
    # "default_jzp" specifically -- once a second LAYOUTS entry with its
    # own area_fy exists, this may need to become per-layout too.
    fx, fy = chain.bare_fy(_ENGINES["default_jzp"])
    rules.append(_Rule([], "@area_fy", fx, fy, []))

    # Blocks area_fy's positioning from leaking into words that aren't
    # actually gou/io/li: any word where area_fy is immediately followed
    # by hui/left/jc/zhu (i.e. this is really a "blank"/other-family word
    # that classic's own layout_blank/layout_<other> rules already
    # position for real -- see README.md) or directly by another family's
    # right-hand glyph. Every genuine rule above requires its own
    # per-signifier class (disjoint from this blocker class, and a subset
    # of the classic per-family class this blocker uses) somewhere in its
    # own lookahead, so it's always at least as specific and never
    # shadowed by this blocker.
    rules.append(_Rule([], "@area_fy", 0, 0, ["@area_fy_blocker"]))

    rules.sort(key=lambda r: -r.specificity)

    other_families = [f for f in config.RIGHT_KEYS if f not in right_keys]
    other_right_class = " ".join(f"@area_right__{f}" for f in other_families)
    class_lines = [
        f"@area_right_other = [ {other_right_class} ];",
        "@area_fy_blocker = [ @area_left @area_hui @area_jc @area_zhu @area_right_other ];",
    ]

    lines = ["# --- dynamic_positioning: per-signifier word positioning (literal, geometry-derived) ---"]
    lines += classes.gen_signifier_classes()
    lines += class_lines
    lines.append("lookup dynamic_pos {")
    lines += [r.render() for r in rules]
    lines.append("} dynamic_pos;")
    lines += ["", "feature kern {", "  lookup dynamic_pos;", "} kern;"]
    return lines
