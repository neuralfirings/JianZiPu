# Panel layout + calmer Structure: summary

Wireframes: `docs/panel-layout-ux.html` (open it in a browser; it uses no external resources).
This is a Layouts-screen design only. It changes no data and no `design.json` shape.

## Decisions

**Structure panel**
1. One line per part: `☑ [glyph▾] Label id [tags]`. Checkbox = in the preview word (● if the part is always there).
   The glyph button opens the same glyph popover as "In this word", not a `<select>` of file names.
2. Everyday controls stay on the line in both modes: preview glyph, leave out / put back, select (click the line).
   Parts with options get one extra line: a switch for which option to preview. Rows get `− n +`.
3. Advanced adds a `⠿` drag handle (replaces ↑↓), plain tags (*can be left out*, *1–4 rows*, *2 options*) and
   **edit ▸**, which opens a card under that line (one at a time) holding every structural edit for the part:
   can be left out, repeats + row range, "only when this part is also there" (`requires`, no UI today),
   what it holds, and **Remove part…** (asks first, lists the spacing rules it takes along).
4. The raw `parts` text field becomes **option blocks**: each option is a row of part chips (area label + element id),
   `+` adds an area to that option, `+ another option` adds an "or" row. Click a chip to rename it, change its area or remove it.
5. **Recognition** becomes a fold at the bottom of Structure (Advanced, folded by default): toggle chips in stack order for
   `requires_any`, and an ordered, draggable chip list for the `priority` tie-break inside the word type (first wins).
6. "Shown as" (the word-type name) moves to the Word types panel (double-click / ⋯ → Rename).
7. The **Advanced** switch moves to the canvas toolbar because it unlocks things in several panels.

**Panels**
8. Every panel has the same header: `⠿` drag · `▾/▸` fold (the chevron or the title) · title (follows the selection) ·
   optional count badge · summary when folded · `⋯` (fold, move to a dock, move up/down).
9. Three docks around a fixed canvas: left column, right column, bottom strip (canvas width). No floating windows.
   Side docks stack panels vertically and scroll as a whole, with sticky headers. The bottom strip stacks open panels and
   collects folded ones into **one tab bar** (the only tabs in the design).
10. Drag: all panels drop to header-only, every dock lights up, the dock under the pointer shows an insert line, the old spot
    shows a dashed gap. The canvas is not a drop target. Esc cancels. An empty side dock shows a thin drop rail at the edge while dragging.
11. An empty dock takes no space, so the canvas widens. The canvas is never narrower than 420 px. If saved columns would squeeze it,
    the left column folds to a rail of names that opens as an overlay.
12. The arrangement is saved in `localStorage`, with **two arrangements** (≥ 1280 px and narrower). It is not part of the design
    and not an unsaved change. **⋯ → Reset panel layout** restores both. This applies to the Layouts screen only.
13. No more auto-folding of Structure/Centering on selection. Selecting a part unfolds a folded Spacing panel once.
    The rule editor still replaces Spacing's body wherever it is docked; Glyphs and Tester grey out while it is open.

## Panel inventory

| Panel | 1440 default | 1100 default | Folded header shows |
|---|---|---|---|
| Word types | left · open | right · folded | count · **current type** |
| Structure | left · open | right · folded | 7 parts · 6 shown |
| Page center | left · folded | right · folded | 500, 500 |
| Font budget | left · folded | right · folded | rules · red badge if skipped |
| In this word | right · open | right · open | 6 of 7 parts |
| Spacing | right · open | right · open | part · rule in effect → gap |
| Centering | right · folded | right · folded | ↕ on N parts · ⇆ off |
| Glyphs (tray) | bottom · open | bottom · open | count · selected glyph |
| Tester | bottom · open | bottom · folded (tab) | N words |

1440: left 280 px, right 420 px, canvas about 740 px. 1100: no left column, right 380 px, canvas about 720 px.

## Interaction notes

- Keyboard: a focused header folds with Space/Enter. The ⋯ menu moves panels without dragging.
- Column width: drag the inner edge (240–520 px); double-click resets it. Bottom strip height: drag its top edge.
- "N skipped ▸" opens the skipped-shapes list inside the Word types panel, under that type.
- Panel moves are not on the ⌘Z stack. ⌘Z stays for design edits only.

## Left out on purpose

Floating windows, panels side by side in one dock, tabs in side columns, hiding a panel entirely, resizing single panels,
arrangements per word type or per screen, and merging the two Chord halves into one Structure (needs a data change).

## Open questions

1. "In this word" overlaps normal-mode Structure. Keep both, or make In this word the folded form of Structure?
2. Is it OK to drop the auto-fold on selection?
3. Advanced switch in the canvas toolbar, or in the app header?
4. Two saved arrangements (wide/narrow), or one?
5. Should Page center be editable without Advanced?
6. Is an ordered, draggable tie-break list worth it, or is one chip per word type always enough?
