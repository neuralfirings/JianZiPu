"""The glossary on the font page (jzpbuild/glossary.py): the tables in site/index.html are the ones
components.csv and site/glossary.json make, every glyph with a spelling has a row, and every example
on the page (lessons included) types the glyphs it shows.

Run:  cd builder && python3 -m pytest tests/test_glossary.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import config, glossary, typing_preview  # noqa: E402
from jzpbuild.glossary import GlossaryError  # noqa: E402

FIELDS = glossary.FIELDS


def rows(*recs: str) -> dict[str, dict]:
    """'lg_gou,,,k,,勾,,gōu' -> the row dict load_rows() makes."""
    out = {}
    for line in recs:
        r = dict(zip(FIELDS, line.split(",")))
        out[r["glyph_name"]] = {f: r.get(f, "") for f in FIELDS}
    return out


def g(name: str, meaning: str = "") -> dict:
    """A glyph's row in site/glossary.json."""
    return {"glyph": name, **({"meaning": meaning} if meaning else {})}


def w(word: str, *glyphs: str, meaning: str = "") -> dict:
    """A word's row in site/glossary.json."""
    return {"word": word, "glyphs": list(glyphs), **({"meaning": meaning} if meaning else {})}


def usage(sid: str, *rs, template=("{}", "{}"), **more) -> dict:
    return {"title": f"{sid}: {sid.upper()}", "kind": "usage", "usage": list(template), **more, "rows": list(rs)}


def vertical(sid: str, *rs) -> dict:
    return {"title": f"{sid}: {sid.upper()}", "kind": "vertical", "rows": list(rs)}


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
    r = rows("lg_gou,,,k,,勾,,gōu", "lg_li,,,U,,历,,lì")
    sec = {"2a": usage("2a", g("lg_gou"), g("lg_li"), template=("0{}5", "散{}五"), examples={"lg_li": ["0{}65", "散{}六五"]})}
    out = glossary.render(page("2a"), r, sec)
    assert "<td>k</td>" in out and "<td>勾</td>" in out and "<td>gōu</td>" in out
    assert "<jzp>0<r>k</r>5</jzp>" in out and "<txs>散<r>勾</r>五</txs>" in out
    assert "<txs>散<r>历</r>六五</txs>" in out
    assert out.startswith("<p>hand</p>")
    assert glossary.render(out, r, sec) == out


def test_rows_show_every_spelling_and_an_id():
    r = rows("mod_fanyin,,,fanyin,fy,泛音,泛音,fànyīn", "mod_chuo,,/,,,绰,綽,chuò", "lg_banlun,,,banlun,bl,半轮,半輪,bàn lún")
    sec = {"1c": usage("1c", g("mod_fanyin"), g("mod_chuo"), template=("{}s9u6", "{}名九挑六")), "2c": vertical("2c", g("lg_banlun"))}
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
    r = rows("mod_ji,,>,,,急,,jí")
    out = glossary.render(page("1b"), r, {"1b": usage("1b", g("mod_ji"), template=("s9{}k3", "名九{}勾三"))})
    assert "<td>&gt;</td>" in out and "s9<r>&gt;</r>k3" in out


def test_vertical_rows_words_partners_and_numbers_in_the_files_order():
    r = rows("md_san,md_san2,0,,,散,,sàn", "md_san2,,,san,,,,", "md_1,,1,,,一,,yī",
             "md_2,,2,,,二,,èr", "md_dai,,,dai,,带,,dài", "md_qi,,,qi,,起,,qǐ")
    sec = {"3c": vertical("3c", g("md_1"), g("md_2"), g("md_san"), w("带起", "md_dai", "md_qi"), g("md_qi"))}
    out = glossary.render(page("3c"), r, sec)
    assert "<td>:1..:2</td>" in out and "<td>:一..:二</td>" in out
    assert "<td><span class=\"nw\">:0</span>, <span class=\"nw\">:san</span></td>" in out and "<td>:散</td>" in out and "<td>sàn</td>" in out
    assert "<td>:daiqi</td>" in out and "<jzp>:带起</jzp>" in out and "<td>dài qǐ</td>" in out
    assert out.index(":1..:2") < out.index(":san") < out.index(":daiqi") < out.index("<td>:qi</td>")   # as listed
    assert glossary.missing(r, sec) == []                        # md_san2 by its partner, md_dai in a word
    sec["3c"]["rows"] = [g("md_qi"), *sec["3c"]["rows"][:-1]]     # moved to the top: first on the page
    out = glossary.render(page("3c"), r, sec)
    assert out.index("<td>:qi</td>") < out.index(":1..:2")


def test_missing_names_glyphs_with_no_row_and_rows_that_cant_be_shown():
    r = rows("lg_gou,,,k,,勾,,gōu", "lg_tiao,,,u,,挑,,tiāo")
    sec = {"2a": usage("2a", g("lg_tiao"), g("lg_tiao"), g("lg_gone"), w("挑挑", "lg_tiao", "lg_tiao"))}
    problems = glossary.missing(r, sec)
    assert any(p.startswith("lg_gou") and "no row" in p and "Glyphs > Glossary" in p for p in problems)
    assert any("lg_tiao is in the section twice" in p for p in problems)
    assert any("uses lg_gone, which isn't a glyph" in p for p in problems)
    assert any("挑挑 is in a section of example words" in p for p in problems)
    assert any("should start with" in p for p in glossary.missing({}, {"1d": {"title": "Special Cases", "kind": "usage"}}))


def test_a_glyph_can_have_a_row_in_two_sections():
    r = rows("md_san,,0,,,散,,sàn")
    sec = {"1d": usage("1d", g("md_san"), template=("{}k5", "{}勾五")), "3c": vertical("3c", g("md_san"))}
    assert glossary.missing(r, sec) == []
    out = glossary.render(page("1d", "3c"), r, sec)
    assert "<td>0</td>" in out and "<td>:0</td>" in out


def test_the_files_must_agree():
    r = rows("lg_gou,,,k,,勾,,gōu")
    with pytest.raises(GlossaryError, match="uses md_nope, which isn't a glyph"):
        glossary.render(page("2a"), r, {"2a": vertical("2a", w("勾勾", "lg_gou", "md_nope"))})
    with pytest.raises(GlossaryError, match="no glossary marker"):
        glossary.render(page(), r, {"2a": usage("2a", g("lg_gou"))})
    with pytest.raises(GlossaryError, match="doesn't define"):
        glossary.render(page("2a"), r, {})


def test_rows_from_the_builder_are_checked():
    secs = {"2a": usage("2a")}
    assert glossary.with_rows(secs, {"2a": [{"glyph": " lg_gou ", "meaning": ""}]})["2a"]["rows"] == [{"glyph": "lg_gou"}]
    assert secs["2a"]["rows"] == []                                  # a copy: the loaded sections stay
    for bad in ({"9z": []}, {"2a": [{"nope": 1}]}, {"2a": [{"word": "x", "glyphs": "a b"}]}, {"2a": "x"}, []):
        with pytest.raises(ValueError):
            glossary.with_rows(secs, bad)


def test_the_file_keeps_one_row_per_line():
    doc = {"about": ["a"], "sections": {"2a": usage("2a", g("lg_gou"), w("带起", "md_dai", "md_qi", meaning="m"))}}
    text = glossary.dumps(doc)
    assert json.loads(text) == doc
    assert '        {"word": "带起", "glyphs": ["md_dai", "md_qi"], "meaning": "m"}\n' in text
    assert glossary.dumps(json.loads(config.GLOSSARY_SECTIONS.read_text(encoding="utf-8"))) == \
        config.GLOSSARY_SECTIONS.read_text(encoding="utf-8"), "site/glossary.json is written as the Builder writes it"


def test_strip_generated_keeps_only_the_hand_written_page():
    sec = {"2a": usage("2a", g("lg_gou"))}
    a = glossary.render(page("2a"), rows("lg_gou,,,k,,勾,,gōu"), sec)
    b = glossary.render(page("2a"), rows("lg_gou,,,g,,勾,,gōu"), sec)
    assert a != b and glossary.strip_generated(a) == glossary.strip_generated(b) == glossary.strip_generated(page("2a"))


def test_hand_written_examples_are_split_at_sentences():
    text = ("<p>Use <text>外</text> or <text>13+</text> for <jzp>:wai</jzp>. Then <text>散</text>.</p>"
            "<li><text>名九勾五</text> or <text>s9k5</text> → <jzp>s9k5</jzp></li>")
    ex = [e for w, e in glossary.examples(text, {}, {})]
    assert ex == [["外", "13+", ":wai"], ["名九勾五", "s9k5", "s9k5"]]


# ---------------------------------------------------------------- the Meaning column

def test_a_meaning_column_joins_only_a_section_that_has_one():
    r = rows("lg_gou,,,k,,勾,,gōu", "lg_tiao,,,u,,挑,,tiāo", "lg_lun,,,lun,,轮,,lún")
    sec = {"2a": usage("2a", g("lg_gou", "Pluck the string inward with the middle finger <m>"), g("lg_tiao"), template=("0{}5", "散{}五")),
           "2c": vertical("2c", g("lg_lun"))}
    out = glossary.render(page("2a", "2c"), r, sec)
    a, c = out.split("<!-- glossary 2c -->")
    assert '<th width="22%">Meaning</th>' in a and '<td class="meaning">Pluck the string inward with the middle finger &lt;m&gt;</td>' in a
    assert '<td class="meaning"></td>' in a                                  # every row of the section gets the cell
    assert "Meaning" not in c and '<th width="23%">ASCII</th>' in c          # 2c has none: the table stays as it was
    assert glossary.render(out, r, sec) == out


def test_a_meaning_belongs_to_the_row_and_keeps_a_number_on_its_own():
    r = rows("md_1,,1,,,一,,yī", "md_2,,2,,,二,,èr", "md_3,,3,,,三,,sān")
    sec = {"3c": vertical("3c", g("md_1"), g("md_2", "two"), g("md_3"))}
    out = glossary.render(page("3c"), r, sec)
    assert '<td class="meaning">two</td>' in out and ":1..:3" not in out and out.count("<tr id=") == 3


def test_a_csv_with_the_old_glossary_columns_still_loads(tmp_path):
    p = tmp_path / "components.csv"
    p.write_text("glyph_name,vert_variant,common,latin,latin_alt,simplified,traditional,pinyin,glossary,glossary_order,meaning\n"
                 "lg_gou,,,k,,勾,,gōu,2a,1,x\n", encoding="utf-8")
    assert glossary.load_rows(p)["lg_gou"] == {**{f: "" for f in FIELDS}, "glyph_name": "lg_gou", "latin": "k", "simplified": "勾", "pinyin": "gōu"}


# ---------------------------------------------------------------- the Builder's check

def shipped(**extra) -> list[dict]:
    """components.csv as the Builder sends it, plus `extra` rows by glyph name."""
    import csv
    with open(config.COMPONENTS_CSV, newline="", encoding="utf-8-sig") as f:
        recs = list(csv.DictReader(f))
    return recs + [{"glyph_name": g, **r} for g, r in extra.items()]


def with_rows(**extra) -> dict[str, dict]:
    """The shipped sections with `extra` rows added at the end of a section, by section id."""
    secs = glossary.load_sections()
    return glossary.with_rows(secs, {sid: secs[sid]["rows"] + rs for sid, rs in extra.items()})


def test_the_check_passes_the_shipped_files():
    pytest.importorskip("uharfbuzz")
    out = glossary.check(glossary.records(shipped()))
    assert out["ok"] and out["problems"] == [] and out["typing"] == [] and out["not_built"] == []
    text = config.SITE_INDEX.read_text(encoding="utf-8")
    assert [t["id"] for t in out["tables"]] == [m.group(2) for m in glossary.BLOCK_RE.finditer(text)]
    assert all(t["html"] in text for t in out["tables"])                    # the tables the page has


def test_the_check_shows_unsaved_rows_and_waits_for_a_build_for_a_new_glyph():
    pytest.importorskip("uharfbuzz")
    new = {"latin": "tc", "simplified": "推出", "pinyin": "tuīchū"}
    out = glossary.check(glossary.records(shipped(md_foo=new, md_bar={"latin": "zz"})), sections=with_rows(
        **{"1c": [g("md_foo", "Push the string out")], "99": [g("md_bar")]}))
    t = next(t for t in out["tables"] if t["id"] == "1c")
    assert "<td>tc</td>" in t["html"] and '<td class="meaning">Push the string out</td>' in t["html"]
    assert out["not_built"] == ["md_bar", "md_foo"] and out["typing"] == []   # not a false alarm: Build, then check
    assert out["problems"] == []


SQUARE = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100v100h-100z" fill="black"/></svg>'


def test_the_check_draws_a_new_glyph_in_from_its_drawing():
    pytest.importorskip("uharfbuzz")
    new = {"latin": "tc", "simplified": "推出", "pinyin": "tuīchū"}
    out = glossary.check(glossary.records(shipped(md_foo=new)), svg=lambda n: SQUARE if n == "md_foo" else None,
                         sections=with_rows(**{"1c": [g("md_foo")]}))
    assert out["ok"] and out["drawn"] == ["md_foo"] and out["not_built"] == [] and out["typing"] == []
    assert out["missing_chars"] == ["出", "推"]         # characters only a Build adds: its examples wait
    assert out["font_key"] and typing_preview.FONTS.by_key(out["font_key"]).font_bytes


def test_the_check_reports_what_a_release_would_stop_on():
    out = glossary.check(glossary.records(shipped(md_foo={"latin": "tc"})), sections=with_rows(**{"1c": [g("md_foo")]}))
    assert not out["ok"] and "needs an ASCII and a Chinese spelling" in out["error"]


def test_the_check_reports_a_new_glyph_with_no_row():
    out = glossary.check(glossary.records(shipped(md_foo={"latin": "tc", "simplified": "推出"})))
    assert out["ok"] and any(p.startswith("md_foo") and "no row in the glossary" in p for p in out["problems"])


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
        new = {"latin": "tc", "simplified": "推出", "pinyin": "tuīchū"}
        secs = glossary.load_sections()
        rows_ = {"1c": secs["1c"]["rows"] + [g("md_foo")]}
        assert post({"rows": shipped(), "glossary": {"9z": []}}, "tok-a")[1]["ok"] is False
        status, res = post({"rows": shipped(md_foo=new)}, "tok-a")       # no row for it yet: reported
        assert any(p.startswith("md_foo") for p in res["problems"])
        status, res = post({"rows": shipped(md_foo=new), "glossary": rows_}, "tok-a")
        assert status == 200 and res["ok"] and res["not_built"] == ["md_foo"]
        assert any("<td>tc</td>" in t["html"] for t in res["tables"])
        assert font(res["font_url"]) and font("/api/glossary/font")
        # the draft's drawing of it comes with the request: drawn in, typed, and the tables' font has it
        status, res = post({"rows": shipped(md_foo=new), "glossary": rows_, "svgs": {"md_foo": SQUARE}}, "tok-a")
        assert status == 200 and res["drawn"] == ["md_foo"] and res["not_built"] == [] and res["typing"] == []
        assert res["font_url"].startswith("/api/preview-fonts/") and font(res["font_url"])
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- 4: Uncategorized and 99: Hidden in Glossary

def test_a_hidden_section_has_no_table_and_leaves_its_glyphs_out_on_purpose():
    sec = {"2a": usage("2a", g("lg_gou"), template=("0{}5", "散{}五")), "99": {"title": "99: Hidden in Glossary", "kind": "hidden", "rows": [g("md_tc")]}}
    r = rows("lg_gou,,,k,,勾,,gōu", "md_tc,,,tc,,,,", "md_left,,,lf,,左,,zuǒ")
    probs = glossary.missing(r, sec)
    assert not any("md_tc" in p for p in probs)                  # hidden on purpose: no complaint
    assert any("md_left" in p and "99: Hidden in Glossary" in p for p in probs)   # in no section: reported, says how
    out = glossary.render(page("2a"), r, sec)                     # no marker for 99, and none needed
    assert "tc" not in out and glossary.section_rows("99", sec["99"], r) == []
    assert [sorted(ex) for _, ex in glossary.examples(out, r, sec)] == [sorted(["0k5", "散勾五"])]


def test_the_shipped_sections_include_uncategorized_and_hidden():
    secs = glossary.load_sections()
    assert {k: v for k, v in secs["4"].items() if k != "rows"} == {"title": "4: Uncategorized", "kind": "vertical"}
    assert {k: v for k, v in secs["99"].items() if k != "rows"} == {"title": "99: Hidden in Glossary", "kind": "hidden"}
    text = config.SITE_INDEX.read_text(encoding="utf-8")
    assert "<!-- glossary 4" in text and "<!-- glossary 99" not in text


def test_a_word_row_shows_its_meaning_and_its_glyphs_count_as_shown():
    r = rows("md_shao,,,shao,,少,,shǎo", "md_xi,,,xi,,息,,xī")
    sec = {"3e": vertical("3e", w("少息", "md_shao", "md_xi", meaning="a short rest"))}
    out = glossary.render(page("3e"), r, sec)
    assert "<td>:shaoxi</td>" in out and '<td class="meaning">a short rest</td>' in out
    assert glossary.missing(r, sec) == []                             # 少 and 息 are shown in the word


def test_the_shipped_glossary_has_its_words():
    secs = glossary.load_sections()
    words = [e.word for sid, sec in secs.items() for e in glossary.entries(sid, sec) if e.word]
    assert len(words) == 15 and "少息" in words
    assert not (config.INPUTS_DIR / "words.csv").exists()
