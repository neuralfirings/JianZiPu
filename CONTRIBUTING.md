# Contributing to JianZiPu

Thank you for helping with the JianZiPu font. There are three ways to help,
depending on what you'd like to change.

## Report a problem or suggest something

Open an [issue](https://github.com/neuralfirings/JianZiPu/issues). Include:

- what you typed;
- what you expected;
- what you got (a screenshot helps);
- the font version (on [jianzipufont.com](https://jianzipufont.com), or in
  your font manager's details for JianZiPu).

## Improve the font itself

Glyphs, spellings and spacing are designed in the JZP Font Builder, and you
don't need git for any of it. Ask for an invite on
[builder.jianzipufont.com](https://builder.jianzipufont.com). There you work
in your own draft and send your changes as a **Change Request**. The
maintainer reviews each change, and kept changes go into the next release
with your name in the release notes. The Builder's Help page explains each
step.

## Change the code

The Builder app (`app/`), the build pipeline and web server (`builder/`), the
font page (`site/`) and the Supabase parts (`supabase/`) take ordinary pull
requests.

1. Branch from `main`.
2. Make your change. `README.md` and `builder/README.md` explain how to
   set up and run everything.
3. Run both test suites: `cd app && npm test` and
   `cd builder && python3 -m pytest tests`.
4. Open a pull request against `main`.

A code branch must not change font files: `builder/inputs/`,
`builder/VERSION`, `CHANGELOG.md`, `site/JianZiPu.ttf` and
`site/version.json`. Those change only through a release, and the `scope`
check on every pull request enforces this. If your change really must touch
them (say, converting `design.json` to a new format), say so in the pull
request and a maintainer will add the `font-files` label.

## Licences

By contributing, you agree that your contribution is licensed like the part
of the repository it goes into:

- the font and its sources under the SIL Open Font License 1.1
  ([OFL.txt](OFL.txt));
- the code under the GNU GPL v3 ([LICENSE](LICENSE)).

`README.md` lists which files are which.

## Maintainers

Reviewing Change Requests, making releases and the one-time service setup
are in [docs/maintainers/](docs/maintainers/README.md).
