"""The font's name table: copyright with the Reserved Font Name and the TW-Kai credit, the OFL
license fields, and who made it.

Run:  cd builder && python3 -m pytest tests/test_names.py
"""

import subprocess
import sys
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import base, config  # noqa: E402

EXPECTED = {
    0: 'Copyright 2021-2026 Nancy Yi Liang, Nellodee LLC, with Reserved Font Name "JianZiPu". '
       "Portions derived from TW-Kai ((c) 2023 Ministry of Digital Affairs, Taiwan, CNS11643, "
       "Open Government Data License, version 1.0).",
    8: "Nellodee LLC",
    9: "Nancy Yi Liang",
    11: "https://jianzipufont.com",
    13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
    14: "https://openfontlicense.org",
}


def check(font: TTFont):
    name = font["name"]
    for nid, want in EXPECTED.items():
        for plat, enc, lang in ((3, 1, 0x409), (1, 0, 0)):
            rec = name.getName(nid, plat, enc, lang)
            assert rec is not None, (nid, plat)
            assert rec.toUnicode() == want, (nid, plat)


def test_set_metadata_writes_the_license_names():
    font = TTFont(str(config.CURRENT_FONT))        # in memory; the golden file is never written
    base.set_metadata(font)
    check(font)


@pytest.mark.skipif(not config.SOURCE_FONT.exists(), reason="needs the base font (src_font/TW-Kai-98.ttf)")
def test_built_font_carries_the_license_names(tmp_path):
    out = tmp_path / "JianZiPu.ttf"
    subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", ""],
                   cwd=config.BUILDER_DIR, check=True, capture_output=True)
    check(TTFont(str(out)))
