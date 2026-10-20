"""Font releases: a release candidate on its own branch, then the release (CHANGELOG.md "Releases"
in builder/README.md). The local Builder's Release screen calls these through the web server; the
command line does the same:

    python3 -m jzpbuild.release status
    python3 -m jzpbuild.release start 3.200                    # branch release/3.200 from origin/main
    python3 -m jzpbuild.release candidate --notes notes.md     # commit, build, tag v3.200-rc.N, push
    python3 -m jzpbuild.release publish                        # after the release PR is merged: tag v3.200
    python3 -m jzpbuild.release scope --base origin/main --head HEAD --branch <name>   # CI check
    python3 -m jzpbuild.release notes v3.200-rc.1    # CI: check the tag matches the files, print its notes

A release branch carries only font files (FONT_PATHS); Builder code goes to main on its own
branches. `scope` checks both directions, here and in CI (.github/workflows/scope.yml).
Stdlib and the git command line only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config

REPO = config.BUILDER_DIR.parent
PREFIX = "release/"
# What a release changes, and the only paths a release branch may touch (repo-relative; a trailing
# slash is a folder). Code branches may touch none of them.
FONT_PATHS = ("builder/inputs/", "builder/VERSION", "CHANGELOG.md", "site/JianZiPu.ttf", "site/version.json")
# also allowed on a release branch (the classic-positioning golden, if a release refreshes it)
RELEASE_EXTRA = ("builder/tests/JianZiPu.ttf",)
VERSION_RE = re.compile(r"\d+\.\d{3}")


class ReleaseError(Exception):
    """A step that can't go ahead, in words for the Release screen."""


Log = Callable[[str], None]


def git(*args: str, repo: Path = REPO, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def _under(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == p or (p.endswith("/") and path.startswith(p)) for p in prefixes)


def scope(files: list[str], branch: str) -> list[str]:
    """The files a branch may not change: anything but font files on a release branch, and any
    font file on every other branch."""
    if branch.startswith(PREFIX):
        return [f for f in files if not _under(f, FONT_PATHS + RELEASE_EXTRA)]
    return [f for f in files if _under(f, FONT_PATHS)]


def parse_version(v: str) -> tuple[int, int]:
    if not VERSION_RE.fullmatch(v or ""):
        raise ReleaseError(f"A version looks like 3.200 (major, then a three-digit minor), not {v!r}.")
    major, minor = v.split(".")
    return int(major), int(minor)


def github_slug(repo: Path = REPO) -> str:
    """owner/name of the origin remote, from any of its URL forms."""
    url = git("remote", "get-url", "origin", repo=repo)
    m = re.search(r"[/:]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        raise ReleaseError(f"can't tell the GitHub repository from {url}")
    return f"{m.group(1)}/{m.group(2)}"


def dirty_files(repo: Path = REPO) -> list[str]:
    """Files with changes not committed yet (new ones included)."""
    r = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], cwd=repo, capture_output=True, text=True)
    if r.returncode != 0:
        raise ReleaseError(f"git status: {r.stderr.strip()}")
    out, parts = [], r.stdout.split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        if len(entry) > 3:
            out.append(entry[3:])
            if entry[0] in "RC":          # a rename: the old path follows
                i += 1
        i += 1
    return out


def current_branch(repo: Path = REPO) -> str:
    return git("rev-parse", "--abbrev-ref", "HEAD", repo=repo)


def rc_tags(version: str, repo: Path = REPO) -> list[str]:
    tags = git("tag", "--list", f"v{version}-rc.*", repo=repo).split()
    return sorted(tags, key=lambda t: int(t.rsplit(".", 1)[-1]) if t.rsplit(".", 1)[-1].isdigit() else 0)


def status(repo: Path = REPO) -> dict:
    """Where things stand, without touching the network."""
    branch = current_branch(repo)
    version = (repo / "builder" / "VERSION").read_text().strip() if (repo / "builder" / "VERSION").exists() else None
    release = branch[len(PREFIX):] if branch.startswith(PREFIX) else None
    tags = git("tag", "--list", "v*", "--sort=-creatordate", repo=repo).split()[:8]
    out = {"branch": branch, "release": release, "version": version, "dirty": dirty_files(repo), "tags": tags,
           "candidates": rc_tags(release, repo) if release else [], "repo": None}
    try:
        out["repo"] = github_slug(repo)
    except ReleaseError:
        pass
    return out


def start(version: str, repo: Path = REPO, log: Log = print) -> dict:
    """A release branch for `version`, from main as it is on GitHub now."""
    want = parse_version(version)
    if dirty_files(repo):
        raise ReleaseError("Save or put aside your changes first: a release starts from a clean copy of main.")
    log("fetching main from GitHub ...")
    git("fetch", "origin", "main", "--tags", repo=repo)
    have = git("show", "origin/main:builder/VERSION", repo=repo, check=False).strip() or "0.000"
    if want <= parse_version(have):
        raise ReleaseError(f"The font on main is already version {have}; a new release needs a higher number.")
    branch = f"{PREFIX}{version}"
    if git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", repo=repo, check=False):
        raise ReleaseError(f"The branch {branch} already exists. Switch to it to carry on with that release.")
    if git("tag", "--list", f"v{version}", repo=repo):
        raise ReleaseError(f"v{version} has already been released.")
    git("switch", "-c", branch, "origin/main", repo=repo)
    log(f"started {branch} from origin/main ({git('rev-parse', '--short', 'HEAD', repo=repo)})")
    return {"branch": branch}


def _check_scope(repo: Path, branch: str):
    committed = git("diff", "--name-only", "origin/main...HEAD", repo=repo).splitlines()
    bad = scope(sorted(set(committed + dirty_files(repo))), branch)
    if bad:
        raise ReleaseError("A release branch carries only font files, and these aren't: "
                           + ", ".join(bad[:8]) + (" …" if len(bad) > 8 else "")
                           + ". Builder code goes to main on its own branch.")


def changelog_with(text: str, version: str, notes: str, date: str) -> str:
    """CHANGELOG.md with the section for `version` written (replaced if it is there already) under
    the title and any Unreleased section."""
    head = f"## [{version}] - {date}"
    body = notes.strip()
    section = f"{head}\n\n{body}\n" if body else f"{head}\n"
    lines = text.splitlines(keepends=True)
    out, i, done = [], 0, False
    while i < len(lines):
        if re.match(rf"## \[{re.escape(version)}\]", lines[i]):
            out.append(section + "\n")
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            done = True
            continue
        out.append(lines[i])
        i += 1
    if done:
        return "".join(out)
    # first version heading that isn't Unreleased: the new section goes just above it
    for j, line in enumerate(out):
        if line.startswith("## ") and not line.lower().startswith("## [unreleased]"):
            return "".join(out[:j]) + section + "\n" + "".join(out[j:])
    return "".join(out).rstrip("\n") + "\n\n" + section


def build_release_font(out: Path, source_commit: str, log: Log = print):
    log(f"building the font ({source_commit}) ...")
    r = subprocess.run([sys.executable, "-m", "jzpbuild", "-o", str(out), "--fea-out", "", "--source-commit", source_commit],
                       cwd=config.BUILDER_DIR, capture_output=True, text=True)
    for line in (r.stdout + r.stderr).splitlines()[-6:]:
        log("  " + line)
    if r.returncode != 0:
        raise ReleaseError("The font did not build; see the log.")


def run_tests(log: Log = print):
    log("running the builder tests ...")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=config.BUILDER_DIR, capture_output=True, text=True)
    log("  " + ((r.stdout.strip().splitlines() or [""])[-1]))
    if r.returncode != 0:
        raise ReleaseError("The builder tests failed; fix them before building a candidate.")


def candidate(notes: str, message: str = "", repo: Path = REPO, log: Log = print, push: bool = True,
              build: Callable[[Path, str, Log], None] = build_release_font, tests: Callable[[Log], None] = run_tests,
              today: str | None = None) -> dict:
    """Commit the design on the release branch, build the font into site/, write the version and
    the changelog, and tag the next release candidate."""
    branch = current_branch(repo)
    if not branch.startswith(PREFIX):
        raise ReleaseError(f"Start a release first: you're on {branch}, not a {PREFIX}… branch.")
    version = branch[len(PREFIX):]
    parse_version(version)
    _check_scope(repo, branch)
    tests(log)
    git("add", "--", "builder/inputs", repo=repo)
    if git("diff", "--cached", "--name-only", repo=repo):
        git("commit", "-m", message.strip() or f"{version}: design changes for the release", repo=repo)
        log("committed the design")
    source = git("rev-parse", "--short", "HEAD", repo=repo)
    (repo / "builder" / "VERSION").write_text(version + "\n")
    build(repo / "site" / "JianZiPu.ttf", source, log)
    date = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = github_slug(repo)
    (repo / "site" / "version.json").write_text(json.dumps(
        {"version": version, "date": date, "notes_url": f"https://github.com/{slug}/releases/tag/v{version}"}, indent=2) + "\n")
    cl = repo / "CHANGELOG.md"
    cl.write_text(changelog_with(cl.read_text() if cl.exists() else "# Changelog\n", version, notes, date))
    n = len(rc_tags(version, repo)) + 1
    tag = f"v{version}-rc.{n}"
    git("add", "--", "builder/VERSION", "site/JianZiPu.ttf", "site/version.json", "CHANGELOG.md", repo=repo)
    git("commit", "-m", f"{tag}: JianZiPu {version}, release candidate {n}", repo=repo)
    git("tag", "-a", tag, "-m", f"JianZiPu {version}, release candidate {n}", repo=repo)
    log(f"tagged {tag}")
    if push:
        log("pushing to GitHub ...")
        git("push", "-u", "origin", branch, repo=repo)
        git("push", "origin", tag, repo=repo)
    return {"tag": tag, "version": version, "branch": branch,
            "pr_url": f"https://github.com/{slug}/compare/main...{branch}?expand=1",
            "release_url": f"https://github.com/{slug}/releases/tag/{tag}"}


def publish(version: str | None = None, repo: Path = REPO, log: Log = print, push: bool = True) -> dict:
    """After the release PR is merged: tag main as the release (the tag's workflow publishes it)."""
    branch = current_branch(repo)
    version = version or (branch[len(PREFIX):] if branch.startswith(PREFIX) else None)
    if not version:
        raise ReleaseError("Which release? Switch to its release branch, or name the version.")
    parse_version(version)
    log("fetching main from GitHub ...")
    git("fetch", "origin", "main", "--tags", repo=repo)
    if git("tag", "--list", f"v{version}", repo=repo):
        raise ReleaseError(f"v{version} is already released.")
    cands = rc_tags(version, repo)
    if not cands:
        raise ReleaseError(f"There is no release candidate for {version} yet. Build one first.")
    last = cands[-1]
    merged = subprocess.run(["git", "merge-base", "--is-ancestor", last, "origin/main"], cwd=repo).returncode == 0
    if not merged:
        raise ReleaseError(f"{last} isn't on main yet: merge the release pull request on GitHub first.")
    moved = git("diff", "--name-only", last, "origin/main", "--", *FONT_PATHS, repo=repo)
    if moved:
        raise ReleaseError(f"Font files changed on main after {last} ({', '.join(moved.splitlines()[:4])}). "
                           "Build a new candidate so the release is exactly what testers tried.")
    tag = f"v{version}"
    git("tag", "-a", tag, "origin/main", "-m", f"JianZiPu {version}", repo=repo)
    log(f"tagged {tag} on main")
    if push:
        git("push", "origin", tag, repo=repo)
        log("pushed: GitHub publishes the release")
    if not dirty_files(repo):
        git("switch", "main", repo=repo)
        git("merge", "--ff-only", "origin/main", repo=repo, check=False)
    slug = github_slug(repo)
    return {"tag": tag, "version": version, "release_url": f"https://github.com/{slug}/releases/tag/{tag}"}


def changelog_section(text: str, version: str) -> str:
    """The body of one version's CHANGELOG section (empty if there is none)."""
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def tag_notes(tag: str, repo: Path = REPO) -> str:
    """For the release workflow: refuse a tag that doesn't match the version in the files it
    points at, and return the release notes (its CHANGELOG section)."""
    m = re.fullmatch(r"v(\d+\.\d{3})(-rc\.\d+)?", tag)
    if not m:
        raise ReleaseError(f"{tag} isn't a release tag (v3.200 or v3.200-rc.1)")
    version = m.group(1)
    have = (repo / "builder" / "VERSION").read_text().strip()
    site = json.loads((repo / "site" / "version.json").read_text()).get("version") if (repo / "site" / "version.json").exists() else None
    if have != version or site != version:
        raise ReleaseError(f"{tag} points at files for version {have} (site/version.json: {site}); build the release with the Release screen")
    cl = repo / "CHANGELOG.md"
    body = changelog_section(cl.read_text(), version) if cl.exists() else ""
    pre = "This is a release candidate: a test version of the next font. " if m.group(2) else ""
    return f"{pre}{body}\n\nDownload JianZiPu.ttf below, or from https://jianzipufont.com.".strip() + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jzpbuild.release", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("start")
    p.add_argument("version")
    p = sub.add_parser("candidate")
    p.add_argument("--notes", type=str, default=None, help="a Markdown file with this version's changelog entry")
    p.add_argument("--message", type=str, default="", help="commit message for the design changes")
    p.add_argument("--no-push", action="store_true")
    p = sub.add_parser("publish")
    p.add_argument("version", nargs="?")
    p.add_argument("--no-push", action="store_true")
    p = sub.add_parser("notes", help="check a tag against the files and print its release notes (CI)")
    p.add_argument("tag")
    p = sub.add_parser("scope", help="list files this branch may not change (CI)")
    p.add_argument("--base", default="origin/main")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--branch", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "status":
            print(json.dumps(status(), indent=2))
        elif args.cmd == "start":
            start(args.version)
        elif args.cmd == "candidate":
            notes = Path(args.notes).read_text() if args.notes else ""
            print(json.dumps(candidate(notes, args.message, push=not args.no_push), indent=2))
        elif args.cmd == "publish":
            print(json.dumps(publish(args.version, push=not args.no_push), indent=2))
        elif args.cmd == "notes":
            sys.stdout.write(tag_notes(args.tag))
        elif args.cmd == "scope":
            files = git("diff", "--name-only", f"{args.base}...{args.head}").splitlines()
            bad = scope(files, args.branch)
            kind = "a release branch may change only font files" if args.branch.startswith(PREFIX) else \
                "font files change only through a release branch (release/<version>)"
            for f in bad:
                print(f"::error file={f}::{kind}")
            print(f"{len(files)} files changed; {len(bad)} outside scope ({kind}).")
            return 1 if bad else 0
    except ReleaseError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
