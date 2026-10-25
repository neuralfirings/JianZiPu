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
- `CHANGELOG.md`
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

The changelog entry is filled in from the requests' titles and credits ("thanks
to Mei Chen"). Edit it before you build. It becomes the `CHANGELOG.md` section
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
6. Writes `site/version.json` and the `CHANGELOG.md` entry, then commits them
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
- The MailerLite download email links to
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

## Scope rules

`jzpbuild/release.py` `FONT_PATHS` is the one list of font files:

- A `release/*` branch may change only those files (plus the shaping golden
  `builder/tests/JianZiPu.ttf`, and `site/index.html` when only its generated
  glossary tables changed).
- Every other branch may change none of them.

**Build candidate** checks this, and so does `.github/workflows/scope.yml` on
every pull request.

Some code changes must also touch font files on purpose, such as a
`design.json` format change that converts the file. For those, an admin adds
the label **`font-files`** to the pull request, and the check lets it through.

The ruleset on main (see [setup.md](setup.md)) makes `scope` a required check,
so the rule holds without anyone having to remember it.

## The glossary

The glossary on the font page ("6. Glossary") is made from `components.csv`,
so its spellings are the font's:

- A glyph's **Glossary** column (Glyphs → Typing) names the section(s) where
  it has a row of its own, by title: `1c: Left Hand Techniques`, or two
  separated by a semicolon (`1d: Special Cases; 3c: Related to String & Hui
  Number`). The cell offers the titles to pick from. Leave it empty for a
  glyph that only appears inside a word, such as 带 in :带起.
- The id before the colon is what the generator goes by, and the titles must
  match `site/glossary.json` (the test says which glyph doesn't). Renaming a
  section means changing its title in both places.
- `site/glossary.json` says how each section's table looks: the example word
  for each row (`0{}5` / `散{}五`, where `{}` is the glyph), the order of the
  rows, and words like :带起. Editing it is an ordinary site change on main.
- `cd builder && python3 -m jzpbuild.glossary` rewrites the tables between the
  `<!-- glossary 1a -->` markers in `site/index.html`. The headings and text
  around them stay as written.

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
