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

from . import geometry, signifiers


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
