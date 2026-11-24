"""The glyph editor's Text tool: characters' outlines from the base font (jzpbuild/base_outline.py,
GET /api/base-font/outline). TW-Kai isn't in the repo, so these read the released font, whose Chinese
characters are TW-Kai's own outlines, as the base font."""

import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jzpbuild import base_outline, config  # noqa: E402
from tests.test_webserver import call, server, svg_dir  # noqa: E402,F401  (fixtures)

FONT = Path(__file__).resolve().parents[2] / "site" / "JianZiPu.ttf"


@pytest.fixture
def base_font(monkeypatch):
    monkeypatch.setattr(config, "SOURCE_FONT", FONT)
    return FONT


def test_each_character_comes_back_in_order_with_its_advance(base_font):
    r = base_outline.outlines("名 起")
    assert [c["char"] for c in r["chars"]] == ["名", "起"]        # the space is dropped
    assert r["missing"] == [] and r["upm"] == 1000 and r["font"] == "JianZiPu"
    assert all(c["advance"] == 1024 and c["d"].startswith("M") for c in r["chars"])


def test_the_outline_is_y_down_with_the_baseline_at_0(base_font):
    # 名 sits mostly above its baseline in the font (y up): in SVG terms, mostly above y 0, i.e. negative
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.svgLib.path import parse_path
    pen = BoundsPen(None)
    parse_path(base_outline.outlines("名")["chars"][0]["d"], pen)
    x0, y0, x1, y1 = pen.bounds
    assert (x0, y0, x1, y1) == (100, -703, 867, 112)        # the font's (100, -112, 867, 703), flipped


def test_characters_the_font_lacks_are_named_once(base_font):
    r = base_outline.outlines("這這名")
    assert [c["char"] for c in r["chars"]] == ["名"] and r["missing"] == ["這"]


def test_at_most_twenty_characters(base_font):
    assert len(base_outline.outlines("名" * 50)["chars"]) == base_outline.MAX_CHARS


def test_without_the_base_font_it_says_where_to_put_it(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SOURCE_FONT", tmp_path / "src_font" / "TW-Kai-98.ttf")
    with pytest.raises(base_outline.NoBaseFont, match="copy TW-Kai-98.ttf into builder/src_font/"):
        base_outline.outlines("名")


def test_http(server, base_font):  # noqa: F811
    status, r = call(server, "GET", "/api/base-font/outline?text=" + urllib.parse.quote("名這"))
    assert status == 200 and r["ok"] and [c["char"] for c in r["chars"]] == ["名"] and r["missing"] == ["這"]


def test_http_without_the_base_font(server, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setattr(config, "SOURCE_FONT", tmp_path / "nope.ttf")
    status, r = call(server, "GET", "/api/base-font/outline?text=x")
    assert status == 404 and r["ok"] is False and "base font" in r["error"]
