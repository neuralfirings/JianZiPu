"""The glossary on the font page (jzpbuild/glossary.py): the tables in site/index.html are the ones
components.csv and site/glossary.json make, every glyph with a spelling has a row, and every example
on the page (lessons included) types the glyphs it shows.

Run:  cd builder && python3 -m pytest tests/test_glossary.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import config, glossary  # noqa: E402
from jzpbuild.glossary import GlossaryError  # noqa: E402

FIELDS = glossary.FIELDS


def rows(*recs: str) -> dict[str, dict]:
    """'lg_gou,,,k,,勾,,gōu,2a' -> the row dict load_rows() makes."""
    out = {}
    for line in recs:
        r = dict(zip(FIELDS, line.split(",")))
        out[r["glyph_name"]] = {f: r.get(f, "") for f in FIELDS}
    return out


def page(*ids: str) -> str:
    return "<p>hand</p>\n" + "".join(f"<!-- glossary {i} -->\n<!-- /glossary {i} -->\n" for i in ids)


# ---------------------------------------------------------------- the page in the repo

def test_the_page_is_up_to_date():
    text = config.SITE_INDEX.read_text(encoding="utf-8")
    assert glossary.render(text) == text, "run `cd builder && python3 -m jzpbuild.glossary` and commit site/index.html"


def test_every_glyph_with_a_spelling_has_a_row():
    assert glossary.missing(glossary.load_rows(), glossary.load_sections()) == []


def test_every_example_on_the_page_types_what_it_shows():
    pytest.importorskip("uharfbuzz")
    problems = glossary.check_typing()
    assert problems == [], "\n".join(problems)


# ---------------------------------------------------------------- the generator

def test_the_columns_match_the_builders():
    from jzpbuild import typing_preview
    assert glossary.FIELDS == typing_preview.ROW_FIELDS


def test_the_scope_check_needs_only_the_standard_library():
    # .github/workflows/scope.yml runs release.py (and so glossary.py) with nothing installed
    import subprocess
    code = ("import sys; sys.modules['fontTools'] = None; sys.modules['uharfbuzz'] = None; "
            "from jzpbuild import release, glossary; print('ok')")
    r = subprocess.run([sys.executable, "-c", code], cwd=config.BUILDER_DIR, capture_output=True, text=True)
    assert r.stdout.strip() == "ok", r.stderr


def test_usage_rows_fill_the_template_with_the_glyphs_spellings():
    r = rows("lg_gou,,,k,,勾,,gōu,2a", "lg_li,,,U,,历,,lì,2a")
    sec = {"2a": {"kind": "usage", "usage": ["0{}5", "散{}五"], "examples": {"lg_li": ["0{}65", "散{}六五"]}}}
    out = glossary.render(page("2a"), r, sec)
    assert "<td>k</td>" in out and "<td>勾</td>" in out and "<td>gōu</td>" in out
    assert "<jzp>0<r>k</r>5</jzp>" in out and "<txs>散<r>勾</r>五</txs>" in out
    assert "<txs>散<r>历</r>六五</txs>" in out
    assert out.startswith("<p>hand</p>")
    assert glossary.render(out, r, sec) == out


def test_spellings_are_escaped():
    r = rows("mod_ji,,>,,,急,,jí,1b")
    out = glossary.render(page("1b"), r, {"1b": {"kind": "usage", "usage": ["s9{}k3", "名九{}勾三"]}})
    assert "<td>&gt;</td>" in out and "s9<r>&gt;</r>k3" in out


def test_vertical_rows_words_partners_and_numbers():
    r = rows("md_san,md_san2,0,,,散,,sàn,3c", "md_san2,,,san,,,,,", "md_1,,1,,,一,,yī,3c", "md_2,,2,,,二,,èr,3c",
             "md_dai,,,dai,,带,,dài,", "md_qi,,,qi,,起,,qǐ,3c")
    sec = {"3c": {"kind": "vertical", "rows": ["md_1", "md_2", "md_san", ["md_dai", "md_qi"]]}}
    out = glossary.render(page("3c"), r, sec)
    assert "<td>:1..:2</td>" in out and "<td>:一..:二</td>" in out
    assert "<td>:0, :san</td>" in out and "<td>:散</td>" in out and "<td>sàn</td>" in out
    assert "<td>:daiqi</td>" in out and "<jzp>:带起</jzp>" in out and "<td>dài qǐ</td>" in out
    assert out.index(":daiqi") < out.index("<td>:qi</td>")     # glyphs rows leaves out come after
    assert glossary.missing(r, sec) == []                        # md_san2 by its partner, md_dai in a word


def test_missing_names_glyphs_with_no_row_and_unknown_sections():
    r = rows("lg_gou,,,k,,勾,,gōu,", "lg_tiao,,,u,,挑,,tiāo,9z")
    problems = glossary.missing(r, {"2a": {"kind": "usage", "usage": ["{}", "{}"]}})
    assert any(p.startswith("lg_gou") and "no row" in p for p in problems)
    assert any("9z" in p for p in problems)


def test_the_files_must_agree():
    r = rows("lg_gou,,,k,,勾,,gōu,")
    with pytest.raises(GlossaryError, match="add 2a there"):
        glossary.render(page("2a"), r, {"2a": {"kind": "usage", "usage": ["{}", "{}"], "rows": ["lg_gou"]}})
    with pytest.raises(GlossaryError, match="no glossary marker"):
        glossary.render(page(), r, {"2a": {"kind": "usage", "usage": ["{}", "{}"]}})
    with pytest.raises(GlossaryError, match="doesn't define"):
        glossary.render(page("2a"), r, {})


def test_strip_generated_keeps_only_the_hand_written_page():
    r = rows("lg_gou,,,k,,勾,,gōu,2a")
    sec = {"2a": {"kind": "usage", "usage": ["{}", "{}"]}}
    a = glossary.render(page("2a"), r, sec)
    b = glossary.render(page("2a"), rows("lg_gou,,,g,,勾,,gōu,2a"), sec)
    assert a != b and glossary.strip_generated(a) == glossary.strip_generated(b) == glossary.strip_generated(page("2a"))


def test_hand_written_examples_are_split_at_sentences():
    text = ("<p>Use <text>外</text> or <text>13+</text> for <jzp>:wai</jzp>. Then <text>散</text>.</p>"
            "<li><text>名九勾五</text> or <text>s9k5</text> → <jzp>s9k5</jzp></li>")
    ex = [e for w, e in glossary.examples(text, {}, {})]
    assert ex == [["外", "13+", ":wai"], ["名九勾五", "s9k5", "s9k5"]]
