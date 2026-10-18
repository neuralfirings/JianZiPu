# Typing in Glyphs (key entry): summary

Artifact: https://claude.ai/artifact/5UrLxJUDKEna7PFnYkMzUu
Wireframes: `docs/key-entry-ux.html` (open it in a browser; it uses no external resources).
How each glyph is typed: the editable columns of `src-fonttools/inputs/components.csv`, edited on the
Glyphs screen. It replaces the small "Typing keys" editor on the Areas screen. Design only: no code or data changed.

**Implemented 2026-10-17** (Glyphs screen, `app/src/lib/typing.ts`, `POST /api/typing/preview`). Where the build
differs from this spec: the blank decimals (md_N.blank) have one pattern, `N.` (七徽 and 七点 type md_7); the
new-glyph prompt is a "give it a spelling →" link on the glyph editor's Typed-as line, not a first-save toast.

**Revised 2026-10-17.** The first version proposed a separate **Typing** nav tab. That is superseded:
spellings now live on the Glyphs screen (decision 1). Everything else from the first version still holds unless marked.

## Where it lives

**Option (d): Glyphs with a Tiles | Typing switch and an editable inspector, under one rule: the inspector shows what the view doesn't.**
The nav stays at five items (`Glyphs · Areas · Layouts · Test & Build · Tester`).

| | (a) Own tab (v1) | (b) Tiles/Table, inspector fields in both | (c) Tiles/Table, edit only in Table | **(d) picked** |
|---|---|---|---|---|
| Compare across glyphs | yes | yes (Table) | yes (Table) | yes (Typing view) |
| One glyph start to finish (draw, part, spelling) | switch tabs | one panel | switch views to type a key | one panel (Tiles) |
| The same value editable twice on screen | no | yes, in Table | no | no |
| Room for Try it | side panel | squeezed | inspector | its own inspector column |
| Nav items | 6 | 5 | 5 | 5 |

Why v1's reasoning no longer holds: "tiles can't compare across glyphs" and "clashes span areas" are both answered by
a table view that covers all parts. "Try it would crowd the inspector" doesn't hold either: the inspector is full-width, so Try it gets
its own column. The data check settles the rest: `filename` equals `glyph_name` in every row (md_tang's is blank), and a
glyph *is* its SVG file. A spelling row is therefore a property of a tile, like its parts, which the inspector already edits.

**Names:** the view is **Typing**, and the inspector column is also **Typing**, so the word means one thing.
"Key Entry" sounds like data entry, and "key" already means a keyboard key and a design.json key.

## Decisions

1. **Inside Glyphs**, with a **Tiles | Typing** segmented switch in the toolbar. The view is kept in the URL (`?view=typing`) and remembered per browser.
2. **The inspector shows what the view doesn't.**
   - Tiles: Glyph facts (today's, plus Edit outline / Replace / Trace / Download) · **Typing fields** · **Try it**.
   - Typing view: Glyph facts · **Try it / What changes / Issues**, with no fields, because the selected row already is the editor.
   - Either way, each value has exactly one editor on screen.
3. **The sidebar groups by part**, not by file prefix: Right hand 16 · Chords 8 · Left hand 5 · Numbers 16 · Modifiers 4 ·
   Characters 43 · Position decimals 130 · Unassigned. The "md_" prefix group mixed fingers, numbers and characters (64 glyphs).
   Below the groups are Typing filters: Needs attention · Clashes · No spellings yet · Vertical pairs · Unsaved.
   Groups and filters work in both views.
4. **Switching views keeps** the selection (`?g=`, scrolled into view, the cursor on Letters), the search and the sidebar group or filter.
   Keyboard: in Tiles, Enter opens the outline editor; in Typing, Enter edits a cell, and double-clicking the picture opens the outline editor.
5. **Tiles show the first working spelling** (Letters, else Number, else 简体) instead of the unused `keys` column, plus `⇄`
   for vertical pairs and a ✕ ⚠ · corner badge. The inspector's "Typing keys →" button goes away.
6. **Typing view table:**
   - Columns: status · glyph (picture + name) · Letters · Short form · Number / symbol (read-only) · 简体 · 繁體 · Vertical form · Reading.
   - Optional columns: Parts, File. File size, path count and box stay in the inspector.
   - Grouped by part when the sidebar is on All. Pick a group and the table goes flat and sortable.
   - Editing works like a spreadsheet: arrows move, Enter/Tab save and move on, Esc reverts, Delete clears.
7. **Position decimals** (md_1.1 … md_13.9, md_N.blank) never get spelling fields.
   - The inspector shows their pattern: `7.6` · `7点6` · 七点六 · 七徽六 · after a finger `s76` / 名七六.
   - In the Typing view they are one folded group. Opened, it shows read-only rows with their pattern spellings, so a search for `7.6` finds md_7.6.
8. **New glyphs:** the glyph editor's first-save toast says "Give it a spelling →" and opens `/glyphs?g=<name>` with Letters focused.
   Letters gets a suggestion from Reading with tones removed (Tab to accept).
9. **Delete** = ⋯ **Clear spellings** (inspector, or the row menu). It is one undo step with no dialog, and it never touches the glyph or its parts.
10. **Bulk:** paste ranges in the Typing view (with a one-line preview). Glyphs ⋯ → Import spellings (CSV)… (a diff, landing as unsaved changes) and Export CSV.
11. **Shared on purpose = a vertical pair** (`validate.py`'s `_is_known_vert_pair`), shown as a blue ⇄ link. Editing one asks to change both (on by default).
    Any other shared spelling is a **clash**: red, ✕ on both glyphs, and **Save is paused** until it's fixed (the draft and undo still work).
12. **Live feedback with unsaved spellings:** Try it (each spelling plus free text with a breakdown) and What changes (sample words before and after).
    Both use a GSUB-only recompile in memory of the last built font (measured at about 0.5 s). A round-trip check runs on every change.
    A new Chinese character (往) shows "added at the next Build".
13. **Areas** keeps a read-only line, `Typed as lun · 轮 · 輪  Edit in Glyphs →`. `edge_cases.fea` is listed read-only in plain words under
    Glyphs ⋯ → Built-in spellings. `glyphRename.csv` is not shown.
14. **Save model:** spellings join the app's one Save, undo, unsaved count and browser draft. Save checks both files' hashes, then writes both.
15. **Data:** keep `components.csv` as its own file, and drop `ID`, `keys` and `filename`, which the build never reads.

## Region inventory (Glyphs screen)

| Region | Contents |
|---|---|
| App header | Nav (Glyphs active), `● N unsaved` (design + spellings), ↶ ↷, Save, ⋯ |
| Toolbar | Search (spelling · character · pinyin with or without tones · glyph name) · **Tiles \| Typing** · Columns ▾ (Typing only) · Reference weight · ⋯ (Import/Export spellings, Built-in spellings) · + New glyph |
| Issue banner (only when needed) | red "1 clash: Save waits until it's fixed. Show" or amber "2 spellings type something else. Show" |
| Sidebar | part groups with counts · Unassigned · **Typing** filters with counts |
| Tiles view | today's tiles; sub-line = first working spelling + ⇄; corner ✕ ⚠ · badge; Edit on hover/selected |
| Typing view | the table: group rows, status, glyph, the spelling cells, ⇄ tags, read-only Number; Position decimals folded |
| Inspector (bottom, full width) | picture · **Glyph** (name, parts with × / + Add to area…, box, file, Edit outline / Replace / Trace / Download) · **Typing** (Tiles only: Letters, Short form, 简体, 繁體, Vertical form, Reading, Number shown; ⋯ Clear spellings) · **Try it** (Tiles) or **Try it / What changes / Issues** (Typing) |

## Plain-language column labels

| Column | Label (en / zh) | Help line | Reaches the font? |
|---|---|---|---|
| glyph_name | **Glyph Name** / 字形 | The drawn part this row types. Its SVG file name and the row's ID. | yes (rule target) |
| latin | **Latin Entry** / 字母 | What you type on an English keyboard: a one-letter shortcut (`k`) or the pinyin (`lun`). Letters and digits, starting with a letter. | yes |
| latin_alt | **Latin Entry (Alt)** / 簡寫 | A second, shorter way to type it (`bl` for banlun, `fy` for fanyin). | yes |
| common | **Number/Symbol** / 數字符號 | Digits and symbols typed the same in any input mode: `7`, `13+`, `/`, `>`. Fixed by the font's number rules; shown, not editable. | no (hard-coded in features.py) |
| simplified | **简体** / 简体 | The character(s) as typed with a simplified-Chinese input method. | yes |
| traditional | **繁體** / 繁體 | Only if it differs from 简体. | yes |
| vert_variant | **Vertical form** / 直排字形 | In vertical notation (after a colon) the font swaps this glyph for its centred version. | yes |
| pinyin | **PinYin** / 讀音 | Pinyin with tones, used for search and labels. Not typed. | no |
| keys | *drop* | Not unique (5 pairs share one, md_tang has none) and never read by the build. Tiles show the first working spelling. md_ban's `0.5` doesn't type md_ban. | no |
| ID, filename | *drop* | Row order, and a copy of the glyph name. | no |

## Checks

| Level | When | Blocks Save? |
|---|---|---|
| Error ✕ | Two glyphs share a spelling and aren't a vertical pair; Letters with characters other than a–z A–Z 0–9, or starting with a digit; a non-CJK character in 简体/繁體; a reserved character (点 點 徽 。 ，) used alone | **Yes**, all of Save, until fixed (draft kept) |
| Warning ⚠ | The round-trip check fails (`xi4` → 息 + 四); a vertical form that isn't in the Character part | No |
| Hint · | Letters (3+ letters) don't match Reading (`yanlou` vs yuán lǒu); 繁體 same as 简体 | No; shown in the inspector and as a badge |
| Info | A new spelling joins two existing ones (`ki` = k + i): shown as a before/after in What changes | No |

## Save model (recommendation, unchanged)

**One explicit Save, shared with the design.** Saving each edit at once (today's model) has four problems:

- There is no undo. A typo that replaces `k` is written to disk before you notice.
- "Add to area" (unsaved) and "give it a spelling" (saved at once) end up half-saved, and they are now in the same inspector.
- A clash would be written to disk and break the next build.
- The hosted phase is draft → proposal, so instant writes would have to be redone anyway.

The glyph editor keeps its own Save because an outline is a separate file with its own drawing undo.
Cost: the server checks two hashes before writing either file.

## Data: keep the CSV (recommendation, your call)

Keep `components.csv` as its own file, one line per glyph, and drop `ID`, `keys` and `filename`. Reasons:

- One-line git diffs.
- It opens in a spreadsheet.
- No build change.
- A spelling proposal and a spacing proposal touch different files, so they don't conflict when merged.

Moving it into `design.json` would give one file, one hash and an atomic Save. The costs:

- design.json grows from 1 741 lines to about 2 600.
- Every role's proposals edit the same file.
- `data.py`, the devserver glyph endpoints and the app's writer change.

Area membership has already moved to design.json, and that's fine: membership is layout, spelling is input.

## Findings in today's data

- `xi4` (细) types 息 + string 4, and `fu4` (復) types 沸 + string 4. Digits are read as numbers first, and only `zhi4` has a
  hand-written rule. Engine fix: generate that rule for every Letters value that contains a digit.
- `keys` = `0.5` on md_ban types 散 . 五. `keys`, `common`, `ID` and `filename` never reach the font (`common` is hard-coded).
- The Areas note "fine, substitution picks by context" is wrong for anything that isn't a vertical pair: `validate.py` fails the build.
- Hints: md_yuanlou `yanlou` vs yuán lǒu. md_fu2 `fu` vs fèi. lg_li's 繁體 `歴` is the Japanese form (Chinese 歷).
  mod_fanyin and xl_la repeat 简体 in 繁體.
- Vertical forms repeat their partner's spellings, but those repeated rows never produce a rule. md_san2 also has its own `san`.

## Interaction notes

- `/` focuses search. ⌘C / ⌘V work on cell ranges in the Typing view. During Chinese IME composition, checks wait for `compositionend`.
- Each field and cell is checked as you type, in a line under it (free ✓ / taken ✕ / shared with its vertical form ⇄ / joins two spellings).
  In Tiles a clash line offers "Show both", which switches to Typing filtered to Clashes.
- Leave guard and draft: the same as the design.

## Superseded from v1

- The separate **Typing** nav tab (`/typing`), its right-hand side panel and its toolbar filter chips. Now: the Glyphs view, the bottom inspector and the sidebar filters.
- The Glyphs inspector's read-only "Typed as … Typing →" line. Now: editable fields in the inspector.

## Left out on purpose

Spelling fields in the inspector while in the Typing view. Editing `edge_cases.fea` or `glyphRename.csv`. A free-form typing-rule builder.
Adding number or symbol spellings. Choosing which glyph wins a shared spelling (the horizontal glyph beats its vertical form). Editable rows
for the decimals. Renaming glyphs. Per-row history.

## Owner decisions (2026-10-17)

These settle the open questions above; where this list and earlier sections differ, this list wins.

1. **Column labels:** Glyph Name, Latin Entry, Latin Entry (Alt), Number/Symbol, PinYin. 简体, 繁體 and Vertical form keep Kat's labels. The view stays "Typing".
2. **Glyph Name is the ID.** `keys`, `ID` and `filename` are dropped from components.csv; tiles show the first working spelling.
3. **Sidebar groups by area** (design.json areas, their own labels, design.json order), in both views. A glyph in several areas appears under each. The 130 position decimals fold inside 徽 position. Unassigned stays as a safety net.
4. **A clash pauses all of Save**, with a clear message naming the spelling and both glyphs, and one-click Undo / Go to each glyph.
5. **Vertical forms store only the link** to their partner, plus any spelling of their own (md_san2's `san`). The partner's spellings show greyed as inherited. The font output is unchanged.
6. **Spellings containing a digit get a generated rule** (as `zhi4` has by hand today), so `xi4` and `fu4` work. The hand-written `zhi4` rule in edge_cases.fea goes away.
7. **No on-the-fly characters in the preview; missing characters show in red.** Every preview (Try it, Tester, Test & Build) reads the character map of the font being tested and wraps any character that font lacks in a red span. The browser still draws it with an installed font, so it stays readable, but it can't pass for part of the font. A new character in 简体 reads "not in the font yet: arrives with the next Build". Leftover letters from a spelling that didn't match are in the font and stay black; Try it's round-trip check flags those. No separate error glyph or error font, and md_placeholder (`*`) keeps its meaning.
