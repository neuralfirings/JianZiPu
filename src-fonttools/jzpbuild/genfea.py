"""Assemble the complete generated feature file."""

import json

from . import config
from .features import gen_gsub
from .gpos import gen_gpos


def load_layouts() -> dict:
    return json.loads(config.LAYOUTS_JSON.read_text())


def generate(classic_pos: bool = False) -> str:
    """GSUB from components.csv + design.json areas, then GPOS: the cursive
    chain rules generated from design.json (default), or, with
    `classic_pos`, the legacy per-frame rules from inputs/layouts.json and
    gpos.py (kept only so the parity test can compare the two)."""
    lines = gen_gsub()
    lines.append("")
    if classic_pos:
        lines += gen_gpos(load_layouts())
    else:
        from .data import load_design
        from .positioning.emit import gen_gpos as gen_cursive_gpos
        lines += gen_cursive_gpos(load_design()).lines
    return "\n".join(lines) + "\n"
