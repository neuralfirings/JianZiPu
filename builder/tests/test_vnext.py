"""site/vnext.html: the font page as it will be after the next release, written from index.html
(jzpbuild/vnext.py). Skipped on a release branch: a candidate may change only font files (and the
glossary on index.html), and once the release is out its changes move into index.html anyway."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jzpbuild import config, glossary, vnext  # noqa: E402


def _release_branch() -> bool:
    ref = os.environ.get("GITHUB_HEAD_REF") or subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=config.BUILDER_DIR, capture_output=True, text=True).stdout.strip()
    return ref.startswith("release/")


needs_main = pytest.mark.skipif(_release_branch(), reason="a release branch changes font files only; vnext.html follows on main")


@needs_main
def test_the_page_is_up_to_date():
    assert vnext.main(["--check"]) == 0, "run `cd builder && python3 -m jzpbuild.vnext`"


@needs_main
@pytest.mark.parametrize("page", ["vnext", "release"])
def test_every_example_on_the_pages_types_what_it_shows(page):
    pytest.importorskip("uharfbuzz")
    path = vnext.VNEXT if page == "vnext" else vnext.release_path(vnext.next_version())
    problems = glossary.check_typing(page=path.read_text(encoding="utf-8"))
    assert problems == [], "\n".join(problems)


def test_the_release_notes_compare_the_two_versions_and_link_out():
    page = vnext.release_page(config.SITE_INDEX.read_text(encoding="utf-8"), "9.900")
    assert "<title>JianZiPu 9.900 release notes</title>" in page and '<meta name="robots" content="noindex">' in page
    assert f'<th class="now">v{vnext.current_version()}</th><th class="next">v9.900</th>' in page
    assert vnext.RELEASES_URL in page and f'href="{vnext.REPO_URL}"' in page
    assert "名九徽七弦" in page and "url('./JianZiPu-vnext.ttf')" in page


def test_it_is_the_font_page_with_the_next_release_in_it():
    page = vnext.render(config.SITE_INDEX.read_text(encoding="utf-8"), "9.900")
    assert "url('./JianZiPu-vnext.ttf')" in page and "url('./JianZiPu.ttf'); font-display" in page   # next, and today's beside it
    assert '<meta name="robots" content="noindex">' in page and "What's new in 9.900" in page
    assert 'id="whats-new-hui"' in page and 'class="vnext-link"' not in page and 'href="./release-9.900.html"' in page
    assert '<table class="cmp">' not in page                                   # the page has the short list; the tables are in the notes
    for _, new in vnext.CHANGES:
        assert new in page


def test_a_lesson_the_page_no_longer_has_is_reported():
    page = config.SITE_INDEX.read_text(encoding="utf-8").replace("The next release reads 十一", "The next release reads 十二")
    with pytest.raises(ValueError, match="update CHANGES"):
        vnext.render(page, "9.900")


def test_the_next_version_follows_builder_version():
    major, minor = (config.BUILDER_DIR / "VERSION").read_text(encoding="utf-8").strip().split(".")
    assert vnext.next_version() == f"{major}.{int(minor) + 100:03d}"
