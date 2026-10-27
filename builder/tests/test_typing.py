"""Tests for spellings (components.csv) as the Builder edits them: the clash and format checks
that pause Save, the generated digit lookup, the hash-checked CSV write, and the in-memory
preview font (GSUB from unsaved rows compiled into a real build).

The preview tests build the font once per session (about 15 s).

Run:  cd builder && python3 -m pytest tests/test_typing.py
"""

import csv
import io
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import config, webserver, features, typing_preview as tp  # noqa: E402
from jzpbuild.data import GlyphRow  # noqa: E402

DESIGN = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))


def csv_records():
    return list(csv.DictReader(io.StringIO(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig"))))


def row(name, **kw):
    return GlyphRow(glyph_name=name, **kw)


# ---------------------------------------------------------------- checks

def test_shipped_spellings_have_no_issues():
    assert tp.issues(tp.rows_from(csv_records(), DESIGN))["errors"] == []


def test_csv_has_only_the_kept_columns():
    assert list(csv_records()[0].keys()) == list(tp.ROW_FIELDS)


def test_a_clash_names_the_spelling_and_both_glyphs():
    errs = tp.issues([row("lg_gou", latin="k"), row("lg_tuo", latin="k")])["errors"]
    assert len(errs) == 1
    e = errs[0]
    assert e["kind"] == "clash" and e["value"] == "k" and e["glyphs"] == ["lg_gou", "lg_tuo"]
    assert "k" in e["message"] and "lg_gou" in e["message"] and "lg_tuo" in e["message"]


def test_latin_and_short_form_share_one_namespace():
    errs = tp.issues([row("lg_banlun", latin="banlun", latin_alt="bl"), row("md_x", latin="bl")])["errors"]
    assert [e["value"] for e in errs] == ["bl"]


def test_a_vertical_pair_may_share_a_spelling():
    rows = [row("lg_lun", latin="lun", vert_variant="md_lun"), row("md_lun", latin="lun")]
    assert tp.issues(rows)["errors"] == []


def test_different_areas_alone_do_not_excuse_a_shared_spelling():
    rows = [row("lg_yan", latin="V", areas={"right"}), row("md_yan", latin="V", areas={"char"})]
    assert [e["kind"] for e in tp.issues(rows)["errors"]] == ["clash"]


@pytest.mark.parametrize("field,value,needle", [
    ("latin", "4xi", "start with a letter"),
    ("latin", "ban-lun", "only letters"),
    ("latin_alt", "0.5", "start with a letter"),
    ("simplified", "abc", "Chinese characters only"),
    ("simplified", "点", "marks a position"),
])
def test_malformed_spellings_are_errors(field, value, needle):
    errs = tp.issues([row("md_x", **{field: value})])["errors"]
    assert len(errs) == 1 and needle in errs[0]["message"]


def test_vertical_form_must_exist():
    errs = tp.issues([row("lg_lun", vert_variant="md_nope")])["errors"]
    assert errs and "md_nope" in errs[0]["message"]


def test_vertical_forms_store_only_the_link():
    """md_lun & co. no longer repeat their partner's spellings (owner decision 2026-10-17)."""
    recs = {r["glyph_name"]: r for r in csv_records()}
    for r in recs.values():
        v = r["vert_variant"]
        if v and v in recs:
            for f in ("latin", "latin_alt", "simplified", "traditional"):
                assert not (recs[v][f] and recs[v][f] == r[f]), f"{v}.{f} repeats {r['glyph_name']}'s"


# ---------------------------------------------------------------- generator

def test_digit_spellings_get_their_own_lookup_defined_before_the_numbers():
    lines = features.gen_gsub()
    text = "\n".join(lines)
    assert "lookup l2j_digit_liga {" in text
    for k in ("z h i four by md_zhi4", "x i four by md_xi4", "f u four by md_fu"):
        assert k in text
    # lookups run in definition order: it must be defined before the ASCII number lookups
    assert text.index("lookup l2j_digit_liga {") < text.index("lookup s2j_liga {")
    assert "lookup l2j_digit_liga;" in text


def test_no_digit_lookup_without_digit_spellings():
    rows = [row("lg_gou", latin="k", areas={"right"})]
    assert features.gen_l2j_digit_liga(rows) == []
    assert "l2j_digit_liga" not in "\n".join(features.gen_liga_feature(digit_lookup=False))


def test_vertical_only_glyphs_are_the_ones_no_other_word_type_places():
    vert = features.vertical_only_glyphs()
    assert {"md_shang", "md_xia", "md_xi4", "md_san2", "md_lun"} <= set(vert)
    # in the char area too, but also a hui, finger, string or right-hand glyph
    assert not {"md_3", "md_13", "md_ming", "md_san", "lg_lun", "blank_colon"} & set(vert)


def test_the_auto_colon_runs_after_the_typed_colon_and_before_the_vertical_forms():
    text = "\n".join(features.gen_gsub())
    assert "@area_vert_only = [ " in text and "lookup auto_colon_insert {" in text
    feature = text[text.index("feature liga {"):]
    assert feature.index("sub colon by blank_colon;") < feature.index("lookup auto_colon {") \
        < feature.index("@area_to_md_for_vert_from'")


TOY_DESIGN = {
    "version": 2,
    "areas": {
        "colon": {"size": [1000, 1000], "glyphs": ["blank_colon"], "advance": 1000},
        "left": {"size": [350, 350], "glyphs": ["md_ming"]},
        "hui": {"size": [350, 350], "glyphs": ["md_3"]},
        "right": {"size": [660, 660], "glyphs": ["lg_lun"]},
        "char": {"size": [350, 350], "glyphs": ["md_3", "md_ming", "md_shang"]},
    },
    "layouts": [
        {"name": "standard", "slots": [{"name": n, "optional": True, "alternatives": [[n]]}
                                       for n in ("left", "hui", "right")]},
        {"name": "vertical", "slots": [{"name": "colon", "alternatives": [["colon"]]},
                                       {"name": "row", "repeat": [1, 4], "alternatives": [["char"], ["left", "hui"]]}]},
    ],
}


def test_a_word_only_a_vertical_layout_places_gets_its_colon():
    from fontTools.fontBuilder import FontBuilder
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    import uharfbuzz as hb
    from jzpbuild.positioning import schema

    keys = {"S": "md_shang", "3": "md_3", "M": "md_ming", "L": "lg_lun", ":": "colon", " ": "space"}
    rows = [row("md_shang", areas={"char"}), row("md_3", areas={"hui", "char"}),
            row("md_ming", areas={"left", "char"}), row("lg_lun", areas={"right"})]
    token = features._DESIGN_OVERRIDE.set(schema.parse_design(TOY_DESIGN))
    try:
        assert features.vertical_only_glyphs() == ["md_shang"]
        fea = "\n".join([
            f"@area_wild = [ {' '.join(features.all_component_glyphs(rows))} ];",
            f"@area_vert_only = [ {' '.join(features.vertical_only_glyphs())} ];",
            f"@auto_colon_word = [ {' '.join(features.word_start_glyphs(rows))} ];",
            *features.gen_auto_colon_insert(rows),
            "feature liga {", "  sub colon by blank_colon;", *features.gen_auto_colon(), "} liga;",
        ])
    finally:
        features._DESIGN_OVERRIDE.reset(token)

    glyphs = [".notdef", "blank", "blank_bar", "blank_colon", *keys.values()]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyphs)
    fb.setupCharacterMap({ord(k): g for k, g in keys.items()})
    fb.setupGlyf({g: TTGlyphPen(None).glyph() for g in glyphs})
    fb.setupHorizontalMetrics({g: (1000, 0) for g in glyphs})
    fb.setupHorizontalHeader()
    fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, fea)
    out = io.BytesIO()
    fb.save(out)
    font = hb.Font(hb.Face(out.getvalue()))

    def typed(text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {"liga": True})
        return " ".join(font.glyph_to_string(i.codepoint) for i in buf.glyph_infos)

    assert typed("S33") == typed(":S33") == "blank_colon md_shang md_3 md_3"
    assert typed("M3S") == "blank_colon md_ming md_3 md_shang"             # found further on in the word
    assert typed("L3 S") == "lg_lun md_3 space blank_colon md_shang"        # one word at a time
    assert typed("M3") == "md_ming md_3"                                    # a standard word stays one
    assert typed("M3:S") == "md_ming md_3 blank_colon md_shang"             # a typed colon ends the look
    assert typed("S:M3") == "blank_colon md_shang blank_colon md_ming md_3"


# ---------------------------------------------------------------- CSV write

@pytest.fixture
def csv_copy(tmp_path, monkeypatch):
    p = tmp_path / "components.csv"
    p.write_text(config.COMPONENTS_CSV.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(config, "COMPONENTS_CSV", p)
    yield p
    webserver.data.cache_clear_all()


def test_write_keeps_order_drops_empty_rows_and_returns_the_new_hash(csv_copy):
    payload = webserver.glyphs_payload()
    rows = [{"glyph_name": r["glyph"], **{k: r[k] for k in tp.ROW_FIELDS if k != "glyph_name"}}
            for r in payload["glyphs"]]
    for r in rows:
        if r["glyph_name"] == "lg_tiao":
            r["latin"] = "t"
    res = webserver.write_glyph_rows(list(reversed(rows)), payload["hash"])
    text = csv_copy.read_text(encoding="utf-8")
    assert res["ok"] and res["hash"] == webserver._hash(text)
    names = [r["glyph_name"] for r in csv.DictReader(io.StringIO(text))]
    assert names[:3] == payload["order"][:3]                     # file order, not request order
    assert "md_1.1" not in names                                  # decimals have nothing to say
    assert "lg_tiao,,,t," in text


def test_write_refuses_a_stale_hash(csv_copy):
    with pytest.raises(webserver.CsvConflict):
        webserver.write_glyph_rows([], "0000000000000000")


def test_write_refuses_a_clash_and_leaves_the_file(csv_copy):
    before = csv_copy.read_text(encoding="utf-8")
    rows = [{"glyph_name": "lg_gou", "latin": "k"}, {"glyph_name": "lg_tuo", "latin": "k"}]
    with pytest.raises(webserver.SpellingErrors) as e:
        webserver.write_glyph_rows(rows)
    assert e.value.errors[0]["value"] == "k"
    assert csv_copy.read_text(encoding="utf-8") == before


# ---------------------------------------------------------------- preview font

@pytest.fixture(scope="session")
def built_font(tmp_path_factory):
    import subprocess
    if not config.SOURCE_FONT.exists():
        pytest.skip("needs the base font (src_font/TW-Kai-98.ttf), which isn't in the repo")
    out = tmp_path_factory.mktemp("font") / "JianZiPu.ttf"
    subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", ""],
                   cwd=Path(__file__).resolve().parent.parent, check=True, capture_output=True)
    return out


def test_every_shipped_spelling_round_trips(built_font):
    rows = tp.rows_from(csv_records(), DESIGN)
    p = tp.FONTS.get(built_font, rows, DESIGN)
    assert tp.roundtrip(p, rows) == []
    assert p.not_built == [] and p.missing_chars == {}


@pytest.mark.parametrize("word,glyphs", [
    ("xi4", ["blank_colon", "md_xi4"]), ("fu4", ["blank_colon", "md_fu"]), ("zhi4", ["blank_colon", "md_zhi4"]),
    ("s7xi4", ["blank_colon", "md_ming", "md_7", "md_xi4"]), (":lun", ["blank_colon", "md_lun"]),
    ("lun", ["lg_lun"]), ("san", ["blank_colon", "md_san2"]), ("就", ["md_jiu"]),
    ("shang34", ["blank_colon", "md_shang", "md_3", "md_4"]), (":shang34", ["blank_colon", "md_shang", "md_3", "md_4"]),
    ("lun3shang", ["blank_colon", "md_lun", "md_3", "md_shang"]), ("lun3", ["lg_lun", "md_3"]),
])
def test_built_font_types_these(built_font, word, glyphs):
    rows = tp.rows_from(csv_records(), DESIGN)
    assert tp.shape(tp.FONTS.get(built_font, rows, DESIGN), [word])[0]["glyphs"] == glyphs


def test_unsaved_spelling_previews_without_a_build(built_font):
    recs = csv_records()
    for r in recs:
        if r["glyph_name"] == "lg_tiao":
            r["latin"] = "t"
    p = tp.FONTS.get(built_font, tp.rows_from(recs, DESIGN), DESIGN)
    a, b = tp.shape(p, ["s7t5", "s7u5"])
    assert a["glyphs"] == ["md_ming", "md_7", "lg_tiao", "md_5"]
    assert b["glyphs"][2] == "u" and b["texts"][2] == "u"       # the old spelling is now a stray letter


def test_a_character_the_font_lacks_is_reported_not_compiled(built_font):
    recs = csv_records()
    for r in recs:
        if r["glyph_name"] == "md_tang":
            r["simplified"] = "往"
    p = tp.FONTS.get(built_font, tp.rows_from(recs, DESIGN), DESIGN)
    assert p.missing_chars == {"md_tang": ["往"]}
    s = tp.shape(p, ["往"])[0]
    assert s["glyphs"] == [".notdef"] and s["texts"] == ["往"]


def test_a_glyph_missing_from_the_build_is_left_out(built_font):
    design = json.loads(json.dumps(DESIGN))
    design["areas"]["char"]["glyphs"].append("md_wang")
    recs = csv_records() + [{"glyph_name": "md_wang", "latin": "wang"}]
    p = tp.FONTS.get(built_font, tp.rows_from(recs, design), design)
    assert p.not_built == ["md_wang"]


# ---------------------------------------------------------------- HTTP

@pytest.fixture
def server(built_font, monkeypatch):
    monkeypatch.setattr(webserver, "_preview_base_font", lambda *_: built_font)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), webserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def post(base, path, body):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_http_preview_words_roundtrip_and_changes(server):
    saved = csv_records()
    edited = [dict(r) for r in saved]
    for r in edited:
        if r["glyph_name"] == "lg_tiao":
            r["latin"] = "t"
    status, res = post(server, "/api/typing/preview", {
        "rows": edited, "words": ["s7t5"], "base_rows": saved, "compare_words": ["s7u5", "s7k5"]})
    assert status == 200 and res["ok"] and res["errors"] == [] and res["roundtrip"] == []
    w = res["words"][0]
    assert w["glyphs"] == ["md_ming", "md_7", "lg_tiao", "md_5"] and w["texts"] == ["s", "7", "t", "5"]
    assert w["pieces"][0]["layout"]                                  # positioned like /api/words
    assert [c["word"] for c in res["changed"]] == ["s7u5"]


def test_http_preview_reports_a_clash(server):
    edited = csv_records()
    for r in edited:
        if r["glyph_name"] == "lg_tuo":
            r["latin"] = "k"
    status, res = post(server, "/api/typing/preview", {"rows": edited})
    assert status == 200 and [e["value"] for e in res["errors"]] == ["k"]
