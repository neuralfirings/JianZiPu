"""Assemble the complete generated feature file."""

import json

from . import config
from .features import gen_gsub
from .gpos import gen_gpos


def load_layouts() -> dict:
    return json.loads(config.LAYOUTS_JSON.read_text())


def generate(dynamic_pos: bool = False, dynamic_pos_only: bool = False) -> str:
    """`dynamic_pos_only` implies `dynamic_pos`, and additionally zeroes out
    every classic-positioned shape dynamic_positioning doesn't cover (the
    remaining right-hand families, vertical-mode words, cuo chords) -- a
    test build where anything dynamic_positioning doesn't actually handle
    renders visibly broken instead of silently working via classic. See
    jzpbuild.build's --dynamic_pos_only flag and gpos.gen_gpos's docstring.
    """
    dynamic_pos = dynamic_pos or dynamic_pos_only
    lines = gen_gsub()
    lines.append("")
    if dynamic_pos:
        # Imported only on demand: a plain build never touches
        # dynamic_positioning/ at all.
        from dynamic_positioning import geometry
        from dynamic_positioning.build import gen_dynamic_gpos
        dynamic_families = set(geometry.FAMILIES)
    else:
        dynamic_families = set()
    lines += gen_gpos(load_layouts(), skip_right_keys=dynamic_families, zero_others=dynamic_pos_only)
    if dynamic_pos:
        lines.append("")
        lines += gen_dynamic_gpos()
    return "\n".join(lines) + "\n"
