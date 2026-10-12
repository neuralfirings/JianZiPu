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
(engine.order) -- a fact about the shaped text, unrelated to which
element's POSITION a given element is computed relative to (chain.py's
concern, see geometry.py's module docstring). area_zhu still gets its own
`pos` rule with correct backtrack/lookahead here even though chain.py
computes its value as an offset from area_right rather than from whatever
preceded it in typed order.

geometry.LAYOUTS is what actually drives this module's coverage: iterate
its entries, and each entry's own selector.contains gives the keys to
generate rules for -- adding a new LAYOUTS entry is picked up here
automatically, no separate registration needed. Every token except the
pivot (engine.pivot, e.g. "right"/"chord") is generic ("@area_{elem}");
the pivot gets classes.signifier_token(...) instead, since that's the one
element whose glyph IS the signifier.
"""

import itertools

from . import anchors, chain, classes, geometry, identity, signifiers

_ENGINES = {layout["name"]: anchors.AnchorEngine(layout) for layout in geometry.LAYOUTS}

# One GPOS lookup per pivot signifier (see _collect_rules), plus this one
# for the bare-fy fallback.
FY_LOOKUP = "dynamic_pos__fy"


def _lookup_name(key: str) -> str:
    return f"dynamic_pos__{signifiers.KEY_TO_GLYPH[key]}"


def _engine_for_key(key: str, layouts: list[dict],
                    engines: dict[str, anchors.AnchorEngine]) -> anchors.AnchorEngine:
    for layout in layouts:
        if key in layout["selector"].get("contains", ()):
            return engines[layout["name"]]
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


def _identity_choices(present: dict[str, bool],
                       buckets: dict[str, dict[str, object]]) -> list[dict[str, str | None]]:
    """One dict per combination of concrete glyph-bucket choices for whichever
    identity-sensitive areas (`buckets`, see identity.area_glyph_buckets) are
    actually present in this combo. A value of `None` means "the catch-all
    bucket" -- present_glyphs gets nothing added for that area, so
    resolve_gap naturally falls through to the catch-all entry. Areas not
    present, or with no bucket at all, aren't iterated -- their token stays
    the generic `@area_{name}` (see _signifier_rules' `token()`)."""
    axes = [(area, list(bucket["glyphs"]) + ([None] if bucket["catch_all"] else []))
            for area, bucket in buckets.items() if present.get(area)]
    if not axes:
        return [{}]
    return [dict(zip((a for a, _ in axes), combo))
            for combo in itertools.product(*(opts for _, opts in axes))]


def _signifier_rules(family: str, key: str, layouts: list[dict],
                     engines: dict[str, anchors.AnchorEngine]) -> list[_Rule]:
    engine = _engine_for_key(key, layouts, engines)
    rules: list[_Rule] = []
    right_token = classes.signifier_token(family, key)
    right_glyph = signifiers.KEY_TO_GLYPH[key]
    flat_optional = engine.flat_optional
    # Which non-pivot areas this layout's own gap overrides reference by
    # glyph identity (e.g. area_hui's md_5/md_9) -- see identity.py. Areas
    # not referenced here never branch below; `token()` stays generic for
    # them exactly as before this feature existed.
    buckets = identity.area_glyph_buckets({"relationships": engine.relationships})

    for combo in itertools.product((True, False), repeat=len(flat_optional)):
        present = dict(zip(flat_optional, combo))
        # the real full sequence for this combo: every always-present
        # element (in its engine.order position -- the pivot might come
        # first, as for cuo's chord, or last, as for default_jzp's right;
        # nothing here assumes either) plus whichever optional elements
        # are present, all in engine.order's declared order.
        seq = [e["area"] for e in engine.order if not e["optional"] or present.get(e["area"])]
        pivot_i = seq.index(engine.pivot)
        before, after = seq[:pivot_i], seq[pivot_i + 1:]

        # For each present identity-sensitive area, branch over its
        # declared glyph buckets (plus catch-all if any) -- e.g. if `hui`
        # is present and its own glyph affects some gap, generate one full
        # rule-set variant per hui glyph bucket, each requiring that
        # bucket's specific class (disjoint from every other bucket for
        # the same area -- see classes.area_glyph_token/
        # area_glyph_other_token) instead of the generic `@area_hui`. No
        # FEA rule-ordering concern between these variants: the classes
        # partition the area's glyphs, so a real word only ever matches
        # exactly one of them.
        for identity_choice in _identity_choices(present, buckets):
            present_glyphs = {engine.pivot: right_glyph}
            present_glyphs.update({a: g for a, g in identity_choice.items() if g is not None})

            def token(area: str, _choice=identity_choice) -> str:
                if area == engine.pivot:
                    return right_token
                if area in _choice:
                    glyph = _choice[area]
                    if glyph is None:
                        return classes.area_glyph_other_token(engine.name, area)
                    return classes.area_glyph_token(engine.name, area, glyph)
                if area in classes.CLASSIC_BASE_AREAS:
                    return f"@area_{area}"
                return classes.repeated_area_token(area)

            positions = chain.resolve(engine, present, present_glyphs)

            # Elements BEFORE the pivot chain together (each attaches to
            # whichever preceded it), with lookahead always ending in
            # right_token -- that's the scoping mechanism (ensures these
            # only ever match words that actually contain THIS signifier,
            # not some other family's word that happens to share the same
            # fy/left/hui/jc glyphs -- see module docstring).
            for i, area in enumerate(before):
                backtrack = [token(e) for e in before[:i]]
                lookahead = [token(e) for e in before[i + 1:]] + [right_token]
                x, y = positions[area]
                rules.append(_Rule(backtrack, token(area), x, y, lookahead))

            # Disambiguating lookahead for anything at-or-after the pivot:
            # only OPTIONAL elements carry any combo-distinguishing
            # information at all (non-optional/always-present ones, e.g.
            # `string`, are attempted in EVERY combo regardless of whether a
            # real word actually has that glyph -- chain.resolve silently
            # tolerates them failing to resolve, see its own docstring --
            # so requiring one in a lookahead would wrongly reject a real
            # word that genuinely lacks it, for zero disambiguating benefit
            # since its presence never varies across combos to begin with).
            def optional_lookahead(elems: list[str]) -> list[str]:
                return [token(e) for e in elems if e in flat_optional]

            # The pivot itself: backtrack is whatever preceded it in this
            # combo. Its own resolved value can depend on which optional
            # elements come AFTER it too (same whole-stack centering-shift
            # coupling as the leaves below), not just which preceded it --
            # so it needs the same kind of disambiguating lookahead, filtered
            # to optional elements only so a genuinely leaf-less/string-less
            # real word (the valid "bare pivot" case) still matches the
            # variant generated for that same absence. Without this, every
            # combo's pivot rule shared byte-identical (empty) context and
            # only the first-generated combo ever won -- e.g. cuo's chord
            # glyph rendering at the wrong height whenever the real word's
            # optional elements didn't match that arbitrary combo.
            pivot_backtrack = [token(e) for e in before]
            x, y = positions[engine.pivot]
            rules.append(_Rule(pivot_backtrack, right_token, x, y, optional_lookahead(after)))

            # Elements AFTER the pivot (leaves: string, and anything future
            # topologies add here) each attach right after whatever precedes
            # them. Scoping against OTHER families already comes from
            # right_token sitting in their backtrack -- but scoping against
            # OTHER PRESENCE COMBOS of this same family still needs a
            # lookahead, for the same reason as the pivot above: a leaf's
            # own (x, y) can depend on which later OPTIONAL leaves are
            # present too. Listing them lets the most-specific-first sort
            # pick the right variant: a real word missing one of those later
            # leaves fails this lookahead and falls through to the next,
            # less-specific matching combo's rule.
            running_backtrack = pivot_backtrack + [right_token]
            for i, area in enumerate(after):
                after_lookahead = optional_lookahead(after[i + 1:])
                x, y = positions[area]
                rules.append(_Rule(running_backtrack, token(area), x, y, after_lookahead))

                # li's double-string case: string_top/string_bottom ride
                # along in the SAME sequence slot "string" occupies
                # (variants of the same leaf, deliberately not separate
                # entries in `order` -- see geometry.py). Emitted alongside
                # (not instead of) the generic "string" rule above -- li
                # words can use either. string_bottom requires string_top
                # immediately before it, then whichever later leaves this
                # combo has. Whether string_top/string_bottom show up in
                # `positions` for THIS signifier at all IS the "is this
                # signifier double-string" signal (see chain.resolve's
                # docstring) -- no separate flag.
                if area == "string" and "string_top" in positions and "string_bottom" in positions:
                    top_x, top_y = positions["string_top"]
                    bottom_x, bottom_y = positions["string_bottom"]
                    rules.append(_Rule(running_backtrack, "@area_string_top", top_x, top_y,
                                        ["@area_string_bottom"] + after_lookahead))
                    rules.append(_Rule(running_backtrack + ["@area_string_top"], "@area_string_bottom",
                                        bottom_x, bottom_y, after_lookahead))
                running_backtrack = running_backtrack + [token(area)]

    return rules


def _pivot_glyphs_before_fy(layouts: list[dict]) -> list[str]:
    """Signifier glyphs of every layout whose pivot is typed BEFORE its fy
    (cuo's chord: "C fy ..."), i.e. the glyphs that can immediately precede
    a fy that some per-signifier lookup already positions."""
    glyphs: list[str] = []
    for layout in layouts:
        areas = [e["area"] for e in layout["order"]]
        pivot = next(e["area"] for e in layout["order"] if e.get("pivot"))
        if "fy" in areas and areas.index("fy") > areas.index(pivot):
            for key in layout["selector"].get("contains", ()):
                glyph = signifiers.KEY_TO_GLYPH[key]
                if glyph not in glyphs:
                    glyphs.append(glyph)
    return glyphs


def _collect_rules(layouts: list[dict] = geometry.LAYOUTS,
                   engines: dict[str, anchors.AnchorEngine] = _ENGINES,
                   families: tuple[str, ...] = geometry.FAMILIES) -> dict[str, list[_Rule]]:
    """{lookup name: rules} for `layouts` -- one GPOS lookup per pivot
    signifier (_lookup_name) plus FY_LOOKUP for the bare-fy fallback, each
    sorted most-specific first (the load-bearing order, see module
    docstring).

    Why one lookup per signifier: the 64KB Offset16 ceiling (see
    estimate_dynamic_pos_bytes) is per lookup subtable, so splitting gives
    every family its own budget instead of one shared one. It changes no
    positions: every rule from _signifier_rules carries its own pivot
    glyph's class in its context, so rules from different signifiers never
    match the same word, and GPOS value accumulation across lookups never
    adds two of them together. The one rule that has no pivot in its
    context -- bare fy -- used to be shadowed by sitting last in the shared
    lookup; in its own lookup it needs the explicit zero-valued blockers
    below instead.

    `engines` must hold one AnchorEngine per layout; the defaults are the
    real geometry.LAYOUTS and the engines built from them at import (what
    the font build uses), while the editor passes a throwaway pair for
    unsaved layouts (see _editor_rules)."""
    lookups: dict[str, list[_Rule]] = {}
    for layout in layouts:
        for key in layout["selector"].get("contains", ()):
            family = signifiers.family_for_key(key)
            # A RIGHT_SELECTORS family (gou/io/li/...) is only covered if
            # it's in `families` (genfea.py's opt-in list). A key outside
            # that system (e.g. cuo's chord keys) is covered simply by
            # appearing in a LAYOUTS selector; the layout's own name then
            # stands in for the family in class names (see
            # classes.signifier_token).
            if family is not None and family not in families:
                continue
            lookups.setdefault(_lookup_name(key), []).extend(
                _signifier_rules(family or layout["name"], key, layouts, engines))

    # The one case with no right-hand glyph at all: bare area_fy, a
    # zero-context (always-matches) rule. Resolved against default_jzp
    # specifically; once a second LAYOUTS entry has its own area_fy this
    # may need to become per-layout.
    fy_rules: list[_Rule] = []
    if "default_jzp" in engines:
        fx, fy = chain.bare_fy(engines["default_jzp"])
        fy_rules.append(_Rule([], "@area_fy", fx, fy, []))
    # Zero-valued blockers, more specific than bare fy so they win: a fy
    # that is part of a real word -- immediately followed by hui/left/jc/zhu
    # or any right-hand glyph (a per-signifier lookup above or classic
    # already positions it), or immediately preceded by a pivot-first
    # layout's signifier (cuo's chord) -- gets nothing from this lookup.
    fy_rules.append(_Rule([], "@area_fy", 0, 0, ["@area_fy_blocker"]))
    if _pivot_glyphs_before_fy(layouts):
        fy_rules.append(_Rule(["@area_fy_blocker_before"], "@area_fy", 0, 0, []))
    lookups[FY_LOOKUP] = fy_rules

    for rules in lookups.values():
        rules.sort(key=lambda r: -r.specificity)
    return lookups


def gen_dynamic_gpos() -> list[str]:
    """Entry point genfea.py calls: FEA text for the classes plus one
    lookup per signifier (see _collect_rules), all registered in `kern`."""
    lookups = _collect_rules()

    class_lines = ["@area_fy_blocker = [ @area_left @area_hui @area_jc @area_zhu @area_right_all ];"]
    before = _pivot_glyphs_before_fy(geometry.LAYOUTS)
    if before:
        class_lines.append(f"@area_fy_blocker_before = [ {' '.join(before)} ];")

    lines = ["# --- dynamic_positioning: per-signifier word positioning (literal, geometry-derived) ---"]
    lines += classes.gen_signifier_classes()
    lines += classes.gen_area_glyph_classes()
    lines += classes.gen_repeated_area_classes()
    lines += class_lines
    for name, rules in lookups.items():
        lines.append(f"lookup {name} {{")
        lines += [r.render() for r in rules]
        lines.append(f"}} {name};")
    lines += ["", "feature kern {"]
    lines += [f"  lookup {name};" for name in lookups]
    lines.append("} kern;")
    return lines


# ---------------------------------------------------------------------------
# editor support (devserver.py's /api/dynamic/rule_count, for
# tools/jzpbuilder-dynamic.html's live complexity badge)


def _editor_rules(layouts: list[dict], families: tuple[str, ...]) -> dict[str, list[_Rule]]:
    """_collect_rules over a throwaway engines dict built from `layouts` (an
    in-editor, possibly unsaved layouts_data.json "layouts" list with each
    entry's "areas" already filled in) -- never touches the real
    geometry.LAYOUTS/_ENGINES globals, so the badge reflects unsaved edits
    without a save-to-disk + reimport round trip, and stays cheap enough to
    call on every edit."""
    engines = {layout["name"]: anchors.AnchorEngine(layout) for layout in layouts}
    return _collect_rules(layouts, engines, families)


def count_dynamic_pos_rules(layouts: list[dict], families: tuple[str, ...] = geometry.FAMILIES) -> int:
    """Total `pos` statements across every lookup for `layouts`.

    On its own this is a WEAK overflow predictor: two layouts_data.json
    revisions with 17,431 and 8,722 rules respectively both overflowed a
    real build (OTLOffsetOverflowError, "All candidates overflowed") --
    what actually overflows is total SUBTABLE BYTES in one Lookup (a hard
    64KB ceiling, 16-bit offsets), which depends on each rule's
    backtrack+lookahead length just as much as rule count. See
    estimate_dynamic_pos_bytes, the actually-predictive metric; this is
    kept as a secondary, human-readable number for the UI."""
    return sum(len(rules) for rules in _editor_rules(layouts, families).values())


# Per-rule byte estimate for one ChainContextPos format-3 subtable (what
# feaLib compiles every dynamic_pos `pos ... ' ...;` statement to): a
# 2-byte Offset16 per backtrack/input/lookahead glyph-class Coverage table,
# plus a fixed ~12 bytes of subtable header (format, 3x glyph-count fields,
# 1x PosLookupRecord -- always exactly one marked/input position here).
# Deliberately does NOT add each Coverage table's own payload bytes (glyph
# lists) -- those are real but small relative to the offset table for this
# codebase's class sizes, and would need per-class dedup logic to estimate
# correctly (fontTools shares one Coverage table across every rule
# referencing the same class) -- so this is a LOWER BOUND, calibrated
# against two known real data points: a working ~863-rule layouts_data.json
# estimated at ~17KB (well under the 64KB ceiling, and did build), and an
# overflowing ~8,722-rule one estimated at ~208KB -- both consistent with
# "closer to 64KB = closer to failing," even though this estimate isn't exact.
_BYTES_PER_CONTEXT_TOKEN = 2
_SUBTABLE_OVERHEAD_BYTES = 12
GPOS_LOOKUP_OFFSET_CEILING_BYTES = 65536  # Offset16 -- the real hard limit


def estimate_dynamic_pos_bytes(layouts: list[dict], families: tuple[str, ...] = geometry.FAMILIES) -> int:
    """Estimated subtable bytes of the LARGEST single lookup for `layouts`
    -- the ceiling is per lookup, so the worst one is what matters. See the
    _BYTES_PER_CONTEXT_TOKEN/_SUBTABLE_OVERHEAD_BYTES comment above for the
    method and its known slight-underestimate bias. Compare against
    GPOS_LOOKUP_OFFSET_CEILING_BYTES -- this is the metric that actually
    predicts real-build overflow, unlike raw rule count."""
    return max((sum((r.specificity + 1) * _BYTES_PER_CONTEXT_TOKEN + _SUBTABLE_OVERHEAD_BYTES
                    for r in rules)
                for rules in _editor_rules(layouts, families).values()), default=0)
