# Where Areas goes: summary

> **Status: implemented 2026-10-18** with the owner's answers to the open questions (end of this file):
> box size stays editable without Advanced; the panel is titled **Area Properties**; position decimals are a
> text grid; no "glyphs reach outside the box" hint (a box smaller than its glyphs is on purpose, so step 5
> of the box-size edit is dropped); removal stays the inspector's / chip's ×; the `/areas` route is removed
> (no redirect). Code: `app/src/lib/components/AreaPanel.svelte`, `app/src/lib/areas.ts`.

Wireframes: `docs/areas-placement-ux.html` (open it in a browser; it uses no external resources).
Design only: no app code or data changed. Builds on `PANEL-LAYOUT-UX.md` and `KEY-ENTRY-UX.md`.

## Recommendation

**Drop the Areas tab, but don't add a ninth panel. Grow the existing Glyphs tray on Layouts into an "Area" panel,
and let the Glyphs screen's area groups take over the big member grid.**

Why:

- **Box size is a layout edit, but today you make it without seeing the word.** On Areas you type 350 → 380 and
  then go to Layouts to see what moved. On Layouts the canvas can show the change as you type.
- **Membership is already edited in three places:** the Areas grid, the Glyphs inspector (In areas ×, + Add to area…)
  and the Layouts tray (Manage: ×, + Add glyphs). The Areas grid is the third, and the Glyphs screen with an area group
  picked in the sidebar is already nearly the same grid.
- **The tray already is "the area of the selected part"**: same subject, same selection, same Manage switch. Its header
  already says "area left · shared by …". Adding one line for name and box makes it the Area panel. A separate
  Area panel would follow the same selection and show the same name twice.
- What stays only on Areas today (name, box, advance, new, delete) is small. It's not enough for a tab.

The nav goes from five items to four: **Glyphs · Layouts · Test & Build · Tester**.

## Where each Areas job goes

| Job (Areas today) | After | Notes |
|---|---|---|
| Box W × H | **Area panel** (Layouts), on the props line | Live preview on the canvas; Enter applies, Esc reverts; one undo step |
| Advance (Advanced) | Area panel, props line, Advanced only | As today |
| "Shown as" (display name) | Area panel, props line | One editor. Glyphs sidebar, Structure and canvas labels just show it |
| Used in: word types | Area panel, props line: word-type chips | Click a chip to open that word type with the same area selected. While a box edit is pending, the chips grow into small before/after previews |
| Member grid, × remove | Area panel members (Manage on) for in-context work; **Glyphs screen** area group for big jobs | Both edit the same design, the same undo and the same Save |
| + Add glyphs (dialog) | Area panel (Manage) and the Glyphs area-group header | Same `AddGlyphsDialog` |
| Member's "Typed as … Edit in Glyphs →" | Dropped | Glyphs owns spellings; a chip's tooltip shows the first spelling |
| List of all areas | **Area switcher** in the panel (a menu) and the Glyphs sidebar | The menu shows a small table: name, id, box, count, used in |
| + New area (Advanced) | Area switcher → **+ New area…**; also Structure → + Add part ▾ → **New area…** | The second one makes the area and the part in one step |
| Delete area (Advanced) | Props line `⋯` → Delete area | Disabled with the reason while a word type uses it |

## The Area panel

Same panel id and default spot as the tray today (bottom strip, open). Title follows the selection like Spacing does.

- **Header:** `⠿ ▾ Area · Left hand  (5)  ⋯`. Folded summary: `350 × 350 · 名 previewed`.
- **Area switcher:** click the title to get a menu of all 11 areas in three groups:
  *In this word type* (picking one selects its part), *Other word types* (picking one opens a word type that has it),
  *Not in any word type* (the panel shows it with no canvas). Advanced adds **+ New area…** at the bottom.
  Clicking a part on the canvas puts the panel back on following the selection.
- **Props line:** `Shown as [Left hand] · Box [350] × [350] · Used in: Standard word · Chord · Chord right · Vertical · ⋯`.
  Advanced adds `Advance [0]`. In a side column it wraps to two lines.
- **Members:** the tray's chips. Click = preview on the canvas (unchanged). **Manage** adds × on each chip and
  **+ Add glyphs**. **Open in Glyphs →** goes to `/glyphs?group=<area>`.

### 147 members (徽 position)

The 17 ordinary members (散, 1–13, 外, 九, blank) stay as glyph chips. The 130 position decimals become a **position grid**:
one small text cell per decimal (`7.6`), 13 hui × 10 (`.` blank, .1 … .9).

- In the bottom strip the grid lies wide: 13 columns (hui) × 10 rows, about 520 × 170 px. In a side column it stands tall:
  13 rows × 10 columns.
- Click a cell = preview that decimal. The previewed cell is outlined.
- Search (shown when an area has more than 28 members) matches spellings as today, and `7.6` lights its cell.
- Manage: a member cell gets × on hover; a missing cell shows a dashed `+` and adds on click. All 130 are members today,
  so normally no cell is dashed.
- Any area whose members include position decimals gets the grid, not only 徽 position.

## Box-size edits on the canvas

1. Focus W or H. Every box of this area in the open word is outlined in the accent colour (both strings in the
   two-string option, every row in Vertical).
2. Type, or use ↑/↓ (Shift = 10). The canvas re-resolves as you go, like a rule edit: the new layout is solid,
   the old one is a dashed ghost.
3. The status line says: `Box of Left hand 350 × 350 → 380 × 350, not applied: moves parts in 4 word types. Enter applies · Esc cancels.`
4. The Used-in chips open into small previews of the other word types, each with its own ghost.
5. ~~If a member's outline would reach outside the new box, a hint says how many.~~ Dropped: a box smaller than its glyphs is on purpose.
6. Enter or leaving the field applies it as one undo step (`Area left: box width 350 → 380`). Esc puts it back.

Box resizing by dragging on the canvas stays out: dragging a part already changes its gap.

## Glyphs screen

- **Area group header (new).** When an area group is picked in the sidebar, a one-line header sits above the tiles:
  `徽 position  hui · 147 glyphs · box 350 × 350 · used in 4 word types · [+ Add glyphs] · Edit box in Layouts →`.
  This plus the tiles replaces the Areas member grid. The sidebar gets an **Areas** heading above its area groups.
- The inspector keeps "In areas: [chip ×] + Add to area…". Its "Box … (from area right)" becomes a link to Layouts.
- Glyph editor: the area chip and "from area …" link go to Layouts (`/layouts?area=right`).
- Nothing conflicts: both screens edit the one in-memory design, so a change in one shows in the other at once,
  and both land in the same undo stack and unsaved count.

## Links and routes

- `/layouts?area=<id>&g=<glyph>`: open the current word type if it uses the area, else the first one that does;
  select the area's first part; preview the glyph; unfold the Area panel. If no word type uses it, the panel shows
  the area with "Not in any word type yet: add it as a part (Structure, Advanced, + Add part)."
- `/areas?…` redirects there, so old links keep working.
- Structure's **area ↗** stops navigating: it switches the Area panel to that area and unfolds it.
- The tray's "Typing keys, box size → Areas" link goes away.

## What gets worse

| | Today | After | Softened by |
|---|---|---|---|
| All areas side by side | Areas list | A menu | The switcher menu is a table with box and count |
| Bulk membership on a big area | Large grid with room | A panel strip | Position grid for decimals; **Open in Glyphs →** for anything big |
| Box size next to everyday controls | On its own screen | Next to the preview chips | Needs Enter to apply, previews first, one undo step |
| "Area" as a visible concept | Its own tab | A panel title and a sidebar heading | Panel title says "Area ·"; the Glyphs sidebar gets an "Areas" heading above its area groups |
| Editing an unused area | Same as any area | Only through the switcher, no canvas | Same as today: an unused area has nothing to preview |
| Getting to box size from Glyphs | One click to Areas | One click to Layouts, which also changes the open word type | The link opens the word type that uses the area |

## Left out on purpose

Dragging box edges on the canvas. A ninth panel. Renaming area ids. Multi-select remove on Glyphs tiles.
Per-word-type box sizes (needs a data change).

## Open questions

1. Is it fine for box size to stay editable without Advanced (as today), or should it move behind Advanced now that it sits next to the preview chips? **Yes, stays editable.**
2. Panel title: "Area · Left hand", or keep "Glyphs of Left hand" and treat the props line as extra? **"Area Properties".**
3. Position decimals as a text grid (`7.6`) instead of glyph pictures: OK? **Yes.**
4. Do you want the "N glyphs reach outside the new box" hint, or is a box that's smaller than its glyphs sometimes on purpose? **On purpose: no hint.**
5. Should the Glyphs area-group header also let you remove tiles from the area (multi-select), or is the inspector's × enough? **× is enough for now.**
6. Old `/areas` links: redirect (proposed), or just remove the route? **Remove.**
