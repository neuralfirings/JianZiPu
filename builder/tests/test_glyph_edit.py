"""Tests for pinned character codes (glyph_ids.py) and renaming or deleting glyphs everywhere
(glyph_edit.py, PUT /api/glyphs/rename, PUT /api/glyph/<name>/rename, DELETE /api/glyph/<name>,
the names CSV). Works on a copy of inputs/ in a temporary folder; never touches the real files.

Run:  cd builder && python3 -m pytest tests/test_glyph_edit.py
"""

import json
import re
import shutil
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import config, data, glyph_edit, glyph_ids, webserver  # noqa: E402

SQUARE = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100v100h-100z" fill="black"/></svg>'
REAL_INPUTS = config.INPUTS_DIR


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    """A copy of inputs/ that config points at for the test."""
    d = tmp_path / "inputs"
    shutil.copytree(REAL_INPUTS, d)
    for attr, name in [("INPUTS_DIR", ""), ("DESIGN_JSON", "design.json"), ("COMPONENTS_CSV", "components.csv"),
                       ("EDGE_CASES_FEA", "edge_cases.fea"), ("COMPONENTS_DIR", "svg"),
                       ("GLYPH_IDS_JSON", "glyph_ids.json")]:
        monkeypatch.setattr(config, attr, d / name if name else d)
    data.cache_clear_all()
    yield d
    data.cache_clear_all()


def hashes():
    return (glyph_edit._hash(config.DESIGN_JSON.read_text(encoding="utf-8")),
            glyph_edit._hash(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig")))


def design():
    return json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))


def rows():
    return glyph_edit._rows(config.COMPONENTS_CSV.read_text(encoding="utf-8-sig"))


def add_conditions(g):
    """Spacing rows conditional on `g` (none in the real design: every glyph they name is locked),
    and a vertical-form link to it."""
    d = design()
    rel = next(r for l in d["layouts"] for r in l["relationships"] if isinstance(r.get("gap"), list))
    rel["gap"][:0] = [{"when_elem": [g], "value": 11}, {"when_base": [g, "md_ming"], "value": 12}]
    config.DESIGN_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rs = rows()
    next(x for x in rs if x["glyph_name"] == "md_zhong")["vert_variant"] = g
    config.COMPONENTS_CSV.write_text(glyph_edit._csv(rs), encoding="utf-8")
    data.cache_clear_all()


def gap_glyphs(d):
    for l in d["layouts"]:
        for r in l["relationships"]:
            if isinstance(r.get("gap"), list):
                for e in r["gap"]:
                    yield from (e.get("when_base") or []) + (e.get("when_elem") or [])


# ---------------------------------------------------------------- pinned codes

def test_every_glyph_in_inputs_has_a_pinned_code():
    ids = glyph_ids.load()
    missing = sorted(p.stem for p in (REAL_INPUTS / "svg").glob("*.svg") if p.stem not in ids["codes"])
    assert not missing, f"no code in inputs/glyph_ids.json for {missing} (save them from the Builder)"
    codes = list(ids["codes"].values()) + list(ids["retired"])
    assert len(codes) == len(set(codes)), "a code is used twice in inputs/glyph_ids.json"


def test_unpinned_glyphs_get_the_next_free_code_in_file_order():
    d = {"codes": {"b": "E2F5", "a": "E2F7"}, "retired": {"E2FA": "old"}, "renamed": []}
    m = glyph_ids.code_map(["a", "b", "md_1", "md_1.1"], d)
    assert m["a"] == 0xE2F7 and m["b"] == 0xE2F5
    assert m["md_1.1"] == 0xE2FB and m["md_1"] == 0xE2FC          # md_1.1.svg sorts before md_1.svg


def test_a_code_used_twice_is_an_error():
    with pytest.raises(ValueError):
        glyph_ids.code_map(["a"], {"codes": {"a": "E2F5", "b": "E2F5"}, "retired": {}, "renamed": []})


def test_a_new_glyph_is_pinned_and_a_deleted_one_retired(inputs):
    before = glyph_ids.load()
    top = max(int(c, 16) for c in before["codes"].values())
    webserver.write_svg("zz_new", SQUARE, overwrite=False)
    assert glyph_ids.load()["codes"]["zz_new"] == f"{top + 1:04X}"
    glyph_ids.retire("zz_new")
    after = glyph_ids.load()
    assert "zz_new" not in after["codes"] and after["retired"][f"{top + 1:04X}"] == "zz_new"
    glyph_ids.pin("zz_other")
    assert glyph_ids.load()["codes"]["zz_other"] == f"{top + 2:04X}"   # the retired code isn't handed out again


# ---------------------------------------------------------------- what can't be deleted

def test_names_the_build_spells_out_cant_be_deleted_but_can_be_renamed(inputs):
    locked = glyph_edit.hardcoded()
    assert {"md_7.6", "md_13", "lg_gou", "mod_chuo", "md_wai"} <= locked
    assert "mod_fanyin" not in locked and "md_ming" not in locked
    u = glyph_edit.uses("md_7.6")["locked"]
    assert u["rename"] is None and "can't be deleted" in u["delete"]
    assert glyph_edit.uses("mod_fanyin")["locked"] == {"rename": None, "delete": None}


def test_one_glyph_is_locked_exactly_when_it_is_locked_among_all(inputs):
    """delete_lock() checks one name at a time; it agrees with renaming every glyph at once."""
    every = glyph_edit.hardcoded()
    for n in ["mod_fanyin", "md_ming", "md_7.6", "lg_gou", "xl_dacuo", "md_jiu2", "md_lun", "md_yan"]:
        assert (n in glyph_edit.hardcoded({n})) == (n in every), n


# ---------------------------------------------------------------- rename

def test_rename_changes_every_place_and_keeps_the_code(inputs):
    code = glyph_ids.load()["codes"]["mod_fanyin"]
    r = glyph_edit.rename("mod_fanyin", "mod_fy", *hashes())
    assert r["ok"] and (r["design_hash"], r["csv_hash"]) == hashes()
    assert not (inputs / "svg/mod_fanyin.svg").exists() and (inputs / "svg/mod_fy.svg").exists()
    assert "mod_fy" in design()["areas"]["fy"]["glyphs"] and "mod_fanyin" not in json.dumps(design())
    row = next(x for x in rows() if x["glyph_name"] == "mod_fy")
    assert row["latin"] == "fanyin"
    ids = glyph_ids.load()
    assert ids["codes"]["mod_fy"] == code and "mod_fanyin" not in ids["codes"]
    assert ids["renamed"][-1]["names"] == {"mod_fanyin": "mod_fy"}
    assert glyph_edit.translate("mod_fanyin") == "mod_fy"
    assert glyph_edit.uses("mod_fy")["code"] == code


def test_rename_carries_spacing_conditions_and_vertical_links(inputs):
    g = "mod_fanyin"
    add_conditions(g)
    n = sum(1 for x in gap_glyphs(design()) if x == g)
    assert n == 2
    partners = [x["glyph_name"] for x in rows() if x["vert_variant"] == g]
    glyph_edit.rename(g, "zz_renamed", *hashes())
    assert sum(1 for x in gap_glyphs(design()) if x == "zz_renamed") == n
    assert g not in set(gap_glyphs(design()))
    assert [x["glyph_name"] for x in rows() if x["vert_variant"] == "zz_renamed"] == partners


def test_rename_refusals(inputs):
    with pytest.raises(glyph_edit.GlyphEditError, match="control glyph"):
        glyph_edit.rename("blank_bar", "bar")
    with pytest.raises(glyph_edit.GlyphEditError, match="already a glyph"):
        glyph_edit.rename("mod_fanyin", "md_ming")
    with pytest.raises(glyph_edit.GlyphEditError, match="letters, digits"):
        glyph_edit.rename("mod_fanyin", "bad name")
    with pytest.raises(glyph_edit.GlyphEditError, match="no glyph"):
        glyph_edit.rename("zz_nothing", "zz_x")
    with pytest.raises(glyph_edit.GlyphEditConflict):
        glyph_edit.rename("mod_fanyin", "mod_fy", "stale", None)
    assert (inputs / "svg/mod_fanyin.svg").exists()


def test_an_old_name_is_not_used_again_except_to_rename_back(inputs):
    glyph_edit.rename("mod_fanyin", "mod_fy")
    with pytest.raises(ValueError, match="before a rename"):
        webserver.write_svg("mod_fanyin", SQUARE, overwrite=False)
    glyph_edit.rename("md_ming", "md_ming2")
    with pytest.raises(glyph_edit.GlyphEditError, match="before a rename"):
        glyph_edit.rename("md_ming2", "mod_fanyin")                  # another glyph's old name
    glyph_edit.rename("mod_fy", "mod_fanyin")                         # back again is fine
    assert glyph_edit.translate("mod_fanyin") == "mod_fanyin" and glyph_edit.translate("mod_fy") == "mod_fanyin"


# ---------------------------------------------------------------- many at once

SCHEME = re.compile(r"^md_(\d+)(\..+)?$")


def scheme():
    """md_7 -> hui_7_md, md_7.6 -> hui_7.6_md: a new naming scheme for every hui glyph."""
    return {g: f"hui_{m.group(1)}{m.group(2) or ''}_md" for g in sorted(glyph_edit._svg_names()) if (m := SCHEME.match(g))}


def test_a_whole_naming_scheme_renames_glyphs_the_code_spells_out(inputs):
    names = scheme()
    assert len(names) > 100 and names["md_7.6"] == "hui_7.6_md" and names["md_13"] == "hui_13_md"
    codes = glyph_ids.load()["codes"]
    check = glyph_edit.check_renames(names)
    assert check["ok"], check["problems"][:3]
    glyph_edit.rename_many(names, *hashes())
    assert (inputs / "svg/hui_7.6_md.svg").exists() and not (inputs / "svg/md_7.6.svg").exists()
    after = glyph_ids.load()
    assert after["codes"]["hui_7.6_md"] == codes["md_7.6"] and len(after["renamed"][-1]["names"]) == len(names)
    # the feature file the code writes comes out in the new names
    from jzpbuild import features
    text = "\n".join(features.gen_gsub())
    tokens = set(glyph_ids.TOKEN.findall(re.sub(r"#.*", "", text)))
    assert "hui_7.6_md" in tokens and "hui_13_md" in tokens
    assert not (set(names) & tokens)
    assert glyph_edit.hardcoded({"hui_7.6_md"}) == {"hui_7.6_md"}      # and still can't be deleted


def test_a_swap_keeps_each_glyph_with_its_drawing_code_and_spellings(inputs):
    before = {g: (inputs / f"svg/{g}.svg").read_text() for g in ("md_ming", "md_zhong")}
    codes = glyph_ids.load()["codes"]
    latin = {x["glyph_name"]: x["latin"] for x in rows()}
    glyph_edit.rename_many({"md_ming": "md_zhong", "md_zhong": "md_ming"}, *hashes())
    assert (inputs / "svg/md_zhong.svg").read_text() == before["md_ming"]
    assert glyph_ids.load()["codes"]["md_zhong"] == codes["md_ming"]
    assert {x["glyph_name"]: x["latin"] for x in rows()}["md_zhong"] == latin["md_ming"]
    assert glyph_ids.current("md_ming") == "md_zhong" and glyph_ids.current("md_zhong") == "md_ming"


def test_batch_problems_are_reported_per_row(inputs):
    r = glyph_edit.check_renames({"md_ming": "x1", "md_zhong": "x1", "zz_none": "y", "mod_fanyin": "md_shang", "blank": "b", "md_7": "bad name"})
    by = {p["from"]: p["problem"] for p in r["pairs"]}
    assert not r["ok"]
    assert "new name of md_ming and md_zhong" in by["md_ming"] and "no glyph" in by["zz_none"]
    assert "already a glyph" in by["mod_fanyin"] and "control glyph" in by["blank"] and "letters, digits" in by["md_7"]
    assert glyph_edit.check_renames({"md_ming": "md_ming", "md_zhong": ""}) == {"ok": True, "pairs": [], "problems": []}


def test_the_names_csv_round_trips(inputs):
    text = glyph_edit.names_csv()
    assert text.startswith("\ufeff" + ",".join(glyph_edit.NAMES_CSV_FIELDS))
    lines = text.splitlines()
    assert len(lines) == len(glyph_edit._svg_names()) + 1
    assert any(l.startswith("mod_fanyin,,fy,fanyin,泛音,泛音,") and l.endswith(",U+E3C8") for l in lines)
    filled = text.replace("mod_fanyin,,", "mod_fanyin,mod_fy,")
    assert {k: v for k, v in glyph_edit.renames_from_csv(filled).items() if v} == {"mod_fanyin": "mod_fy"}
    with pytest.raises(glyph_edit.GlyphEditError, match="glyph_name and new_name"):
        glyph_edit.renames_from_csv("name,new\na,b\n")


# ---------------------------------------------------------------- delete

def test_delete_removes_the_glyph_and_what_names_it(inputs):
    g = "mod_fanyin"
    add_conditions(g)
    u = glyph_edit.uses(g)
    assert u["spacing_rows"] == 2 and u["spacing_rows_only"] == 1 and u["vertical_of"] == ["md_zhong"]
    code = u["code"]
    r = glyph_edit.delete(g, *hashes())
    assert r["ok"] and r["spacing_rows_dropped"] == 1
    assert any(e.get("when_base") == ["md_ming"] for e in
               next(r for l in design()["layouts"] for r in l["relationships"] if isinstance(r.get("gap"), list))["gap"])
    assert not (inputs / f"svg/{g}.svg").exists()
    after = design()
    assert g not in json.dumps(after["areas"]) and g not in set(gap_glyphs(after))
    for l in after["layouts"]:
        for rel in l["relationships"]:
            if isinstance(rel.get("gap"), list):
                assert rel["gap"] and all(e.get("when_base") != [] and e.get("when_elem") != [] for e in rel["gap"])
    assert all(x["glyph_name"] != g and x["vert_variant"] != g for x in rows())
    ids = glyph_ids.load()
    assert g not in ids["codes"] and ids["retired"][code] == g


def test_delete_refuses_locked_glyphs(inputs):
    with pytest.raises(glyph_edit.GlyphEditError):
        glyph_edit.delete("lg_gou")
    assert (inputs / "svg/lg_gou.svg").exists()


# ---------------------------------------------------------------- HTTP

@pytest.fixture
def server(inputs):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), webserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(base, method, path, body=None):
    raw = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=raw, method=method,
                                 headers={"Content-Type": "application/json"} if raw else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_http_uses_rename_and_delete(server, inputs):
    status, r = call(server, "GET", "/api/glyph/mod_fanyin/uses")
    assert status == 200 and r["areas"] == ["fy"] and r["locked"] == {"rename": None, "delete": None}
    dh, ch = hashes()
    status, r = call(server, "PUT", "/api/glyph/mod_fanyin/rename", {"to": "mod_fy", "design_hash": "stale", "csv_hash": ch})
    assert status == 409 and r["conflict"]
    status, r = call(server, "PUT", "/api/glyph/mod_fanyin/rename", {"to": "mod_fy", "design_hash": dh, "csv_hash": ch})
    assert status == 200 and r["ok"] and r["name"] == "mod_fy"
    status, r = call(server, "PUT", "/api/glyph/mod_fy/rename", {"to": "md_ming"})
    assert status == 400 and "already a glyph" in r["error"]
    status, r = call(server, "GET", "/api/base")
    assert r["renamed"][-1]["names"] == {"mod_fanyin": "mod_fy"}
    dh, ch = hashes()
    status, r = call(server, "DELETE", f"/api/glyph/mod_fy?design_hash={dh}&csv_hash={ch}")
    assert status == 200 and r["ok"] and not (inputs / "svg/mod_fy.svg").exists()


def test_http_names_csv_check_and_rename_many(server, inputs):
    req = urllib.request.urlopen(server + "/api/glyphs/names.csv", timeout=10)
    assert req.headers["Content-Disposition"] == 'attachment; filename="glyph-names.csv"'
    text = req.read().decode("utf-8")
    filled = text.replace("mod_fanyin,,", "mod_fanyin,mod_fy,").replace("md_ming,,", "md_ming,md_zhong,")
    status, r = call(server, "POST", "/api/glyphs/rename/check", {"csv": filled})
    assert status == 200 and not r["ok"] and any("already a glyph" in (p["problem"] or "") for p in r["pairs"])
    status, r = call(server, "POST", "/api/glyphs/rename/check", {"csv": "x\n"})
    assert status == 200 and not r["ok"] and "glyph_name and new_name" in r["error"]
    dh, ch = hashes()
    status, r = call(server, "PUT", "/api/glyphs/rename", {"names": {"mod_fanyin": "mod_fy", "md_ming": "md_ming2"}, "design_hash": dh, "csv_hash": ch})
    assert status == 200 and r["renamed"] == {"mod_fanyin": "mod_fy", "md_ming": "md_ming2"}


def test_hosted_mode_refuses_rename_and_delete(server, monkeypatch):
    monkeypatch.setattr(webserver, "SETTINGS", webserver.hosted.Settings(hosted=True))
    status, r = call(server, "PUT", "/api/glyph/mod_fanyin/rename", {"to": "mod_fy"})
    assert status == 403
    status, r = call(server, "DELETE", "/api/glyph/mod_fanyin")
    assert status == 403
