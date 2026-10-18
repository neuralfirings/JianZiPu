# Glyph Editor: summary

Artifact: https://claude.ai/artifact/LdBmi12pa7ETZHGYS8jxTh
Wireframes: `docs/glyph-editor-ux.html` (open it in a browser; it uses no external resources).
A touch-up and import tool for `src-fonttools/inputs/svg/<name>.svg`, built on Paper.js
(+ paperjs-offset, + a potrace WASM build). It writes SVG files only; it changes no
`design.json` shape except one new optional key, `reference_weight` (units).

## Takeover or modal

**Takeover, as routes:** `/glyphs/<name>/edit` and `/glyphs/new`, with the app header and nav kept.
Reasons: the canvas needs the full width (660 box + 250 px side panel); Esc can mean "finish
path / deselect" without risking a close; ⌘Z belongs to the glyph while you are there; the URL
can be bookmarked and survives a reload; one leave guard covers nav, Back, ← Glyphs and closing the tab; the
rest of the app stays reachable; Figma's vector edit mode works the same way, filling the canvas.
Alternative: a large modal would do for one-point nudges, but it fights Esc, has no URL and puts
two undo stacks on one screen. Small single-decision steps (New glyph, SVG import options,
leave guard, disk conflict) are dialogs.

## Decisions

1. **Edit affordance:** an **Edit** button under the tile name, shown on hover/focus and always on
   the selected tile. Double-click or Enter on a tile also opens it. The inspector's "soon" buttons
   become **Edit outline**, **Replace from file…** (editor with the file loaded, unsaved),
   **Trace from image…** (editor in trace mode).
2. **Own Save.** **Save glyph** (⌘S in the editor) writes the file at once via a new
   `PUT /api/svg/<name>` with the hash of the file as loaded (409 → conflict dialog: Compare /
   Load disk version / Overwrite). Layouts and the Tester use the new outline right away; the font needs
   a Build (the toast links to it). On the editor route the header reads "Design: saved" /
   "Save design" and its ↶ ↷ buttons are hidden, so there is only one undo and one ⌘S here. Trade-off: two Saves
   exist in the app; the labels keep them apart. A draft of curves has no place in
   design.json's undo history.
3. **Undo** per editing session (each drag/stroke/import/trace/op is one step, named in the
   tooltip). It survives Save and is cleared on leaving. **Discard** goes back to the file and can be undone.
   A browser draft (IndexedDB, per glyph) restores edits after a crash, with the same banner as the design draft.
4. **One pointer tool (V).** A selected shape always shows its points: drag the fill to move the shape,
   drag a point to move the point, double-click a point for corner ↔ smooth, ⌥-drag a handle to move it alone. Pen over a
   segment adds a point, pen over a point or Delete removes one. No separate point mode (A = V), no
   transform box (scale/rotate/size are numbers in the side panel, plus Fit to box / Center).
5. **Tools:** Select V, Pen P, Pencil ⇧P, Rectangle/Ellipse R/O, Hand H/Space, Zoom Z.
   **Open paths are lines** drawn at the reference weight with round ends (WYSIWYG via
   paperjs-offset `offsetStroke`). **Outline line** (⌥⌘O) or Save turns them into filled
   shapes, so the file only ever holds fills (the build would expand `stroke=` itself, but the
   editor does it so what you see is what gets written). The pencil auto-simplifies when you let go.
6. **Reference weight** is one font-wide number (`design.json` → `reference_weight`, set on the
   Glyphs screen toolbar, saved with the app's Save). It makes sense because SVG units equal font
   units for every box. Caveat shown in the UI: match the *body* of main strokes, not tapers.
   The editor's dot can change it for the session only ("Reset").
7. **Compare overlays** (translucent blue, drawn on top, click-through, never saved):
   reference dot (filled, diameter = reference weight, draggable, D); another glyph (filled,
   search by name/key/char/pinyin, same-area chips, lined up by box top-left or centred, G);
   last saved (dashed blue outline, L). Blue fill means "compare" and nothing else.
8. **Shape ops** share one pattern: a popover, a live result on the canvas, the "before" as a grey dashed line,
   Apply = one undo step, Esc cancels. **Simplify:** one slider (Paper.js tolerance 0.5–10 units)
   + point count "57 → 11". **Thicken/thin:** total width change in units ("+4 = 2 each side"),
   selection or whole glyph, round/sharp corners, warns before thin parts would vanish.
   **Combine:** Union / Subtract / Intersect / Exclude, enabled with ≥ 2 shapes. Pointing at a button previews the result.
   Subtract: the newest shape cuts the older ones, and ⇧ while pointing swaps them. The result is final, not a live group.
9. **New glyph** dialog: Name (validated live, case-insensitive. A taken name offers "Open md_9"
   and never overwrites), Area (sets the box; "No area yet" = 350 × 350), Start from: Blank /
   SVG file / Image to trace. The editor opens with a sibling glyph already ghosted. The area is
   joined on **first save**, as a design change in the header's unsaved set, so design.json never
   names a missing file. Typing keys are set in the editor's Typing panel or Glyphs → Typing (the Areas screen these lines once pointed to was folded into Layouts → Area Properties, 2026-10-18).
10. **SVG import** (Import ▾, Replace from file, drop on canvas or grid, ⌘V of SVG text):
    asked only when the viewBox differs from the box (fit, default / keep size); stroked lines outlined
    by default; colours, opacity, text and images dropped, and the dialog says so; Replace or Add for existing glyphs.
    Dropping `md_9.svg` on the grid when md_9 exists asks Replace md_9 / Save as new / Cancel.
11. **Trace** (JPG/PNG): place the image under a live traced preview (drag frame, ⇧ for proportions),
    potrace settings in plain words: Threshold (+ Auto), Clean specks, Corners, Simplify, Light on dark,
    image visibility. **Use this outline** = one undo step, Replace or Add. The source image is
    kept **in this browser** per glyph for Re-trace (warns if the traced shape was edited since); not
    written to the repo.
12. **In-context test** inside the editor: 3–5 real words (default: the Tester words that use the
    glyph; editable) rendered with live rules and the *unsaved* outline (`/api/words`, outline
    swapped in), at 32 / 64 / 120 px, plus "Open in Tester ↗".
13. **Checks** (live in the side panel, shown again at Save, never blocking except an empty glyph):
    outside the box (also hatched red on canvas and in the status line), open lines (they get outlined), specks
    under 6 units (Remove them). **Written file:** one `<path fill="black">` per shape, viewBox/width/height
    = area box, coordinates to 0.1 unit, nothing else. Git is the history.

## Region inventory (editor)

| Region | Contents |
|---|---|
| App header | Nav (Glyphs active), "Design: saved / N unsaved", Save design, ⋯. Undo buttons hidden on this route. |
| Glyph bar | ← Glyphs (or ← Layouts when opened from there, `?back=`) · thumbnail · name · character · area chip with box size · state chip (Saved 14:02 / ● Edited · N changes / Saving… / new) · ↶ ↷ · Discard · **Save glyph** |
| Tool rail (left) | V · P · ⇧P · R/O · H · Z |
| Action bar (top of canvas) | Combine ∪ − ∩ ⊕ · Simplify… · Thicken… · Outline line · ⇆ ⇅ · Import ▾ (SVG file / Image to trace / Paste) |
| Canvas | Area box (white) on grey, units 1:1 from 0,0 top-left, selected shape's outline + points + handles, overlays, red hatch outside the box, optional 10-unit grid |
| Status line | cursor x/y in units · shapes · points · selected · outside-box warning · zoom |
| Panels (built 2026-10-18) | Dockable like the Layouts screen (`PanelWorkspace`, store `editorPanels`, localStorage `jzp-editor-panels-v1`): fold, drag between the right column / left column / bottom strip, resize, ⋯ menu. Default: right = **Selection** (point x/y + Corner/Smooth/Free; shape position/size/scale/rotate; picked compare overlays; nothing selected: glyph totals + Fit/Center) · **Compare** (dot, compare glyph, Line up, last saved; dot and compare glyph drag and nudge on the canvas) · **Glyph** (areas with × / + Add to area, file, box) · **Typing** (the Glyphs screen's spelling fields) · **Checks**; bottom = **Tester** (the shared `WordTester`: words that use the glyph, sample sets, 40/72/116 px, Test & Build ↗) · **Try it** (spelling checks). ⋯ → Reset panel layouts puts them back. |
| Trace mode | a **Trace** panel appears (opened and shown wherever it sits), the canvas shows image + frame + preview, drawing tools paused, Save disabled until Use/Cancel |

## Interaction notes

- Esc on the canvas never leaves the editor. Enter applies a popover, or finishes a pen path as a line.
- Disabled buttons explain themselves in a tooltip ("select 2 shapes").
- Arrow keys nudge 1 unit, ⇧ for 10; ⇧-drag keeps to 45° or keeps proportions.
- Shortcuts follow Figma: ⇧1 fit, ⇧0 100 %, ⇧2 selection, ⇧H/⇧V flip, ⌥⇧U/S/I/E booleans,
  ⌥⌘O outline. Our own: D dot, G reference glyph, L last saved, ⇧G grid, ? shortcut sheet.
- Leave guard: Keep editing / Discard and leave / Save and leave, on every way out.

## Left out on purpose

Layers and groups, colour, opacity, text, gradients, images in the output; pressure or
variable-width brushes; a separate point mode; live boolean groups; a transform box on the canvas;
renaming a glyph; editing area membership or typing keys inside the editor; versions, proposals and review
(hosted phase); batch import of many SVGs; automatic stroke-weight measurement.

## Open questions

1. Edit button on every tile all the time, or hover + selected as drawn?
2. Default reference weight: which number? (Today's glyphs sit around 30–45 units.)
3. Keep trace sources in the repo (`inputs/sources/`) so the brush originals survive a browser reset?
4. Is the pencil worth having next to the pen, or is "trace a scan, then tidy" the real workflow?
5. Drop many SVGs at once (a whole Figma export): a batch import list, or one at a time?
6. A weight badge on Glyphs tiles (measured stroke width vs the reference)? It needs a raster
   measurement, beyond what Paper.js gives for free.
7. Subtract by drawing order with ⇧ to swap: clear enough without a layers panel?
