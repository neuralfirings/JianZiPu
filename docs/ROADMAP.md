# Roadmap: the web editor becomes the only design path

Decided 2026-10-12. Wireframes: `mockups/lofi-wireframes.html` (9 frames).

## Decisions

| question | decision |
|---|---|
| Where are glyphs and layouts designed? | In the web app, by signed-in Calligraphers and Layout Managers. Figma is legacy; `src-fonttools/jzpbuild/figma.py` stays as a one-way importer only. |
| Layout model | `dynamic_positioning` only. Every family is expressed in `dynamic_positioning/layouts_data.json`; classic `inputs/layouts.json` + `gpos.py` become legacy and `--dynamic_pos` becomes the default build. |
| Backend | GitHub + GitHub Actions + Supabase. Supabase: auth, roles, proposals, requests, comments. Each proposal is a GitHub branch written through a bot token (contributors never need GitHub accounts). Actions builds the font on proposal-branch push (preview) and on merge to main (release). No server to run. |
| First end-to-end slice | Layout Manager: sign in → edit a dynamic layout → save as proposal → admin approves → font built. |
| Front end | SvelteKit. |
| Roles | Calligrapher, Layout Manager, Requester (implicitly every signed-in user), Admin. One person can hold several. Roles are entry points, not separate logins. |
| Proposal state machine | draft → submitted → in review → approved → merged. Reject returns to draft (work is kept). Build failure does not un-approve: the proposal stays approved with a failed-build badge and an admin can retry. |

## Answers to the wireframe's open questions

- **Is "vertical" a separate layout or a flag?** A separate `LAYOUTS` entry (`vert`), using repeated-slot areas (`char_1`, `char_2`, `left_1`, …). The dynamic model already supports this; classic's per-row `layout_vertjzpN` frames collapse into one topology.
- **Horizontal centering per layout or global?** Per layout: a `horizontal_center_order` key mirroring `vertical_center_order` (chords and single words center differently).
- **Overlapping gap conditions: first-match or error?** First-match, top to bottom, with a final "otherwise" (what `anchors.resolve_gap` does). The editor shows rows in evaluation order; an "otherwise" row is required whenever any condition exists.
- **Is the current role a mode or a label?** A mode: it changes the nav. The data is shared; the mode only decides which editor you land in.

## Phases

### Phase 0: pipeline prerequisite (in progress)

Make `dynamic_positioning` able to express everything the font needs, so the layout editor can be the only layout tool.

1. **One GPOS lookup per pivot signifier** instead of one `dynamic_pos` lookup. The 64KB subtable ceiling then applies per family, not to the whole font; exact centering is kept. Rules from different signifiers never match the same word (each rule's context contains its own pivot glyph), so the split changes no positions. The bare-`fy` fallback gets explicit zero-valued blockers (derived from the layouts) instead of relying on sharing a lookup.
2. **Horizontal centering** (`horizontal_center_order`), same mechanism as vertical.
3. **loki / nc / tiao / mo** join `default_jzp`'s selector, with per-signifier gaps seeded from classic `layouts.json` so they start where the Figma frames put them.
4. **cuo** (`chord_left` / `chord_right`): add `fy`/`left`/`hui`, remaining chord keys (`DC`, `FC`, `TTT`, `B`, `L`, `BL`), and zero classic's cuo rules under `--dynamic_pos` so nothing double-stacks.
5. **vert mode** (`:` topology with repeated-slot rows), replacing `layout_vertjzp1..4`.
6. **Flip the default**: `python3 -m jzpbuild` builds with dynamic positioning; `--classic_pos` keeps the old path for comparison. A parity report (classic vs dynamic positions over `tests/test_shaping.py`'s corpus) is the acceptance test for 3–5; the golden `tests/JianZiPu.ttf` is regenerated once the result is accepted.

### Phase 1: Layout Manager slice

- SvelteKit app (`app/`), Supabase auth, roles table, workspace home.
- Layout editor: port of `tools/jzpbuilder-dynamic.html` (frame 5). Live resolve runs **in the browser via Pyodide** executing the real `dynamic_positioning` package (pure Python), so the preview cannot drift from the build; the rule-count/bytes badge uses the same code.
- Proposal: a Supabase row + a GitHub branch `proposal/<id>` holding the changed `layouts_data.json`, created and updated through a serverless function with the bot token. Submit → PR. Admin "Approve & build" → merge.
- GitHub Actions: `.github/workflows/font.yml` builds on `proposal/**` push (uploads the `.ttf` as an artifact the tester can load) and on `main` (release: commits/publishes the built font).
- Proposal detail (frame 8) for layout changes: before/after rendered words, comments, state strip, build status.

### Phase 2: Calligrapher slice

- Glyph library (frame 3) over `inputs/svg/` + `components.csv`.
- Glyph editor (frame 4): upload SVG, trace from image (client-side, e.g. a Potrace port), path editing, "in context" preview. Saves land in the same proposal model (SVG + `components.csv` row changes on the branch).

### Phase 3: Requester slice and Admin

- Font tester with "file a request" (frames 6–7), request ↔ proposal linking.
- Admin: approvals queue, users & roles, builds, released font.

## Out of scope / kept as legacy

`src-fontforge/` (FontForge pipeline), `figma.py`, classic `gpos.py` + `inputs/layouts.json` after Phase 0.6, and the `tools/*.html` editors once the app covers them.
