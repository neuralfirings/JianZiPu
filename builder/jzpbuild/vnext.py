"""Write site/vnext.html: the font page as it will be once the next release is out.

It's site/index.html with the next release's changes applied, so the two never drift apart:

- the notation is drawn in a preview build of the next font (site/JianZiPu-vnext.ttf; `--font`
  rebuilds it from builder/inputs), and the glossary is written as the next font reads it (no colon
  before a word only a vertical word can hold);
- the lessons say what the next release changes (CHANGES below);
- a short "What's new in <next>" list (a bullet and one example per change), and a release notes page,
  site/release-<next>.html, showing each change in the released font beside the next one, with links
  to all releases and to the repository.

    cd builder && python3 -m jzpbuild.vnext            # rewrite site/vnext.html
    cd builder && python3 -m jzpbuild.vnext --font     # and rebuild site/JianZiPu-vnext.ttf
    cd builder && python3 -m jzpbuild.vnext --check    # exit 1 when it's out of date (a test runs this)

Once the release is out, its changes move into index.html for good (docs/maintainers/releasing.md,
"The coming-next page") and the lists below start over.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from . import config, glossary

VNEXT = config.SITE_DIR / "vnext.html"
VNEXT_FONT = config.SITE_DIR / "JianZiPu-vnext.ttf"


def next_version() -> str:
    """The version after builder/VERSION (3.200 -> 3.300): the next release's, as the Release screen offers it."""
    major, minor = (config.BUILDER_DIR / "VERSION").read_text(encoding="utf-8").strip().split(".")
    return f"{major}.{int(minor) + 100:03d}"


# what the lessons on index.html say differently once the next release is out: (as today, as next), each
# found exactly once (a test fails when index.html moves on and one no longer matches)
CHANGES: list[tuple[str, str]] = [
    # More rules: the hui numbers
    ("""<li>The next release reads 十一 to 十三 as hui 11 to 13, and adds 弦 to mark a string: <a href="./vnext.html#whats-new-hui">see what's coming</a>.</li>""",
     """<li><text>名十二勾五</text> or <text>s12k5</text> → <jzp>s12k5</jzp> 十一 to 十三 are hui 11 to 13. 10.2 is <text>名十徽二</text> or <text>名十点二</text>.</li>
        <li><text>名九徽半轮六</text> or <text>s9,banlun6</text> → <jzp>s9,banlun6</jzp> 徽 before a word that starts with 半 ends the number: 9, then 半轮. Without it, <text>名九半轮六</text> is 9.5, then 轮.</li>
        <li><text>名九七弦</text> or <text>s9,7</text> → <jzp>s9,7</jzp> 弦 marks a string: hui 9, string 7, not 9.7. In a chord it closes the first half: <text>撥大九四六弦｜散五</text> or <text>Bv9.4,6|05</text> → <jzp>Bv9.4,6|05</jzp></li>"""),
]

HEAD = """    /* the release notes: the released font, beside the next one */
    @font-face { font-family: 'JZP-now'; src: url('./JianZiPu.ttf'); font-display: swap; font-feature-settings: "kern", "liga"; }
    .vnext-banner { background: var(--target); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; }
    .whats-new table.cmp { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    .whats-new table.cmp th { text-align: left; font-weight: 600; padding: 6px 10px; border-bottom: 2px solid var(--border-strong); background: var(--bg-sunken); vertical-align: bottom; }
    .whats-new table.cmp td { padding: 6px 10px; border-bottom: 1px solid var(--hairline); vertical-align: middle; }
    .whats-new td.n { color: var(--ink-faint); text-align: right; width: 2.5em; font-size: .9em; }
    .whats-new td.typed { font-family: "LXGW WenKai TC", "Roboto Mono", serif; font-size: 1.15rem; white-space: nowrap; }
    .whats-new td.now, .whats-new td.next { font-size: 44px; line-height: 1.3; white-space: nowrap; }
    .whats-new td.now { font-family: 'JZP-now'; color: var(--ink-faint); }
    .whats-new td.next { font-family: 'JianZiPu'; }
    .whats-new .cmp-scroll { overflow-x: auto; }
    @media (max-width: 759.98px) { .whats-new td.now, .whats-new td.next { font-size: 34px; } }
"""


def _row(n: int, typed: str, *cells: str) -> str:
    mid = "".join(f"<td>{c}</td>" for c in cells)
    return (f'        <tr><td class="n">{n}</td><td class="typed">{typed}</td>{mid}'
            f'<td class="now">{typed}</td><td class="next">{typed}</td></tr>')


def _table(head: list[str], rows: list[tuple], current: str, version: str) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "\n".join(_row(i, *r) for i, r in enumerate(rows, 1))
    return (f'    <div class="cmp-scroll"><table class="cmp">\n'
            f'        <tr><th></th><th>Typed</th>{th}<th class="now">v{current}</th><th class="next">v{version}</th></tr>\n'
            f"{body}\n    </table></div>")


REPO_URL = "https://github.com/neuralfirings/JianZiPu"
RELEASES_URL = REPO_URL + "/releases"


def current_version() -> str:
    """The released version (builder/VERSION)."""
    return (config.BUILDER_DIR / "VERSION").read_text(encoding="utf-8").strip()


def release_path(version: str) -> Path:
    """The next release's notes page, beside vnext.html: release-3.300.html."""
    return config.SITE_DIR / f"release-{version}.html"


def _links(version: str) -> str:
    return (f'<a href="./release-{version}.html">Release notes for {version}</a> · '
            f'<a href="{RELEASES_URL}">All releases</a> · '
            f'<a href="{REPO_URL}">Contribute on GitHub</a>')


def whats_new(version: str) -> str:
    """The font page's short list: a bullet and one example (drawn in the next font) per change."""
    return f"""    <div class="whats-new">
    <h3 id="whats-new">What's new in {version}</h3>
    <ul>
      <li id="whats-new-hui"><strong>十一 to 十三 are hui 11 to 13.</strong> 10.2 is <text>十徽二</text> or <text>十点二</text>: <text>名十二勾五</text> → <jzp>名十二勾五</jzp></li>
      <li><strong>徽 before 半轮 ends the number.</strong> 9, then 半轮: <text>名九徽半轮六</text> → <jzp>名九徽半轮六</jzp> (<text>名九半轮六</text> is still 9.5, then 轮)</li>
      <li id="whats-new-xian"><strong>弦 marks a string.</strong> Hui 9, string 7, not 9.7: <text>名九七弦</text> → <jzp>名九七弦</jzp></li>
    </ul>
    <p><small>{_links(version)}</small></p>
    </div>
"""


def release_body(version: str, current: str) -> str:
    """The release notes: each change drawn in the released font beside the next one."""
    hui = [("名九半轮六", "9.5", "轮", "6"), ("名九，半轮六", "9", "半轮", "6"), ("名九徽半轮六", "9", "半轮", "6"),
           ("名九半勾六", "9.5", "勾", "6"), ("名九徽半勾六", "9.5", "勾", "6"), ("名十二勾五", "12", "勾", "5"),
           ("名十二徽勾五", "12", "勾", "5"), ("名十徽勾五", "10", "勾", "5"), ("名十徽二勾五", "10.2", "勾", "5"),
           ("名十徽二分勾五", "10.2", "勾", "5"), ("名十点二勾五", "10.2", "勾", "5"), ("名七六挑五", "7.6", "挑", "5"),
           ("名七徽六挑五", "7.6", "挑", "5")]
    xian = [("名九七", "hui 9.7"), ("名九七弦", "hui 9, string 7"), ("名九徽七弦", "hui 9, string 7"),
            ("撥大九四六弦|散五", "撥: thumb, hui 9.4, string 6 | open string 5"),
            ("撥大九四弦|散五", "撥: thumb, hui 9, string 4 | open string 5"),
            ("撮名七徽五弦|二", "撮: hui 7, string 5 | string 2")]
    t = lambda head, rows: _table(head, rows, current, version)
    return f"""  <div class="container whats-new">
    <p><a href="./">← The JianZiPu font</a> · <a href="./vnext.html">The font page once {version} is out</a></p>
    <h1>JianZiPu {version}</h1>
    <p class="vnext-banner"><small>Coming in the next release: not in the download yet. Each example is drawn in v{current} (grey, the font you can download now) and in v{version}.
      {_links(version).replace(f'<a href="./release-{version}.html">Release notes for {version}</a> · ', '')}</small></p>
    <h3 id="hui">Hui numbers in Chinese</h3>
    <ul>
      <li><strong>十一, 十二 and 十三 are always hui 11, 12 and 13.</strong> 10.2 is written <text>十徽二</text>, <text>十徽二分</text> or <text>十点二</text>. 十四 to 十九 and 十半 are still 10.4 to 10.9 and 10.5.</li>
      <li><strong>徽 is a decimal point, as 点 is:</strong> <text>十徽二</text> is 10.2 and <text>七徽六</text> is 7.6. 分 may close the decimal (<text>十徽二分</text>). 徽 with nothing after it closes the number: <text>十徽</text> is 10.</li>
      <li><strong>徽 before a 半 that starts a word ends the number</strong>, as a comma does: <text>名九徽半轮六</text> is 9, then 半轮. Without 徽, 9.5 comes first: <text>名九半轮六</text> is 9.5, then 轮.</li>
    </ul>
{t(["Hui", "Right hand", "String"], hui)}
    <h3 id="xian">弦 marks a string</h3>
    <p>弦 (or 絃) after a number marks it as a string, and keeps it from joining the number before it, whatever point comes first (<text>名九徽七弦</text> is 9, string 7).
      In a chord it closes the first half before the bar: <text>撥大九四六弦|散五</text> is 撥 with the thumb at hui 9.4 on string 6, and the open string 5, the same as <text>Bv9.4,6|05</text>.</p>
{t(["Reads as"], xian)}
  </div>
"""


def _once(page: str, old: str, new: str, what: str) -> str:
    n = page.count(old)
    if n != 1:
        raise ValueError(f"site/index.html: {what} is there {n} times, not once: update CHANGES in "
                         f"builder/jzpbuild/vnext.py to match the page ({old[:60]!r}…)")
    return page.replace(old, new)


def render(index: str, version: str | None = None) -> str:
    """vnext.html from index.html's text."""
    version = version or next_version()
    page = index
    page = _once(page, '<meta name="viewport" content="width=device-width, initial-scale=1">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                 f'  <!-- written by `cd builder && python3 -m jzpbuild.vnext` from index.html: edit those, not this -->\n'
                 '  <meta name="robots" content="noindex">', "the viewport meta")
    page = re.sub(r"<title>[^<]*</title>", f"<title>JianZiPu Font {version} (preview)</title>", page, count=1)
    page = _once(page, "src: url('./JianZiPu.ttf');", "src: url('./JianZiPu-vnext.ttf');", "the font's @font-face src")
    page = _once(page, "  </style>", HEAD + "  </style>", "the end of the page's style")
    current = current_version()
    banner = (f'<p class="vnext-banner"><small>A preview of this page once JianZiPu {version} is out, its notation drawn in a '
              f'preview build of {version}. <a href="#whats-new">What\'s new in {version}</a> · '
              f'<a href="./release-{version}.html">Release notes</a> · <a href="./">The page for v{current}</a>. '
              f'The download is still v{current}.</small></p>')
    page = re.sub(r'<p class="vnext-link">.*?</p>', lambda _: banner, page, count=1, flags=re.S)
    if banner not in page:
        raise ValueError("site/index.html: the coming-next link at the top (<p class=\"vnext-link\">) isn't there")
    page = _once(page, '<a href="#how-to-type">How to type</a>',
                 f'<a href="#whats-new">What\'s new in {version}</a>\n        <a href="#how-to-type">How to type</a>', "the contents link to How to type")
    page = _once(page, '<h3 id="how-to-type">', whats_new(version).lstrip() + '\n    <h3 id="how-to-type">', "the How to type title")
    for old, new in CHANGES:
        page = _once(page, old, new, "a lesson the next release changes")
    # the glossary as the next font reads it: no colon where it sets the word vertically by itself
    return glossary.render(page, vertical_only=glossary.vertical_only_for())


def release_page(index: str, version: str | None = None) -> str:
    """release-<next>.html: the release notes, in the font page's look (its <head> from index.html)."""
    version = version or next_version()
    head = index[index.index("<head>"):index.index("</head>") + len("</head>")]
    head = _once(head, '<meta name="viewport" content="width=device-width, initial-scale=1">',
                 '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                 '  <!-- written by `cd builder && python3 -m jzpbuild.vnext` from index.html and vnext.py: edit those, not this -->\n'
                 '  <meta name="robots" content="noindex">', "the viewport meta")
    head = re.sub(r"<title>[^<]*</title>", f"<title>JianZiPu {version} release notes</title>", head, count=1)
    head = _once(head, "src: url('./JianZiPu.ttf');", "src: url('./JianZiPu-vnext.ttf');", "the font's @font-face src")
    head = _once(head, "  </style>", HEAD + "  </style>", "the end of the page's style")
    return (f'<!DOCTYPE html>\n<html lang="en">\n{head}\n<body>\n  <div class="scroll-rod"></div>\n'
            f"{release_body(version, current_version())}"
            '  <div class="scroll-rod bottom"></div>\n'
            '  <script>document.fonts.ready.then(() => document.documentElement.classList.remove("fonts-loading"));</script>\n'
            "</body>\n</html>\n")


def build_font() -> None:
    subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(VNEXT_FONT), "--fea-out", ""], cwd=config.BUILDER_DIR, check=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jzpbuild.vnext", description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="change nothing; exit 1 if site/vnext.html is out of date")
    ap.add_argument("--font", action="store_true", help="also rebuild site/JianZiPu-vnext.ttf (needs the base font)")
    args = ap.parse_args(argv)
    version = next_version()
    try:
        index = config.SITE_INDEX.read_text(encoding="utf-8")
        pages = {VNEXT: render(index, version), release_path(version): release_page(index, version)}
    except (ValueError, glossary.GlossaryError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    stale = [p for p, text in pages.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if args.check:
        for p in stale:
            print(f"error: site/{p.name} is out of date: run `cd builder && python3 -m jzpbuild.vnext`.", file=sys.stderr)
        if not stale:
            print("site/vnext.html and its release notes are up to date")
        return 1 if stale else 0
    if args.font:
        build_font()
    for p in stale:
        p.write_text(pages[p], encoding="utf-8")
        print(f"wrote site/{p.name}")
    if not stale:
        print("site/vnext.html and its release notes are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
