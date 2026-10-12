"""Which areas' own glyph identity a LAYOUTS entry's gap overrides depend on,
and what glyphs each such area can take -- shared by classes.py (class
generation) and build.py (rule branching) so the two agree by construction on
which areas get a specific-glyph class and which don't.

A relationship's gap override list only ever names GLYPHS (components.csv's
glyph_name column -- unambiguous, unlike ASCII keys which can collide across
areas, e.g. "0" means both md_san in area_hui and md_san2 in area_char), split
across two keys: "base_signifiers" (names the relationship's own `base`
area's glyph) and "elem_signifiers" (names its `elem` area's glyph) -- see
anchors.resolve_gap. Which AREA a listed glyph belongs to is therefore read
directly off the relationship (`rel["base"]`/`rel["elem"]`), not inferred by
scanning components.csv for a matching row -- e.g. area_right's own technique
glyphs (the pivot, already handled by signifiers.KEY_TO_GLYPH/
classes.signifier_token) show up here too whenever a relationship's `elem` or
`base` happens to be the pivot area itself; this module doesn't special-case
that, build.py's `token()` does.
"""

from jzpbuild import data

from . import signifiers


def area_glyph_buckets(layout: dict) -> dict[str, dict[str, object]]:
    """For `layout` (one geometry.LAYOUTS entry): {area: {"glyphs": [...],
    "catch_all": bool}} for every area some relationship's gap-override
    "base_signifiers"/"elem_signifiers" list references (keyed by that
    relationship's own `base`/`elem`, respectively). `glyphs` is the
    ordered, deduplicated list of that area's own glyphs actually
    referenced anywhere in this layout (NOT every glyph the area could ever
    contain -- see build.py's branching, which is scoped to just these for
    efficiency). `catch_all` is True if any override entry touching this
    area's role in some relationship omits that role's signifier key (i.e.
    would match regardless of this area's specific glyph), meaning an
    "every other glyph in this area" class/rule-variant is needed too."""
    buckets: dict[str, dict[str, object]] = {}
    unconstrained: list[tuple[str, str, list]] = []  # (area, key, gap) to check for catch-all
    for rel in layout["relationships"]:
        gap = rel["gap"]
        if not isinstance(gap, list):
            continue
        for area, key in ((rel["base"], "base_signifiers"), (rel["elem"], "elem_signifiers")):
            if area is None:
                continue
            for entry in gap:
                glyphs = entry.get(key)
                if not glyphs:
                    continue
                bucket = buckets.setdefault(area, {"glyphs": [], "catch_all": False})
                for glyph in glyphs:
                    if glyph not in bucket["glyphs"]:
                        bucket["glyphs"].append(glyph)
            unconstrained.append((area, key, gap))

    for area, key, gap in unconstrained:
        if area not in buckets:
            continue  # never referenced by an explicit signifier -- not identity-sensitive
        if any(not entry.get(key) for entry in gap):
            other_glyphs = [g for g in area_glyphs(area) if g not in buckets[area]["glyphs"]]
            if other_glyphs:
                buckets[area]["catch_all"] = True
    return buckets


def area_glyphs(area: str, rows: list["data.GlyphRow"] | None = None) -> list[str]:
    """Every glyph_name belonging to `area` (components.csv rows under
    signifiers.csv_column_for(area) -- resolves a numbered "repeat slot"
    like "char_2" to its base area's column automatically, see that
    function's docstring)."""
    col = signifiers.csv_column_for(area)
    rows = rows if rows is not None else data.load_components()
    return [row.glyph_name for row in rows if row.in_area(col)]
