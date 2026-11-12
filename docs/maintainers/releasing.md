# Releasing the font

How a new version of JianZiPu goes from kept Change Requests to a font people
download. Everything here runs from the **local** Builder's Release screen
(`/release`) on the maintainer's computer. The online Builder can't make a
release.

The first release made this way was 3.200 (October 2026). Its pull request,
https://github.com/neuralfirings/JianZiPu/pull/48, is a good example of what
one looks like.

## The short version

1. On Review, decide on the Change Requests (see [reviewing.md](reviewing.md)).
2. Release → **Start release** `3.300`.
3. **Add kept changes**, check them in Layouts and Build & test, then **Save**.
4. **Build candidate**. This tags `v3.300-rc.1` and GitHub publishes a pre-release.
5. Open the pull request, test the candidate, and build `rc.2` and so on if
   something needs fixing.
6. Merge the pull request with **Create a merge commit**, not squash or rebase.
7. Release → **Publish**. This tags `v3.300` and GitHub publishes the release.

## Before you start

- You need a one-time setup: see [setup.md](setup.md), "Your computer".
- Start the local Builder (`cd builder && python3 -m jzpbuild.webserver`) and
  open http://127.0.0.1:5713/release.
- Sign in as the admin on Review. Without signing in, the Release screen can't
  see the Change Requests, and **Build candidate** and **Publish** stay greyed
  out.
- Your copy must be clean, with no uncommitted changes. Commit or stash them
  first.

## Step by step

### 1. Start a release candidate

Type the version (the screen suggests the next one; see
[Versions](#versions)) and choose **Start release**. The Builder fetches main
from GitHub and creates the branch `release/<version>` from `origin/main`. You
are now working on that branch, and the Builder's files are main's files.

A release branch holds **only font files**:

- `builder/inputs/`
- `builder/VERSION`
- `CHANGELOG.md` (open to code branches too, for the Unreleased lines)
- `site/JianZiPu.ttf`
- `site/version.json`
- `builder/tests/JianZiPu.ttf`

Builder code goes to main on its own branch (see [Scope rules](#scope-rules)).

### 2. Bring in the kept changes

**Add kept changes** applies every kept change from the requests that are In
review, oldest request first, as unsaved changes. When two requests change the
same thing, the screen opens the later one so you can pick which version wins.

Only kept changes come in. Skipped ones stay in the tester's draft.

### 3. Check and adjust

Look the result over in Layouts (the word strip) and in Build & test (build a
font and type in it). Fix anything you like here: you are the last reviewer.
Then **Save**, which writes `builder/inputs/`.

### 4. Build the candidate

The changelog entry is filled in from the lines code changes queued under
`## [Unreleased]` in `CHANGELOG.md` (see [A fix that doesn't come from a Change
Request](#a-fix-that-doesnt-come-from-a-change-request)), then the requests'
titles and credits ("thanks to Mei Chen"). A second candidate starts from the
first one's entry. Edit it before you build. It becomes the `CHANGELOG.md` section
and the GitHub release notes. Use the Keep a Changelog headings: `### Added`,
`### Changed`, `### Fixed`, `### Removed`.

**Build candidate** then does this:

1. Checks the branch carries only font files.
2. Rewrites the glossary tables on the font page (`site/index.html`) from
   `components.csv` (`python3 -m jzpbuild.glossary`), so a new or changed
   spelling shows there. See [The glossary](#the-glossary).
3. Runs the builder tests (`cd builder && python3 -m pytest tests`). If they
   fail, it stops and the log shows which test failed and why; see
   [Troubleshooting](#troubleshooting).
4. Commits `builder/inputs/` and the page as "3.300: changes from N Change Requests".
5. Writes `builder/VERSION` and builds the font into `site/JianZiPu.ttf`, with
   name ID 5 "Version 3.300; git-<that commit>" and `head.fontRevision` 3.3.
6. Writes `site/version.json` and the `CHANGELOG.md` entry (and empties
   `## [Unreleased]`: its lines are in the entry now), then commits them
   as "v3.300-rc.1: JianZiPu 3.300, release candidate 1".
7. Tags `v3.300-rc.1`, and pushes the branch and the tag.
8. Marks the requests as In a release candidate, which emails their authors.

So every candidate is **two commits**: the design, then the built font. The
font records the hash of the design commit it was built from, and that hash
only exists once the design is committed.

Pushing the tag starts `.github/workflows/release.yml`. It checks that the tag
matches `builder/VERSION` and `site/version.json`, then publishes a GitHub
**pre-release** with `JianZiPu.ttf` attached and the changelog entry as notes.
CI can't build the font, because the TW-Kai base font isn't in the repository.
It attaches the font committed at the tag.

### 5. Open the pull request and test the candidate

The screen links to the pull request ("compare main…release/3.300"). Its checks
must pass: `scope`, `app`, `builder`, `emails`. The diff should touch only the
font files listed above.

Ways to try the candidate:

- **The pre-release.** Download `JianZiPu.ttf` from the
  [releases page](https://github.com/neuralfirings/JianZiPu/releases), install
  it (Font Book on a Mac) and type in a real document. Uninstall the old version
  first, since both have the same name.
- **Build & test** in the Builder: "Test the font file" → open a local file →
  `site/JianZiPu.ttf`. Compare it with a second font, such as the last release.
- **The website.** Run `cd site && python3 -m http.server 8000` and open
  http://localhost:8000. Opening `index.html` straight from disk can't load
  `version.json`.
- **Testers.** Send them the pre-release link. Pre-releases never show as the
  "latest" release, so nobody gets one by accident.

To fix a problem, stay on the release branch and fix it in the Builder, then
**Save** and **Build candidate** again. That makes `rc.2`, another pre-release,
and updates the same pull request.

### 6. Merge the pull request

On GitHub, merge with **Create a merge commit**. Squash and rebase rewrite the
commits, so the candidate's tag would no longer be on main, and Publish would
refuse to go ahead.

Merging doesn't make the GitHub release, but main now has the new files:

- Cloudflare redeploys jianzipufont.com from main, so the site starts serving
  the new `site/JianZiPu.ttf` at this point.
- Railway redeploys the hosted Builder from main.

Publish right after merging. The site's "Release notes" link points at the
`v3.300` release, which doesn't exist until you publish.

### 7. Publish

Go back to the Release screen while still on `release/3.300`, and choose
**Publish v3.300**. It does this:

1. Checks that the last candidate's tag is on main, and that no font file
   changed on main after it. The release is exactly the candidate testers tried.
2. Tags main as `v3.300` and pushes the tag. The workflow then publishes the
   GitHub release as **latest**, with the font attached.
3. Marks the requests Released, which emails their authors.
4. Switches your copy back to `main` and pulls.

After that:

- https://github.com/neuralfirings/JianZiPu/releases/latest/download/JianZiPu.ttf
  always serves the newest font.
- The EmailOctopus download email links to
  `https://jianzipufont.com/JianZiPu.ttf`, which is also the newest.
- In the hosted Builder (redeployed at the merge), testers see "JianZiPu
  3.300 is out" and choose **Set reference font to 3.300 (latest)…**, which
  drops their released changes out of Your changes.

You can delete the `release/3.300` branch on GitHub. The tags keep its history.

## Versions

A version is `MAJOR.MINOR`, and the minor part always has three digits: 3.100,
3.200, 3.201. Fonts store their version as a number (`head.fontRevision`), so
3.10 would equal 3.1. The three digits keep the numbers in order.

| Change | Example | Next version |
| --- | --- | --- |
| New glyphs, spellings, spacing, layout fixes | the usual release | 3.200 → 3.300 |
| A small fix to the last release, nothing new | a wrong gap | 3.300 → 3.301 |
| Existing documents would look different or break: PUA codepoints move, a spelling is removed or changes meaning | | 3.x → 4.000 |

This is semantic versioning adapted to fonts. The "patch" and "minor" levels
share the three-digit part.

The version lives in `builder/VERSION`, and only a release changes it.
`CHANGELOG.md` lists every version. Tags: `v3.300-rc.1` for a candidate and
`v3.300` for the release.

## A fix that doesn't come from a Change Request

- **A font fix** (the design, a glyph, a spelling): start a release, for
  example 3.301. Make the change in the local Builder on the release branch,
  **Save**, and build a candidate. Font files never change on main any other
  way.
- **A Builder code fix**: an ordinary branch and pull request to main. It
  doesn't need a release. Railway deploys it when it merges.
- **A code change that changes the font the Builder builds** (a new
  substitution rule, say): an ordinary pull request to main that also adds a
  line under `## [Unreleased]` in `CHANGELOG.md`. Every build from then on has
  it: Build & test lists the queued lines ("Builds include changes that aren't
  in the released font 3.200 yet"), and a font built outside a release says
  "dev build, not a release" in its version. It goes out with the next
  release, whose changelog entry starts from those lines.

## Scope rules

`jzpbuild/release.py` `FONT_PATHS` is the one list of font files:

- A `release/*` branch may change only those files (plus the shaping golden
  `builder/tests/JianZiPu.ttf`, `CHANGELOG.md`, and `site/index.html` when
  only its generated glossary tables changed).
- Every other branch may change none of them.
- `CHANGELOG.md` (`SHARED_PATHS`) is open to both: a release writes its
  section, and a code change that alters the built font queues a line under
  `## [Unreleased]`.

**Build candidate** checks this, and so does `.github/workflows/scope.yml` on
every pull request.

Some code changes must also touch font files on purpose, such as a
`design.json` format change that converts the file. For those, an admin adds
the label **`font-files`** to the pull request, and the check lets it through.

The ruleset on main (see [setup.md](setup.md)) makes `scope` a required check,
so the rule holds without anyone having to remember it.

## The glossary

The glossary on the font page ("6. Glossary") is made from `site/glossary.json`
and the spellings in `components.csv`, so its spellings are the font's:

- `site/glossary.json` holds the whole glossary: its section titles (`groups`:
  "1: Left Hand", a short `nav` name for the page's contents, a description, and
  its subtitles in order) and its subtitles (`sections`, by id, `1c`), each with
  its title, a description, how its table looks (an example word per row,
  `0{}5` / `散{}五` with `{}` the glyph, or a vertical table) and its **rows in
  page order**. A row is a glyph (`{"glyph": "lg_gou"}`) or a word written
  together (`{"word": "带起", "glyphs": ["md_dai", "md_qi"]}`), with an optional
  `"meaning"` for the Definition column (a section gets that column once one of
  its rows has one).
- A section with an example word per row (`"kind": "usage"`) has its example
  as `"usage": [ASCII, 中文]`, with `{}` where the row's glyph goes; a row's own
  `"usage"` replaces it for that row (the Builder's Input column, where you type
  the example in one language and the other is made from the spellings). A row
  of a vertical section can have one too: its Output then shows that example
  (`[":vxi7", ":大息七"]`) in place of the row typed on its own.
- `"typed"` keeps what was typed to add or edit a row (`:shaoxi`, `勾`); the
  Builder shows it again when the row is edited. A row without one opens with
  its ASCII spelling, or its Chinese when it has none.
- The rows are edited in the Builder's Glyphs → **Glossary**: drag a row to
  move it, + Add to put a glyph or a word in a section, a definition and (in a
  usage section) an example per row. The
  Builder writes the file one row per line, so a diff shows the rows that moved.
  It's a font file (`FONT_PATHS` in `jzpbuild/release.py`), so it changes through
  a release, or a pull request with the `font-files` label (a new section or a
  changed example template is such a change: add its `<!-- glossary <id> -->`
  marker to `site/index.html` in the same pull request).
- Every glyph with a spelling is in some section, on its own or in a word.
  `4: Uncategorized` is for a glyph that doesn't fit a section yet. A subtitle
  or a section title with `"hidden": true` (the Builder's eye switch) is left
  off the page, a section title with everything under it, and its glyphs count
  as left out on purpose, so the check doesn't report them (`99: Hidden in
  Glossary` is a subtitle switched off; the old `"kind": "hidden"` still reads
  as one).
  A word can go in any section: among example words it shows typed on its own
  after a colon, as in a vertical section.
- A Change Request carries the glossary a section at a time: Review keeps or
  skips a section whole, rows in the draft's order.
- A glyph only a vertical word can hold (上, 退…) gets its colon from the font,
  so the page writes its spellings without one, but only once `site/JianZiPu.ttf`
  does that (the generator types one such spelling with it to see). A
  candidate rewrites the glossary again after building the font, so the
  release that brings a change like that brings the page's new spellings too.
- `cd builder && python3 -m jzpbuild.glossary` rewrites the glossary between the
  `<!-- glossary all -->` markers in `site/index.html` (every section title,
  subtitle, description and table) and the contents links between
  `<!-- glossary nav -->`; the rest of the page stays as written. Descriptions
  are a little Markdown (`builder/jzpbuild/glossary.py` `markdown()`, the same
  as the Builder's preview): any HTML but the page's `<u>`, `<jzp>`, `<text>`,
  `<small>` and `<br>` is escaped.
- Each row shows every spelling: the ASCII ones (`fanyin, fy`) and the
  Chinese ones (simplified, then traditional when it differs: `绰, 綽`), with
  the example word typed each way.
- Each row has an ID, one count down the whole glossary (1a's rows are 1–5,
  1b's start at 6…), which links to the row (`jianzipufont.com/#12`). IDs go
  by position, so a row added anywhere renumbers the rows after it.

`builder/tests/test_glossary.py` fails when the page's tables are out of date,
when a glyph with a spelling has no row, or when an example anywhere on the
page (the lessons too) doesn't type what it shows. A new glyph in a release
needs a Glossary section before the candidate's tests pass.

## Doing it from the command line

The Release screen runs these commands. They work just as well in a terminal,
from `builder/`:

```bash
python3 -m jzpbuild.release status                  # branch, version, tags, candidates
python3 -m jzpbuild.release start 3.300
python3 -m jzpbuild.release candidate --notes notes.md --message "3.300: hui spacing"
python3 -m jzpbuild.release publish                 # after the merge
```

The command line doesn't change the requests' statuses; only the Release
screen does that, signed in. If you release from the terminal, set them from
the Release screen afterwards, or in Supabase (table `change_requests`, columns
`status` and `release`).

## Troubleshooting

**"The builder tests failed (test_shaping_matches_current_font)".**
`tests/test_shaping.py` types 78 sample inputs with HarfBuzz and compares the
glyphs and positions with the golden font `builder/tests/JianZiPu.ttf` (v3.1).
It builds with the legacy `--classic_pos` positioning, so it mostly guards
typing (which glyphs an input becomes). It also catches changes that reach the
classic path, such as the width of a control glyph. Each `DIFF for '…'` line
shows the golden's glyph and numbers against the new build's.

- If the difference is a mistake, fix it and build again.
- If it's intended, the golden can be replaced on the release branch.
  `builder/tests/JianZiPu.ttf` is allowed there. Do this only when every listed
  difference is intended, because the golden is what the test protects.

For example, 3.200 first failed because the chord divider `|` had become 1000
units wide where v3.1 had 500. Setting **Width of |** in Area Properties back
to 500 fixed it.

**Build candidate is greyed out.** It is greyed out in any of these cases:

- you're not on a `release/` branch;
- you're not signed in as the admin (Review → Sign in; your local
  `builder/.env` needs `SUPABASE_URL` and `SUPABASE_ANON_KEY`);
- kept changes are still waiting to be added.

**"Save or put aside your changes first".** Start needs a clean copy. Run
`git status`, then commit or `git stash` what's there.

**"v3.300-rc.N isn't on main yet".** Either the pull request isn't merged, or it
was squashed or rebased. If it was squashed, first check that main has exactly
the candidate's font files:

```bash
git diff v3.300-rc.N origin/main -- builder/inputs builder/VERSION CHANGELOG.md site/JianZiPu.ttf site/version.json
```

If that prints nothing, tag by hand:

```bash
git tag -a v3.300 origin/main -m "JianZiPu 3.300" && git push origin v3.300
```

Then mark the requests Released in Supabase. If it prints differences, build a
new candidate.

**The release pull request conflicts in `CHANGELOG.md`.** A code change queued
a line under Unreleased on main after the candidate emptied it. On the release
branch, run `git merge origin/main`, keep both the new version's section and
the new line under Unreleased (it goes out with the next release), commit and
push. Build a new candidate only if you want that change in this release.

**"Font files changed on main after …".** Something reached main outside the
release, through the `font-files` label or an admin bypass. On the release
branch, run `git merge origin/main`, check the result, and build a new
candidate.

**The `scope` check failed on a code pull request.** The branch touches a font
file. Move that change to a release, or add the `font-files` label if it's
meant to be there.

**The release workflow failed.** Look in GitHub → Actions → release. The notes
step refuses a tag whose files say a different version. After fixing it, delete
the tag (`git push origin :refs/tags/<tag>`, plus `git tag -d <tag>`) and build
or publish again.

**The Builder still shows the old design after a step.** The screen reloads the
design after each step. If it didn't, reload the page.

**Authors got no email.** Check the `notify` Edge Function's logs in Supabase,
and the webhook; see `supabase/functions/notify/README.md`.

## Where things live

| What | Where |
| --- | --- |
| The design (sources of truth) | `builder/inputs/` (`design.json`, `components.csv`, `svg/`) |
| The version | `builder/VERSION` |
| What each version changed | `CHANGELOG.md` |
| The released font (built, committed by each candidate) | `site/JianZiPu.ttf`, plus `site/version.json` for the website |
| The glossary on the font page | rows from `components.csv` (Glossary column), layout in `site/glossary.json`, written by `builder/jzpbuild/glossary.py` |
| Downloads of every version | [GitHub Releases](https://github.com/neuralfirings/JianZiPu/releases) |
| The release steps | `builder/jzpbuild/release.py`, the screen `app/src/routes/release/` |
| The tag workflow and the scope check | `.github/workflows/release.yml`, `.github/workflows/scope.yml` |
| Change Requests and their emails | `supabase/004_change_requests.sql`, `supabase/functions/notify/` |
