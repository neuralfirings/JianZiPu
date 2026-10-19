# UX review: JianZiPu Workbench lo-fi wireframes

Reviewed: `mockups/lofi-wireframes.html` (frames 0–9), against `docs/ROADMAP.md`, the two
current single-page tools (`src-fonttools/tools/jzpbuilder-dynamic.html`,
`src-fonttools/tools/jzpbuilder.html`) and `dynamic_positioning/README.md` +
`layouts_data.json`. Written for the author of the wireframes. Frame numbers
(f1…f9) and callout numbers (f5·4 = frame 5, callout 4) are used throughout.

---

## 1. Overall assessment

The wireframes get the hard part right: there is one hub (the Proposal), every
editor save lands in it, reviewers see pictures instead of diffs, and the
requester loop (see → flag → track → auto-resolve) is drawn end to end. The
layout editor (f5) is a faithful port of `jzpbuilder-dynamic.html` and the
proposal page (f8) already shows the right things in the right order (what
changed, how it looks, decide).

The biggest risks, in order:

1. **The layout editor speaks the engine's language.** "Relationships", "base ·
   edge", "pivot", "signifier", "selector", "canvas", keys like `k`/`U`, and set
   notation (`base ∈ {lg_gou, lg_da}`) are all on screen. A guqin musician who
   is also a good layout designer will not learn this vocabulary; they think
   "注 sits a bit too far from 勾". The first slice will be judged on whether a
   Layout Manager can change one gap without help. Today they cannot.
2. **The proposal flow has no author's-draft design.** f8 is drawn from the
   admin's seat. The Layout Manager's path (make a change → where did it go? →
   name it → submit → see it come back with comments → fix → resubmit) is the
   first slice, and the only artefacts for it are a "Save to proposal ▾" popover
   and one sentence in f8·1.
3. **Concurrency is undesigned.** Every proposal is a branch and every layout
   proposal edits the same `layouts_data.json`. Two Layout Managers (or one
   person with two drafts, as f2 shows) will produce merge conflicts that no
   screen can show, because contributors never see git.
4. **The size badge is specified against the wrong numbers.** f5·7 says warn at
   80%, block at 100%; the existing tool warns at 35% and goes red at 55%
   because the estimate undercounts bytes and real builds overflowed at wildly
   different rule counts. And since Phase 0.1 the ceiling applies per signifier
   lookup, not to the whole font.
5. **No global navigation.** Frames 3–7 have no way to reach Proposals, the
   tester, or another section except via Home. The "role as mode" decision
   makes this worse, not better.

None of these needs new screens; they need the existing ones reframed.

---

## 2. Cross-cutting issues

### 2.1 Navigation and IA (f0, f2–f8 headers)

- **Problem:** The header carries the logo, a single section pill, a breadcrumb,
  a context chip and the user menu. There is no persistent way to get to
  Glyphs / Layouts / Tester / Requests / Proposals / Admin. f8's header pill
  says "Proposals" but no other frame links there.
- **Fix:** One persistent nav with the sections the user has access to:
  `Glyphs · Layouts · Tester · Requests · Proposals · Admin`. Sections the user
  lacks a role for are hidden (not greyed). Drop the role pill from the header;
  "where you are" is the highlighted nav item.
- **On "role is a mode" (f0·1, f2·1, roadmap):** present it as *sections*, not
  modes. A mode switcher is a step with no payoff when the data is shared and
  one person holds three roles (f2 shows exactly that user). The role concept
  should survive only in two places: the home cards (f2) and Users & roles (f9).
  Nothing else should ask "which hat are you wearing?".

### 2.2 The proposal mental model (f0, f4·7, f5 footer, f8)

What a non-engineer needs: *my work is kept somewhere until I say it's ready;
then someone looks at it; then it's in the font.* The wireframes mostly deliver
this but leak implementation in four places:

| On screen | Why it leaks | Say instead |
|---|---|---|
| state "merged" (f0, f2, f8) | git verb; also ambiguous with "released" (f9·5) | "In the font" / "Released in v1.15" |
| "submitted → in review" as two states (f0, f8·1) | nobody moves it from submitted to in review; it's a queue position, not a state | one state: "Awaiting review"; show "being reviewed by li" as a sub-label if you must |
| "Request changes" *and* "Reject…" (f8·6) when reject returns to draft | two buttons, one transition | one button "Send back with comments" (→ draft, work kept) and a separate, rarer "Close" (archived, can be reopened). This is the answer to f0·3. |
| "rev 1 / rev 2" (f8 Revisions), "For engineers: branch proposal/17 · 3 files · view diff" | fine for admins, noise for authors | "Update 1 / Update 2"; show the engineers panel to admins only |

Also:

- **"Save to proposal ▾" on every save (f4·7, f5 footer) is the wrong moment.**
  Choosing the proposal is a once-per-editing-session decision. Ask it when the
  user makes the *first* change ("Where should this go? ▸ current draft 'zhu↔right
  gap for lg_li' / new draft") and then show it as the context chip the header
  already has ("editing in: …"). Save is then just Save. "Save & submit" stays as
  a shortcut in the chip's menu.
- **Autosave vs Save (f4 footer shows both: "last autosave 14:02" and "Save to
  proposal").** Pick one model and state it: the draft autosaves to the app
  (Supabase), and "Submit for review" is the only deliberate act that writes the
  branch. Don't push a branch per keystroke; don't make people remember to save.
- **"Drafts are private until submitted" (f0·5)** conflicts with f3·4 ("a glyph
  with an unmerged change shows a dashed border… clicking opens the proposal's
  version"). Decide: private drafts are invisible to others everywhere, and
  "in flight" badges appear only from Awaiting review onward.
- **Stale and conflicting proposals are missing entirely.** Needed states:
  "based on v1.14; the font has changed since (v1.15). Update this draft" and
  "this draft conflicts with proposal #19 (both change default_jzp · zhu ↔ right)".
  For the first slice the simplest honest design is a *soft lock*: when a
  layout already has a proposal in Awaiting review or later, the editor shows
  a banner "li is changing this layout in #19 (awaiting review). You can keep
  editing, but yours will have to wait until that one is decided." and the
  server rebases drafts on merge, surfacing a conflict as a proposal state
  ("Needs update") the author fixes by re-applying. See §6.

### 2.3 Terminology (mostly f5, also f3, f8)

The engine's words are precise; the UI's words should be a musician's. Keep the
engine names in tooltips and in the JSON, never as the primary label.

| Engine / wireframe | Problem | Recommended label (en) | Suggested zh (please check) |
|---|---|---|---|
| area | fine, already in use; keep | Area | 區域 |
| relationship (f5·4) | abstract | Spacing rule / Position rule | 間距規則 |
| element / base / base·edge | directional jargon | "**zhu** sits **66** to the right of **right**'s left edge" as a sentence; "relative to" | 相對於 |
| gap | fine | Gap | 間距 |
| canvas (f5 "base = canvas") | means "no base"; confusing with the drawing canvas | Fixed position (on the page) | 固定位置 |
| pivot (f5·3) | engine term for "the glyph the word is keyed on" | Main glyph / Main area | 主筆 / 主區域 |
| signifier / "by glyph" | never say signifier; "by glyph" is good | "depends on which glyph" | 依字形而定 |
| selector: "applies when word contains one of k l i o U" | ASCII keys mean nothing | "Used for words with: 勾 大 剔 摘 歷 …" (glyph thumbnails, keys in tooltip) | 適用於含有… |
| optional (f5·3) | ok but ambiguous | "may be absent" | 可省略 |
| order ("Areas in order", f5·3) | this is *typed* order, which also drives GPOS context; reordering is dangerous | "Typing order" with an advanced/lock affordance | 輸入順序 |
| vertical_center_order (f5·5 "groups centered as a stack") | ok | "Rows (for centering)" | 置中行 |
| `default_jzp`, `chord_left`, `lg_gou`, `md_13` | internal ids | display names with id secondary: "Standard word (default_jzp)", "勾 lg_gou" | 標準字 / 撮·左 |
| `base ∈ {lg_gou, lg_da}` (f8·3) | set notation | "when the main glyph is 勾 or 大" | |

Glyph pills everywhere (f5 conditions, f3 cards, f8 diff) should show the
**character or thumbnail first** and the `lg_*` name second. The glyph *is* the
picture; the name is bookkeeping.

### 2.4 Bilingual text and Chinese input

- **UI language:** the chrome is English-only in every frame while the content
  is Chinese. Decide now whether the UI is bilingual on day one (recommended:
  yes, with a language switch in the account menu and on sign-in, stored per
  user). Retrofitting i18n into a SvelteKit app is cheap now and expensive in
  Phase 3; at minimum keep all strings in a message table from the first commit.
- **Test-word inputs (f4·6, f5·6, f6·2) accept key strings and Chinese.** Three
  things the sketches do not say and the build must do: (1) do not re-render
  during IME composition (`compositionstart`/`compositionend`), (2) always show
  the *interpreted* key string under each rendered word (f6's modal does this
  with `s9j2`; do it everywhere, it is how a user learns the input rules), (3)
  accept full-width spaces/punctuation and ignore them.
- **The IME variants question (f6·2):** no dropdown. All spellings
  (`common / latin / latin_alt / simplified / traditional`) should simply work in
  the same field; a "How to type" popover lists them. A dropdown is a mode the
  user must know about before typing.
- Pinyin exists in `components.csv`; use it for search (f3·2) and in the
  glyph pickers.

### 2.5 Accessibility

Not a lo-fi concern, but three things change the design, so decide them now:

- **Every canvas edit needs a keyboard path.** The existing tool nudges with
  arrows (shift ×10); keep that, and make the selected area's gap a plain
  number input that is always on screen (f5 does this in the table; make sure it
  stays visible when the canvas has focus).
- **State is never colour-only.** The pills use border style (solid/dashed/filled);
  keep that discipline when a visual designer adds colour.
- **Modals (f6 request, f4·7 save popover) need focus trapping and a close on
  Esc; the auto screenshot needs alt text = the word string.**
- Touch targets ≥ 44 px on anything a calligrapher will hit with a finger or
  Pencil (f4 toolbar is 34×30).
- "Flip" compare (f8·4) must respect `prefers-reduced-motion` (no auto-cycling).

### 2.6 Empty, loading and error states (none are drawn)

The ones that will actually bite, by frame:

| Where | State | What to show |
|---|---|---|
| f5 on open | Pyodide + `dynamic_positioning` boot (several seconds, ~10 MB first time) | Editor loads read-only with "Preparing live preview…" progress; rules table usable; canvas renders last-known positions greyed |
| f5 | Resolver error (bad rule, cycle, no pivot) | Inline on the offending rule, in words: "zhu can't be placed: its rule points at hui, which may be absent in this word" |
| f5 footer / f8 | Preview build running (≈1 min per f9) | "Building preview… usually under a minute" with live status; disable "try in tester" until done |
| f8 | Build failed | **Not** a link to GitHub Actions logs for authors. A one-paragraph plain explanation ("the layout rules are too large for the font format; try fewer per-glyph conditions") + "Logs" for admins + "Ask an engineer" button that files an issue with the log attached |
| f8 | Proposal stale / conflicting | see §2.2 |
| f4 upload | Invalid SVG (strokes instead of fills, open paths, text, transforms, embedded raster) | A pre-flight "SVG check" list with fix-it buttons (Outline strokes, Close paths, Flatten) — the picosvg/pathops pipeline will reject these silently otherwise |
| f3, f7, f2 | Nothing yet | "No proposals yet — open Layouts or Glyphs to start one"; "No requests — try the tester" |
| any editor | Session expired / offline mid-edit | Keep the draft in IndexedDB; on return, "You have unsaved changes from 14:02 — restore?" |

### 2.7 Mobile and tablet

The sketches are fixed 960 px and say nothing about smaller screens. Decide
per section rather than per breakpoint:

- **Glyph editor (f4) on iPad is a real use case** (calligraphers draw in
  Procreate/brush apps, then trace). Design f4 for touch from the start: pointer
  events, no hover-only affordances, a 44 px toolbar, two-finger pan/pinch,
  Pencil for node dragging. It does not need to work on a phone.
- **Layout editor (f5) is desktop/large-tablet only.** Say so on screen below
  ~1024 px ("best on a larger screen") rather than attempting a stacked layout.
- **Tester, requests, proposals (f6, f7, f8) must be phone-usable**: musicians
  will file "this looks wrong" from a phone, and admins will approve from one.
  f6's "show glyph boxes on hover" needs a tap equivalent.

### 2.8 Consistency between the three editors (f4, f5, f6)

Define one **editor shell** and reuse it:

- Header: nav · breadcrumb (`Layouts › Standard word`) · proposal chip ·
  user menu. f6 currently has a font picker where f4/f5 have the chip; put the
  font picker inside the test-word strip instead (every editor benefits from
  "render with: released v1.14 / this draft / proposal #19").
- A shared **test-word strip** (f4 "In context", f5 "Test words", f6 main input)
  with the same input, the same interpreted-key labels, the same random/sample
  sets, the same hover-to-show-areas.
- A shared **footer**: changes summary ("1 spacing rule changed · 2 glyphs
  changed") · Undo/Redo · Discard · Submit. f4 and f5 currently have different
  footers, and f5 has no undo at all while f4 does (f4·3).
- Download buttons (`Download SVG`, `Download layouts.json`) go into an overflow
  menu. They are engineer escape hatches, not primary actions.

---

## 3. Frame-by-frame findings

### f0 — IA & proposal flow

- **f0·1 (role: mode or label?)** Neither — sections (§2.1). Rationale: with
  shared data and multi-role users a mode is a step with no payoff.
- **f0·2 (Requester implicit?)** Yes. Rationale: every signed-in person must be
  able to say "this looks wrong"; a role nobody can lack is not a role.
- **f0·3 (reject → draft or dead end?)** Back to draft, as decided, but split
  the admin action into "Send back" (→ draft) and "Close" (archived, reopenable).
  Rationale: "reject" has two meanings today and authors can't tell which they got.
- **f0·4 (auto-notify on failed build?)** Yes, author and all admins, in-app and
  email. More generally the wireframes have **no notifications at all**; an
  async review workflow needs them for: comment on my proposal, state change,
  request acknowledged/linked/resolved, build failed. P1.
- The state diagram omits the states the UI will need: *Needs update* (stale
  after a merge) and *Closed*. Add them so the data model has them from day one.

### f1 — Sign in

- **f1·2 (invite-only?)** Invite-only. Rationale: roles are granted by an admin
  anyway, and a public sign-up form on guqintabs.com invites spam proposals.
- **Prefer magic link (email OTP) over password** as the primary path; Supabase
  supports both. Calligraphers who use the app monthly will not remember a
  password, and "Forgot password?" becomes the real sign-in path. Keep password
  as an option in the account menu for people who want it.
- "No account? Ask an admin" needs a target: a `mailto:` or the admin's name.
- Add the language switch here (§2.4); it is the first screen a Chinese-first
  user sees.
- f1·3's note "email is recorded as proposal author in the commit message" is
  fine, but say it in the privacy line of the invite email, not on this screen.

### f2 — Workspace home

- **f2·1 (global role switcher?)** No. Remove the "Roles: Calligrapher · Layout ·
  Admin" pill from the header; it is static information that belongs in the
  account menu. Rationale: it is the only header element that never changes and
  never does anything.
- The three role cards are right for a first visit and wrong for the tenth.
  Make the page answer "what needs me?" first: a single **Attention** list at
  the top (proposals sent back to me, comments I haven't read, requests
  assigned to my role, builds that failed on my proposal), then the cards
  (smaller), then the two tables. f2·3 states this intent; the layout doesn't
  deliver it.
- "My proposals" and "My requests" as two separate tables duplicate f7/f8
  lists. Keep them, but each row needs the one fact that drives action: for
  proposals "1 new comment" / "sent back"; for requests "linked to #19".
- "Released font v1.14" should be a link (download + "what changed in v1.14").
- A user with exactly one role should not have to pick a card: show their
  section's content (e.g. the layouts list) directly under Attention.

### f3 — Glyph library

- **f3·3 (card shows glyph in a sample word?)** Bare glyph on the card, sample
  words in the inspector strip (f3·5), which is already drawn. Rationale: the
  grid is for recognising shapes; composed words at 5-per-row would be
  unreadable.
- Group labels are file prefixes ("lg_ large strokes"). Lead with meaning:
  "Right-hand strokes (lg_)", "Fingers & strings (md_)", "Chords (xl_)",
  "Modifiers (mod_)", "Hui decimals". The counts (222) match `inputs/svg/`
  exactly, but `components.csv` has only 92 rows, so ~130 SVGs have no
  key/area assignment. The library needs an explicit state for those
  ("not yet assigned to an area — ask a Layout Manager") and a filter for it;
  otherwise a Calligrapher will "edit" a glyph the font never uses.
- "Show: vertical variants" is a filter on a property almost no glyph has
  (`vert_variant` column, currently empty). Make it a badge on cards that have
  one and a "has vertical variant" filter under *By area*.
- **f3·4 ("clicking opens the proposal's version")** contradicts private drafts
  (§2.2) and makes a card's click target ambiguous. Clicking always opens the
  released glyph in the inspector; the inspector shows "A change is awaiting
  review: *Rework lg_gou stroke weight* ▸ open" and "Edit" warns "li is already
  changing this glyph in #17".
- The inspector's "Preview in words" and "History" are the two things a
  calligrapher wants; promote them above "Edit" visually, since Edit is
  destructive-ish (creates a draft).
- Search placeholder "gou, k, 勾" is good; add pinyin.
- "Upload SVG" and "+ New glyph" are the same action with different first steps;
  one button "+ New glyph" with a chooser (Upload / Trace / Draw) is clearer.

### f4 — Glyph editor

- **f4·1 (may the Calligrapher change key/area?)** Name, key and area are
  read-only for existing glyphs; they are identity, and changing the area
  changes the box size every layout assumes. Char (the Chinese input character)
  is editable by the Calligrapher. For a **new** glyph, the Calligrapher must
  pick an area (it sets the box) in the "New glyph" step; key is suggested and
  confirmed by a Layout Manager/Admin at review. Rationale: a wrong area breaks
  every word; a wrong char only breaks typing.
- **f4·3 (pen from scratch needed?)** No; defer. Realistic inputs are a scan or
  an SVG from Illustrator/Inkscape/iPad apps. Keep: select, node edit, delete
  node, simplify, flip H/V, scale, undo/redo. Drop: pen, cut, rectangle.
- The three tabs (Upload / Trace / Draw) look like persistent modes but are
  entry points. Make them a "Start from…" chooser (empty state) and a
  "Replace from…" menu on an existing glyph; the canvas is always the editor.
- **The box preview anchors the glyph in the centre; the font bottom-anchors
  it.** `jzpbuilder-dynamic` has an "exact font placement (bottom-anchored,
  natural size)" toggle for exactly this reason. Show the glyph where the font
  will put it (bottom-left of the area box), and make "Center" (f4·5) a
  horizontal-only action with a tooltip. Otherwise "Fit to box" + "Center" will
  produce glyphs that jump at build time.
- Add the SVG pre-flight check (§2.6) to the Upload path; it is the most common
  failure in this pipeline and the sketch has no place for it.
- "also vertical variant" checkbox (f4·1 row): unclear what it does (a second
  SVG? a flag?). Either remove it from this row or make it a second canvas
  tab "Vertical variant" with its own upload.
- The in-context strip (f4·6) is the best part of this frame. Add a
  "released / this edit" **flip** toggle on each word, not just a ghost; ghosts
  of similar black strokes are hard to read.
- Toolbar is 34×30 px; iPad-first means 44 px (§2.7).

### f5 — Layout editor

This is the first slice; §5 covers what to build. Findings on the sketch itself:

- **f5·1 (vertical: layout or flag?)** Separate layout (decided). Draw it as a
  real entry "Vertical word (vert)" and plan the repeated-slot UI
  (`char_1, char_2…`) as a "repeats ×N" property on an area, not as N areas.
  Hide "+ new" (new topologies are an engineer's job for now); keep "duplicate".
- **f5·4 (first-match or error?)** First-match top-to-bottom with a required
  "otherwise" (decided), **plus** shadow detection: a glyph listed in a row
  below a row that already matches it is marked "never used — 勾 is already
  handled above", and a row after "otherwise" is impossible (otherwise is pinned
  last and undeletable). Rationale: first-match is the right engine rule; the
  editor's job is to make the order visible and the mistakes impossible.
- **f5·5 (horizontal centering per layout or global?)** Per layout (decided).
  The toggle is fine. Add the same for the canvas center: expose `center_y`
  (Phase 0 found 300 vs 500 is a design call) as a global "Word baseline"
  setting with the released value shown and a "preview with released value"
  compare, because it shifts every word.
- **The relationships table (f5·4) should not be the primary editor.** 27 rows
  of x/y mixed is an overview, not a tool. Primary: click an area → a
  **Position** panel for that area with two sentence-form rules ("Horizontal:
  66 to the right of 勾's left edge", "Vertical: 44 below 就's bottom"), each
  expandable into the by-glyph table. The full table becomes a "All rules"
  view with a filter by area. This is what `jzpbuilder-dynamic`'s relPanel
  already does; the sketch regressed it into a spreadsheet.
- **Which glyph is being previewed is a first-class control** and is missing.
  The canvas shows 勾, which decides which conditional row applies, but there
  is no "Preview with: 勾 lg_gou ▾" selector (the existing tool has
  `signifierSelect`). Put it on the canvas toolbar, and let the test-word strip
  show all signifiers so a change to the "otherwise" row is seen on 剔/摘/歷
  at once.
- **"Dragging a box edits the gap number" (f5·2) must say which number.** In
  the existing tool, a drag writes into the first conditional row that matches
  the *currently previewed* glyphs, or appends a catch-all. That is the right
  behaviour but it must be visible: while dragging, a label on the arrow reads
  "gap for 勾/大: 66 → 72" and the matching row highlights. See §5.
- **"Areas in order" (f5·3) edits typed order**, which the README says drives
  GPOS backtrack/lookahead and must not be conflated with attachment or
  centering order. A Layout Manager tuning gaps never needs to reorder it.
  Lock it behind "Advanced"; show it read-only otherwise.
- **Area sizes "shared across layouts"** (f5 left) edited here changes three
  layouts silently. Show "used by: Standard word, Chord left" and require
  confirmation; or make sizes read-only in the first slice.
- **Size badge (f5·7):** wrong thresholds and wrong scope. Use the real
  estimator's fractions (warn ≈35%, danger ≈55%, from `jzpbuilder-dynamic`),
  compute **per signifier lookup** (Phase 0.1) and show the worst one; never
  "block submit" on an estimate — the preview build is the truth and f9·2
  already prevents approving a failed build. Also explain what grows it
  ("each 'depends on glyph' row multiplies rules for every optional-area
  combination").
- Missing: **undo/redo**, per-rule "changed" markers with "revert this", and a
  "what changed" list that matches f8's diff wording.
- `k l i o U` in the Selector panel → glyph thumbnails (§2.3).

### f6 — Font tester with "file a request"

- **f6·2 (expose IME rules as a dropdown?)** No; accept everything, show the
  interpreted keys under each word, offer a "How to type" popover (§2.4).
- **f6·5 (categories missing?)** Add "wrong glyph appears (typed X, got Y)" —
  substitution/input bugs are a distinct fix (components.csv) from "glyph looks
  wrong" (SVG). Add "inconsistent across words" (a layout-rule smell). Drop
  "other" to the end and require a sentence for it. Consider "suggest a sample
  word" for the sample sets.
- "Shift-click to compare with the previous release" is an invisible gesture.
  Make it a toggle in the Display panel: "Compare with: v1.13 ▾" that renders
  each word twice (flip or side by side), reusing f8·4's control.
- Selection: "Click a word (or drag over several)" then one "Flag selected"
  button is good; make sure one request can carry several words, and that
  tapping a word on a phone shows a small "Flag" affordance (no drag-select on
  touch).
- The modal's "Region: whole word / just an area" is excellent; also capture
  the display size and the browser, since "collides at small sizes" is
  size-dependent.
- Button label "Send request" → "File request" (it creates a record; it does
  not message anyone).
- **The tester is needed in Phase 1, not Phase 3.** Reviewers "try in tester"
  (f8·6) and Layout Managers need a place to type arbitrary words against a
  proposal's preview font. Pull a read-only tester (no request filing, font
  picker included) into the first slice.

### f7 — My requests

- **f7·1 (can requesters see each other's?)** Yes, all open requests are
  visible to everyone signed in; add "+1 / I see this too" and "duplicate of
  #n" so admins can merge. Rationale: with a small community, duplicates are
  the main cost and visibility is the cure.
- Status vocabulary (f7·2): "acknowledged" → "Seen"; "in proposal" → "Fix in
  progress (#19)"; "resolved" → "Fixed in v1.15" (show the version; the
  requester wants to know when to update their font); "won't fix" → "Declined"
  with a required reason shown in the timeline.
- The thumbnail column: render the word live from the released font (so it
  stays current) and keep the original screenshot in the detail pane for
  "what I saw then".
- Tabs "Mine / All open / Resolved" should be filters above one list; "Mine" as
  a tab hides that "All open" includes mine.
- Detail pane "Add a comment" / "Withdraw" are fine. Add "Edit" (category and
  description) while the request is still Open.

### f8 — Proposal detail

- **f8·4 (side by side or flip as default?)** Flip for layout changes, side by
  side for glyph shape changes, overlay available for both; keyboard `space`
  toggles flip. Rationale: a 6-unit shift is only visible when the image
  stays put and changes in place; a stroke redesign is better read side by side.
- **f8·6 (one approval or two for layouts?)** One, with two guards that cost
  nothing: the preview build must be green (already in f9·2) and the
  approver ≠ author when any other admin exists; if the author is the only
  admin, allow it and record "approved by author" in the timeline. This also
  answers f9·2 ("may an admin approve their own?").
- **The author's view is missing.** Draw f8 in Draft state as the author sees
  it: editable title and description (pre-filled from the change list:
  "Changed zhu ↔ 勾 gap 66 → 72 in Standard word"), a list of what is in the
  proposal with "remove from proposal" per item, "Submit for review" as the
  only primary action, and "Sent back by li: …" banner when returned. This is
  on the first-slice path.
- Layout diff wording (f8·3): `x · zhu ← right · if base ∈ {lg_gou, lg_da}` →
  "Standard word: horizontal gap of 注 from 勾/大: 66 → 72". Also render the
  specific words that row affects right under the row; the "Rendered words"
  panel below is global, and a reviewer wants the per-change evidence.
- The Rendered words strip (f8·4) auto-picks affected words; also let the
  reviewer type a word there (same strip component as the editors, §2.8) and
  mark which words came from linked requests ("from #38").
- "Approve & build" → "Approve" with the consequence as helper text ("builds
  the font and releases it as v1.15"). The build is a consequence, not a choice.
- Build status (f8·6): the progress bar with no label reads as "stuck". Show
  the stage name and elapsed time; when failed, show the plain-language
  explanation (§2.6), not just "logs".
- Comments: "paste a word to render it" is a great detail; also allow a
  comment to be attached to a specific changed item (glyph or rule). Defer the
  attachment part; keep the thread for slice 1.

### f9 — Admin (not in the brief, but it's in the file)

- Four tabs are right; the sketch shows all four at once, which is fine for
  discussion. Keep Approvals as the landing tab.
- **f9·5 (release = merge, or batched?)** Release on merge, auto-numbered,
  until there are enough merges per week to make batching worth a screen.
  Rationale: a proposal that is "in the font" but not downloadable is a
  support question waiting to happen. Add a one-line changelog per version
  (generated from proposal titles) for the website.
- Users & roles: role changes "take effect at next page load" — just re-fetch
  on change; don't make the user reload.
- "Retry" on a failed build belongs on the proposal (f8) too, not only here.

---

## 4. Prioritised recommendations

| Pri | Issue | Fix | Frames |
|---|---|---|---|
| P0 | Engine jargon as primary labels (relationship, base·edge, pivot, selector keys, canvas, set notation) | Terminology table in §2.3; glyph thumbnails before names; sentence-form rules | f5, f8, f3 |
| P0 | Relationships spreadsheet is the primary editor | Area-first "Position" panel (X rule, Y rule, by-glyph table); full table as secondary view | f5 |
| P0 | Drag-to-edit doesn't say which gap/row it edits | Live label on the arrow + row highlight; "Preview with: glyph" selector on canvas | f5 |
| P0 | Size badge thresholds/scope wrong (80%/100%, whole font) | Use estimator's ≈35/55%, per signifier lookup, never blocks submit | f5, f9 |
| P0 | No author's-draft proposal view (title, contents, Submit, sent-back banner) | Draw f8 in Draft state; pre-fill title from changes | f8 |
| P0 | "Save to proposal ▾" on every save; autosave vs save ambiguity | Choose proposal on first change → context chip; autosave draft; Submit is the only deliberate act | f4, f5 |
| P0 | No global navigation; role-as-mode | Persistent section nav; drop role pill; roles only on home cards and admin | all |
| P0 | Concurrent layout proposals conflict with no UI | Soft lock banner + "Needs update" state + server rebase | f5, f8, f0 |
| P0 | Loading/error states for Pyodide boot, build in progress, build failed | §2.6 table; plain-language build failure | f5, f8 |
| P0 | No undo/redo in layout editor | Shared editor footer with Undo/Redo, Discard, change list | f5 |
| P0 | Tester needed by reviewers in slice 1 | Read-only tester with font picker in Phase 1 | f6, f8 |
| P1 | "Request changes" vs "Reject" both → draft | "Send back with comments" + separate "Close" | f8, f0 |
| P1 | State names leak git ("merged", "submitted/in review") | "Awaiting review", "Approved", "In the font vX" | f0, f2, f8 |
| P1 | No notifications | In-app + email for comments, state changes, build failures, request updates | f0, f8, f7 |
| P1 | Glyph preview centred; font bottom-anchors | Show glyph at font placement; Center = horizontal only | f4 |
| P1 | No SVG pre-flight check | Upload-time validation with fix-it actions | f4 |
| P1 | Key/area editable by Calligrapher; "also vertical variant" unclear | Identity read-only for existing glyphs; vertical variant as its own tab or removed | f4 |
| P1 | f3·4 opens the proposal's version on click; drafts not private | Always open released; inspector shows in-flight change; edit warns on conflict | f3 |
| P1 | Request status vocabulary and version visibility | Seen / Fix in progress (#n) / Fixed in vX / Declined (reason) | f7, f2 |
| P1 | iPad for glyph editor; phone for tester/requests/proposals | Touch targets, pointer events, responsive on f6–f8; f5 desktop-only notice | f4, f6, f7, f8 |
| P1 | Bilingual UI decision; IME composition handling; interpreted-key labels | i18n from first commit; composition events; keys under each word | all, f4–f6 |
| P1 | Typed order and area sizes editable casually | Lock behind Advanced / confirm with "used by" | f5 |
| P2 | Home is role cards first | "Attention" list first; cards smaller | f2 |
| P2 | Magic-link sign-in | Email OTP primary, password optional | f1 |
| P2 | Category list gaps | Add "wrong glyph appears", "inconsistent across words" | f6 |
| P2 | Hidden gestures (shift-click compare, hover boxes) | Explicit toggles | f6 |
| P2 | Group labels are file prefixes | Human names with prefix secondary | f3 |
| P2 | Download buttons as primary actions | Overflow menu | f4, f5 |
| P2 | Flip compare default / per-change rendered words | Flip for layout, side-by-side for glyphs; words under each diff row | f8 |
| P2 | Release = merge decision; changelog | Auto-version per merge; generated changelog | f9 |

---

## 5. The first slice: Layout Manager

### Minimum viable layout editor

Build exactly this and nothing more:

1. **Layout list** (read-only): Standard word, Chord left, Chord right, with
   ids secondary. No "+ new"; "duplicate" deferred.
2. **Canvas**: areas as boxes with glyphs; selected area highlighted; gap arrows
   for the selected area only; zoom/pan; **"Preview with: 勾 ▾"** signifier
   selector; a boxes/glyphs toggle.
3. **Position panel** for the selected area: Horizontal rule and Vertical rule,
   each as a sentence with an editable number; "depends on glyph ▾" expands to
   the conditional table (ordered rows, glyph pickers with thumbnails, pinned
   "otherwise", shadow warnings). Rule *structure* (which area it is relative
   to, which edge) is shown but **read-only** in slice 1.
4. **Test-word strip**: key strings + Chinese, interpreted keys under each word,
   rendered through Pyodide from the unsaved state; a "words affected by the
   rule you're editing" auto-set; a sample-set picker.
5. **Horizontal centering toggle** and read-only display of centering rows.
6. **Size badge** per signifier lookup, from the same Pyodide code, with the
   real thresholds.
7. **Footer**: change list ("1 rule changed · revert"), Undo/Redo, Discard,
   proposal chip, Submit for review.
8. **Proposal page in Draft and Awaiting review states** for layout changes:
   sentence diff with per-row rendered words, flip compare, build status,
   comments, Approve / Send back.
9. **Read-only tester** with font picker (released / this proposal).

Defer: creating areas or topologies, editing area sizes, editing typed order,
editing centering rows, vertical layout, changing a rule's base/edge, the
"random" button, downloads, request linking, @mentions, per-item comments.

### Interaction details that make or break it

**1. Drag edits a gap.**
- Dragging is constrained to the axes that have a rule for the selected area
  (both, usually). Positions re-resolve live (optimistic local math during the
  drag, as `jzpbuilder-dynamic` does with `lastResolved`; reconcile from Pyodide
  on pointer-up, debounced 50–100 ms during the drag if the worker keeps up).
- A label rides on the gap arrow: "gap from 勾's left edge: 66 → 72". If the
  gap is conditional, the label names the row being edited ("for 勾, 大") and
  that row highlights in the panel. If no row matches the previewed glyphs, the
  drag edits "otherwise" and says so.
- Dependants move with the dragged area (positions are derived); the status
  line says "moving zhu also moves: right, string" so it is not a surprise.
- Integers only; Shift = ×10; arrow keys nudge; Esc cancels and restores; every
  drag is one undo step.

**2. Authoring a conditional rule.**
- From a plain number: "Make it depend on the glyph" turns the number into the
  "otherwise" row and adds one empty row above it.
- A row = a glyph multi-picker for the base area (thumbnails, pinyin search,
  "select the rest") [+ optional second picker for the element area, hidden
  until "and also depends on zhu's glyph" is clicked] + a number.
- Rows are reorderable; "otherwise" is pinned last and cannot be deleted; a
  glyph already caught by an earlier row is struck through in later rows with
  "handled above". The rendered test words show, per word, which row it hit
  (small "row 2" tag on hover).
- Shortcut from the canvas: with "Preview with: 歷" selected, dragging a gap
  whose matching row is "otherwise" offers "give 歷 its own row" so the author
  doesn't widen the otherwise value by accident. This is the single most
  likely mistake with first-match rules.

**3. The size badge.**
- Computed by the same `estimate_dynamic_pos_bytes` running in Pyodide, debounced
  ~400 ms, per signifier lookup; the badge shows the worst lookup ("勾: 21.6 KB
  of ~36 KB safe") and expands to all of them.
- Amber at the estimator's warn fraction, red at danger; red says "the preview
  build will probably fail" and still allows Submit. Approval stays blocked by
  a failed build (f9·2), which is the real gate.
- The badge delta is shown in the change list and in the proposal diff
  ("21.6 → 21.9 KB").

**4. Pyodide latency.** Load it in a worker on app start (not on editor open),
cache it, and give the editor a usable read-only state until it is ready. If
the first resolve takes longer than ~2 s, the canvas shows last-known positions
greyed with "updating…" rather than nothing.

---

## 6. Open questions for the product owner

1. **Concurrency policy.** When two drafts change the same layout, which wins:
   soft lock, hard lock (one open proposal per layout), or merge with manual
   conflict resolution in the app? The soft lock in §2.2 is my recommendation,
   but it depends on how many Layout Managers there will be.
2. **Who owns `components.csv` rows?** `jzpbuilder-dynamic` lets the layout
   editor add/remove glyph candidates per area and edit IME spellings; the
   wireframes put key/area on the glyph editor (f4·1) and nowhere else. Is
   "which glyphs may occupy this area" a Layout Manager task, a Calligrapher
   task, or admin-only?
3. **`center_y` 300 vs 500.** Phase 0 says this is a design call for the layout
   editor. Should the first slice expose it (as "word baseline") or should it be
   decided and fixed before the editor ships?
4. **Bilingual UI on day one, or English UI with Chinese content?** This changes
   the first commit, not the design.
5. **Expected user counts and cadence** (3 people and a proposal a week, or 30
   and daily?). This decides whether notifications, two-person approval and
   batched releases are P1 or never.
6. **Calligraphers' actual tools.** Do they produce scans/photos (trace path),
   Procreate exports (PNG, trace path) or vectors (upload path)? This decides
   whether Trace or Upload is the default and whether the iPad case is real.
7. **Public tester?** Should visitors to guqintabs.com be able to file requests
   without an account (captcha'd), or is sign-in required for everything?
8. **Vertical layout authoring.** The repeated-slot model (`char_1, char_2…`)
   has no UI sketch; is it in scope for the Layout Manager at all, or will
   engineers author `vert` once and the editor only tunes its numbers?
9. **Versioning.** Who decides v1.14 → v1.15 vs v2.0, and does the website
   need a changelog generated from proposal titles?
10. **Build failure handling for non-engineers.** Is there always an engineer
    on call, so "Ask an engineer" can file a GitHub issue with the log, or must
    the admin be able to resolve common failures (size overflow) alone?
