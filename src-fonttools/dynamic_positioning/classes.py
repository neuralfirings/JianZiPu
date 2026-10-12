"""Per-signifier glyph classes for dynamic_positioning's own GPOS scoping.

Deliberately separate from jzpbuild/features.py's shared
@area_right__{family} classes (one class per FAMILY, e.g. lg_gou and
lg_da both in @area_right__gou) -- those stay untouched and are still
what classic gpos.py's zeroing (--dynamic_pos's skip_right_keys) and this
module's own cross-family "blocker" rule rely on. This module additionally
needs one class per SIGNIFIER (per actual glyph, e.g. @area_right__gou__k
for lg_gou vs @area_right__gou__l for lg_da -- named after the ASCII key,
see signifiers.py) so build.py can generate independently-positioned
rules for lg_gou and lg_da instead of forcing them to share one value.

Driven by geometry.LAYOUTS, same as build.py -- every key any LAYOUTS
entry's selector.contains lists gets a class here, regardless of which
topology it resolves through.

Nothing here is imported unless --dynamic_pos/--dynamic_pos_only is
active (see jzpbuild/genfea.py) -- plain `jzpbuild` never reaches this
file, so reverting dynamic_positioning entirely is just "stop passing the
flag," no code path here runs otherwise.
"""

from . import geometry, identity, signifiers

# Areas classic jzpbuild/features.py::gen_classes() already declares an
# identically-named base class for (@area_left, @area_hui, @area_char, ...)
# -- build.py's generic token() can reference these directly, no class of
# ours needed. Every OTHER non-pivot area a LAYOUTS entry uses (e.g. vert's
# char_1, char_2, left_2, ...) needs a class gen_repeated_area_classes()
# below generates itself, since classic has no base declaration for it at
# all under THIS name -- see repeated_area_token for why "under this name"
# matters.
CLASSIC_BASE_AREAS = frozenset(signifiers.AREA_TO_CSV_COLUMN)


def repeated_area_token(area: str) -> str:
    """FEA class name for a self-generated "repeat slot" area (build.py's
    token() fallback for anything not in CLASSIC_BASE_AREAS). Deliberately
    NOT `@area_{area}` -- classic jzpbuild/features.py::gen_classes() already
    declares its own row-numbered vert-mode aliases (@area_char1, @area_
    left_1, @area_hui_1, ...) for an unrelated purpose, under a naming
    scheme (char{i} vs left_{i}, capped at 4) this module doesn't follow.
    "left_1" collides by pure coincidence with one of those -- since
    fontTools' feaLib silently lets a later `@name = [...]` overwrite an
    earlier one with no duplicate-definition error (SymbolTable.define is a
    plain dict write), reusing classic's `@area_` namespace here would work
    by luck only as long as membership happens to match, and silently
    corrupt classic's own (still-unconditionally-emitted, see gpos.py's
    vert_rules) rules the moment it doesn't. A distinct prefix makes that
    class of bug structurally impossible instead of coincidentally avoided."""
    return f"@dp_area_{area}"


def gen_repeated_area_classes() -> list[str]:
    """One repeated_area_token(name) class per LAYOUTS area that ISN'T one
    of classic's own pre-declared base classes (CLASSIC_BASE_AREAS) and
    isn't any topology's own pivot (pivots get their per-signifier class
    from signifier_token instead) -- auto-detected purely from
    geometry.LAYOUTS, no separate registration. `signifiers.csv_column_for`
    is what actually resolves a numbered area like "char_2" to a real
    components.csv column (stripping the trailing "_2" and finding "char"'s
    own column) -- an area that resolves to nothing (a control-glyph area
    like colon/bar, always a pivot) is silently skipped, since
    csv_column_for raising KeyError for it is expected, not an authoring
    mistake."""
    areas: dict[str, str] = {}
    for layout in geometry.LAYOUTS:
        pivot = next(e["area"] for e in layout["order"] if e.get("pivot"))
        referenced = {e["area"] for e in layout["order"]}
        referenced |= {r["elem"] for r in layout["relationships"]}
        referenced |= {r["base"] for r in layout["relationships"] if r["base"]}
        for area in referenced:
            if area == pivot or area in CLASSIC_BASE_AREAS or area in areas:
                continue
            try:
                areas[area] = signifiers.csv_column_for(area)
            except KeyError:
                continue
    lines = []
    for area in sorted(areas):
        glyphs = identity.area_glyphs(area)
        lines.append(f"  {repeated_area_token(area)} = [ {' '.join(glyphs)} ];")
    return lines


def signifier_token(family: str, key: str) -> str:
    """FEA class name for this (family, key) signifier. Built from the
    GLYPH name, not the raw key -- some keys (e.g. cuo's "|") aren't valid
    characters inside a FEA identifier, but glyph names in this pipeline
    always are."""
    glyph = signifiers.KEY_TO_GLYPH[key]
    return f"@area_right__{family}__{glyph}"


def gen_signifier_classes() -> list[str]:
    lines = []
    for layout in geometry.LAYOUTS:
        for key in layout["selector"].get("contains", ()):
            # Falls back to the layout's own name when this key isn't part
            # of the RIGHT_SELECTORS/family system at all (e.g. cuo's
            # chord keys) -- see build.py's gen_dynamic_gpos.
            family = signifiers.family_for_key(key) or layout["name"]
            glyph = signifiers.KEY_TO_GLYPH[key]
            lines.append(f"{signifier_token(family, key)} = [ {glyph} ];")
    return lines


def area_glyph_token(layout_name: str, area: str, glyph: str) -> str:
    """FEA class name for one specific glyph within a non-pivot area (e.g.
    area_hui's md_5) -- the generalization of signifier_token to any area a
    gap override references, not just the pivot. Scoped by layout name (like
    signifier_token is scoped by family) so two LAYOUTS entries referencing
    the same area with different override subsets never collide. See
    identity.py."""
    return f"@area_{layout_name}__{area}__{glyph}"


def area_glyph_other_token(layout_name: str, area: str) -> str:
    """FEA class name for "every glyph in this area except the ones with
    their own area_glyph_token" -- the catch-all counterpart."""
    return f"@area_{layout_name}__{area}__other"


def gen_area_glyph_classes() -> list[str]:
    """One class per (layout, area, glyph) any LAYOUTS entry's gap overrides
    reference (identity.area_glyph_buckets), plus an "other" class per
    (layout, area) that also declares a catch-all override -- see
    identity.py."""
    lines = []
    for layout in geometry.LAYOUTS:
        for area, bucket in identity.area_glyph_buckets(layout).items():
            for glyph in bucket["glyphs"]:
                token = area_glyph_token(layout["name"], area, glyph)
                lines.append(f"{token} = [ {glyph} ];")
            if bucket["catch_all"]:
                other_glyphs = [g for g in identity.area_glyphs(area) if g not in bucket["glyphs"]]
                other_token = area_glyph_other_token(layout["name"], area)
                lines.append(f"{other_token} = [ {' '.join(other_glyphs)} ];")
    return lines
