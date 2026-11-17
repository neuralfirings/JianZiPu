"""Tests for the web server's glyph-file endpoints (PUT /api/svg/<name>, POST /api/svg/check)
and the catalog they feed. Uses a temporary svg/ folder; never touches inputs/.

Run:  cd builder && python3 -m pytest tests/test_webserver.py
"""

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import config, webserver  # noqa: E402

SQUARE = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100v100h-100z" fill="black"/></svg>'
BAD = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100"/></svg>'
# a glossary.json frozen for the save tests (site/glossary.json's titles and sections change with releases)
GLOSSARY_FIXTURE = Path(__file__).resolve().parent / "data" / "glossary.json"


@pytest.fixture
def svg_dir(tmp_path, monkeypatch):
    d = tmp_path / "svg"
    d.mkdir()
    monkeypatch.setattr(config, "COMPONENTS_DIR", d)
    return d


# ---------------------------------------------------------------- names

@pytest.mark.parametrize("name", ["md_9", "lg_gou", "md_7.5", "a-b", "X1"])
def test_valid_names(svg_dir, name):
    assert webserver.svg_path_for(name) == svg_dir / f"{name}.svg"


@pytest.mark.parametrize("name", ["", "../evil", "a/b", "a b", ".hidden", "md_9.", "x" * 65, "名"])
def test_invalid_names_are_refused(svg_dir, name):
    with pytest.raises(ValueError):
        webserver.svg_path_for(name)


# ---------------------------------------------------------------- write_svg

def test_write_new_file(svg_dir):
    r = webserver.write_svg("zz_new", SQUARE, overwrite=False)
    assert r["ok"] and r["existed"] is False and r["contours"] == 1
    text = (svg_dir / "zz_new.svg").read_text(encoding="utf-8")
    assert text == SQUARE + "\n"
    assert r["hash"] == webserver._hash(text)


def test_existing_file_needs_a_hash_or_overwrite(svg_dir):
    webserver.write_svg("g", SQUARE, overwrite=False)
    with pytest.raises(FileExistsError):
        webserver.write_svg("g", SQUARE, overwrite=False)
    r = webserver.write_svg("g", SQUARE, overwrite=True)
    assert r["ok"] and r["existed"] is True


def test_matching_hash_allows_the_write_and_a_stale_one_conflicts(svg_dir):
    first = webserver.write_svg("g", SQUARE, overwrite=False)
    changed = SQUARE.replace("h100v100", "h50v50")
    r = webserver.write_svg("g", changed, overwrite=False, base_hash=first["hash"])
    assert r["ok"] and r["hash"] != first["hash"]
    with pytest.raises(webserver.SvgConflict):
        webserver.write_svg("g", SQUARE, overwrite=False, base_hash=first["hash"])   # stale
    assert "h50v50" in (svg_dir / "g.svg").read_text()                               # untouched


def test_invalid_svg_is_not_written(svg_dir):
    with pytest.raises(ValueError):
        webserver.write_svg("g", BAD, overwrite=False)
    assert not (svg_dir / "g.svg").exists()


def test_catalog_sees_the_new_file(svg_dir):
    webserver.write_svg("zz_cat", SQUARE, overwrite=False)
    rows = {r["glyph"]: r for r in webserver.glyphs_payload()["glyphs"]}
    assert rows["zz_cat"]["svg"] is True and rows["zz_cat"]["areas"] == []


# ---------------------------------------------------------------- over HTTP

@pytest.fixture
def server(svg_dir):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), webserver.Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_http_check(server):
    status, r = call(server, "POST", "/api/svg/check", {"svg": SQUARE})
    assert status == 200 and r["ok"] and r["points"] == 4 and r["d"]
    status, r = call(server, "POST", "/api/svg/check", {"svg": BAD})
    assert status == 200 and r["ok"] is False and "viewBox" in r["error"]


def test_http_put_new_then_conflict_then_overwrite(server, svg_dir):
    status, r = call(server, "PUT", "/api/svg/zz_http", {"svg": SQUARE})
    assert status == 200 and r["ok"] and r["file"] == "inputs/svg/zz_http.svg"
    h = r["hash"]
    # someone else edits the file
    (svg_dir / "zz_http.svg").write_text(SQUARE.replace("h100v100", "h60v60"), encoding="utf-8")
    status, r = call(server, "PUT", "/api/svg/zz_http", {"svg": SQUARE, "base_hash": h})
    assert status == 409 and r["conflict"] is True and "h60v60" in r["disk"]
    status, r = call(server, "PUT", "/api/svg/zz_http", {"svg": SQUARE})
    assert status == 409 and r["exists"] is True
    status, r = call(server, "PUT", "/api/svg/zz_http", {"svg": SQUARE, "overwrite": True})
    assert status == 200 and r["ok"]
    assert (svg_dir / "zz_http.svg").read_text() == SQUARE + "\n"


def test_http_put_bad_name_and_bad_svg(server):
    status, r = call(server, "PUT", "/api/svg/..%2Fevil", {"svg": SQUARE})
    assert status in (400, 404) and r["ok"] is False
    status, r = call(server, "PUT", "/api/svg/zz_bad", {"svg": BAD})
    assert status == 400 and r["ok"] is False


def test_http_svgs_lists_the_folder(server, svg_dir):
    (svg_dir / "one.svg").write_text(SQUARE, encoding="utf-8")
    status, r = call(server, "GET", "/api/svgs")
    assert status == 200 and r == {"one": SQUARE}


def test_http_delete(server, svg_dir):
    (svg_dir / "zz_del.svg").write_text(SQUARE, encoding="utf-8")
    req = urllib.request.Request(server + "/api/svg/zz_del", method="DELETE")
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200 and json.loads(resp.read())["ok"]
    assert not (svg_dir / "zz_del.svg").exists()
    req = urllib.request.Request(server + "/api/svg/zz_del", method="DELETE")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=10)
    assert e.value.code == 404


# ---------------------------------------------------------------- path traversal

TRAVERSALS = ["/../../builder/.env.example", "/" + "../" * 30 + "etc/passwd", "/%2e%2e/%2e%2e/builder/pyproject.toml",
              "/assets/../../../builder/pyproject.toml", "/..%2f..%2fbuilder/pyproject.toml", "/inputs/../jzpbuild/config.py"]


@pytest.fixture
def app_build(tmp_path, monkeypatch):
    d = tmp_path / "appbuild"
    d.mkdir()
    (d / "index.html").write_text("<!doctype html><title>app</title>", encoding="utf-8")
    monkeypatch.setattr(webserver, "APP_BUILD_DIR", d)
    return d


def raw_get(base, path):
    """GET with the path sent exactly as written (urllib would leave it alone too, but be sure)."""
    import http.client
    host, port = base.removeprefix("http://").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.putrequest("GET", path, skip_host=True)
    c.putheader("Host", f"{host}:{port}")
    c.endheaders()
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, body


@pytest.mark.parametrize("path", TRAVERSALS)
def test_no_path_traversal(server, app_build, path):
    status, body = raw_get(server, path)
    assert status == 404 or body.startswith(b"<!doctype html><title>app")
    assert b"root:" not in body and b"[project]" not in body and b"SUPABASE" not in body and b"SOURCE_FONT" not in body


def test_missing_files_are_404_but_screens_get_the_app(server, app_build):
    (app_build / "llms.txt").write_text("# JianZiPu 减字谱", encoding="utf-8")
    with urllib.request.urlopen(server + "/llms.txt", timeout=10) as r:
        assert r.headers["Content-Type"] == "text/plain; charset=utf-8"
        assert r.read().decode("utf-8") == "# JianZiPu 减字谱"
    for p in ("/robots.txt", "/help.md", "/sitemap.xml", "/nope.png"):
        assert raw_get(server, p)[0] == 404, p
    for p in ("/", "/help", "/glyphs/md_1.1/edit", "/layouts"):
        status, body = raw_get(server, p)
        assert status == 200 and body.startswith(b"<!doctype html><title>app"), p


@pytest.fixture
def site_dir(tmp_path, monkeypatch):
    d = tmp_path / "site"
    (d / "help").mkdir(parents=True)
    (d / "index.html").write_text('<a href="./JianZiPu.ttf">x</a><a href="/help/">h</a>'
                                  '<script src="https://cdn.example/x.js"></script><a href="//cdn.example/y">y</a>',
                                  encoding="utf-8")
    (d / "help" / "index.html").write_text('<link href="/help.md"><a href="/">home</a>', encoding="utf-8")
    (d / "help.md").write_text("# 减字谱", encoding="utf-8")
    (d / "JianZiPu.ttf").write_bytes(b"released font")
    (d / "_headers").write_text("/*\n  X-Frame-Options: SAMEORIGIN", encoding="utf-8")
    monkeypatch.setattr(config, "SITE_DIR", d)
    return d


def raw_get_headers(base, path):
    import http.client
    host, port = base.removeprefix("http://").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    out = r.status, dict(r.getheaders()), r.read()
    c.close()
    return out


def test_site_is_served_under_site(server, app_build, site_dir):
    """/site is the font page folder as jianzipufont.com serves it, for a pull request's preview."""
    status, headers, body = raw_get_headers(server, "/site")
    assert status == 301 and headers["Location"] == "/site/"          # its links are relative
    assert raw_get_headers(server, "/site?x=1")[1]["Location"] == "/site/?x=1"
    status, headers, body = raw_get_headers(server, "/site/")
    assert status == 200 and headers["Content-Type"] == "text/html; charset=utf-8"
    # links from the site's root move under /site; relative and other hosts' links stay
    assert body.decode() == ('<a href="./JianZiPu.ttf">x</a><a href="/site/help/">h</a>'
                             '<script src="https://cdn.example/x.js"></script><a href="//cdn.example/y">y</a>')
    assert raw_get_headers(server, "/site/JianZiPu.ttf")[2] == b"released font"
    assert raw_get_headers(server, "/site/help")[1]["Location"] == "/site/help/"
    assert raw_get_headers(server, "/site/help/")[2] == b'<link href="/site/help.md"><a href="/site/">home</a>'
    status, headers, body = raw_get_headers(server, "/site/help.md")
    assert headers["Content-Type"].endswith("charset=utf-8") and body.decode() == "# 减字谱"
    for p in ("/site/_headers", "/site/nope.html", "/site/%2e%2e/builder/pyproject.toml", "/site/../VERSION"):
        assert raw_get(server, p)[0] == 404, p
    # the Builder's own paths are untouched
    assert raw_get(server, "/sitemap.xml")[0] == 404
    assert raw_get(server, "/layouts")[1].startswith(b"<!doctype html><title>app")


def test_safe_path():
    assert webserver._safe_path("/glyphs/md_9/edit")
    assert webserver._safe_path("/_app/immutable/x.js")
    for p in ("/../x", "/a/../b", "/%2e%2e/x", "/a/./b", "/a\\b", "/a%00b", "/..%2fx"):
        assert not webserver._safe_path(p), p


# ---------------------------------------------------------------- Host / Origin / Content-Type

def raw(base, method, path, headers, body=b""):
    import http.client
    host, port = base.removeprefix("http://").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.putrequest(method, path, skip_host=True)
    hs = {"Host": f"{host}:{port}", **headers}
    if body:
        hs["Content-Length"] = str(len(body))
    for k, v in hs.items():
        if v is not None:
            c.putheader(k, v)
    c.endheaders(body or None)
    r = c.getresponse()
    out = r.status, r.read()
    c.close()
    return out


def test_foreign_host_is_refused(server):
    """DNS rebinding: a page on evil.example whose name resolves to 127.0.0.1."""
    status, body = raw(server, "GET", "/api/design", {"Host": "evil.example:5713"})
    assert status == 403 and b"localhost" in body


@pytest.mark.parametrize("host", ["localhost:5173", "127.0.0.1:5713", "[::1]:5713", "LOCALHOST"])
def test_loopback_hosts_are_fine(server, host):
    status, _ = raw(server, "GET", "/api/config", {"Host": host})
    assert status == 200


def test_cross_site_writes_are_refused(server, svg_dir):
    body = json.dumps({"svg": SQUARE}).encode()
    for method, path in (("PUT", "/api/svg/zz_x"), ("POST", "/api/svg/check"), ("DELETE", "/api/svg/zz_x")):
        status, _ = raw(server, method, path, {"Origin": "https://evil.example", "Content-Type": "application/json"},
                        body if method != "DELETE" else b"")
        assert status == 403, method
    assert not (svg_dir / "zz_x.svg").exists()


def test_same_origin_and_dev_server_writes_work(server, svg_dir):
    body = json.dumps({"svg": SQUARE}).encode()
    status, _ = raw(server, "PUT", "/api/svg/zz_y", {"Origin": server, "Content-Type": "application/json"}, body)
    assert status == 200
    status, _ = raw(server, "POST", "/api/svg/check", {"Origin": "http://localhost:5173", "Host": "localhost:5173",
                                                       "Content-Type": "application/json"}, body)
    assert status == 200


def test_writes_need_json(server, svg_dir):
    """A cross-site <form> or a text/plain fetch can't send application/json without a preflight."""
    body = json.dumps({"svg": SQUARE}).encode()
    for ctype in ("text/plain", "application/x-www-form-urlencoded", None):
        status, _ = raw(server, "PUT", "/api/svg/zz_z", {"Content-Type": ctype}, body)
        assert status == 415, ctype
    assert not (svg_dir / "zz_z.svg").exists()
    status, _ = raw(server, "PUT", "/api/svg/zz_z", {"Content-Type": "application/json; charset=utf-8"}, body)
    assert status == 200


def test_security_headers(server):
    import http.client
    host, port = server.removeprefix("http://").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.request("GET", "/api/config")
    r = c.getresponse()
    r.read()
    assert r.getheader("X-Content-Type-Options") == "nosniff"
    assert "frame-ancestors 'none'" in r.getheader("Content-Security-Policy")
    assert r.getheader("X-Frame-Options") == "DENY"
    assert "Python" not in (r.getheader("Server") or "")
    assert r.getheader("Strict-Transport-Security") is None          # local: plain http


# ---------------------------------------------------------------- the PR preview's tab icon

from jzpbuild import preview_favicon  # noqa: E402

ICONS = """    <title>JianZiPu Font Builder</title>
    <link rel="icon" href="/favicon.ico" sizes="any" />
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
"""


@pytest.mark.parametrize("host, pr", [
    ("builder-pr-29.up.railway.app", "29"), ("Builder-PR-104.up.railway.app:443", "104"),
    ("builder-pr-7.up.railway.app, proxy.internal", "7"),
    ("builder.jianzipufont.com", None), ("jianzipufont.com", None), ("x-pr-3.jianzipufont.com", None),
    ("builder-production.up.railway.app", None), ("localhost:5713", None), ("", None), (None, None),
])
def test_preview_pr_number(host, pr):
    assert preview_favicon.pr_number(host) == pr


def test_preview_icon_is_the_number_in_dark_brown():
    from urllib.parse import unquote
    svg = unquote(preview_favicon.href("29").removeprefix("data:image/svg+xml,"))
    assert ">29</text>" in svg and 'fill="#5C3A21"' in svg and 'font-size="26"' in svg
    assert 'font-size="14"' in unquote(preview_favicon.href("1234"))
    with pytest.raises(ValueError):
        preview_favicon.href("<b>")


def test_preview_page_gets_one_icon_and_production_none():
    out = preview_favicon.apply(ICONS, "builder-pr-29.up.railway.app")
    assert out.count('rel="icon"') == 1 and 'href="data:image/svg+xml,' in out and 'type="image/svg+xml"' in out
    assert "apple-touch-icon" in out and "favicon.ico" not in out
    assert out.splitlines()[1].startswith('    <link rel="icon" href="data:')
    assert preview_favicon.apply(ICONS, "builder.jianzipufont.com") == ICONS
    assert preview_favicon.apply(ICONS, "127.0.0.1:5713") == ICONS


def test_hosted_server_puts_the_pr_icon_in_the_page(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<head>\n" + ICONS + "</head>", encoding="utf-8")
    monkeypatch.setattr(webserver, "APP_BUILD_DIR", tmp_path)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), webserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/glyphs"

    def page(host):
        req = urllib.request.Request(url, headers={"X-Forwarded-Host": host})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8")
    try:
        assert "favicon.ico" in page("builder-pr-29.up.railway.app")      # local mode: never changed
        monkeypatch.setattr(webserver.SETTINGS, "hosted", True)
        assert "data:image/svg+xml" in page("builder-pr-29.up.railway.app")
        assert "favicon.ico" in page("builder.jianzipufont.com")
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- the glossary's rows (site/glossary.json)

def test_the_glossary_rows_are_listed_and_saved_with_a_hash(tmp_path, monkeypatch):
    f = tmp_path / "glossary.json"
    f.write_text(GLOSSARY_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(config, "GLOSSARY_SECTIONS", f)
    p = webserver.glyphs_payload()
    secs = {s["id"]: s for s in p["glossary_sections"]}
    assert secs["1a"]["title"] == "1a: Left Hand Finger" and secs["1a"]["usage"] == ["{}9k3", "{}九勾三"]
    assert secs["1a"]["rows"][0] == {"glyph": "md_ming"}
    assert {"word": "少息", "glyphs": ["md_shao", "md_xi"]} in secs["3e"]["rows"]
    rows = {"3e": [{"word": "大息", "glyphs": ["md_da", "md_xi"], "meaning": "rest"}], "1a": secs["1a"]["rows"][::-1]}
    r = webserver.write_glossary(rows, p["glossary_hash"])
    doc = json.loads(f.read_text(encoding="utf-8"))
    assert r["ok"] and doc["sections"]["3e"]["rows"] == rows["3e"] and doc["sections"]["1a"]["rows"][-1] == {"glyph": "md_ming"}
    assert doc["sections"]["1a"]["usage"] == ["{}9k3", "{}九勾三"] and doc["about"]       # the rest of the file stays
    assert doc["sections"]["2a"]["rows"] == secs["2a"]["rows"]                             # sections not sent stay
    with pytest.raises(webserver.CsvConflict):
        webserver.write_glossary(rows, p["glossary_hash"])        # the file moved on since that hash
    with pytest.raises(ValueError, match="no section 9z"):
        webserver.write_glossary({"9z": []}, r["hash"])
    with pytest.raises(ValueError):
        webserver.write_glossary({"3e": [{"glyph": ""}]}, r["hash"])


def test_the_glossary_titles_and_descriptions_are_saved_with_the_rows(tmp_path, monkeypatch):
    f = tmp_path / "glossary.json"
    f.write_text(GLOSSARY_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(config, "GLOSSARY_SECTIONS", f)
    p = webserver.glyphs_payload()
    groups = p["glossary_groups"]
    assert groups[0]["title"] == "1: Left Hand" and groups[0]["sections"][0] == "1a"
    metas = {s["id"]: {k: s[k] for k in ("title", "usage", "description") if s.get(k)} for s in p["glossary_sections"]}
    assert metas["2b"]["description"].startswith("These notes")
    rows = {s["id"]: s["rows"] for s in p["glossary_sections"]}
    # a new subtitle under a new section title, a renamed one, a description
    metas["5a"] = {"title": "5a: Ornaments", "description": "Written **after** the note."}
    metas["1a"]["title"] = "1a: Fingers"
    layout = {"groups": groups + [{"id": "ornaments", "title": "5: Ornaments", "sections": ["5a"]}], "sections": metas}
    rows["5a"] = [{"glyph": "md_placeholder"}]
    rows["3x"] = []
    r = webserver.write_glossary(rows, p["glossary_hash"], layout)
    doc = json.loads(f.read_text(encoding="utf-8"))
    assert r["ok"] and doc["groups"][-1] == {"id": "ornaments", "title": "5: Ornaments", "sections": ["5a"]}
    assert doc["sections"]["5a"] == {"title": "5a: Ornaments", "description": "Written **after** the note.",
                                     "rows": [{"glyph": "md_placeholder"}]}
    assert doc["sections"]["1a"]["title"] == "1a: Fingers" and list(doc)[:3] == ["about", "groups", "sections"]
    # a subtitle with rows can't be dropped
    del layout["sections"]["2b"]
    layout["groups"][1]["sections"].remove("2b")
    with pytest.raises(ValueError, match="still has"):
        webserver.write_glossary(rows, r["hash"], layout)


def test_words_space_vertical_words_as_the_font_does():
    """/api/words moves the pen as the font does: a vertical word's colon gives its em back to the
    space after the word, so two words typed with a space are one em apart, not two (the Glossary's
    Output showed a gap between them); a colon straight after a word keeps it, a # after a vertical
    word makes room for it and pulls what follows back. Figures checked against the released font."""
    from jzpbuild.positioning import schema
    design = schema.load_design()
    runs = {
        "yin": ["blank_colon", "md_yin"],
        "s9k6": ["md_ming", "md_9", "lg_gou", "md_6"],
        "daiqi": ["blank_colon", "md_dai", "md_qi"],
    }
    def laid(*parts):
        glyphs = [g for p in parts for g in (runs.get(p) or [p])]
        w = webserver.words_payload(design, ["x"], runs=[glyphs])["words"][0]
        return {e["glyph"]: e["x"] for p in w["pieces"] for e in p["elements"]}, w["advance"]
    alone = {g: x for p in runs for g, x in laid(p)[0].items()}
    xs, adv = laid("yin", "space", "blank_colon", "md_nao")
    assert xs["md_nao"] - alone["md_yin"] == 1000 and adv == 1000
    xs, adv = laid("s9k6", "space", "daiqi")
    assert xs["md_dai"] - alone["md_dai"] == 1000 and adv == 1000
    xs, adv = laid("s9k6", "daiqi")                        # s9k6:daiqi: the colon keeps its em
    assert xs["md_dai"] - alone["md_dai"] == 1000 and adv == 1000
    assert laid("yin")[1] == 0
    xs, adv = laid("yin", "numbersign", "s9k6")
    assert xs["md_ming"] - alone["md_ming"] == 1000 and adv == 2000
    xs, adv = laid("s9k6", "numbersign", "yin")
    assert xs["md_yin"] == alone["md_yin"] and adv == 1000
