"""Assemble the complete generated feature file."""

import json

from . import config
from .features import gen_gsub
from .gpos import gen_gpos


def load_positions() -> dict:
    return json.loads(config.POSITIONS_JSON.read_text())


def generate() -> str:
    lines = gen_gsub()
    lines.append("")
    lines += gen_gpos(load_positions())
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    text = generate()
    if len(sys.argv) > 1:
        from pathlib import Path
        Path(sys.argv[1]).write_text(text)
    else:
        sys.stdout.write(text)
