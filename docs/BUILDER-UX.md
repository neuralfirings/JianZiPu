# JZP Font Builder — UX design

Local SvelteKit app served by the Python dev server (`python3 -m jzpbuild.devserver`).
One user, no accounts, writes repo files. Edits `dynamic_positioning/layouts_data.json`
(layouts, areas, spacing) and `inputs/components.csv` (glyph → area membership, typing keys).
Reads `inputs/svg/` (222 SVGs). Builds `JianZiPu.ttf`.

Builds on `docs/UX-REVIEW.md` (terminology, area-first position panel, drag labelling,
badge scope) and `docs/ARCH-REVIEW.md` §2.3 (slots with alternatives; badge at 80 % / 95 %
per main-glyph lookup). Those findings are taken as given and not re-argued here.

**One design decision drives everything below:** the engine's new model is a *chain*
(first glyph gets a fixed height, each later glyph hangs under the previous one, x is per
part). So the editor never asks the user to draw a graph. The user edits a **stack**: an
ordered list of parts, a gap between each neighbouring pair, and one horizontal position per
part. The prototype's click-edge→click-edge relationship creation is dropped; its
drag-to-set-gap, exception list, typing-order list and budget badge are kept.

---

## 1. Information architecture

```
┌ JZP Font Builder ────────────────────────────────────────────────────────────┐
│  Glyphs   Areas   Layouts   Test & Build          ● Unsaved (3)  Save ⌘S  ⋯ │
└──────────────────────────────────────────────────────────────────────────────┘
                                                        ⋯ = Import… / Export… / Reload from disk / Open repo folder
```

| Section | Question it answers | Writes |
|---|---|---|
| **Glyphs** | What shapes exist on disk? Which are unused? How is each typed? | the glyph editor (`/glyphs/<name>/edit`, `/glyphs/new`): outlines, imports, traces; the Typing view: `components.csv` (see `docs/KEY-ENTRY-UX.md`) |
| **Areas** | Which glyphs can stand in which part of a word? | `design.json` |
| **Layouts** | How are parts stacked and spaced for each word type? | `layouts_data.json` |
| **Test & Build** | Does it look right in real words, in the real font? | `JianZiPu.ttf` (build output) |

Links between sections (all deep-linkable, `#/layouts/standard?part=zhu&word=s7\k5`):

- Glyph tile → "Used in: left, char" chips → **Areas/left** with that glyph highlighted.
- Area member chip → "Appears in: Standard word, Vertical word" → **Layouts** with that part selected.
- Any rendered test word (Layouts strip or Test) → click → opens **Layouts** on the word type that
  word resolves to, with the word loaded as the preview word and its glyphs pinned.
- Budget badge → click → **Layouts** sidebar expands "Font budget" breakdown.
- Build error naming a glyph or rule → link to the exact part/rule.

Global, always visible: save state chip, Save, overflow menu, Undo/Redo (⌘Z / ⇧⌘Z) in the
header of every editing section. Layouts and Areas are desktop-only (≥ 1100 px); below that
show "Best on a larger screen" with the Glyphs and Test sections still usable.

---

## 2. Screens

### 2.1 Glyphs

```
┌ Glyphs ──────────────────────────────────────────────────────────────────────┐
│ [Search  gou · k · 勾 · pinyin]        Group ▾  Area ▾  ☐ Unassigned only     │
│ ┌ Groups ─────────┐ ┌──────────────────────────────────────────────────────┐ │
│ │ All         222 │ │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐   │ │
│ │ Right-hand   16 │ │  │ 勾 │ │ 大 │ │ 剔 │ │ 摘 │ │ 歷 │ │ 挑 │ │ 抹 │   │ │
│ │  strokes (lg_)  │ │  │    │ │    │ │    │ │    │ │    │ │    │ │    │   │ │
│ │ Fingers,    194 │ │  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘   │ │
│ │  numbers (md_)  │ │  lg_gou  lg_da   lg_ti  lg_zhai  lg_li  lg_tiao lg_mo │ │
│ │ Chords (xl_)  8 │ │  k·right l·right i·right o·right U·right j·right …   │ │
│ │ Modifiers     4 │ │  ┌────┐ ┌────┐                                       │ │
│ │ ───────────     │ │  │ 7.5│ │ 8  │  ◌ md_7.5  no area yet                │ │
│ │ Unassigned  130 │ │  └────┘ └────┘                                       │ │
│ └─────────────────┘ └──────────────────────────────────────────────────────┘ │
│ ┌ Inspector: 勾 lg_gou ──────────────────────────────────────────────────────┐│
│ │  ┌──────────┐  Typed as   k · 勾                                          ││
│ │  │          │  In areas   [right ×]                      + Add to area ▾  ││
│ │  │    勾    │  Box        660 × 660 (from area "right")                    ││
│ │  │          │  File       inputs/svg/lg_gou.svg  · 2 paths · 1.9 KB        ││
│ │  └──────────┘  Seen in    [s7k5] [大七勾一] [fy>\k5]   → open in Layouts     ││
│ │  [Edit design  🔒 soon]  [Replace SVG  🔒 soon]  [Download SVG]             ││
│ └────────────────────────────────────────────────────────────────────────────┘│
│                                              [+ Upload SVG  🔒 soon]          │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Primary action: *select a tile* (opens the inspector strip; grid stays). No destructive
  actions on this screen.
- Secondary: "Add to area" (same data as Areas screen; writes `components.csv`), "Download SVG".
- Tiles: glyph rendered from the SVG at 96 px in a 120 px cell, name under it, then
  `key · area` in muted text. Unassigned tiles get a dotted ring and "no area yet"; the
  Unassigned group is pinned at the bottom of the group list because 130 of 222 SVGs
  (the `md_N.M` decimal hui set) are in this state today and the user must see it.
- Group names lead with meaning, prefix in parentheses. Hui decimals (`md_7.5`) are a sub-group
  under Fingers & numbers, collapsed by default.
- Empty: search with no hits → "No glyph matches ‘xyz’. Try the pinyin (gou) or the key (k)."
- Loading: tiles render as 120 px skeleton squares; SVGs stream in (one `/api/svgs` call,
  ~222 items; render progressively, don't block on all).
- Error: `inputs/svg/` unreadable → full-panel notice "Can't read inputs/svg/ — is the dev
  server running from src-fonttools/?" with a Retry button.
- **Glyph editor (built 2026-10-17, design in `docs/GLYPH-EDITOR-UX.md` /
  `glyph-editor-ux.html`).** Every tile has an **Edit** button (hover / selected; double-click or
  Enter also opens it); the inspector has **Edit outline**, **Replace from file…** and **Trace from
  image…**; the toolbar has **+ New glyph** (name, area = box, start from blank / SVG / image) and the
  font-wide **Reference weight** (`design.json` → `glyph_weight`, units; today's glyphs sit around
  28–45). The editor takes over the main window as a route and keeps the app header; the glyph has its
  own undo and **Save glyph** (⌘S, writes `inputs/svg/<name>.svg` at once, hash-checked, conflict
  dialog); the header's Save reads "Save design" there. One pointer tool (a selected shape shows its
  points), Pen, Pencil, Rectangle, Ellipse, Hand, Zoom. Open paths are lines at the reference weight and
  are outlined on save. Combine ∪ − ∩ ⊕ (hover previews), Simplify and Thicken popovers with live
  preview, Outline line, Clean up, flips, numeric position / size / scale / rotate. Compare overlays in
  translucent blue: reference dot (D), another glyph (G, same-area chips), last saved (L). Import SVG
  (file, drop, paste) with fit / keep-size and replace / add; trace JPG / PNG with potrace (threshold +
  Auto, specks, corners, simplify, light-on-dark, placement). In-context strip renders the unsaved outline
  in real words. Checks: empty, outside the box, open lines, specks, "as built" flatten. Leave guard on
  every way out; a browser draft per glyph survives reloads. New glyphs join their area on first save
  (a design change).

### 2.2 Areas

```
┌ Areas ───────────────────────────────────────────────────────────────────────┐
│ ┌ Areas ────────────┐ ┌ left · Finger ──────────────────────────────────────┐│
│ │ fy      1  泛音    │ │ Name  left        Shown as  Finger   Box  350 × 350  ││
│ │ left    5  Finger  │ │ Used in  Standard word · Vertical word · Chord (left) ││
│ │ hui    21  Position│ │                                                      ││
│ │ jc      2  急/綽   │ │ Members (5)                          + Add glyphs ▾  ││
│ │ zhu     1  注      │ │ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐                  ││
│ │ right  16  Stroke  │ │ │ 名 │ │ 中 │ │ 食 │ │ 大 │ │ 跪 │                  ││
│ │ string  7  String  │ │ └────┘ └────┘ └────┘ └────┘ └────┘                  ││
│ │ char   40  Vert.   │ │  s ×    d ×    f ×    v ×    x ×                     ││
│ │ chord   8  Chord   │ │                                                      ││
│ │ bar     1  |       │ │ Typing keys for 名 md_ming                           ││
│ │ ──────────────     │ │   key [s]  alt [ ]  简 [名]  繁 [ ]  pinyin míng       ││
│ │ + New area  (adv.) │ │   ⚠ "0" is also a key in area "char" — fine, GSUB     ││
│ └───────────────────┘ │     picks by context.                                 ││
│                       └──────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

- One row per `components.csv` area column, display name editable ("Shown as") and used as
  the label everywhere else in the app; the column id stays visible in muted text.
- Primary action: **Add glyphs** → picker dialog: the Glyphs grid filtered to glyphs not yet
  in this area, multi-select, search by name/key/char/pinyin, "Add N". Each member chip has an
  `×` (remove from area; confirm only if the glyph is referenced by a spacing exception:
  "lg_gou is named in 7 spacing exceptions in Standard word — remove anyway? Those rows will
  be dropped.").
- Selecting a member shows how it is typed, read-only, with "Edit in Glyphs →". *(Superseded
  2026-10-17: the typing-keys editor that was here moved to Glyphs → Typing, where a clash
  holds Save; see `docs/KEY-ENTRY-UX.md`.)*
- Box size is edited here and only here ("Used in" tells the user what will move). Changing it
  re-resolves every open preview; the Layouts screen shows the change immediately.
- "+ New area" is under an "Advanced" divider: new areas need a new `components.csv` column
  and engine support; the dialog says so ("Creates column area_<name>; the build must know
  about it. Usually an engineer's job.").
- Empty: an area with no members → "No glyphs yet. Add glyphs so words can use this part."
- Error on save: csv write fails → inline red bar on the chip row with the server's message;
  the edit stays in the unsaved set.

### 2.3 Layouts (the editor; detail in §3)

```
┌ Layouts ───────────────────────────────────────────── Font budget ● 7 % ok ──┐
│ ┌ Word types ──┐ ┌ Canvas ─────────────────────────────┐ ┌ Inspector ──────┐│
│ │ ● Standard   │ │  Preview with: [勾 ▾] [名 ▾] [七 ▾]… │ │ Structure       ││
│ │   word       │ │  boxes ◉ glyphs ○   + −  fit        │ │ ┌ Stack ───────┐││
│ │   Vertical   │ │ ┌──────────────────────────────────┐ │ │ │ ☑ 泛音 fy    │││
│ │   word       │ │ │        ┌fy────┐                  │ │ │ │ ☑ Finger left│││
│ │   Chord      │ │ │        └──────┘  ↕ 0             │ │ │ │ ☑ Position   │││
│ │              │ │ │   ┌left┐┌hui─┐                   │ │ │ │ ☑ 急/綽 jc   │││
│ │ Duplicate    │ │ │   │ 名 ││ 七 │                   │ │ │ │ ☑ 注 zhu     │││
│ │ + New (adv.) │ │ │   └────┘└────┘  ↕ 10            │ │ │ │ ★ Stroke     │││
│ │ ───────────  │ │ │        ┌jc┐                      │ │ │ │ ☐ String     │││
│ │ Page center  │ │ │        └──┘   ↕ gap 勾/大: 66     │ │ │ └──────────────┘││
│ │  x 500 y 500 │ │ │     ┌zhu┐┌right──────┐           │ │ │ Spacing: 注 zhu ││
│ │ Center word  │ │ │     │ 注 ││    勾     │           │ │ │  Above: Stroke  ││
│ │  ☑ vertical  │ │ │     └───┘└───────────┘           │ │ │  gap  [66] ▾    ││
│ │  ☐ horizontal│ │ │         ┌string┐                 │ │ │  Horizontal     ││
│ │              │ │ │         │  五  │                 │ │ │  [66] right of  ││
│ │              │ │ │         └──────┘                 │ │ │   Stroke's left ││
│ │              │ │ └──────────────────────────────────┘ │ │ Centering rows  ││
│ └──────────────┘ │  ⓘ Dragging 注 changes "gap above,  │ └─────────────────┘│
│                  │    for 勾/大": 66 → 72               │                    │
│ ┌ Test words ─────────────────────────────────────────────────────────────┐  │
│ │ [s7k5 fys9k5 大七勾一 s7>\k5 …                 ] Sample set ▾  Random   │  │
│ │  ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐   ← rendered as boxes+glyphs, 120 px     │  │
│ │  └──┘ └──┘ └──┘ └──┘ └──┘ └──┘      interpreted keys under each word     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Primary action: select a part (click a box or a Stack row) and change its gap (drag or
  number). Secondary: toggle optional parts on/off for the preview, change preview glyphs,
  edit exceptions, reorder (Advanced), centering.
- Loading: the canvas renders last-known positions greyed with "Updating…" until the server
  resolve returns (`/api/dynamic/resolve`, ~50 ms locally; debounce drags at 60 ms).
- Error: resolver failure is shown *on the part*: red outline on the box, red row in the Stack,
  and the message in plain words in the Spacing panel ("注 can't be placed: no gap is set for
  when the part above it is 急. Add a value or an ‘otherwise’ row."). Never a bare traceback;
  the traceback is behind a "details" disclosure.
- Empty (new word type): canvas shows a dotted page outline and "Add parts to the Stack to
  start"; the Stack panel has the Add-part control focused.

### 2.4 Test & Build

```
┌ Test & Build ────────────────────────────────────────────────────────────────┐
│ Render with  ◉ Live preview (boxes, unsaved rules)  ○ Built font  JianZiPu.ttf│
│              built 14:02 from saved files · ⚠ 3 unsaved changes not in font  │
│ [Build font]  ▸ last build: ok, 12.4 s                                       │
│ ┌ Sample sets ──┐ ┌────────────────────────────────────────────────────────┐ │
│ │ Basic words   │ │  [type words: s7k5 名七勾五 :fenkai C03|s6,5           ] │ │
│ │ Decimals      │ │  Size ◦───●───◦ 96 px     ☐ show boxes   ☐ compare both │ │
│ │ Modifiers     │ │                                                        │ │
│ │ Chords        │ │   名      泛      大                                    │ │
│ │ Vertical      │ │   七     名九     七                                    │ │
│ │ Chinese input │ │   勾      勾      歷                                    │ │
│ │ Edge cases    │ │   五      五     四三                                   │ │
│ │ + My set      │ │  s7k5    fys9k5   v7U43      ← interpreted keys        │ │
│ └───────────────┘ │  click a word → open its word type in Layouts           │ │
│                   └────────────────────────────────────────────────────────┘ │
│ ┌ Build log (collapsed) ─────────────────────────────────────────────────────┐│
│ │ ✓ base font  ✓ glyphs 222  ✓ GSUB  ✓ GPOS 20 lookups  ✓ wrote JianZiPu.ttf ││
│ └────────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

- Two render modes, same word list, same size slider. "Built font" loads the latest build's
  exact file (`/api/builds/<id>/JianZiPu.ttf`) via `FontFace` under a family name of its own
  (`JZP-build-b3`), with no fallback family, so an installed JianZiPu can never stand in; "Live preview" draws
  boxes/glyphs from the resolver (what the Layouts strip does). "Compare both" renders each
  word twice, side by side, so a drift between preview and font is visible.
- **Build font** is the one long action in the app. States: idle → running (progress steps as
  they stream; usually 12 s) → ok (font reloads automatically, timestamp updates) → failed
  (the plain-language cause first: "The rules for 歷 are too large for the font format (71 KB,
  limit 64 KB). Remove some ‘depends on glyph’ rows in Standard word." then the raw log).
  Build does not require saving first; it builds from the saved files and says so. If there
  are unsaved changes, the button reads "Save & build".
- Every build writes to its own temp folder. A row under the toolbar shows the latest one
  (id, size, time) with **Download JianZiPu.ttf** and **Open in Tester ↗**; "N earlier builds"
  folds out the rest of the session's builds (last 8 kept, removed when the server stops).
- **Tester** (`/tester?build=<id>`, in the nav): free text in one exact font, picked from this
  session's builds or opened from a `.ttf` on disk, with size, liga/kern switches, vertical
  columns, sample sets and an optional second font beside it. The chip names the file that is
  rendering.
- Sample sets are the groups in `font_tester.html`; "My set" is stored in the app's local
  draft and included in export.
- Phone-usable (this is the only section that needs to be).

### 2.5 Import / Export (dialog from the ⋯ menu)

```
┌ Export ─────────────────────────────────┐  ┌ Import ───────────────────────────────┐
│ One file with everything the Builder    │  │ Drop a .json here or [Choose file]    │
│ edits:                                   │  │                                       │
│  ☑ Word types & spacing (3)             │  │ jzp-builder-2026-10-15.json           │
│  ☑ Areas: box sizes & glyph members (10)│  │  3 word types · 10 areas · 27 rules   │
│  ☑ Typing keys (92 glyphs)              │  │  Differences from what's loaded:      │
│  ☑ Test word sets (2)                   │  │   • Standard word: 4 gaps differ      │
│  ☐ Include SVG files (zip, 1.1 MB)      │  │   • area "hui": +2 glyphs             │
│                                          │  │   • Vertical word: new                │
│ [Download jzp-builder-2026-10-15.json]  │  │  ◉ Replace everything                 │
└──────────────────────────────────────────┘  │  ○ Merge: keep mine, add what's new   │
                                              │  ○ Pick per item ▾                    │
                                              │  [Import]  (becomes unsaved changes)  │
                                              └───────────────────────────────────────┘
```

The exported file is a superset of `layouts_data.json` (same `layouts`, `area_sizes`,
`center_*` keys, so the engine can read it directly) plus `areas.members`, `areas.keys`
(the `components.csv` columns) and `test_sets`. Import never writes to disk by itself;
it lands in the unsaved set so the user can inspect it in the editor and Save or Discard.

---

## 3. The layout editor in depth

### 3.1 Vocabulary: engine term → UI label

| Engine | UI label (en) | zh (short) | Where it appears |
|---|---|---|---|
| layout / topology (`default_jzp`, `chord_left`…) | Word type: *Standard word*, *Vertical word*, *Chord* | 標準字 / 直排字 / 撮 | Word types list; id in muted text |
| area | Part (of a word); the Areas section keeps "Area" as the noun for the reusable definition | 部件 / 區域 | everywhere |
| `order` | Stack (typing order) | 堆疊順序 | Structure panel |
| `optional: true` | ☑ checkbox "can be left out" | 可省略 | Stack row |
| pivot (and anchor) | ★ Main glyph — "the glyph that tells the font which word type this is" | 主筆 | Stack row, canvas tag |
| relationship (y, elem ← base) | Gap above (between this part and the one above it) | 上方間距 | Spacing panel, canvas arrow |
| relationship (x) | Horizontal position: "fixed at N" or "N right of ★'s left edge" | 水平位置 | Spacing panel |
| `base=None` gap | Start height (only the top part has one) | 起始高度 | Spacing panel of the first part |
| gap list / buckets | Exceptions ("depends on which glyph") | 依字形而定 | Spacing panel |
| `base_signifiers` / `elem_signifiers` | "when the part above is …" / "when this part is …" | 當上方是… / 當本身是… | exception row |
| catch-all | Otherwise | 其他情況 | pinned last row |
| `vertical_center_order` | Centering rows | 置中行 | Centering panel |
| `horizontal_center`, `center_x/y` | Center word: ☑ vertically ☐ horizontally · Page center x/y | 置中 | sidebar |
| `selector.contains` | Recognised by: [勾][大][剔]… (glyph chips; keys in tooltip) | 識別字形 | Structure panel header |
| slot with alternatives (`one_of`) | "holds one of: …" | 其中之一 | Vertical row template, String slot |
| repeated slot (`char_1..4`) | Rows × up to 4 | 列 | Vertical word |
| segments (`chord_left` / `chord_right`) | Left side · Right side | 左側 / 右側 | Chord |
| `estimate_dynamic_pos_bytes` | Font budget | 字型容量 | header badge |

Engine ids are never hidden: every label has the id in 11 px muted text next to it (`注 zhu`,
`Standard word · default_jzp`), so a user reading the JSON or an engineer reading the screen
can match them.

### 3.2 Structure panel: Standard word

```
Structure                                   Recognised by  [勾][大][剔][摘][歷][挑][抹]… ▾
┌ Stack (typing order) ─────────────── Advanced: reorder 🔒 ┐
│ ⠿ ☑ 泛音  fy        can be left out                       │
│ ⠿ ☑ Finger left     can be left out                       │
│ ⠿ ☑ Position hui    can be left out                       │
│ ⠿ ☑ 急/綽  jc       can be left out                       │
│ ⠿ ☑ 注     zhu      can be left out                       │
│ ⠿ ★ Stroke right    main glyph                            │
│ ⠿ ☐ String          holds one of: [String] [Two strings ▾] │
│                                                 + Add part ▾ │
└──────────────────────────────────────────────────────────────┘
```

- The checkbox is the *preview* toggle (the prototype's eye icon) **and** shows optionality:
  a part that cannot be left out has no checkbox, only ★ or a dot. Toggling a checkbox
  re-resolves the canvas so the user sees what happens when that part is absent — this is
  how a non-expert discovers that "gap above" depends on *which* part is above.
- Reordering (drag handles) and marking optional/main are behind **Advanced** (a toggle at the
  panel top, remembered per session). The reason is shown when hovering the lock: "Typing
  order defines how words are recognised. Change it only when the input rules change."
- "holds one of" is the slot-with-alternatives from ARCH-REVIEW: the String slot is
  `[string] | [string_top, string_bottom]`; the user sees two alternative chips and picks which
  one the preview uses.

### 3.3 Structure panel: Vertical word (repeated rows)

```
Structure · Vertical word (vert)            Recognised by  [：]
┌ Rows ────────────────────────────────────────────────┐
│ A vertical word has 1 to [4] rows, stacked top down.  │
│ Each row holds one of:                               │
│   ◉ one glyph        from  [Vertical glyphs char ▾]  │
│   ◉ finger + position  [Finger left ▾] + [Position hui ▾] │
│ Gap between rows  [ 40 ] ▾                            │
│ Gap inside a finger+position row  [ 0 ] ▾             │
│ Preview with  [3] rows:  row 1 [上 ▾]  row 2 [名 ▾][九 ▾]  row 3 [進 ▾] │
└──────────────────────────────────────────────────────┘
```

- The user never sees `char_1`, `left_2`, `hui_2`. The app expands the row template into
  numbered slots when it writes JSON and collapses them when it reads (any `_N` suffix on a
  known area name, as `signifiers.csv_column_for` already does).
- "Gap between rows" is one rule applied to every row boundary; a per-boundary override is
  available under Advanced ("different gap after row 1") because the data model allows it, but
  the template is the default and keeps the budget flat (16 combos for 4 rows).
- The main glyph is the invisible `：` control glyph; it is shown as a row-0 chip "starts with
  ：" and is not selectable or movable. Its start height is the "Start height" of the stack.
- Centering rows are generated: each row is one centering row.

### 3.4 Structure panel: Chord (two segments)

```
Structure · Chord (chord_left + chord_right)    Recognised by  [撮][大撮][反撮][雙彈]… ▾
┌ Chord glyph  ★ ─────────────────────────────────────────────┐
│ ┌ Left side (under the chord's left) ┐ ┌ Right side (after |) ┐ │
│ │ ☑ 泛音 fy      can be left out     │ │ ☑ 急/綽 jc  can be left out │ │
│ │ ☑ Finger left  can be left out     │ │ ● Position hui             │ │
│ │ ☑ Position hui can be left out     │ │ ● String                   │ │
│ │ ☑ 急/綽 jc     can be left out     │ │                            │ │
│ │ ☑ 注 zhu       can be left out     │ │  bar "|" is typed between   │ │
│ │ ● String                           │ │  the two sides             │ │
│ └────────────────────────────────────┘ └────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

- One screen entry "Chord" edits the two engine layouts together (`chord_left` keyed on the
  chord glyphs, `chord_right` keyed on `|`). The user sees one word; the canvas shows both
  sides with the `|` bar drawn as a thin dotted divider. Selecting a part on either side opens
  its Spacing panel; the JSON writer puts it in the right entry.
- Each side is an independent stack hanging from the chord glyph's bottom edge (left) or from
  the bar (right). Their first parts' "Start height" is labelled "Below the chord glyph:
  N" / "Below the bar: N".

### 3.5 Spacing panel (selected part) — built as the rule builder (2026-10-15)

Superseded the gap-row sketch below by the design in `docs/rule-builder-ux.html`
(chosen by the user after the canvas-first "Option D" of `SPACING-UX-OPTIONS.md`).
What is built, in `app/src/lib/components/{WordStrip,RulePanel,RuleEditor}.svelte`:

- **Word strip** at the top of the inspector: one chip per part of the preview word
  (click = select; × leaves an optional part out; a dashed chip puts it back).
- **Spacing · part** with ↕ Vertical / ⇆ Horizontal tabs. A row of **base pills** shows the
  chain of candidates in search order ("relative to [● 急/綽 modifier] else [徽 position]
  else [Left hand] else [start −30] + ▾"). Red = in effect for the preview word; dashed =
  that part is not in the word. Clicking a pill that is not in effect edits the preview
  word so it is (earlier optional bases are left out, an absent base is put back) and shows
  that base's rules. Pills drag to reorder the search; `+ ▾` adds a base; `remove ×`
  drops one. The edge sentence ("Right hand's top edge sits at X's bottom + gap") gets
  edge selects under Advanced.
- **Rule rows** of the viewed base: numbered, `≡` drag to reorder, glyph chips for the
  part and (when the base area has several glyphs) for the base, `→ gap` inline number,
  × to delete; the red ● marks the row in effect for the pinned glyphs. "otherwise" is
  pinned last; when it is missing the panel says so and offers `+ set`. Chip columns only
  appear for sides whose area has more than one glyph.
- `+ new rule` / `+ new rule for <pinned glyph>` and clicking a row open the **rule editor**
  in place of the panel: a glyph grid for the part (all / none) and for the base (any / all
  / presets such as whole vs with-fraction / search), a gap field, and the canvas in edit
  mode (other parts dimmed, base outlined, only the part draggable along the rule's axis,
  overlay of all ticked glyphs or a ◀ 1/n ▶ stepper). Ticked glyphs that an earlier rule
  already catches get a numbered badge and a conflict banner ("Move this rule above rule
  N" / "Untick"). Confirm (or Enter) writes the entry as one undo step; Cancel (Esc)
  discards. New rules land at position 1 unless moved.
- Nothing auto-folds on selection any more (2026-10-17); selecting a part only unfolds a
  folded Spacing panel once. See §4 "Panels" for the dockable panel system.

Original sketch, kept for the vocabulary:


```
Spacing · 注 zhu                                           in Standard word
┌ Gap above ──────────────────────────────────────────────────────────────┐
│ The part above 注 can be:  急/綽 · Position · Finger · 泛音 · (nothing)  │
│   after 急/綽 jc      [ 10 ]                                             │
│   after Position hui  [  0 ]                                             │
│   after Finger left   [  0 ]                                             │
│   after 泛音 fy        [  0 ]                                             │
│   when 注 is first    start height [ 498 ]                               │
│ Same gap for all ☐  (fills every row from the first)                    │
└─────────────────────────────────────────────────────────────────────────┘
┌ Horizontal ─────────────────────────────────────────────────────────────┐
│ ◉ Next to the main glyph:  [ 66 ] ▾  right of ★ Stroke's left edge      │
│ ○ Fixed on the page:  x = [ ]                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

- The rows under "Gap above" are **derived** from the Stack: every part that can precede this
  one (walking up through optional parts) gets a row. The user never creates a relationship;
  they fill in numbers. A row the resolver cannot reach (e.g. after reordering) is shown struck
  through with "never happens with the current order".
- Each number field has a `▾` that turns it into an exception list (§3.6).
- The row that is active for the current preview (what `lastChosen` reports) has a blue dot
  and matches the arrow highlighted on canvas. Changing a preview checkbox moves the dot.
- **Horizontal** has exactly two shapes in the UI: "next to the main glyph" (`base: right`,
  edges fixed to ★'s left edge) or "fixed on the page" (`base: null`). The prototype's free
  choice of any base/edge pair on x is dropped from the UI; existing JSON with other bases
  loads read-only with a note "custom rule — edit in JSON" so nothing is lost.

### 3.6 Exceptions: entering and reading glyph-conditional gaps

Clicking `▾` on any gap number:

```
Gap above 注, after ★ Stroke                                    [plain number]
┌───────────────────────────────────────────────────────────────────────────┐
│ 1  when Stroke is  [勾][大] ▾           and 注 is  (any) ▾      gap [ 66 ] ● │
│ 2  when Stroke is  [剔][摘] ▾           and 注 is  (any) ▾      gap [ 32 ] │
│ 3  when Stroke is  [歷] ▾                                       gap [ 48 ] │
│    ┊ 挑 ⚠ already handled by row 1                                        │
│ ↓  rows are tried top to bottom; the first match wins                     │
│ ∞  otherwise                                                   gap [ 35 ] │
│ [+ Add exception]                                     Preview: row 1 (勾)  │
└───────────────────────────────────────────────────────────────────────────┘
```

- **Entering.** "+ Add exception" inserts a row above "otherwise" with the *currently previewed*
  glyphs pre-filled (so the common path is: set the preview to 歷, see it hit "otherwise",
  click Add, type the number). The glyph picker is a chip list with thumbnails, pinyin search,
  "select all the rest", and shows only glyphs legal for that part in this word type (the
  prototype's `legalCandidatesForArea`). The second condition ("and 注 is…") appears
  collapsed as a link "also depends on 注's glyph" unless already set, because conjunctions
  are rare.
- **Reading back.** Each row is a sentence; glyph chips come first, ids on hover. The active
  row for the preview has a dot and the canvas arrow label repeats it ("gap 勾/大: 66"). A
  glyph caught by an earlier row is shown struck through in later rows with "already handled by
  row N" (shadow detection). "otherwise" is pinned last, undeletable while any exception
  exists; deleting the last exception collapses the list back to a plain number.
- **No otherwise** is allowed only under Advanced ("Leave unmatched glyphs unplaced" — the
  engine's leaf-style behaviour for `string_top/bottom`); the panel then shows which preview
  glyphs would be unplaced.
- Budget feedback: adding a row shows "+N rules" inline next to the badge delta (§3.8).

### 3.7 Canvas: drag, labels, keyboard, undo

- **Drag a box** vertically → edits the active "gap above" row for that part (the row with the
  dot). The arrow label reads live: `gap above 注, after Stroke, for 勾/大: 66 → 72`. If the
  active row is "otherwise" and the preview glyph is not the typical one, a toast offers
  "Give 歷 its own exception instead" (one click; avoids widening "otherwise" by accident).
  Horizontal drag edits the Horizontal number the same way. Drag is axis-locked after 4 px of
  movement; both at once is not allowed (two numbers changing with one gesture is unreadable).
- Dependants move with the dragged box (positions are derived); the status line under the
  canvas says "also moves: Stroke, String".
- Dragging the ★ main glyph or the first part edits "Start height".
- Box **resize** is not on the canvas (box sizes are shared; edit them in Areas).
- Keyboard: ↑↓←→ nudge the active number by 1, ⇧ by 10; `Tab`/`⇧Tab` cycle parts in stack
  order; `Esc` cancels a drag and restores; `Enter` in a number field commits; `⌘Z`/`⇧⌘Z`
  undo/redo; `B` toggles boxes/glyphs; `Space` held = peek at the built font rendering of the
  preview word (if a build exists).
- Undo: one step per drag, per field commit, per checkbox, per exception row add/remove/reorder,
  per import. The Undo button tooltip names the step ("Undo: gap above 注 66 → 72"). History
  is per session and survives Save (saving is not an edit).
- Preview glyph selectors ("Preview with: 勾 ▾ 名 ▾ 七 ▾") sit above the canvas, one per
  present part, in stack order; clicking a glyph chip in an exception row sets them (kept from
  the prototype). "Random" fills them from the legal candidates.

### 3.8 The Font budget badge

```
Font budget ● 7 %   ──click──▶  ┌ Font budget ─────────────────────────────────┐
                                │ Each main glyph gets its own rule table in the │
                                │ font; the biggest one must stay under 64 KB.   │
                                │ 歷 lg_li     4.4 KB  ████░░░░░░  7 %            │
                                │ 勾 lg_gou    3.5 KB  ███░░░░░░░  5 %            │
                                │ 大 lg_da     3.5 KB  ███░░░░░░░  5 %            │
                                │ …                                              │
                                │ What grows it: every ‘can be left out’ part     │
                                │ doubles the combinations; every exception row   │
                                │ on a non-main part multiplies them again.       │
                                │ Standard word: 96 combinations × 16 main glyphs │
                                └────────────────────────────────────────────────┘
```

- Value = worst main-glyph lookup, `est_bytes + 1 KB` over 64 KB (ARCH-REVIEW §2.3), from
  `/api/dynamic/rule_count`, debounced 400 ms. Green < 80 %, amber 80–95 % ("the build may
  fail"), red ≥ 95 % ("the build will fail — remove exception rows or optional parts"). Red
  never disables Save; it disables nothing. The Build step is the real gate and reports the
  exact failing lookup.
- Every edit that changes it shows a transient delta next to the badge (`+0.3 KB`) for 2 s.
- The expanded panel lists, per main glyph, the top three contributors ("exceptions on 注: ×3
  branches") so the user knows which row to remove.

---

## 4. Interaction details

**Selection.** One selection at a time: a part in the current word type. Clicking a canvas
box, a Stack row, or an arrow label selects it; the Spacing panel follows. Clicking empty
canvas clears it. Multi-select is not needed (nothing acts on several parts). Selected box:
2 px accent outline + its arrows; hovered box: 1 px accent. Preview glyph choice is not
selection and survives switching parts.

**Panels (built 2026-10-17, design in `docs/PANEL-LAYOUT-UX.md` / `panel-layout-ux.html`).**
The Layouts screen is eight panels in three docks around a fixed canvas: left column, right
column, bottom strip. Every panel has the same header: ⠿ drag · ▾/▸ fold (chevron or title)
· title (follows the selection) · count badge · one-line summary when folded · ⋯ menu (fold,
move to a dock, move up/down). Side docks stack panels and scroll; the bottom strip stacks
open panels and collects folded ones into one tab bar. Drag a panel's grip to any dock (an
insert line shows where it lands; Esc cancels); the canvas is not a drop target. Docks resize
by dragging their inner edge (left/right columns) or top edge (bottom strip); dragging one
shut hides it and leaves a thin rail with the panel names, click the rail to bring it back
at its previous size. Two arrangements are saved in `localStorage` (≥ 1280 px wide, and
narrower); ⋯ → **Reset panel layout** restores both. Panel moves are not undo steps.
Defaults, wide: left = Word types, Structure, Page center (folded), Font budget (folded);
right = Spacing, Centering (folded); bottom = Glyphs, Tester. Narrow: no left column,
everything but Spacing folded on the right, Tester folded into the bottom tab bar.

**Structure panel.** One line per part: ⠿ drag (typing order, both modes) · ☑ in the
preview word (● when the part is always there) · glyph chip ▾ (preview glyph popover) ·
label + id (click to select) · tags (*anchor*, *by glyph*). Parts with options get a
switch line; repeated parts get `− n +` and one line per row. Left-out parts show their
would-be glyphs dimmed. Advanced adds plain tags (*optional*, *1–4 rows*, *2 options*,
*needs …*) and **edit ▸**, a card with every structural edit: optional, repeats + range,
"only when … is also there", option blocks (area select + id + × per chip, `+` area, `+
another option`, **area ↗** to the Areas screen), **Remove part…** (lists the rules it takes
along). `+ Add part ▾` picks an area; areas themselves (name, box, glyphs) are made on the
Areas screen (Advanced → + New). **Recognition** is a fold at the bottom: toggle chips for
`requires_any` and `priority` (rank shown in tick order).

**Always visible vs Advanced.** Always: Structure (preview checkboxes, glyph chips, drag
order), Spacing (gap rows, exceptions, horizontal), Centering, Page center, Glyphs, Tester,
Font budget. Advanced (checkbox in the app header, off by default): the Structure edit cards,
add/remove parts, Recognition, "no otherwise", per-row-boundary gaps in Vertical, edge choice
(shown read-only otherwise), new / duplicate / delete / rename word type, new area.

**Autosave vs Save.** Edits autosave to the browser (IndexedDB) every change; nothing touches
the repo until **Save (⌘S)**, which writes `layouts_data.json` and/or `components.csv` through
the dev server. The header chip states both facts: `● Unsaved (3)` → on Save → `Saved 14:02`.
The chip's menu lists the changes in sentence form ("Standard word: gap above 注 after Stroke
for 勾/大 66 → 72", "Area hui: +md_7.5") with "revert" per line, and "Discard all". On reopen
with a draft newer than disk: banner "You have unsaved changes from 14:02 — Restore / Discard".
Before writing, the server compares the file hash it loaded against disk; if it changed
(git checkout, another editor): dialog "layouts_data.json changed on disk since you loaded it.
[Reload from disk (lose my 3 changes)] [Overwrite] [Export mine first]". Save never silently
clobbers.

**Build.** Reads saved files only. "Save & build" when dirty. Serial: one build at a time; the
button shows elapsed time; the log streams.

**Import/export.** See §2.5. Export always available; Import lands in the unsaved set and
shows a diff summary before applying; "Pick per item" expands to a checklist grouped by word
type / area. Unknown keys in the file are kept and written back untouched (forward
compatibility); a file without `layouts[]` is rejected with "This isn't a Builder or
layouts_data file."

**Disabled future features.** Same component as a normal button with `data-soon`: 45 %
opacity, lock icon, suffix "soon", `aria-disabled="true"`, focusable, tooltip with one line
of what it will do. Never hidden, never moved. Current list: Upload SVG, Edit design, Replace
SVG (Glyphs); "Trace from image" (Glyphs inspector). Nothing else is faked.

**Bilingual.** All UI strings in one message table from day one; labels ≤ 2 words so the zh
and en versions fit the same widths. Chinese test-word input: never re-render during IME
composition (`compositionstart/end`); interpreted keys shown under every rendered word;
full-width punctuation accepted.

---

## 5. Visual system (plain CSS, SvelteKit)

**Principle:** the glyphs are the content; the chrome is quiet, dense and grey. Only two
accent uses: selection/active (blue) and state (amber/red/green).

Type scale (system UI stack; Chinese falls back to `"PingFang TC", "Noto Sans CJK TC"`):

| token | size/line | use |
|---|---|---|
| `--t-xs` | 11/14 | ids, keys, chip captions |
| `--t-sm` | 12/16 | table rows, hints, status |
| `--t-md` | 13/18 | body, inputs, buttons (default) |
| `--t-lg` | 15/20 | panel titles, inspector name |
| `--t-xl` | 20/26 | section title |
| mono | 12/16 `ui-monospace` | typed keys, JSON |

Glyph display sizes: tile 96 px; inspector 240 px; canvas boxes at 1 unit = 0.4 px at 100 %
zoom (660-unit box = 264 px), zoom 25–400 %; test-strip words 120 px; Test section slider
48–240 px. All glyph previews are inline `<svg viewBox>` with the SVG's own paths, `fill:
currentColor`, `shape-rendering: geometricPrecision`, no raster, no CSS `transform: scale`
on text; the built-font view uses the TTF via `FontFace` with
`font-feature-settings: "kern","liga"` and `text-rendering: optimizeLegibility`.

Spacing: 4-pt scale `--s-1..--s-8` = 4 8 12 16 24 32 48 64. Panel padding `--s-4`, row gap
`--s-2`, control height 28 px (dense), 44 px for anything on the Test section (touch).

Color tokens:

| token | light | dark | use |
|---|---|---|---|
| `--bg` | #ffffff | #141517 | page |
| `--bg-2` | #f5f5f4 | #1d1e21 | panels, sidebars |
| `--bg-3` | #ebebe9 | #26272b | hover rows, chips |
| `--line` | #d9d9d6 | #34363b | borders |
| `--fg` | #1c1c1a | #e8e8e6 | text, glyph fill |
| `--fg-2` | #6b6b68 | #9a9a97 | secondary text, ids |
| `--accent` | #1f6fe5 | #5b9bff | selection, active row, links |
| `--accent-bg` | #e8f0fe | #1c2a44 | selected row fill |
| `--ok` | #1e8e3e | #4ccc6a | saved, build ok |
| `--warn` | #b26a00 | #f0a93b | 80 % budget, unsaved |
| `--danger` | #c5221f | #ff6b66 | 95 % budget, errors |
| `--canvas` | #fafaf8 | #0f1012 | canvas page |
| `--box` | rgba(31,111,229,.08) | rgba(91,155,255,.12) | area box fill |
| `--box-line` | #8fb4f0 | #3f6db5 | area box outline |
| `--arrow` | #d93838 | #ff7a7a | gap arrows (kept from prototype) |

Dark mode via `prefers-color-scheme` plus a manual override in the ⋯ menu. State is never
colour-only: unsaved = dot + text, optional = checkbox, main = ★, future = lock + "soon".

Component list (one Svelte file each, no library): `AppHeader`, `SaveChip`, `BudgetBadge`,
`SectionNav`, `GlyphTile`, `GlyphGrid`, `GlyphPicker` (dialog), `GlyphChip` (thumbnail +
id), `Inspector`, `AreaList`, `MemberGrid`, `KeyFields`, `WordTypeList`, `Canvas`
(`AreaBox`, `GapArrow`, `PreviewGlyphBar`), `StackPanel` (`StackRow`), `RowTemplate`
(Vertical), `SegmentPanel` (Chord), `WordStrip`, `RulePanel`, `RuleEditor` (replaced the
planned `SpacingPanel`/`GapRow`/`ExceptionList`), `CenteringPanel`, `TestStrip`, `RenderedWord`, `SampleSets`, `BuildPanel`,
`ImportExportDialog`, `ConflictDialog`, `Toast`, `Tooltip`, `SoonButton`, `NumberField`
(arrow-key nudge, ⇧×10, scrub on drag), `Disclosure`.

---

## 6. Build order

Each step ships usable; acceptance = what the font author can do without reading code.

1. **Shell + data loading + Test (live preview).** Header, nav, save chip (read-only),
   `/api/dynamic/data` + `/api/svgs` loaded into a store, Test section with sample sets and
   live-preview rendering through `/api/dynamic/resolve`, interpreted keys under words.
   *Accept:* type `s7k5 名七勾五 :fenkai C03|s6,5`, see boxes+glyphs for each, IME input
   does not flicker, dark mode works.
2. **Layouts: canvas + Stack + Spacing with plain numbers.** Select part, see gap rows and
   horizontal, edit numbers, drag with live label, undo/redo, preview checkboxes and glyph
   selectors, centering checkboxes. No exceptions yet (conditional gaps load read-only as
   "by glyph — see step 3").
   *Accept:* change "gap above 注 after Stroke" from 66 to 72 by dragging; the arrow label
   names the row; ⌘Z restores it; the test strip updates within 100 ms.
3. **Exceptions + budget.** Exception list editor with shadow detection, pinned otherwise,
   "give X its own exception" toast; budget badge with per-main-glyph breakdown.
   *Accept:* give 歷 its own gap without changing 勾's; badge shows the delta; a struck-through
   glyph appears when a row is shadowed.
4. **Save to disk + conflict handling + Build.** ⌘S writes `layouts_data.json`, hash check,
   conflict dialog, change list in the chip, draft restore on reload; Build button with
   streaming log and plain-language failure; "Built font" mode in Test with compare-both.
   *Accept:* edit → Save → Build → the TTF reloads and the word matches the preview; edit
   the JSON externally → Save shows the conflict dialog.
5. **Areas + Glyphs.** Area list, member grid, Add-glyphs picker, typing keys, box sizes,
   writes `components.csv`; Glyphs grid with groups, unassigned filter, inspector, soon-buttons.
   *Accept:* add `md_7.5` to area hui, type `s7.5k5` in Test, see it placed; Glyphs shows
   129 unassigned afterwards.
6. **Vertical word and Chord structure panels.** Row template with count and alternatives
   (expands to numbered slots on write), two-segment Chord view over the two engine entries,
   bar divider on canvas.
   *Accept:* set Vertical to 4 rows with "gap between rows 40", preview with 3 rows, Build,
   `:v8.5banlun7` renders stacked; Chord `Cv9,6|03` has both sides editable from one screen.
7. **Import/Export + Advanced.** Builder bundle export/import with diff summary and merge
   modes; Advanced toggle (reorder, optional/main, add/remove part, new word type, raw JSON).
   *Accept:* export, change a gap, import with "Pick per item", keep only the area changes;
   reorder is impossible with Advanced off.

Deferred (absent by design): Pyodide
in-browser resolve (the dev server is local, so latency is not a problem here), multi-user
anything.
