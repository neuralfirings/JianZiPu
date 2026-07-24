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
    their own area_glyph_token" -- the catch-all counterpart, mirroring
    build.py's existing @area_right_other pattern."""
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
