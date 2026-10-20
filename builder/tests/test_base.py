"""The base font's control glyphs: how wide | and : are comes from the design (Area Properties).

Run:  cd builder && python3 -m pytest tests/test_base.py
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import base, config  # noqa: E402


def design_with(tmp_path, **areas):
    d = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    for name, patch in areas.items():
        d["areas"][name].update(patch)
    p = tmp_path / "design.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    return p


def test_control_glyphs_take_their_areas_advance(tmp_path):
    widths = base.control_widths(design_with(tmp_path, bar={"advance": 500}))
    assert widths["blank_bar"] == 500
    assert widths["blank_colon"] == 1000          # the Vertical marker's own advance
    assert widths["blank"] == 0                   # in no area with an advance: the default


def test_an_area_without_advance_keeps_the_default(tmp_path):
    p = design_with(tmp_path, bar={"advance": 0})
    assert base.control_widths(p)["blank_bar"] == config.CONTROL_GLYPHS["blank_bar"][1]


def test_an_unreadable_design_keeps_the_defaults(tmp_path):
    (tmp_path / "broken.json").write_text("{")
    assert base.control_widths(tmp_path / "broken.json") == {n: w for n, (_, w) in config.CONTROL_GLYPHS.items()}


@pytest.mark.skipif(not config.SOURCE_FONT.exists(), reason="needs the base font (src_font/TW-Kai-98.ttf)")
def test_built_font_uses_the_bar_width_from_the_design(tmp_path):
    out = tmp_path / "JianZiPu.ttf"
    subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", "",
                    "--design", str(design_with(tmp_path, bar={"advance": 500, "size": [500, 1000]}))],
                   cwd=config.BUILDER_DIR, check=True, capture_output=True)
    assert TTFont(str(out))["hmtx"]["blank_bar"][0] == 500
