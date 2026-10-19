# Roadmap: the web editor becomes the only design path

Decided 2026-10-12. Wireframes: `docs/archive/lofi-wireframes.html` (9 frames).

## Decisions

| question | decision |
|---|---|
| Where are glyphs and layouts designed? | In the web app, by signed-in Calligraphers and Layout Managers. Figma is retired: its importer (`figma.py`, `--figma_pull`) was removed on 2026-10-18; the SVGs it fetched live on in `inputs/svg/`. |
| Layout model | `jzpbuild/positioning/` only (cursive-attachment GPOS from `inputs/design.json`). Classic `inputs/layouts.json` + `gpos.py` are legacy, reachable with `--classic_pos` for the parity report. (Decided 2026-10-15, replacing the earlier `dynamic_positioning` plan.) |
| Backend | GitHub + GitHub Actions + Supabase. Supabase: auth, roles, proposals, requests, comments. Each proposal is a GitHub branch written through a bot token (contributors never need GitHub accounts). Actions builds the font on proposal-branch push (preview) and on merge to main (release). No server to run. |
| First end-to-end slice | **Local-first Builder** (done 2026-10-15): the SvelteKit app in `app/` served by the Python web server, reading/writing repo files directly. Logins, proposals and hosting come later. |
| Front end | SvelteKit. |
| Roles | Calligrapher, Layout Manager, Requester (implicitly every signed-in user), Admin. One person can hold several. Roles are entry points, not separate logins. |
| Sign-up (2026-10-17) | Open: anyone can sign up and is a Requester. Contributor roles are granted by an admin. |
| Review (2026-10-17) | Every proposal goes through admin approval; there may be several admins later. No self-merge. |
| Repo visibility | Public (`neuralfirings/JianZiPu`): Actions minutes and preview hosting are free. |
| Hosting (2026-10-17, decided 2026-10-18) | A separate domain the owner has set aside, not guqintabs.com. Nothing on guqintabs.com depends on this repo's files (so `src-fontforge/demo/` could go). |
| Runtime (2026-10-17) | Stay on Python, no Node migration. The hosted app is static; positioning runs in the browser via Pyodide (the `positioning/` package is pure stdlib); the font builds in GitHub Actions; only the GitHub glue (commit to a proposal branch, open / merge the PR) is TypeScript, in Supabase Edge Functions. Typed-word preview needs harfbuzzjs in the browser instead of uharfbuzz. |
| Contributions and sequencing (2026-10-18) | Non-technical contributors (guqin players, calligraphers) both file requests and fulfil them. **GitHub Issues hold the requests** (labels for kind and state; the bot files them; "Fixes #n" links a proposal PR), replacing the Supabase requests/comments tables; Supabase keeps sign-in, roles, notifications (non-GitHub users get no GitHub mail) and request images (the API can't upload issue attachments). Use a GitHub App, not a personal token. **Order: ship the hosted Builder first to a few testers for feedback, then the request side**; "Claim this request → open a proposal" joins them last. |
| Pilot hosting (2026-10-18) | The first shared Builder runs today's Python webserver on **Railway** (where the owner's other services are), **read-only**, for a few invited testers on a separate domain. Testers sign in with a Supabase magic link (invite-only); each has a private **draft** in Supabase Storage (`drafts/<user id>/draft.json`). Nothing a tester does touches main. The owner merges drafts in the **local** Builder (Review screen, three-way merge per item) and commits as usual. The TW-Kai base font lives in a private Supabase `assets` bucket. The static + Pyodide setup stays the target for wide release, after the pilot feedback. |
| Draft bundle (2026-10-18) | One format for a tester's draft, Export / Import and the Review screen: `manifest.json` (format, based-on font version, author, deleted glyphs), whole `design.json` + `components.csv`, only the added/changed SVGs, and `base/` copies for the merge. Merge units: a glyph, a spelling cell, an area, a word type, the page center. Per-rule picks inside a word type are v2. A later proposal starts as a draft, so the words and the format carry over. |
| Proposal state machine | draft → submitted → in review → approved → merged. Reject returns to draft (work is kept). Build failure does not un-approve: the proposal stays approved with a failed-build badge and an admin can retry. |

## Answers to the wireframe's open questions

- **Is "vertical" a separate layout or a flag?** A separate `LAYOUTS` entry (`vert`), using repeated-slot areas (`char_1`, `char_2`, `left_1`, …). The dynamic model already supports this; classic's per-row `layout_vertjzpN` frames collapse into one topology.
- **Horizontal centering per layout or global?** Per layout: a `horizontal_center_order` key mirroring `vertical_center_order` (chords and single words center differently).
- **Overlapping gap conditions: first-match or error?** First-match, top to bottom, with a final "otherwise" (what `anchors.resolve_gap` does). The editor shows rows in evaluation order; an "otherwise" row is required whenever any condition exists.
- **Is the current role a mode or a label?** A mode: it changes the nav. The data is shared; the mode only decides which editor you land in.

## Phases

### Phase 0: pipeline prerequisite (done 2026-10-15)

`dynamic_positioning/` was replaced by `jzpbuild/positioning/`, a
cursive-attachment model proven first as a spike (`spike_cursive.py`,
2026-10-12: 266/266 words identical to the dynamic font on HarfBuzz and
CoreText) and then extended to every word type. The default build now
positions from `inputs/design.json`; `--classic_pos` keeps the old path.

Parity vs classic over the shaping corpus plus 150 generated words: 65
identical, 56 within 10 units, 51 within 40, 42 within 100, 16 larger. The
large ones are classic holes or quirks rather than regressions: `fy` above
`U5`'s x, `綽`/`quanfu3`/`banfu2`/`0.5` (character-only words classic never
positioned), one-row vertical words (`:v8` at 318 vs 125), li's string next
to a jc, and no-left words with fy+jc+right (classic's `*3` frames are not
centred at 300). Each is a design call to make in the Builder, not code.
The golden `tests/JianZiPu.ttf` is still classic; regenerate it once those
calls are made.

Open: 12 design-time warnings (no catch-all on `y right <- jc`, string_top/
bottom only for li, vertical hui without an absolute position) and 497
skipped shape/glyph combinations in `standard`, all from the migrated
classic gaps having no "otherwise" row — add them in the Spacing panel.

### Phase 1: Builder, local-first (done 2026-10-15)

`app/` (SvelteKit 2 + Svelte 5, static) served by `jzpbuild.webserver`:
Glyphs (grid, groups, unassigned, inspector, upload/edit as disabled
placeholders), Areas (members, box size, typing keys → `components.csv`),
Layouts (word types, canvas with draggable parts and rule arrows,
Structure/Spacing/Centering panels, glyph exceptions, Advanced structural
edits, live test strip, font budget), Test & Build (live preview vs built
font, sample sets, build log), Import/Export of `design.json`, undo/redo,
browser draft, Save with on-disk hash check. `docs/BUILDER-UX.md` is the
spec. Live resolve runs on the Python server (no Pyodide needed locally).

Next for this phase: per-item import ("pick per item"), a change list
with per-line revert, the "give X its own exception" toast on drag, and
regenerating the golden font.

### Phase 1a: hosted pilot (built 2026-10-18)

Spec: `docs/PILOT-UX.md` (wireframes `docs/pilot-ux.html`). Server: `webserver --hosted`
(`jzpbuild/hosted.py`): read-only, sign-in checked against Supabase, per-tester builds from
the draft, base font fetched from Storage. App: sign-in gate, "✎ Your draft" pill, Save and
30-second autosave to the draft, "saved somewhere else", offline buffer, font-updated banner
and Update my draft (merge.ts `fontUpdateItems`), Export/Import .zip, Discard, See my changes.
Local Builder: `/review` (testers' drafts with an admin sign-in, or a .zip) → Keep/Skip →
Apply as one undo step (glyph files wait for Save) → Save → Copy commit message.
Deploy: `Dockerfile`, `supabase/setup.sql`; steps in `font/README.md` "Hosted pilot".

### Phase 1b: hosted Layout Manager (later)

Supabase auth + roles, proposals as GitHub branches, Actions builds, the
proposal detail page — as in the original plan, on top of the local app.

### Phase 2: Calligrapher slice

- Glyph library (frame 3) over `inputs/svg/` + `components.csv`.
- Glyph editor (frame 4): upload SVG, trace from image (client-side, e.g. a Potrace port), path editing, "in context" preview. Saves land in the same proposal model (SVG + `components.csv` row changes on the branch).
  **Local-first version done 2026-10-17** (`app/src/lib/glyphed/`, `docs/GLYPH-EDITOR-UX.md`): Paper.js editing, SVG import, potrace tracing, compare overlays, in-context strip, direct save to `inputs/svg/`. The proposal model is the hosted part that remains.

### Phase 3: Requester slice and Admin

- Font tester with "file a request" (frames 6–7), request ↔ proposal linking.
- Admin: approvals queue, users & roles, builds, released font.

## Out of scope / kept as legacy

Classic `gpos.py` + `inputs/layouts.json` (`--classic_pos` only, until the golden is regenerated). Removed 2026-10-18: the Figma importer (`figma.py`, `--figma_pull`, the `requests` dependency), `src-fontforge/` (FontForge pipeline, v3.x sources and backups; git tag `fontforge-final`), the broken root Parcel `package.json`, and `font/tools/` (`font_tester.html` is replaced by the Builder's Tester screen). Superseded reviews and wireframes moved to `docs/archive/`.
