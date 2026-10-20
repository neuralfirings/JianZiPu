"""Font releases (jzpbuild/release.py): what a release branch may change, starting a release,
building candidates, and publishing, against a scratch git repo with a local "GitHub" (a bare repo).
The font build and the test run are stubbed; nothing leaves the machine.

Run:  cd builder && python3 -m pytest tests/test_release.py
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jzpbuild import release  # noqa: E402
from jzpbuild.release import ReleaseError  # noqa: E402


def sh(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "neuralfirings" / "JianZiPu.git"
    origin.parent.mkdir()
    sh(tmp_path, "init", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    sh(tmp_path, "clone", str(origin), str(work))
    for k, v in (("user.name", "Test"), ("user.email", "t@example.com"), ("commit.gpgsign", "false"), ("tag.gpgsign", "false")):
        sh(work, "config", k, v)
    (work / "builder" / "inputs").mkdir(parents=True)
    (work / "builder" / "inputs" / "design.json").write_text('{"v": 1}\n')
    (work / "builder" / "VERSION").write_text("3.100\n")
    (work / "builder" / "jzpbuild").mkdir()
    (work / "builder" / "jzpbuild" / "x.py").write_text("x = 1\n")
    (work / "site").mkdir()
    (work / "site" / "JianZiPu.ttf").write_bytes(b"old font")
    (work / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n## [3.100] - 2026-10-19\n\n- the first\n")
    sh(work, "add", "-A")
    sh(work, "commit", "-m", "start")
    sh(work, "push", "-u", "origin", "main")
    return work


def fake_build(out, commit, log):
    out.write_bytes(f"font from {commit}".encode())


def no_tests(log):
    pass


def candidate(repo, notes="- wider hui", **kw):
    return release.candidate(notes, "3.200: Hui spacing (Mei)", repo=repo, log=lambda _: None, build=fake_build,
                             tests=no_tests, today="2026-10-21", **kw)


def test_scope_both_ways():
    files = ["builder/inputs/design.json", "site/JianZiPu.ttf", "app/src/x.ts", "CHANGELOG.md", "builder/VERSION"]
    assert release.scope(files, "release/3.200") == ["app/src/x.ts"]
    assert release.scope(files, "feat/release-management") == ["builder/inputs/design.json", "site/JianZiPu.ttf", "CHANGELOG.md", "builder/VERSION"]
    assert release.scope(["builder/tests/JianZiPu.ttf"], "release/3.200") == []
    assert release.scope(["builder/inputsx/a"], "release/3.200") == ["builder/inputsx/a"]   # a folder, not a prefix


def test_changelog_section_goes_under_unreleased_and_is_replaced_on_a_new_candidate():
    text = "# Changelog\n\n## [Unreleased]\n\n## [3.100] - 2026-10-19\n\n- the first\n"
    once = release.changelog_with(text, "3.200", "- wider hui", "2026-10-21")
    assert once.index("## [3.200] - 2026-10-21") < once.index("## [3.100]")
    assert once.index("## [Unreleased]") < once.index("## [3.200]")
    again = release.changelog_with(once, "3.200", "- wider hui\n- new glyph", "2026-10-22")
    assert again.count("## [3.200]") == 1 and "- new glyph" in again and "2026-10-21" not in again
    assert "- the first" in again


def test_versions_need_a_three_digit_minor():
    assert release.parse_version("3.200") == (3, 200)
    with pytest.raises(ReleaseError):
        release.parse_version("3.2")


def test_start_refuses_a_lower_version_or_a_dirty_copy(repo):
    with pytest.raises(ReleaseError, match="higher number"):
        release.start("3.100", repo=repo, log=lambda _: None)
    (repo / "builder" / "inputs" / "design.json").write_text('{"v": 2}\n')
    with pytest.raises(ReleaseError, match="clean copy"):
        release.start("3.200", repo=repo, log=lambda _: None)


def test_a_release_from_start_to_publish(repo):
    assert release.start("3.200", repo=repo, log=lambda _: None) == {"branch": "release/3.200"}
    (repo / "builder" / "inputs" / "design.json").write_text('{"v": 2}\n')     # Add kept changes + Save
    r = candidate(repo)
    assert r["tag"] == "v3.200-rc.1"
    assert r["pr_url"] == "https://github.com/neuralfirings/JianZiPu/compare/main...release/3.200?expand=1"
    assert (repo / "builder" / "VERSION").read_text() == "3.200\n"
    design_commit = sh(repo, "rev-parse", "--short", "HEAD~1")
    assert (repo / "site" / "JianZiPu.ttf").read_bytes() == f"font from {design_commit}".encode()
    assert json.loads((repo / "site" / "version.json").read_text()) == {
        "version": "3.200", "date": "2026-10-21", "notes_url": "https://github.com/neuralfirings/JianZiPu/releases/tag/v3.200"}
    assert "## [3.200] - 2026-10-21\n\n- wider hui" in (repo / "CHANGELOG.md").read_text()
    assert sh(repo, "log", "--format=%s", "-2").splitlines() == ["v3.200-rc.1: JianZiPu 3.200, release candidate 1", "3.200: Hui spacing (Mei)"]
    assert "v3.200-rc.1" in sh(repo, "ls-remote", "--tags", "origin")
    assert not release.dirty_files(repo)

    # a fix, and a second candidate
    (repo / "builder" / "inputs" / "design.json").write_text('{"v": 3}\n')
    assert candidate(repo)["tag"] == "v3.200-rc.2"

    # not merged yet
    with pytest.raises(ReleaseError, match="merge the release pull request"):
        release.publish(repo=repo, log=lambda _: None)
    # merged on GitHub (here: main fast-forwards to the branch, plus a Builder-code commit)
    sh(repo, "push", "origin", "release/3.200:main")
    sh(repo, "switch", "main")
    sh(repo, "merge", "--ff-only", "origin/main")
    (repo / "builder" / "jzpbuild" / "x.py").write_text("x = 2\n")
    sh(repo, "commit", "-am", "Builder code")
    sh(repo, "push", "origin", "main")
    sh(repo, "switch", "release/3.200")
    p = release.publish(repo=repo, log=lambda _: None)
    assert p == {"tag": "v3.200", "version": "3.200", "release_url": "https://github.com/neuralfirings/JianZiPu/releases/tag/v3.200"}
    assert sh(repo, "rev-list", "-n", "1", "v3.200") == sh(repo, "rev-parse", "origin/main")
    assert release.current_branch(repo) == "main"
    with pytest.raises(ReleaseError, match="already released"):
        release.publish("3.200", repo=repo, log=lambda _: None)


def test_a_release_branch_refuses_code(repo):
    release.start("3.200", repo=repo, log=lambda _: None)
    (repo / "builder" / "jzpbuild" / "x.py").write_text("x = 3\n")
    with pytest.raises(ReleaseError, match="only font files.*builder/jzpbuild/x.py"):
        candidate(repo)


def test_publish_refuses_when_font_files_moved_on_main_after_the_candidate(repo):
    release.start("3.200", repo=repo, log=lambda _: None)
    (repo / "builder" / "inputs" / "design.json").write_text('{"v": 2}\n')
    candidate(repo)
    sh(repo, "push", "origin", "release/3.200:main")
    sh(repo, "switch", "main")
    sh(repo, "merge", "--ff-only", "origin/main")
    (repo / "builder" / "inputs" / "design.json").write_text('{"v": 9}\n')
    sh(repo, "commit", "-am", "sneaky design change")
    sh(repo, "push", "origin", "main")
    with pytest.raises(ReleaseError, match="Font files changed on main"):
        release.publish("3.200", repo=repo, log=lambda _: None)


def test_the_local_server_runs_one_release_step_at_a_time(monkeypatch):
    from jzpbuild import webserver
    import threading
    gate = threading.Event()
    r = webserver.ReleaseRunner()
    assert r.start("start", lambda log: (log("fetching"), gate.wait(5), {"branch": "release/3.200"})[-1]) == (True, None)
    assert r.start("candidate", lambda log: None) == (False, "start is still running")
    gate.set()
    for _ in range(100):
        if r.job["state"] == "done":
            break
        threading.Event().wait(0.02)
    assert r.job["result"] == {"branch": "release/3.200"} and r.job["log"] == ["fetching"]
    assert r.start("publish", lambda log: (_ for _ in ()).throw(ReleaseError("not merged"))) == (True, None)
    for _ in range(100):
        if r.job["state"] == "done":
            break
        threading.Event().wait(0.02)
    assert r.job["error"] == "not merged"
