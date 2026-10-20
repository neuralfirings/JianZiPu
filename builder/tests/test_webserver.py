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


def test_safe_path():
    assert webserver._safe_path("/glyphs/md_9/edit")
    assert webserver._safe_path("/_app/immutable/x.js")
    for p in ("/../x", "/a/../b", "/%2e%2e/x", "/a/./b", "/a\\b", "/a%00b", "/..%2fx"):
        assert not webserver._safe_path(p), p
