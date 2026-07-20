"""Browser-tool data mirror for builder/inputs/glyphAreas.csv.

tools/positions_checker.html runs over file://, where fetch()/XHR can't
load local sibling files (verified against Chromium) but <script src> can
— see figma.py::write_browser_data() for the same trick applied to the
Figma-fetched positions.json/svg/*.svg. This does the equivalent for the
one hand-maintained CSV the tool also needs.

  python -m jzpbuild.toolsdata   # refresh inputs/glyphAreas.js from the CSV
"""

import json

from . import config


def write_glyph_areas_js() -> None:
    raw = config.AREA_KEY_CSV.read_text()
    config.GLYPH_AREAS_JS.write_text(
        "window.JZP_GLYPH_AREAS_CSV = " + json.dumps(raw) + ";\n")
    print(f"  wrote {config.GLYPH_AREAS_JS}")


if __name__ == "__main__":
    write_glyph_areas_js()
