"""Generate the GPOS half of the feature file (glyph positioning).

Each composed JZP word is laid out by contextual single-position rules: a rule
matches the sequence of area classes that make up a word shape and moves the
marked glyph to its area's x/y for the active layout. Layout geometry comes
from layouts.json (derived from Figma).

Rules are plain token lists: "@area_left'" positions the left-hand glyph
(trailing apostrophe = marked), "@area_left" is context. The marked token's
area name (with any "__variant" suffix stripped) is looked up in the active
layout to produce the `<x yd 0 0>` value record — replicating what
`scripts.cjs --add-positions` used to do with the `<>` placeholders.

Rule ORDER is load-bearing: within the lookup, earlier rules win for a given
glyph, and several fallbacks (e.g. bare @area_hui at the very end) rely on
being last. Don't reorder blocks casually.
"""

from . import config

Rule = list  # of str tokens; trailing "'" marks the positioned glyph

# The (left || hui) presence combinations, in canonical rule order: both,
# left only, hui only.
LH_COMBOS = (["@area_left", "@area_hui"], ["@area_left"], ["@area_hui"])


class FillError(Exception):
    pass


def word_layout_rules(right: str | None, jc: bool,
                      strings: str = "single") -> list[Rule]:
    """Rules for one word layout: fy? (left||hui) jc? zhu? right? string?.

    right: right-hand class suffix ("gou", "li", ...) or None for the blank
    (no right hand) layouts. jc: whether the 急/绰 marker area is part of this
    layout (always present in its rules when so). strings: "single" for one
    string area, "li" for the two-string 历 variant, matching the historical
    rule sets.
    """
    R_ = [f"@area_right__{right}"] if right else []
    jc_ = ["@area_jc"] if jc else []
    rules: list[Rule] = []

    # In the blank (no right hand) layouts the word ends before zhu can
    # follow fy/left/hui/jc, so those groups only have the no-zhu variant.
    head_zhus = (["@area_zhu"], []) if right else ([],)

    # fy' — with zhu, then without
    for zhu in head_zhus:
        for lh in LH_COMBOS:
            rules.append(["@area_fy'"] + lh + jc_ + zhu + R_)

    # left'
    for zhu in head_zhus:
        for hui in (["@area_hui"], []):
            rules.append(["@area_left'"] + hui + jc_ + zhu + R_)

    # hui'
    for zhu in head_zhus:
        if not jc and not zhu and not R_:
            continue  # bare hui fallback handled separately (blank layouts)
        rules.append(["@area_hui'"] + jc_ + zhu + R_)

    # jc'
    if jc:
        for zhu in head_zhus:
            for lh in LH_COMBOS:
                rules.append(lh + ["@area_jc'"] + zhu + R_)

    # zhu'
    for lh in LH_COMBOS:
        rules.append(lh + jc_ + ["@area_zhu'"] + R_)

    # right'
    if right:
        for zhu in (["@area_zhu"], []):
            for lh in LH_COMBOS:
                rules.append(lh + jc_ + zhu + [f"@area_right__{right}'"])

    # strings
    prefix_combos = [lh + jc_ + zhu + R_ for zhu in (["@area_zhu"], []) for lh in LH_COMBOS]
    if strings == "li":
        for p in prefix_combos:
            rules.append(p + ["@area_string_top'", "@area_string_bottom'"])
        # historical quirk: the single-string rules for li2 only cover the
        # with-zhu combos; plain li covers all six
        limit = 3 if jc else 6
        for p in prefix_combos[:limit]:
            rules.append(p + ["@area_string'"])
    else:
        for p in prefix_combos:
            rules.append(p + ["@area_string'"])
    return rules


def no_left_layout_rules(right: str | None, jc: bool = True) -> list[Rule]:
    """The *3 layouts: fy? jc? zhu? right string? — no left hand at all.

    layout_li3 historically has no jc rules (jc=False).
    """
    R_ = [f"@area_right__{right}"] if right else []
    if right:
        rules: list[Rule] = []
        if jc:
            rules += [
                ["@area_fy'", "@area_jc", "@area_zhu"] + R_,
                ["@area_fy'", "@area_jc"] + R_,
            ]
        rules += [
            ["@area_fy'", "@area_zhu"] + R_,
            ["@area_fy'"] + R_,
        ]
        if jc:
            rules += [
                ["@area_jc'", "@area_zhu"] + R_,
                ["@area_jc'"] + R_,
            ]
        rules += [
            ["@area_zhu'"] + R_,
            [f"@area_right__{right}'"],
        ]
        if right == "li":
            rules += [
                R_ + ["@area_string_top'", "@area_string_bottom'"],
                R_ + ["@area_string'"],
            ]
        else:
            rules += [R_ + ["@area_string'"]]
    else:
        # layout_blank3
        rules = [["@area_jc'"], ["@area_zhu'"], ["@area_string'"]]
    return rules


def vert_rules(n: int) -> list[Rule]:
    """layout_vertjzpN: after ':', N stacked rows of (left+hui | one char).

    All rows are positioned by a single rule; every presence combination is
    enumerated in binary-count order (row 1 = least significant bit,
    char = 1).
    """
    rules = []
    if n == 1:
        return [["@area_char_colon", "@area_char1'"]]
    for combo in range(2 ** n):
        rule = ["@area_char_colon"]
        for row in range(1, n + 1):
            if combo & (1 << (row - 1)):
                rule.append(f"@area_char{row}'")
            else:
                rule += [f"@area_left_{row}'", f"@area_hui_{row}'"]
        rules.append(rule)
    return rules


def cuo_rules(anchor: str) -> list[tuple[str, list[Rule]]]:
    """The 撮 chord segments: anchor is '@area_chord__cuo' (left segment,
    after the chord glyph) or '@area_cuo_bar' (right segment, after '|').

    Returns (layout, rules) blocks; the left/right segments share rule
    structure but read positions from their own layout frames.
    """
    A = anchor
    side = "left" if "chord" in anchor else "right"
    blocks = []
    # common rules (positions from the base cuo layout)
    common: list[Rule] = []
    if side == "left":
        common += [["@area_fy'", A], [A + "'"]]
    common += [
        [A, "@area_left'"],
        [A, "@area_left", "@area_hui'"],
        # 1-7 default to strings; force hui reading before zhu/string (7z7, 77)
        [A, "@area_hui'", "@area_zhu"],
        [A, "@area_hui'", "@area_string"],
    ]
    blocks.append((f"layout_cuo_{side}", common))

    # jc variant ("2" geometry)
    b2: list[Rule] = [
        [A, "@area_left", "@area_hui'", "@area_jc"],
        [A, "@area_hui'", "@area_jc"],
        [A, "@area_left", "@area_hui", "@area_jc'"],
        [A, "@area_hui", "@area_jc'"],
    ]
    for lh in LH_COMBOS:
        b2.append([A] + lh + ["@area_jc", "@area_zhu'"])
    for zhu in (["@area_zhu"], []):
        for lh in LH_COMBOS:
            b2.append([A] + lh + ["@area_jc"] + zhu + ["@area_string'"])
    blocks.append((f"layout_cuo_{side}2", b2))

    # plain variant
    b1: list[Rule] = []
    for lh in LH_COMBOS:
        b1.append([A] + lh + ["@area_zhu'"])
    for zhu in (["@area_zhu"], []):
        for lh in LH_COMBOS:
            b1.append([A] + lh + zhu + ["@area_string'"])
    blocks.append((f"layout_cuo_{side}", b1))

    # no-left-hand variant ("3" geometry)
    b3: list[Rule] = [
        [A, "@area_jc'"],
        [A, "@area_jc", "@area_zhu'"],
        [A, "@area_zhu'"],
        [A, "@area_jc", "@area_zhu", "@area_string'"],
        [A, "@area_jc", "@area_string'"],
        [A, "@area_zhu", "@area_string'"],
        [A, "@area_string'"],
    ]
    blocks.append((f"layout_cuo_{side}3", b3))

    # hui fallback (must come after the *3 string rules)
    blocks.append((f"layout_cuo_{side}2", [[A, "@area_hui'"]]))
    return blocks


# ---------------------------------------------------------------------------
# position filling


def token_area(token: str) -> str:
    """'@area_right__li'' -> 'area_right'; '@area_hui_1'' -> 'area_hui_1'."""
    return token.rstrip("'").lstrip("@").split("__")[0]


def fill_rule(rule: Rule, layout: str, layouts: dict,
              overrides: dict[str, str] | None = None, zero: bool = False) -> str:
    areas = layouts.get(layout)
    if areas is None:
        raise FillError(f"no geometry for layout {layout}")
    parts = ["pos"]
    for token in rule:
        if token.endswith("'"):
            if zero:
                # Same match context/specificity as the real rule (still
                # blocks less-specific fallback rules, e.g. layout_blank,
                # from matching this word instead), but contributes no net
                # offset -- used when this family's real positioning comes
                # from elsewhere (dynamic_positioning) instead of layouts.json.
                parts.append(f"{token} <0 0 0 0>")
                continue
            area = (overrides or {}).get(token.rstrip("'")) or token_area(token)
            p = areas.get(area)
            if p is None:
                raise FillError(f"{layout} has no area {area} (token {token})")
            parts.append(f"{token} <{p['x']} {p['yd']} 0 0>")
        else:
            parts.append(token)
    return " ".join(parts) + ";"


def emit_block(lines: list[str], layout: str, rules: list[Rule],
               layouts: dict, comment: str | None = None,
               overrides: dict[str, str] | None = None, zero: bool = False) -> None:
    lines.append(f"  # layout: {layout}" + (f" — {comment}" if comment else ""))
    for r in rules:
        lines.append("  " + fill_rule(r, layout, layouts, overrides, zero=zero))


def gen_gpos(layouts: dict, skip_right_keys: set[str] = frozenset(),
             zero_others: bool = False) -> list[str]:
    """`skip_right_keys`: families whose real positioning comes from
    dynamic_positioning instead (their own classic rules here are zeroed,
    not omitted -- see the comment on the six-family loop below).
    `zero_others`: also zero every OTHER classic-positioned shape this
    module generates (the remaining right-hand families, vertical-mode
    words, cuo chords) -- a dynamic-pos-only test build, so that anything
    dynamic_positioning doesn't actually cover renders visibly broken
    (glyphs piled at the origin) instead of silently looking correct via
    classic and giving false confidence that dynamic positioning handled
    it. See jzpbuild.build's --dynamic_pos_only flag.
    """
    lines = ["lookup jzp_glyph_positioning {"]

    # vertical stacks. Special case first: ':大息' would otherwise be read as
    # 大 = left hand and positioned by a word layout.
    emit_block(lines, "layout_vertjzp2",
               [["@area_char_colon", "md_da'", "md_xi'"]], layouts,
               comment="special case :大息",
               overrides={"md_da": "area_char1", "md_xi": "area_char2"},
               zero=zero_others)
    for n in (4, 3, 2, 1):
        emit_block(lines, f"layout_vertjzp{n}", vert_rules(n), layouts, zero=zero_others)

    # 历 (li) — takes two strings. Same zeroing rationale as the six
    # standard right-hand techniques below: when dynamic_positioning owns
    # li's real positioning, these rules must still be emitted (so the
    # "blanks" fallback below can't wrongly match a li word) but with a
    # zeroed value record, not omitted -- see the comment on the loop below.
    li_zero = "li" in skip_right_keys
    emit_block(lines, "layout_li2", word_layout_rules("li", jc=True, strings="li"), layouts, zero=li_zero)
    emit_block(lines, "layout_li", word_layout_rules("li", jc=False, strings="li"), layouts, zero=li_zero)
    emit_block(lines, "layout_li3", no_left_layout_rules("li", jc=False), layouts, zero=li_zero)

    # 撮 chords: left segment then right segment
    for anchor in ("@area_chord__cuo", "@area_cuo_bar"):
        for layout, rules in cuo_rules(anchor):
            emit_block(lines, layout, rules, layouts, zero=zero_others)

    # the six standard right-hand techniques
    for right in config.RIGHT_KEYS:
        # Real positioning for this family comes from dynamic_positioning
        # instead (--dynamic_pos) -- but still emit these rules with zeroed
        # value records, not omitted entirely: omitting them would let the
        # less-specific "blanks (no right hand)" rules below incorrectly
        # match a prefix of this family's words (their contextual matching
        # has no way to require a right-hand glyph's ABSENCE), additively
        # leaking an unwanted offset on top of dynamic_positioning's own
        # (since GPOS single-adjustment accumulates across lookups, unlike
        # mark attachment). Zeroed rules keep the same match specificity
        # (still take precedence over the blank fallback) while
        # contributing nothing. `zero_others` extends the same treatment to
        # families dynamic_positioning was never asked to cover in the
        # first place (a dynamic-pos-only test build) -- see gen_gpos's
        # docstring.
        zero = right in skip_right_keys or zero_others
        emit_block(lines, f"layout_{right}2", word_layout_rules(right, jc=True), layouts, zero=zero)
        emit_block(lines, f"layout_{right}", word_layout_rules(right, jc=False), layouts, zero=zero)
        emit_block(lines, f"layout_{right}3", no_left_layout_rules(right), layouts, zero=zero)

    # blanks (no right hand) -- zero_others covers these too: a "blank"
    # word (fy/left/hui/jc/zhu/string with no right-hand technique glyph at
    # all) is a shape ANY non-right-hand-family pivot's glyphs can
    # accidentally match by coincidence (nothing in these rules' own
    # backtrack/lookahead excludes e.g. cuo's xl_cuo/xl_tt), so leaving them
    # unzeroed under --dynamic_pos_only let a real bug through: chord_left's
    # own fy_1 rule and this unzeroed classic fallback both fired on the
    # same "fy followed by left/hui" glyph run, and GPOS single-adjustment
    # values from separate lookups accumulate (see README's "Why not GPOS
    # mark attachment") -- e.g. "Cfys5" landed mod_fanyin at (580, 1439)
    # instead of dynamic_pos's own intended (290, 741), literally the sum of
    # both rules' offsets.
    emit_block(lines, "layout_blank2", word_layout_rules(None, jc=True), layouts, zero=zero_others)

    blank_rules = word_layout_rules(None, jc=False)
    # the bare-hui cases need explicit zhu/string context (7z7, 77) and a
    # left-context variant so lone 1-7 can fall through to layout_blank3
    extra = [
        ["@area_left", "@area_hui'"],
        ["@area_hui'", "@area_zhu"],
        ["@area_hui'", "@area_string"],
    ]
    # insert after the left' rules (2 fy-groups of 3, then 2 left rules... )
    emit_block(lines, "layout_blank", blank_rules[:8] + extra + blank_rules[8:], layouts, zero=zero_others)

    emit_block(lines, "layout_blank3", no_left_layout_rules(None), layouts, zero=zero_others)

    # final fallback: hui position for 8+ when nothing else matched
    emit_block(lines, "layout_blank", [["@area_hui'"]], layouts,
               comment="hui fallback for 8-13 after string rules", zero=zero_others)

    lines.append("} jzp_glyph_positioning;")
    lines += ["", "feature kern {", "  lookup jzp_glyph_positioning;", ""]
    # cleanup: hide stray glyphs of half-formed words (up to 10 deep), and
    # give space its advance back at word boundaries
    for context, marked, value in (("numbersign", "@area_wild", "<-1000 0 0 0>"),
                                   ("blank_colon", "@area_wild", "<-1000 0 0 0>"),
                                   ("@new_word_char", "@space_char", "<0 0 -1000 0>")):
        for n in range(10, -1, -1):
            tokens = " ".join([context] + ["@area_wild"] * n + [f"{marked}'"])
            lines.append(f"  pos {tokens} {value};")
    lines.append("} kern;")
    return lines
