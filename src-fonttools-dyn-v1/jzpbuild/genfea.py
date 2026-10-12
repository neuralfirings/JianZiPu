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
    layouts = load_layouts()
    if dynamic_pos:
        from dynamic_positioning.geometry import RIGHT_KEYS as dynamic_right_keys
        dynamic_families = set(dynamic_right_keys)
    else:
        dynamic_families = set()
    lines += gen_gpos(layouts, skip_right_keys=dynamic_families, zero_others=dynamic_pos_only)
    if dynamic_pos:
        from dynamic_positioning import gen_dynamic_gpos
        lines.append("")
        lines += gen_dynamic_gpos(layouts, right_keys=tuple(dynamic_right_keys))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    text = generate()
    if len(sys.argv) > 1:
        from pathlib import Path
        Path(sys.argv[1]).write_text(text)
    else:
        sys.stdout.write(text)
