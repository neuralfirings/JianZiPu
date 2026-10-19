# Spacing panel: UX options

Status: proposal, for the font author to pick from. Companion to `BUILDER-UX.md` §3.5–3.7
(the current spec) and `src-fonttools/jzpbuild/positioning/schema.py` (the data). Vocabulary
follows §3.1: *part*, *gap above*, *start height*, *exceptions* / *otherwise*, *anchor*,
★ *main glyph*. Nothing here changes `design.json`'s shape; every option is a different
window onto the same relationship list.

## 1. Why this is hard

A word is a stack of parts, most of them optional, so "the part above me" is not a fact but
a question: for `right` in the Standard word it is 急/綽 if present, else Position/Finger, else
泛音, else nothing (then `right` is first and has a start height). The data model answers that
question with an *ordered* list of rules per part and axis, and the first rule whose base is
present wins — so declaration order is semantics, invisible in the drawing. On top of that,
the gap itself can depend on which glyph is drawn: eight of the Standard word's rules carry a
7-row exception list keyed on the right-hand stroke (勾/大, 挑/托, 歷, …), tried top to bottom.
The result is 7 parts, 37 rules, ~70 exception rows and 96 word shapes × 16 strokes, which
the current panel shows as a flat list *for one part at a time* — the user sees 4–9 rules,
has to infer which one is live from a blue dot, and has to remember the other six parts.
The three things a calligrapher needs to see at once — *which parts are present, which rule
is therefore active, and what the stroke does to it* — live on three different screens of
state.

Two regularities in the real data make the problem tractable, and every option below leans
on them:

1. **Parts that sit side by side share rules.** Finger `left` and Position `hui` have
   identical gap rules everywhere (`jc←hui 0 / jc←left 0`, `right←hui` ≡ `right←left`, …). The
   Standard word is really five *tiers*: 泛音 · Finger+Position · 急/綽 · 注+Stroke · String.
2. **Every exception list uses the same seven stroke families** (`dazhai/gouti`, `pi/qiaqi`,
   `tiao/tuo`, `mo/motiao/yan/lun/banlun`, `gou/da`, `ti/zhai`, `li`), repeated eight times.
   There is one classification of strokes, not eight; the UI can detect and present it as one.

## 2. Options

Effort: S = days, M = 1–2 weeks, L = 3+ weeks, assuming the existing resolver endpoint
(`/api/resolve` already returns `chosen`, the active rule per part and axis).

### Option A — "Who is above me" matrix

Rows = parts in typing order; columns = the parts that can be above (nearest first) plus
*page*. A cell is the gap, or a `by glyph ▾` badge that expands to the exception list.

```
Spacing · Standard word                         Vertical ▾ (Horizontal)
                 ┌── when the part above is ─────────────────────────┐
 part            │ 注      Stroke   急/綽   Finger·Position  泛音  │ nothing (start height)
─────────────────┼───────────────────────────────────────────────────┼──────────────────────
 泛音 fy          │   ·        ·        ·          ·           ·     │  830
 Finger·Position │   ·        ·        ·          ·         -30     │  450
 急/綽 jc         │   ·        ·        ·          0          47     │  498
 Stroke right ★  │   ·        ·    by glyph▾  by glyph▾    by glyph▾ │  -30
 注 zhu           │   ·  by glyph▾ ⁽ᵗᵒᵖ⁾   6         -32          –     │  125
 String          │   ·  by glyph▾ ⁽ᵗᵒᵖ⁾   0         -35          –     │  125
─────────────────┴───────────────────────────────────────────────────┴──────────────────────
 ● = active for the preview word      – = no rule (part is skipped)      ⁽ᵗᵒᵖ⁾ = measured from
 the base's top edge, not its bottom
```

Reading: scan a row left to right and you read the resolver's search order: "Stroke sits
under 急/綽 if there, else under Finger/Position, else under 泛音, else starts at -30". The
active cell has the ● dot and matches the canvas arrow. Columns left of the diagonal are
empty by construction (a part cannot attach to one typed after it) — the blank triangle is
itself informative.

Editing: type in a cell; click an empty cell to create the rule (defaults: base bottom →
my top, gap 0); `by glyph ▾` opens the existing GapEditor inline below the row; drag on the
canvas still edits the ● cell. Declaration order is *implied* by column order (nearest
first); a rule whose actual position in the list deviates gets a small ①②③ superscript and an
Advanced toggle "custom order" that reveals up/down arrows.

Data-model mapping: expresses every y rule with default edges; non-default edges show as a
footnote glyph (`⁽ᵗᵒᵖ⁾`) and are edited under Advanced; `base: "prev"` (Vertical word) is one
extra column "previous row". Cannot show *why* a cell is active without the preview — it is a
rule table, not a picture. Hides declaration order (and that is mostly right: in the current
data the order always equals nearest-first).

- Pro: the only option that shows all 37 rules on one screen; duplicates (Finger ≡ Position)
  become one merged column; holes (`注` has no rule after 泛音) are visible as `–`.
- Pro: trivially maps to the JSON; the engineer and the author read the same table.
- Con: it is a spreadsheet. The author thinks in pictures and strokes, not in cells; the
  Horizontal axis needs a second table; exceptions are still a click away.
- Con: a 6×6 grid with 7-row expanders gets tall when two cells are open.
- Effort: **S–M** (pure derivation over `layout.relationships`; reuses GapEditor).

### Option B — The ladder (resolved stack for the preview word, scenario chips)

Replace the per-part rule list with the *resolved* stack of the current preview word, one
tier per group of parts at the same height, the gap drawn between tiers as an editable chip.
Only the rules that are live for this word are shown; the inactive ones are one click away.

```
Spacing · Standard word          Preview: [勾▾] [名▾] [七▾] [急▾] [注▾] [五▾]    ⟲ random
┌─────────────────────────────────────────────────────────────────────────────┐
│  start height ───────────────────────────── [ 830 ] ▾                       │
│  ┌ 泛音 fy ───────────────────────────────┐                                  │
│  └────────────────────────────────────────┘                                  │
│      ↕ gap above Finger·Position, after 泛音     [ -30 ]                     │
│  ┌ Finger left ┐ ┌ Position hui ┐    ⇆ Position: 0 right of Finger          │
│  └─────────────┘ └──────────────┘                                            │
│      ↕ gap above 急/綽, after Position           [  0 ]                      │
│  ┌ 急/綽 jc ┐                                                                │
│  └──────────┘                                                                │
│      ↕ gap above Stroke, after 急/綽   for 勾/大  [ 120 ] ▾ by glyph (7)     │
│  ┌ 注 zhu ┐ ┌ Stroke right ★ ────┐   ⇆ 注: -24 below Stroke's top, for 勾/大 │
│  └────────┘ └────────────────────┘                                           │
│      ↕ gap above String, after Stroke's top  for 勾/大  [ -181 ] ▾ by glyph  │
│  ┌ String ┐                                                                  │
│  └────────┘                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Try without:  [☑ 泛音] [☑ Finger] [☑ Position] [☑ 急/綽] [☑ 注] [☑ String]  │
│ Other situations for Stroke ▾   (3 more rules: after Position, after 泛音, first)│
└─────────────────────────────────────────────────────────────────────────────┘
```

Reading: top to bottom is the word. Every number on screen is a number that is in effect
*right now*; the chip's sentence ("gap above Stroke, after 急/綽, for 勾/大") is the same
sentence the canvas arrow and the undo label use. Side-by-side parts are one tier; their
horizontal relation is a `⇆` chip on the right of the tier. A tier that is absent from the
preview is simply not drawn.

Editing:
- Change a gap: type in the chip, or drag the box on the canvas (unchanged behaviour; the chip
  is the "active rule" and gets the ● implicitly — it is the only one shown).
- Add an exception: `▾ by glyph` opens the existing exception list under the chip, with the
  current preview stroke pre-filled (§3.6 behaviour kept). The chip wears a "(7)" so the
  author knows a plain-looking number hides seven cases.
- See/create the rules for other situations: untick a part in **Try without** — the ladder
  re-resolves, the tier disappears, and the gap chip under the vanished tier is replaced by
  the rule that now applies (`after Position [10]`), highlighted for 1 s so the eye follows
  the change. If no rule exists for that situation the chip reads `no rule · Stroke is not
  placed  [+ add gap above, after Position]` and one click creates it. This is the
  *only* way to create a rule, and it is the right one: you cannot write a gap for a
  situation you are not looking at.
- Declaration order: hidden. The resolver's order (`chosen`) is the truth; "Other situations"
  lists the inactive rules for the selected part *in search order* with the words "tried
  first / then / then", and an Advanced reorder. In the current data the order is always
  nearest-above-first, so this list is mostly reassurance.

Data-model mapping: complete for y and for the two sanctioned x shapes. Rules with non-default
edges display their edge in the sentence ("after Stroke's top"). `prev` tiers in the Vertical
word render as "row 1 / row 2 / row 3" with one shared chip "gap between rows" (as §3.3
already specifies). Centering overlays as a dashed line through the centred tiers.

- Pro: nothing abstract — the author reads the word, not the rules. The combinatorics are
  tamed by making the *preview* the index into the rule set, which is also how the current
  canvas already works (the ● dot becomes the whole panel).
- Pro: side-by-side parts collapse into tiers, so Finger/Position stop being two parts with
  duplicate rules; an edit on the tier chip writes both `…←left` and `…←hui` rules (they are
  equal in all current data; if they ever differ the chip splits with an "unlink" under
  Advanced).
- Con: you never see all the rules at once; coverage ("did I set a gap for every situation?")
  needs the Try-without chips or the matrix (Option A) as a secondary view.
- Con: "Other situations" is a drawer the author may never open; the resolver's order must be
  explained once and then trusted.
- Effort: **M**. The resolver already gives positions and `chosen`; the tiering is a grouping
  of elements by resolved y (±1 unit) and the chips are the existing GapEditor.

### Option C — Scenario gallery

Every realistic shape of the word (the resolver can enumerate them; 96 for the Standard word,
far fewer that matter) rendered as a thumbnail; click one to make it the preview and edit the
gaps that apply there. For the selected part, thumbnails are grouped by *what is above it*.

```
Spacing · Stroke right ★ in Standard word      grouped by: what is above Stroke ▾
┌ after 急/綽 (24 shapes) ───┐ ┌ after Finger·Position (40) ┐ ┌ after 泛音 (8) ┐ ┌ first (4) ┐
│ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐  │ │ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐  │ │ ┌──┐ ┌──┐     │ │ ┌──┐ ┌──┐ │
│ │名七││泛名││ 七 ││ 急 ││…│  │ │ 名 ││ 七 ││名七││泛七││…│  │ │ 泛 ││ 泛 │     │ │ 勾 ││勾五│ │
│ │急勾││七急││急勾││ 勾 ││ │  │ │ 勾 ││ 勾 ││ 勾 ││ 勾 ││ │  │ │ 勾 ││勾五│     │ │    ││    │ │
│ └──┘ └──┘ └──┘ └──┘ └──┘  │ │ └──┘ └──┘ └──┘ └──┘ └──┘  │ │ └──┘ └──┘     │ │ └──┘ └──┘ │
│ gap 120 (勾/大) ▾ by glyph │ │ gap 10 (勾/大) ▾ by glyph  │ │ gap -21 ▾     │ │ start -30 │
└───────────────────────────┘ └───────────────────────────┘ └───────────────┘ └───────────┘
 stroke shown: 勾 ▾   (change to see every card with 挑, 歷 …)
```

Reading: each group *is* one rule; the thumbnails under it are the shapes that rule governs.
The author sees immediately that "after Finger·Position" is the common case (40 shapes) and
that the 泛音-only case is rare. A card drawn in red means "no rule reaches this shape".

Editing: the gap field under a group edits that rule; clicking a card loads it into the main
canvas (like the Test words strip does today) for drag editing. Adding a rule = a group that
exists only as a grey placeholder "after 泛音: no rule" with `+ add`. Exceptions: the stroke
selector at the bottom re-renders every card with that stroke and the gap fields switch to
that stroke's row, so "tune 歷 everywhere" is: pick 歷, walk the groups.

Data-model mapping: groups ≡ rules, cards ≡ shapes; declaration order is implicit in the
grouping (a shape appears only under the *first* rule whose base it contains), which makes
the semantics *visible* for the first time — reorder under Advanced and the cards migrate
between groups. Cannot show x and y at once; one axis at a time.

- Pro: the only option that makes "first rule whose base is present" something you can see
  rather than read. Excellent for coverage and for QA ("which shapes hit otherwise?").
- Pro: cheap thumbnails exist (`WordCanvas` at 72 px, as in the Test words strip).
- Con: heavy — 96 renders per part per stroke; needs a server endpoint that enumerates shapes
  per layout and resolves them in bulk. Scrolling a gallery to change one number is slow.
- Con: four groups with thumbnails take the whole inspector; works better as a full-width
  mode than as a side panel.
- Effort: **L** (shape enumeration + bulk resolve + a new screen).

### Option D — Canvas-first: connect the edges

No panel. Rules are drawn on the canvas as arrows; a rule is created by dragging the top edge
of a box to another box's bottom edge; its gap is edited by dragging the box; an exception is
made by switching the preview stroke and dragging again ("give 歷 its own gap").

```
          ┌fy────────┐                 ghost arrows (grey) = inactive rules of the
          └──────────┘                 selected part; solid red = active rule
     ┌left┐┌hui─┐     ┆ -30 (after 泛音, not in effect)
     │ 名 ││ 七 │     ┆
     └────┘└────┘
          ┌jc┐   ┆ 10 (after Position, not in effect)
          └──┘ ──┼── 120  after 急/綽, for 勾/大   ◄ drag the box to change
       ┌zhu┐┌right────────┐
       │ 注 ││     勾      │   ⟵ drag this box's top edge onto another box
       └───┘└─────────────┘      to attach it there instead / additionally
             ┌string┐
             └──────┘
   floating: [ 120 ] ▾ by glyph   ·   Stroke is 勾 ▾  ·  "give 勾 its own gap" ☐
```

Reading: the arrow *is* the rule; ghost arrows show the alternatives. Hovering a ghost reads
"after Position: 10 — in effect when 急/綽 is left out".

Editing: drag box = gap (exists today). Drag edge → edge = create rule (new). Toggle "give 勾
its own gap" before dragging = the drag writes an exception row for the current stroke instead
of the otherwise/plain value (the §3.7 toast, made a mode). Deleting a rule = select its arrow,
press Delete. Reordering = not available on canvas; falls to Advanced.

Data-model mapping: creates rules only between parts that are *both visible*, so to create
"Stroke after 泛音" the author must first tick 泛音 and untick 急/綽 and Position — the same
scenario dance as Option B but without the chips to prompt it. Edge choice is natural here
(drag *this* edge onto *that* edge), which is the one thing D does better than everyone.
Declaration order invisible; ghosts show existence, not priority.

- Pro: zero vocabulary. The author points at the thing and moves it.
- Pro: edges are explicit — the only option where "measured from Stroke's top" is obvious.
- Con: discoverability (edge handles, modifier toggles), precision (one unit = one pixel at
  some zoom), and crowding: `right` already has four y rules; four ghosts plus x arrows is a
  hairball. The author cannot answer "what gaps have I set?" without hovering everything.
- Con: largest build: hit-testing edges, link gestures, ghost rendering, arrow selection.
- Effort: **L**.

### Option E — Stroke table (exceptions first)

The variable that dominates the Standard word is the right-hand stroke. Put it on the rows,
and on the columns every gap that depends on it. One screen tunes 勾 vs 挑 vs 歷 everywhere.

```
By stroke · Standard word          (8 gaps depend on the stroke; 29 others do not)
                   │ Stroke ↕ after │ Stroke ↕ after │ Stroke ↕ after │ 注 ↕ from  │ String ↕ from│ 注 ⇆  │ String ⇆ │
 stroke family     │   急/綽        │ Finger·Position│   泛音         │ Stroke top │ Stroke top   │ Stroke│ Stroke   │
───────────────────┼────────────────┼────────────────┼────────────────┼────────────┼──────────────┼───────┼──────────┤
 [打摘][勾剔]       │     -70        │    -160        │    -221        │   -104     │    -181      │   57  │   128    │
 [劈][掐起]         │      60        │     -30        │    -113        │    -60     │    -230      │    5  │   155    │
 [挑][托]           │      50        │      10        │    -113        │    -60     │    -120      │   -5  │   177    │
 [抹][抹挑][掩][輪][半輪]│  -40       │     -30        │    -161        │   -100     │    -385      │   77  │   155    │
 [勾][大] ●         │     120        │      10        │     -21        │    -24     │    -181      │   77  │   128    │
 [剔][摘]           │     -40        │     -90        │    -201        │    -24     │    -180      │   77  │   130    │
 [歷]               │      60        │     -30        │    -113        │    -60     │    -240      │    5  │   155    │
                   │                │                │                │            │              │       │  two strings: top -70 · bottom -450
───────────────────┼────────────────┴────────────────┴────────────────┴────────────┴──────────────┴───────┴──────────┤
 otherwise          │  (none: every stroke is in a family)                                   [+ family] [+ otherwise] │
 ● = preview stroke  ·  click a row to preview that stroke  ·  click a column head to select that part on the canvas
```

Reading: a row is "what 歷 does to the word"; a column is "the gap above Stroke, after
急/綽, for every stroke". The thumbnails make it a calligrapher's table, not an engineer's.
The ● row is the preview; the ● row × the selected part's column is the canvas arrow.

Editing: type in a cell (edits one exception row's `value`); drag on canvas edits the ● cell
of the active column, same as today. Row operations are the new power: `+ family` adds a row
to *all eight* lists at once (copying the otherwise/nearest values); dragging a glyph chip
from one row to another moves it in all eight lists; deleting a row asks "fold into
otherwise?". The `two strings` line is the `string_top/bottom` special case (only 歷, no
otherwise), shown as a sub-row rather than hidden.

Data-model mapping: a *derived* view. The UI partitions the glyphs by the when-sets, and as
long as every list uses the same partition (true today) the table is lossless. If a list
diverges (someone edits one list in JSON), that column shows `split` cells with a disclosure
to the raw list; the table never writes a partition it cannot read back. Rule order within a
list is irrelevant when the families are disjoint, so declaration order is hidden *and*
genuinely immaterial here — the only option where hiding it costs nothing. A later schema
version could name the families (`"groups": {"gou_da": [...]}`) and reference them from the
lists, shrinking the JSON eightfold; the UI would not change.

- Pro: this is the author's actual mental model ("勾 sits lower than 挑"). The eight
  exception lists become one table with 56 numbers instead of eight scattered lists.
- Pro: consistency enforced structurally: a stroke cannot be in family X for one gap and Y
  for another by accident.
- Con: covers only glyph-dependent gaps (8 of 37 rules). It is a second view, not the
  Spacing panel; the 29 unconditional rules still need A or B.
- Con: a 7×8 numeric grid is dense; needs row-hover highlighting and the thumbnails to stay
  readable. Chord and Vertical words have no stroke dependence, so the tab is empty there.
- Effort: **M** (partition detection + a table; writes go through the existing `gap` lists).

### Comparison

```
                        A matrix   B ladder   C gallery   D canvas   E stroke table
 reads as a picture       no        yes        yes         yes        thumbnails
 all rules at once        yes       no         per part    no         exceptions only
 shows "which is active"  dot       implicit   by group    arrow      dot
 shows rule order         implied   hidden     visible     hidden     immaterial
 creates rules            cell      scenario   placeholder edge drag  n/a
 exceptions               expander  expander   per stroke  mode       native
 cross-rule consistency   no        tiers      no          no         families
 effort                   S–M       M          L           L          M
```

## 3. Recommendation

Build **B (ladder) as the Spacing panel**, with **E (stroke table) as a second tab** of the
same panel, and keep **A (matrix) as the Advanced "all rules" view** that replaces today's
raw list. Skip C and D: C's value (seeing which shapes a rule governs) is delivered more
cheaply by B's Try-without chips plus a count on each "other situation" ("after Position ·
40 shapes"), and D's one unique strength (edge choice) is an Advanced detail.

Why this combination: the three views answer the three questions in §1. The ladder answers
"what is in effect for this word" (and makes the preview the navigation, which is how the
canvas already behaves). The stroke table answers "what does the stroke change", which is the
author's daily tuning task and the source of 70 of the ~110 numbers in the layout. The matrix
answers "have I covered everything", for the engineer and for the audit before a build.

Panel layout:

```
┌ Spacing ─────────────────────────────────── [This word] [By stroke] [All rules ⚙] ┐
│  (B)                      (E)                (A, Advanced)                        │
```

Migration from the current panel, in order:

1. **Tiering and the ladder, read-only numbers.** Group resolved elements by y; render tiers
   and the active gap chips using `editor.activeRel` and `GapEditor` unchanged. The canvas
   drag, the ● semantics (now "the chip that is shown"), the arrow label sentence and the undo
   labels are all kept verbatim — the chip's sentence should be generated by the same function
   as the drag label so they can never drift.
2. **Try-without chips** = the Structure checkboxes, duplicated at the bottom of the panel
   (or, better, the Structure checkboxes move down and the Structure panel shrinks to the
   glyph selectors, since the ladder now shows the stack). "No rule" placeholder with
   `+ add gap above, after X` replaces the `+ Add rule relative to…` dropdown.
3. **Other situations drawer** per selected part, in search order, with shape counts from
   `/api/dynamic/rule_count`-style data; Advanced reorder lives here.
4. **By stroke tab**: partition detection, table, row operations. Ship after 1–3; the author
   can already tune strokes through the ladder's `by glyph` expander in the meantime.
5. **All rules tab**: the matrix, Advanced only; delete the current per-part list.
6. Later, optional: named glyph families in the schema; `string_top/bottom` folded into the
   stroke table as a sub-row.

What to keep from today's panel, explicitly: canvas drag editing the active rule, axis lock,
↑↓ nudge, the ● dot concept (now the ladder chip), the toast "give 歷 its own exception"
(becomes the default of `by glyph` → add), undo per field/drag/row, and the shadow detection
in the exception list (struck-through glyph already caught by an earlier row).

## 4. Where glyph membership lives in the Layouts context

The author wants, when a part is selected, to "see all possible glyphs, and within all
possible glyphs add, remove, edit". Today that is a preview-glyph `<select>` in the Structure
row; the member grid is on the Areas screen.

Candidates:

- **Structure row expands into the member grid.** Keeps everything in one panel, but the
  inspector is 460 px wide: 147 Position glyphs at 56 px is ~20 rows, pushing Spacing off
  screen. The one panel that must stay visible while tuning is the one it would bury.
- **Slide-over of the Areas screen.** No duplication, full feature set (keys, box size), but
  it covers the canvas — and the whole point of seeing the glyphs *here* is to click one and
  watch the word change.
- **Glyph tray under the canvas.** (recommended) A strip between the status line and the
  Test words strip, showing the selected part's members as thumbnails. Clicking one sets the
  preview glyph; the strip is wide (the canvas column), stays visible, and sits next to the
  thing it changes.

```
┌ Canvas ───────────────────────────────────────────────────────────────────┐
│                               (word)                                       │
├───────────────────────────────────────────────────────────────────────────┤
│ Stroke right · drag to change its active rule                              │
├ Glyphs of Stroke right (16) · shared by Standard word, Chord ──── Manage ☐ ┤
│ [勾]● [挑] [大] [剔] [摘] [劈] [掐起] [托] [抹] [抹挑] [掩] [輪] [半輪] [歷] [打摘] [勾剔] │
│  ▲ preview                     colour band = stroke family (By stroke tab) │
├ Test words ───────────────────────────────────────────────────────────────┤
```

With **Manage** on:

```
├ Glyphs of Stroke right (16) · shared by Standard word, Chord ──── Manage ☑ ┤
│ [勾×] [挑×] [大×] [剔×] … [歷×]   [+ Add glyphs]   Typing keys → Areas       │
```

States:

- **1 glyph** (`注 zhu`, `泛音 fy`): one chip, preview fixed; the tray still shows so the
  author learns the part has one glyph and can `+ Add`. Height: one row.
- **2–20 glyphs** (`jc`, `right`, `string`, `chord`): one wrapping row at 32 px chips, no
  search. For `right`, chips are tinted by stroke family so the tray doubles as the legend of
  the By stroke tab; a glyph in no family is outlined red ("hits otherwise / no rule").
- **147 glyphs** (`hui`, `char`): two rows of chips, a search field (name / key / pinyin —
  reuse `GlyphSetPicker`'s matcher) and a `show all ▾` that grows the tray to a scrollable
  drawer of at most 40 % of the canvas height. The preview chip is always scrolled into view.
- **Part not selected**: the tray collapses to one line "Select a part to see its glyphs".
- **Manage on**: × on each chip (with the same `referenced()` confirm as Areas — "named in
  N exception rows"), `+ Add glyphs` opening the same picker dialog, and a link to the Areas
  screen with `?area=hui&g=md_7` for typing keys, box size and label. Removing the previewed
  glyph re-pins to the first member.

No duplicated logic: extract from `routes/areas/+page.svelte` an `AreaMembers.svelte`
(chip/grid rendering, remove with the `referenced` check, `syncCatalog`) and an
`AddGlyphsDialog.svelte` (the current modal), used by both screens with a `dense` prop for
the tray. `referenced()` and `syncCatalog()` move to `$lib/state.svelte.ts`. The tray edits the
*area* (shared by every word type that uses it), and says so in its header, which is also
where the author discovers that Position in the Chord and in the Standard word are one set.

Why under the canvas and not in the inspector: the inspector is for *rules*, the canvas
column is for *what the word looks like*; glyph choice belongs to the second. It also gives
the Structure panel a reason to lose its `<select>` (the tray replaces it; the row keeps the
small preview thumbnail as a button that focuses the tray), which shortens the inspector
exactly when the ladder needs the room.
