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


def test_rows_show_every_spelling_and_an_id():
    r = rows("mod_fanyin,,,fanyin,fy,泛音,泛音,fànyīn,1c", "mod_chuo,,/,,,绰,綽,chuò,1c", "lg_banlun,,,banlun,bl,半轮,半輪,bàn lún,2c")
    sec = {"1c": {"kind": "usage", "usage": ["{}s9u6", "{}名九挑六"]}, "2c": {"kind": "vertical"}}
    out = glossary.render(page("1c", "2c"), r, sec)
    assert "<td><span class=\"nw\">fanyin</span>, <span class=\"nw\">fy</span></td>" in out and "<td>泛音</td>" in out          # the same traditional isn't repeated
    assert "<txs><r>fanyin</r>s9u6</txs>" in out and "<txs><r>fy</r>s9u6</txs>" in out
    assert "<td><span class=\"nw\">绰</span>, <span class=\"nw\">綽</span></td>" in out and "<txs><r>綽</r>名九挑六</txs>" in out
    assert "<span class=\"nw\">:bl</span>" in out and "<span class=\"nw\">:半輪</span>" in out
    # one count down the whole page: 1c has rows 1 and 2, so 2c starts at 3
    assert '<tr id="1">' in out and '<a href="#2">2</a>' in out and '<tr id="3">' in out and 'id="4"' not in out
    ex = [e for w, e in glossary.examples(out, r, sec)]          # every spelling gets typed
    assert ["泛音名九挑六", "fanyins9u6", "fys9u6"] in ex and ["绰名九挑六", "綽名九挑六", "/s9u6"] in ex


def test_spellings_are_escaped():
    r = rows("mod_ji,,>,,,急,,jí,1b")
    out = glossary.render(page("1b"), r, {"1b": {"kind": "usage", "usage": ["s9{}k3", "名九{}勾三"]}})
    assert "<td>&gt;</td>" in out and "s9<r>&gt;</r>k3" in out


def test_vertical_rows_words_partners_and_numbers():
    r = rows("md_san,md_san2,0,,,散,,sàn,3c: Numbers", "md_san2,,,san,,,,,", "md_1,,1,,,一,,yī,3c: Numbers",
             "md_2,,2,,,二,,èr,3c: Numbers", "md_dai,,,dai,,带,,dài,", "md_qi,,,qi,,起,,qǐ,3c: Numbers")
    sec = {"3c": {"title": "3c: Numbers", "kind": "vertical", "rows": ["md_1", "md_2", "md_san", ["md_dai", "md_qi"]]}}
    out = glossary.render(page("3c"), r, sec)
    assert "<td>:1..:2</td>" in out and "<td>:一..:二</td>" in out
    assert "<td><span class=\"nw\">:0</span>, <span class=\"nw\">:san</span></td>" in out and "<td>:散</td>" in out and "<td>sàn</td>" in out
    assert "<td>:daiqi</td>" in out and "<jzp>:带起</jzp>" in out and "<td>dài qǐ</td>" in out
    assert out.index(":daiqi") < out.index("<td>:qi</td>")     # glyphs rows leaves out come after
    assert glossary.missing(r, sec) == []                        # md_san2 by its partner, md_dai in a word


def test_missing_names_glyphs_with_no_row_and_unknown_sections():
    r = rows("lg_gou,,,k,,勾,,gōu,", "lg_tiao,,,u,,挑,,tiāo,9z: Nowhere")
    problems = glossary.missing(r, {"2a": {"title": "2a: Basic Right Hand", "kind": "usage", "usage": ["{}", "{}"]}})
    assert any(p.startswith("lg_gou") and "no row" in p for p in problems)
    assert any("9z: Nowhere" in p for p in problems)


def test_the_column_names_sections_by_title():
    sec = {"1d": {"title": "1d: Special Cases", "kind": "usage", "usage": ["{}k5", "{}勾五"]},
           "3c": {"title": "3c: Related to String & Hui Number", "kind": "vertical"}}
    r = rows("md_san,,0,,,散,,sàn,1d: Special Cases; 3c: Related to String & Hui Number")
    assert glossary.section_ids(r["md_san"]) == ["1d", "3c"]
    assert glossary.missing(r, sec) == []
    out = glossary.render(page("1d", "3c"), r, sec)
    assert "<td>0</td>" in out and "<td>:0</td>" in out
    # a title that doesn't match glossary.json, and a section title without its id
    stale = rows("md_san,,0,,,散,,sàn,1d: Special cases")
    assert any("Use the same title" in p for p in glossary.missing(stale, sec))
    assert any("should start with" in p for p in glossary.missing({}, {"1d": {"title": "Special Cases", "kind": "usage"}}))


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


# ---------------------------------------------------------------- the Meaning column

def test_a_meaning_column_joins_only_a_section_that_has_one():
    sec = {"2a": {"kind": "usage", "usage": ["0{}5", "散{}五"]}, "2c": {"kind": "vertical"}}
    r = rows("lg_gou,,,k,,勾,,gōu,2a,Pluck the string inward with the middle finger <m>",
             "lg_tiao,,,u,,挑,,tiāo,2a,", "lg_lun,,,lun,,轮,,lún,2c,")
    out = glossary.render(page("2a", "2c"), r, sec)
    a, c = out.split("<!-- glossary 2c -->")
    assert '<th width="22%">Meaning</th>' in a and '<td class="meaning">Pluck the string inward with the middle finger &lt;m&gt;</td>' in a
    assert '<td class="meaning"></td>' in a                                  # every row of the section gets the cell
    assert "Meaning" not in c and '<th width="23%">ASCII</th>' in c          # 2c has none: the table stays as it was
    assert glossary.render(out, r, sec) == out


def test_a_vertical_row_falls_back_to_the_partners_meaning():
    sec = {"3c": {"title": "3c: Numbers", "kind": "vertical"}}
    r = rows("md_san,md_san2,0,,,散,,sàn,3c: Numbers,", "md_san2,,,san,,,,,,Open string")
    assert '<td class="meaning">Open string</td>' in glossary.render(page("3c"), r, sec)
    r["md_san"]["meaning"] = "Its own"
    assert '<td class="meaning">Its own</td>' in glossary.render(page("3c"), r, sec)


def test_a_csv_without_the_meaning_column_still_loads(tmp_path):
    p = tmp_path / "components.csv"
    p.write_text("glyph_name,vert_variant,common,latin,latin_alt,simplified,traditional,pinyin,glossary\n"
                 "lg_gou,,,k,,勾,,gōu,2a\n", encoding="utf-8")
    assert glossary.load_rows(p)["lg_gou"]["meaning"] == ""


# ---------------------------------------------------------------- the Builder's check

def shipped(**extra) -> list[dict]:
    """components.csv as the Builder sends it, plus `extra` rows by glyph name."""
    import csv
    with open(config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        recs = list(csv.DictReader(f))
    return recs + [{"glyph_name": g, **r} for g, r in extra.items()]


def test_the_check_passes_the_shipped_files():
    pytest.importorskip("uharfbuzz")
    out = glossary.check(glossary.records(shipped()))
    assert out["ok"] and out["problems"] == [] and out["typing"] == [] and out["not_built"] == []
    text = config.SITE_INDEX.read_text(encoding="utf-8")
    assert [t["id"] for t in out["tables"]] == [m.group(2) for m in glossary.BLOCK_RE.finditer(text)]
    assert all(t["html"] in text for t in out["tables"])                    # the tables the page has


def test_the_check_shows_unsaved_rows_and_waits_for_a_build_for_a_new_glyph():
    pytest.importorskip("uharfbuzz")
    new = {"latin": "tc", "simplified": "推出", "pinyin": "tuīchū", "glossary": "1c: Left Hand Techniques",
           "meaning": "Push the string out"}
    out = glossary.check(glossary.records(shipped(md_foo=new, md_bar={"latin": "zz", "glossary": "9z: Nowhere"})))
    t = next(t for t in out["tables"] if t["id"] == "1c")
    assert "<td>tc</td>" in t["html"] and '<td class="meaning">Push the string out</td>' in t["html"]
    assert out["not_built"] == ["md_bar", "md_foo"] and out["typing"] == []   # not a false alarm: Build, then check
    assert any("9z: Nowhere" in p for p in out["problems"])


def test_the_check_reports_what_a_release_would_stop_on():
    out = glossary.check(glossary.records(shipped(md_foo={"latin": "tc", "glossary": "1c: Left Hand Techniques"})))
    assert not out["ok"] and "needs an ASCII and a Chinese spelling" in out["error"]


def test_the_check_reports_a_glyph_whose_glossary_column_is_empty():
    # a draft older than the Glossary column: glossary.json lists the glyph, the row doesn't name the section
    recs = [{**r, "glossary": ""} if r["glyph_name"] == "mod_chuo" else r for r in shipped()]
    out = glossary.check(glossary.records(recs))
    assert not out["ok"] and "lists mod_chuo" in out["error"]


def test_http_check_locally_and_online(monkeypatch):
    pytest.importorskip("uharfbuzz")
    import json
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer
    from jzpbuild import hosted, webserver
    srv = ThreadingHTTPServer(("127.0.0.1", 0), webserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"

    def post(body, token=None):
        headers = {"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
        req = urllib.request.Request(base + "/api/glossary/check", data=json.dumps(body).encode(), method="POST",
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def font(url):
        with urllib.request.urlopen(base + url, timeout=30) as r:
            return r.read()[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true")
    try:
        status, res = post({"rows": shipped()[::-1]})       # the Builder sends them in any order
        assert status == 200 and res["ok"] and res["problems"] == [] and res["tables"]
        text = config.SITE_INDEX.read_text(encoding="utf-8")
        assert all(t["html"] in text for t in res["tables"])  # in components.csv's order, as the page has them
        assert post({"rows": "nope"})[1]["ok"] is False
        assert font(res["font_url"]) and font("/api/glossary/font")
        # online: a signed-in tester checks their draft's spellings; signed out, nothing
        s = hosted.Settings(hosted=True, supabase_url="https://example.supabase.co", supabase_anon_key="anon")
        auth = hosted.Auth(s)
        monkeypatch.setattr(auth, "fetch_user", lambda token: {"id": "user-a"} if token == "tok-a" else None)
        monkeypatch.setattr(webserver, "SETTINGS", s)
        monkeypatch.setattr(webserver, "AUTH", auth)
        assert post({"rows": shipped()})[0] == 401
        new = {"latin": "tc", "simplified": "推出", "pinyin": "tuīchū", "glossary": "1c: Left Hand Techniques"}
        status, res = post({"rows": shipped(md_foo=new)}, "tok-a")
        assert status == 200 and res["ok"] and res["not_built"] == ["md_foo"]
        assert any("<td>tc</td>" in t["html"] for t in res["tables"])
        assert font(res["font_url"]) and font("/api/glossary/font")
    finally:
        srv.shutdown()
