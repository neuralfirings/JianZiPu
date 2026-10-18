"""Tests for the dev server's build registry: each UI build lives in its own temp dir, the last
few are listed, each one is served (and downloadable) by id, old ones are pruned.
Uses fake font files; never runs the real build (tests/test_shaping.py does that).

Run:  cd src-fonttools && python3 -m pytest tests/test_builds.py
"""

import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import devserver  # noqa: E402


@pytest.fixture
def runner(monkeypatch):
    r = devserver.BuildRunner()
    monkeypatch.setattr(devserver, "BUILD", r)
    yield r
    r.cleanup()


def fake_build(r: devserver.BuildRunner, content: bytes = b"\x00\x01\x00\x00fake") -> dict:
    r._seq += 1
    d = Path(tempfile.mkdtemp(prefix="jzp-build-test-"))
    p = d / "JianZiPu.ttf"
    p.write_bytes(content)
    return r.register(p, seconds=1.5)


def test_register_lists_newest_first_and_latest(runner):
    assert runner.status()["builds"] == [] and runner.latest is None
    a = fake_build(runner)
    b = fake_build(runner, b"x" * 10)
    st = runner.status()
    assert [x["id"] for x in st["builds"]] == [b["id"], a["id"]]
    assert st["build"]["id"] == b["id"] and st["build"]["bytes"] == 10
    assert st["build"]["url"] == f"/api/builds/{b['id']}/JianZiPu.ttf"
    assert runner.latest == b["path"]
    assert runner.get(a["id"]) is a and runner.get("nope") is None


def test_old_builds_are_pruned_and_their_folders_removed(runner):
    made = [fake_build(runner) for _ in range(runner.KEEP + 2)]
    assert len(runner.builds) == runner.KEEP
    assert not made[0]["path"].exists() and not made[1]["path"].parent.exists()
    assert made[-1]["path"].exists()


def test_cleanup_removes_everything(runner):
    b = fake_build(runner)
    runner.cleanup()
    assert runner.builds == [] and not b["path"].parent.exists()


@pytest.fixture
def server(runner):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), devserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=10) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read()


def test_http_serves_the_exact_file_and_download_header(server, runner):
    b = fake_build(runner, b"FONTBYTES")
    status, headers, body = get(server, b["path"] and f"/api/builds/{b['id']}/JianZiPu.ttf")
    assert status == 200 and body == b"FONTBYTES"
    assert headers["Content-Type"] == "font/ttf" and "Content-Disposition" not in headers
    status, headers, body = get(server, f"/api/builds/{b['id']}/JianZiPu.ttf?download=1")
    assert status == 200 and headers["Content-Disposition"] == 'attachment; filename="JianZiPu.ttf"'
    status, _, body = get(server, "/JianZiPu.ttf")             # latest build
    assert status == 200 and body == b"FONTBYTES"
    status, _, body = get(server, "/api/build/status")
    assert status == 200 and json.loads(body)["build"]["id"] == b["id"]


def test_http_unknown_build_is_404(server, runner):
    status, _, body = get(server, "/api/builds/b99/JianZiPu.ttf")
    assert status == 404 and json.loads(body)["ok"] is False
    status, _, body = get(server, "/api/builds/..%2F..%2Fetc/JianZiPu.ttf")
    assert status in (404, 400)
