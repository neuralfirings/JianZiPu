"""Tests for the web server's hosted (pilot) mode: read-only, signed-in testers only, builds of a
tester's draft that belong to that tester. Supabase is stubbed; nothing leaves the machine.

Run:  cd builder && python3 -m pytest tests/test_hosted.py
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

from jzpbuild import config, webserver, hosted  # noqa: E402
import os  # noqa: E402

SQUARE = '<svg viewBox="0 0 350 350" xmlns="http://www.w3.org/2000/svg"><path d="M10 10h100v100h-100z" fill="black"/></svg>'
USERS = {"tok-a": {"id": "user-a"}, "tok-b": {"id": "user-b"}}


@pytest.fixture
def runner(monkeypatch):
    r = webserver.BuildRunner()
    monkeypatch.setattr(webserver, "BUILD", r)
    yield r
    r.cleanup()


@pytest.fixture
def hosted_mode(monkeypatch, runner):
    s = hosted.Settings(hosted=True, supabase_url="https://example.supabase.co", supabase_anon_key="anon",
                        supabase_service_key="SERVICE-SECRET", commit="abc123")
    auth = hosted.Auth(s)
    calls = []

    def fetch_user(token):
        calls.append(token)
        return USERS.get(token)
    monkeypatch.setattr(auth, "fetch_user", fetch_user)
    monkeypatch.setattr(webserver, "SETTINGS", s)
    monkeypatch.setattr(webserver, "AUTH", auth)
    return calls


@pytest.fixture
def server(hosted_mode):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), webserver.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def call(base, method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if resp.headers.get_content_type() == "application/json" else raw)
    except urllib.error.HTTPError as err:
        raw = err.read()
        return err.code, (json.loads(raw) if err.headers.get_content_type() == "application/json" else raw)


def fake_build(r, owner, content=b"\x00\x01\x00\x00fake"):
    r._seq += 1
    d = Path(tempfile.mkdtemp(prefix="jzp-build-test-"))
    (d / "JianZiPu.ttf").write_bytes(content)
    return r.register(d / "JianZiPu.ttf", seconds=1.0, owner=owner)


# ---------------------------------------------------------------- settings

def test_public_settings_never_carry_the_service_key():
    s = hosted.Settings(hosted=True, supabase_url="https://x.supabase.co", supabase_anon_key="anon",
                        supabase_service_key="SERVICE-SECRET")
    pub = s.public()
    assert pub["mode"] == "hosted" and pub["supabase_anon_key"] == "anon"
    assert "SERVICE-SECRET" not in json.dumps(pub)
    assert hosted.Settings().public()["mode"] == "local"


def test_auth_caches_answers(hosted_mode):
    auth = webserver.AUTH
    assert auth.user("tok-a") == {"id": "user-a"}
    assert auth.user("tok-a") == {"id": "user-a"}
    assert auth.user(None) is None and auth.user("nope") is None
    assert hosted_mode == ["tok-a", "nope"]


def test_base_font_is_left_alone_when_present(tmp_path):
    f = tmp_path / "TW-Kai-98.ttf"
    f.write_bytes(b"x")
    assert "present" in hosted.fetch_base_font(hosted.Settings(), f)
    assert "missing" in hosted.fetch_base_font(hosted.Settings(), tmp_path / "none.ttf")


# ---------------------------------------------------------------- HTTP

def test_env_file(tmp_path, monkeypatch):
    f = tmp_path / ".env"
    f.write_text('# local settings\nSUPABASE_URL="https://x.supabase.co"\nexport SUPABASE_ANON_KEY=anon\n\nJZP_TEST_KEEP=file\n')
    monkeypatch.setenv("JZP_TEST_KEEP", "shell")
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert sorted(hosted.load_env_file(f)) == ["SUPABASE_ANON_KEY", "SUPABASE_URL"]
    assert os.environ["SUPABASE_URL"] == "https://x.supabase.co" and os.environ["SUPABASE_ANON_KEY"] == "anon"
    assert os.environ["JZP_TEST_KEEP"] == "shell"          # the shell wins
    assert hosted.load_env_file(tmp_path / "missing") == []
    for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
        os.environ.pop(k, None)                            # set by the loader, not by monkeypatch


def test_config_and_base(server):
    status, r = call(server, "GET", "/api/config")
    assert status == 200 and r["mode"] == "hosted" and r["commit"] == "abc123"
    assert "feedback_url" not in r and "SERVICE" not in json.dumps(r)
    status, base = call(server, "GET", "/api/base")
    _, design = call(server, "GET", "/api/design")
    _, cat = call(server, "GET", "/api/glyphs")
    assert base["design_hash"] == design["hash"] and base["csv_hash"] == cat["hash"]
    assert base["svg_hashes"] and all(len(h) == 16 for h in base["svg_hashes"].values())
    assert base["date"] and base["date"][:2] == "20"     # "the font of 18 Oct"


def test_read_only(server):
    status, r = call(server, "PUT", "/api/design", {"design": {}}, token="tok-a")
    assert status == 403 and r["readonly"] is True
    status, r = call(server, "PUT", "/api/svg/zz", {"svg": SQUARE}, token="tok-a")
    assert status == 403
    status, r = call(server, "DELETE", "/api/svg/md_7", token="tok-a")
    assert status == 403 and r["readonly"] is True


def test_posts_need_a_signed_in_tester(server):
    body = {"words": ["s7k5"]}
    status, r = call(server, "POST", "/api/words", body)
    assert status == 401 and r["auth"] is True
    status, r = call(server, "POST", "/api/words", body, token="bad")
    assert status == 401
    status, r = call(server, "POST", "/api/svg/check", {"svg": SQUARE}, token="tok-a")
    assert status == 200 and r["ok"]


def test_no_folder_browsing(server):
    """Only the app and inputs/ are served: anything else gets the app's page (or 404), never the
    golden font or the base font."""
    for path in ("/tests/JianZiPu.ttf", "/src_font/TW-Kai-98.ttf", "/jzpbuild/config.py"):
        status, body = call(server, "GET", path)
        assert status in (200, 404)
        assert not (isinstance(body, bytes) and (body[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true")
                                                 or b"SOURCE_FONT" in body))


def test_builds_belong_to_their_tester(server, runner):
    a = fake_build(runner, "user-a", b"AAAA")
    b = fake_build(runner, "user-b", b"BBBB")
    status, st = call(server, "GET", "/api/build/status", token="tok-a")
    assert status == 200 and [x["id"] for x in st["builds"]] == [a["id"]]
    assert call(server, "GET", "/api/build/status")[0] == 401
    # ids are random, so a build's URL is only known to its owner; the file itself needs no token
    assert len(a["id"]) > 8 and a["id"] != b["id"]
    status, body = call(server, "GET", f"/api/builds/{b['id']}/JianZiPu.ttf")
    assert status == 200 and body == b"BBBB"


def test_main_build_is_the_fallback_font(runner):
    m = fake_build(runner, webserver.MAIN, b"MAIN")
    assert runner.font_for("user-a") == m["path"]
    a = fake_build(runner, "user-a", b"AAAA")
    assert runner.font_for("user-a") == a["path"] and runner.font_for("user-b") == m["path"]


def test_pruning_is_per_owner(runner):
    m = fake_build(runner, webserver.MAIN)
    for _ in range(runner.KEEP + 3):
        fake_build(runner, "user-a")
    assert runner.get(m["id"]) is m and m["path"].exists()
    assert len([b for b in runner.builds if b["owner"] == "user-a"]) == runner.KEEP


def test_one_build_at_a_time(runner):
    runner.running = "user-b"
    ok, why = runner.start("user-a")
    assert not ok and "try again" in why
    runner.running = None


# ---------------------------------------------------------------- draft inputs

@pytest.fixture
def svg_dir(tmp_path, monkeypatch):
    d = tmp_path / "svg"
    d.mkdir()
    (d / "keep.svg").write_text(SQUARE, encoding="utf-8")
    (d / "gone.svg").write_text(SQUARE, encoding="utf-8")
    monkeypatch.setattr(config, "COMPONENTS_DIR", d)
    return d


def test_draft_inputs_are_written_and_flagged(tmp_path, svg_dir):
    work = tmp_path / "work"
    work.mkdir()
    design = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    rows = [{"glyph_name": "zz_new", "latin": "zz"}, {"glyph_name": "empty"}]
    args = webserver.write_build_inputs(work, {"design": design, "rows": rows,
                                               "svgs": {"zz_new": SQUARE}, "deleted": ["gone"]})
    assert args == ["--design", str(work / "design.json"), "--input-components", str(work / "components.csv"),
                    "--input-svg-dir", str(work / "svg")]
    assert json.loads((work / "design.json").read_text()) == design
    csv_text = (work / "components.csv").read_text()
    assert csv_text.splitlines()[0].startswith("glyph_name,") and "zz_new" in csv_text and "empty" not in csv_text
    assert sorted(p.name for p in (work / "svg").iterdir()) == ["keep.svg", "zz_new.svg"]


def test_draft_inputs_are_validated(tmp_path, svg_dir):
    def work(n):
        d = tmp_path / f"w{n}"
        d.mkdir()
        return d
    with pytest.raises(ValueError):
        webserver.write_build_inputs(work(1), {"svgs": {"../evil": SQUARE}})
    with pytest.raises(Exception):
        webserver.write_build_inputs(work(2), {"svgs": {"bad": "<svg/>"}})
    with pytest.raises(Exception):
        webserver.write_build_inputs(work(3), {"design": {"version": 2}})


def test_a_bad_draft_does_not_leave_the_runner_busy(runner):
    with pytest.raises(Exception):
        runner.start("user-a", {"svgs": {"../evil": SQUARE}})
    assert runner.running is None and runner.job("user-a")["ok"] is False


@pytest.mark.skipif(not config.SOURCE_FONT.exists(), reason="needs the base font (src_font/TW-Kai-98.ttf)")
def test_a_draft_builds_into_a_font_with_its_new_glyph(runner):
    """End to end: a draft that adds a glyph to the Character area with a spelling builds into a
    font that has the glyph and types it, without touching inputs/."""
    import time
    from fontTools.ttLib import TTFont
    from jzpbuild import data
    design = json.loads(config.DESIGN_JSON.read_text(encoding="utf-8"))
    design["areas"]["char"]["glyphs"].append("md_zztest")
    rows = webserver.glyphs_payload()["glyphs"]
    recs = [{k: r.get(k, "") for k in webserver.CSV_FIELDS if k != "glyph_name"} | {"glyph_name": r["glyph"]}
            for r in rows if r["row"]]
    recs.append({"glyph_name": "md_zztest", "latin": "zztest"})
    before = config.DESIGN_JSON.read_text(encoding="utf-8")
    ok, why = runner.start("user-a", {"design": design, "rows": recs, "svgs": {"md_zztest": SQUARE}})
    assert ok, why
    deadline = time.time() + 300
    while runner.running and time.time() < deadline:
        time.sleep(0.5)
    job = runner.job("user-a")
    assert job["ok"], "\n".join(job["log"][-30:])
    font = TTFont(runner.latest_for("user-a"))
    assert "md_zztest" in font.getGlyphOrder()
    assert config.DESIGN_JSON.read_text(encoding="utf-8") == before
    data.cache_clear_all()


@pytest.mark.parametrize("path", ["/../../builder/.env.example", "/" + "../" * 30 + "etc/passwd",
                                  "/%2e%2e/%2e%2e/builder/jzpbuild/hosted.py", "/" + "../" * 30 + "etc/hosts"])
def test_no_path_traversal(server, tmp_path, monkeypatch, path):
    import http.client
    d = tmp_path / "appbuild"
    d.mkdir()
    (d / "index.html").write_text("<!doctype html><title>app</title>", encoding="utf-8")
    monkeypatch.setattr(webserver, "APP_BUILD_DIR", d)
    host, port = server.removeprefix("http://").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.putrequest("GET", path, skip_host=True)
    c.putheader("Host", f"{host}:{port}")
    c.endheaders()
    r = c.getresponse()
    body = r.read()
    assert r.status == 404 or body.startswith(b"<!doctype html><title>app")
    assert b"root:" not in body and b"localhost" not in body and b"SERVICE-SECRET" not in body


def test_hosted_cross_site_posts_are_refused(server):
    import http.client
    host, port = server.removeprefix("http://").split(":")
    body = json.dumps({"svg": SQUARE}).encode()
    for origin, want in (("https://evil.example", 403), (f"http://{host}:{port}", 200)):
        c = http.client.HTTPConnection(host, int(port), timeout=10)
        c.request("POST", "/api/svg/check", body=body, headers={"Origin": origin, "Content-Type": "application/json",
                                                                "Authorization": "Bearer tok-a"})
        assert c.getresponse().status == want, origin
        c.close()


def test_hosted_errors_carry_no_internals(server, monkeypatch, capsys):
    """A crash answers with a plain sentence; the traceback goes to the server log only."""
    def boom(*a, **k):
        raise RuntimeError("secret detail /repo/builder/x.py")
    monkeypatch.setattr(webserver, "typing_payload", boom)
    status, r = call(server, "POST", "/api/typing/preview", {"rows": []}, token="tok-a")
    assert status == 500 and "traceback" not in r and "secret detail" not in r["error"]


def test_hosted_build_list_has_no_server_paths(server, runner):
    fake_build(runner, "user-a")
    status, r = call(server, "GET", "/api/build/status", token="tok-a")
    assert status == 200 and r["build"] and "file" not in r["build"]
    assert all("file" not in b for b in r["builds"])


def test_sign_in_service_down_is_a_503_without_details(server, hosted_mode, monkeypatch):
    def down(token):
        raise hosted.AuthUnavailable("The sign-in service isn't answering. Try again in a minute.")
    monkeypatch.setattr(webserver.AUTH, "fetch_user", down)
    status, r = call(server, "POST", "/api/svg/check", {"svg": SQUARE}, token="tok-new")
    assert status == 503 and "urlopen" not in r["error"]
    status, r = call(server, "GET", "/api/build/status", token="tok-new")
    assert status == 503


def test_fetch_user_maps_network_errors(monkeypatch):
    import urllib.error
    a = hosted.Auth(hosted.Settings(hosted=True, supabase_url="https://example.supabase.co", supabase_anon_key="anon"))

    def raise_(exc):
        def f(*args, **kw):
            raise exc
        return f
    monkeypatch.setattr(urllib.request, "urlopen", raise_(urllib.error.URLError("nodename nor servname")))
    with pytest.raises(hosted.AuthUnavailable):
        a.fetch_user("t")
    monkeypatch.setattr(urllib.request, "urlopen", raise_(urllib.error.HTTPError("u", 401, "no", {}, None)))
    assert a.fetch_user("t") is None
