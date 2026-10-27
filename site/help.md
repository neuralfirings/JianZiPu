<!-- Generated from app/src/routes/help/+page.svelte by `npm run help:export` in app/. Edit the page, not this file. -->

# How to use the Builder

The JZP Font Builder is where the JianZiPu font is made: the drawings of its parts, how each part is typed, and how the parts sit together in a 减字 character. This page walks through each screen in the order you'd usually use them.

Changing the Builder itself? The [design guide](https://builder.jianzipufont.com/help/design.html) says how it looks and behaves, on a computer and on a phone.

## Getting started

A JianZiPu character is built from parts, much as an English word is built from letters. You type a short code such as `s7k5`, and the font swaps each piece for a drawn part (名, 七, 勾, 五) and stacks them into one character. The Builder has a screen for each of those steps:

- **[Glyphs](https://builder.jianzipufont.com/glyphs)**: The drawn parts. Each one belongs to an area (finger, hui, string…), and each has spellings: what you type to get it.
- **[Layouts](https://builder.jianzipufont.com/layouts)**: How the parts of each kind of character sit together: which parts it has, the gaps between them, and how it's centred.
- **[Build & test](https://builder.jianzipufont.com/test)**: Build the real font file and type in it.

A usual round: change a glyph or a rule, watch it in the live preview, **Save**, then **Build font** and check the result in real text.

> The Builder runs in two ways. **Online**, for invited testers, everything you do goes into [your own draft](https://jianzipufont.com/help/#draft); the real font doesn't change until your draft is reviewed. **On your own computer** (the **Local files** chip in the header), Save writes the files in `builder/inputs/`, which you then commit.

### On a phone

The Builder is made for a computer, but it opens on a phone too. Controls are larger there, the screens are tabs along the bottom, and tapping a button that shows only an icon also shows its name for a moment. Drawing glyphs, Review (apart from your own changes), making a release and importing or exporting the design need a mouse and a big screen, so on a phone they say so first: **Copy link** copies the page's address to open on a computer, and **Open anyway** opens the tool on the phone until you reload the page.

## How words are typed

Every box where you type words in the Builder, and the font itself, read the same codes. A word is its parts in order, with no spaces; a space starts the next word.

| Type | You get |
| --- | --- |
| `s7k5` | 名 (finger) + 七 (hui) + 勾 (right hand) + 五 (string). Typed in Chinese, `名七勾五` gives the same character. |
| `0k3` | 散 (open string) + 勾 + string 3. |
| `s7,5` | A comma separates hui and string when there's no right-hand technique. |
| `s7.6k5` | A dot makes a position decimal (七徽六分). `13+` is 徽外. |
| `s7>\k5` | Modifiers: `>` 急, `/` 绰, `\` 注. |
| `fys9k5` | `fy` (or `fanyin`) adds 泛音. |
| `:fenkai` `:shang79` | A colon starts a vertical word: one to four rows, each a character or a finger + hui. A glyph's vertical form is used after the colon. New in 3.300: a word with a part only a vertical word can hold (上, 下, 分开…) gets its colon without one: `shang79` is `:shang79`. Type the colon for a word that would otherwise be read as a standard note: `:lun3`, `:v8`. |
| `C03\|s6,5` | Chords: `C` 撮 (also `DC`, `FC`), the left note, `\|`, the right note. `TT` 双弹 and `BL` 拨剌 work the same way. |
| `#` `+` | `#` starts a new word without a space; `+` adds an advance between words. |

The exact keys for each part are its spellings, listed and edited in [Glyphs → Typing](https://builder.jianzipufont.com/glyphs?view=typing). The **Sample set…** menus in Layouts and Build & test hold ready-made word lists (basic words, decimals, modifiers, chords, vertical words, Chinese input, edge cases).

## Glyphs

[Glyphs](https://builder.jianzipufont.com/glyphs) lists every drawn part. The sidebar groups them by **area** (all glyphs in an area share a box size and can stand in for each other in a word); **Unassigned** holds drawings that aren't in an area yet, so the font can't place them.

![The Glyphs screen: areas in the sidebar, the Right hand area as tiles, and the inspector for 勾 below](https://builder.jianzipufont.com/help/glyphs.jpg)
*The Right hand area as tiles, with 勾 (`lg_gou`) selected: its areas, file and spellings below, and Try it on the right.*

### Finding and adding

- **Search** finds a glyph by spelling, character, pinyin, name or decimal: `k`, `勾`, `gou`, `lg_gou` and `7.6` all work.
- **+ New glyph** opens a new drawing: give it a name (such as `md_9`), pick its area, and start blank, from an SVG file, or from an image to trace.
- With an area picked, **+ Add glyphs** puts existing drawings into it. One glyph can be in several areas.
- Click a tile to select it; double-click it (or press Enter, or its **Edit** pill) to open the [glyph editor](https://jianzipufont.com/help/#editor).

On a phone, two menus above the tiles pick the area and a spelling filter, and tapping a tile opens the glyph's card over the tiles: its areas, its spellings to edit, and Try it. **All glyphs** goes back. Drawing needs a computer, and so do **+ New glyph**, the reference weight and the CSV import and export.

Below the tiles, the inspector shows the selected glyph: its areas, its file, buttons for **Edit outline**, **Replace…** and **Trace…**, its spellings, and **Try it**, which types each spelling and any word you enter through the unsaved spellings, live.

### Typing: spellings

The **Tiles | Typing** switch turns the screen into a table of every glyph's spellings. Each column is one way to type the glyph:

![The Typing table for the Left hand area: glyph names with their Latin entries, 简体 characters and pinyin](https://builder.jianzipufont.com/help/typing.jpg)
*Typing, showing the Left hand area: `s` types 名, `d` types 中.*

- Latin Entry: What you type on an English keyboard: a one-letter shortcut (`k`) or the pinyin (`lun`). On an empty cell, Tab accepts the greyed suggestion made from the pinyin.
- Latin Entry (Alt): A second way to type it (`bl`, `fy`).
- Number/Symbol: Digits and symbols typed the same in any input mode (`7`, `13+`, `/`). Shown, not edited here.
- 简体 / 繁體: The characters as typed with a Chinese input method. 繁體 only when it differs from 简体.
- Vertical form: The glyph the font swaps in after a colon (the centred version).
- PinYin: For search and labels only; never typed.
- Glossary: Where the glyph has a row in the glossary on jianzipufont.com, by the section's title: pick one from the list, such as `1c: Left Hand Techniques`, or two separated by a semicolon (`1d: Special Cases; 3c: Related to String & Hui Number`). Empty when it only appears inside a word (带 in :带起). The page is rewritten from this at the next release; never typed.

- Enter keeps a cell and moves down (⇧Enter moves up), Tab moves right, Esc puts the old value back.
- Paste a range copied from a spreadsheet to fill down and across in one step.
- **More** → **Import spellings (CSV)…** and **Export spellings (CSV)** move the whole table in and out. An import only changes the screen until you Save.
- Each spelling is checked as you type. Two glyphs can't share a spelling (except a glyph and its own vertical form): a **clash** holds Save until it's fixed. A spelling that types something else gets a warning, but Save still works.
- The **Typing** filters in the sidebar (Needs attention, Clashes, No spellings yet, Vertical pairs, Unsaved) narrow the table to what needs work.

On a phone, Typing is a list of cards, one per glyph: its spellings and anything wrong with them. Tap a card to edit its spellings on the glyph's card. Pasting a range and the CSV import and export need the table, on a computer.

## The glyph editor

Opening a glyph, or [+ New glyph](https://builder.jianzipufont.com/glyphs/new), brings up the editor: a drawing canvas with the glyph's box, a tool rail on the left and panels around it.

![The glyph editor with 勾 on the canvas, tools on the left, Selection, Compare and Glyph panels on the right and the Tester below](https://builder.jianzipufont.com/help/editor.jpg)
*勾 in the editor: tools on the left, panels on the right, and the Tester showing it in words below.*

### Drawing

- Tools: Select `V`, Pen `P`, Pencil `⇧P`, Rectangle `R`, Ellipse `O`, Hand `H` (or hold Space), Zoom `Z`. **Keyboard shortcuts** on the rail lists every shortcut.
- To edit points, use Select (`V`): click a shape to show its points, then click a point and drag it (arrow keys nudge it, `⇧` × 10). A selected point shows its curve handles; drag a handle's round end to bend the curve. On a smooth point the opposite handle follows; `⌥`-drag moves one handle alone. Double-click a point to switch it between corner and smooth. `⇧`-click adds points to the selection, and `⇧`-drag a box around them picks several. With the Pen, click the outline to add a point, or click a point to remove it.
- Combine two selected shapes with Union, Subtract, Intersect or Exclude (hover to preview). **Simplify…** removes points; **Thicken…** makes strokes heavier or lighter; **Clean up** fixes overlaps.
- Lines drawn with the Pen or Pencil are strokes until **Outline line(s)** turns them into filled shapes. Save does this for you.
- **SVG file…** imports a drawing (fit to the box, or keep its size; replace or add). You can also drop a file on the canvas or paste SVG text.
- **Image to trace…** turns a scan or photo into an outline: adjust Threshold, Corners and Simplify in the Trace panel, then **Use this outline**. The image itself stays in your browser.

### The panels

Each panel's **?** shows the same text as below.

- **Selection**: The position and size of what is selected: points (corner, smooth or free) or whole shapes (move, scale, rotate, centre in the box). With nothing selected it shows the glyph's shape count and its estimated stroke weight.
- **Compare**: Things to measure against while drawing: a **reference dot** (`D`) at the stroke weight to aim for, another glyph laid over this one (`G`), or the last saved outline (`L`).
- **Glyph**: Which areas the glyph is in (and so its box size), and the file it saves to.
- **Typing**: The glyph's spellings: what you type to get it, in Latin letters, numbers and symbols, 简体 and 繁體. Two glyphs can't share a spelling. The same fields are in [Glyphs → Typing](https://builder.jianzipufont.com/glyphs?view=typing).
- **Try it**: Types each spelling on its own, and any word you enter, through the spellings as they are now, saved or not. Red means "not in the font" until the next build.
- **Checks**: Problems the build would trip on: an empty glyph, parts outside the box, open lines and specks, each with a button to fix it. **Check as built** runs the same conversion as the font build.
- **Tester**: Words that use this glyph, drawn live as you edit, so you can see it in context before saving.
- **Trace**: Turns the image you opened into an outline. Adjust **Threshold** (or **Auto**), specks, corners and simplify, then **Use this outline**. The image stays in your browser. `Esc` leaves trace mode.

### Saving a glyph

The editor has its own **Save glyph** (`⌘S`) and its own undo. Edits that aren't saved yet are kept in the browser, and leaving asks whether to save or discard them. Online, saving puts the glyph into your draft. On your own computer, saving writes `builder/inputs/svg/<name>.svg` at once; if the file changed on disk meanwhile, you're asked which version to keep. A new glyph joins its area on its first save. The font picks up the new drawing at the next **Build font**.

## Layouts

[Layouts](https://builder.jianzipufont.com/layouts) is where the parts are arranged. A **word type** is one kind of character (a standard note, a chord, a vertical word…): which parts it has, in which order, and how they're spaced. The canvas shows one example word; the panels around it edit it.

![The Layouts screen: word types and structure on the left, the standard word on the canvas with part boxes, area properties and tester below](https://builder.jianzipufont.com/help/layouts.jpg)
*The standard word type: its parts on the left, an example word with its part boxes in the middle.*

### The canvas

- Click a part to select it (Tab cycles through parts). Drag it, or nudge it with the arrow keys, to change its gap.
- Arrows show spacing rules: click one to edit it. Drag a part's ○ handle onto another part's edge to attach it there.
- **boxes** and **glyphs** switch the outlines; `b` toggles boxes, `⇧1` fits the word.
- On a phone: a swipe scrolls, even when it starts on the canvas; a tap selects a part or an arrow; press and hold a part (or a ○ handle): a ring fills around your finger, then the part lifts with a thicker outline and a shadow. Drag it; the rule's arrow and the line under the canvas show the gap, and letting go is one undo step.

### The panels

Panels can be docked left, right or below, folded and resized; **More** → **Reset panel layouts** puts them back. Each panel's **?** shows the same text as below.

- **Word types**: Pick the word type to edit: a standard note, a vertical word, the two halves of a chord. Each shows how many positioning rules it makes; **skipped** lists shapes that get no rule. With **Advanced** on you can add, duplicate or delete word types.
- **Structure**: The parts of the word type, in order. Tick a part to include it in the example word and pick which glyph it shows. **anchor** marks the first part of the chain, which carries the word's position. With **Advanced** on you can add, remove, reorder and make parts optional or repeating.
- **Page center**: The point on the page that centring aims for, in font units. Every word type that is centred uses it.
- **Font budget**: How many positioning rules each word type makes, and an estimate of their size. The build stores each rule as its own small table, so size is far from a limit (a single lookup can hold 65,535). What to watch is **skipped**: word shapes that get no rule because a part has nothing placing it, so those words won't be laid out. The **rules · KB** pill in the header opens this panel; it shows **!** while anything is skipped.
- **Spacing**: How the selected part sits against the others, vertically or horizontally (the **Vertical** and **Horizontal** tabs). A rule reads as a sentence: "its top edge sits at the bottom of 七 + gap". Rows change the gap when certain glyphs are present; *otherwise* covers the rest. **+ new rule** picks the glyphs it applies to, and the canvas previews every combination. You can also drag the part on the canvas (on a phone, press and hold it first).
- **Centering**: Which parts the word is centred on, and where. When a word is centred on an axis, the whole word is shifted to the target, so a start height on that axis (marked * on the canvas) doesn't move it: change the gaps between parts instead, or the target here.
- **Area Properties**: An area is a set of glyphs that share a box size and can stand in for each other in a word (all the strings, all the hui numbers…). Here: the box size (type to preview, `Enter` applies, `Esc` cancels), the word types that use the area, and its glyphs (**Manage** to add or remove). **Delete area** works only on an empty area nothing uses. The **Chord divider** and **Vertical marker** areas also have **Width of |** (or **:**): how far the next part moves after the divider, and the divider's own width in the font; it sets the box width too.
- **Tester**: Words drawn by the live preview, unsaved changes included. Type your own, pick a **Sample set…** or **Random**; click a word to put it on the canvas. **Build & test** opens the same words next to the built font.

Structural edits (adding, removing or reordering parts, new word types, recognition rules) are behind the **Advanced** checkbox in the header, so they aren't changed by accident. It's off again after a reload.

On a phone, the canvas stays at the top and the panels are sections under it, in a fixed order: tapping a part opens its **Spacing** just below the canvas, and pressing and holding it drags it. In Spacing, drag a rule row by its grip to change the order, and press and hold a base in the *relative to* line to drag it to another place in the line. Reordering the parts in **Structure** and the **Advanced** edits need a computer.

## Build & test

[Build & test](https://builder.jianzipufont.com/test) makes the real font file and shows text in it.

- **Build font** builds from the saved files. Online, it builds from your draft as it is now, unsaved edits included. On your own computer, with unsaved changes the button reads **Save & build** and saves first. It takes about half a minute; the build log opens below.
- Each build is a separate file. **Download JianZiPu.ttf** saves it; earlier builds from this session stay in the list.
- **Font** is the font the page shows: the newest build, an earlier one, or any **.ttf file** you open (the released font, say). It's loaded into the page under its own name, so a JianZiPu installed on your computer never stands in for it.
- When the Builder has changes the released font doesn't have yet, a note at the top says so (**Builds include changes that aren't in the released font … yet**) and lists them. They go out with the next release. A font built here says "dev build, not a release" in its version.

![Build and test, Test the design view: each word drawn live above the same word in the built font](https://builder.jianzipufont.com/help/build-design.jpg)
***Test the design** with Compare both: the live drawing on top, the built font below. Under each word, what was typed and the glyphs it became.*

### Two views

- **Test the design**: One cell per word, to check your design without building. **Live preview** draws from the design as it is now, unsaved changes included, with optional boxes; **Font** shows the built font; **Compare both** puts them one above the other. Click a live word to open it in Layouts. **+ Save as set** keeps the current words as a sample set.
- **Test the font file**: Running text in the font file, as a reader sees it. Switch **liga** (substitution) and **kern** (positioning) off to see the raw parts, try **vertical columns**, or **compare with a second font** side by side.

![Build and test, Test the font file view: the same words as running text in the built font](https://builder.jianzipufont.com/help/build-font.jpg)
***Test the font file**: the same words as running text in the built font.*

On a phone, the words come first and the box you type in sits under them, above the keyboard. The line at the top (**No build yet**, or when the last build was made) opens the build, font and view settings and the build log.

A character the font doesn't have is drawn by another font in red, so it can't pass for part of the font. In Test the design, **warning** under a word means some of its parts matched no word type.

## Saving and undo

- Edits to the design and the spellings stay in the browser until you **Save** (`⌘S`). The header shows **unsaved** with a count; click it to see the list or **Discard all**.
- **Undo** **Redo** in the header (`⌘Z`, `⇧⌘Z`) undo and redo whole steps, such as one rule change or one paste. Hover them to see which step.
- Save waits while a spelling clashes, and says which ones; fix them in [Glyphs → Typing](https://builder.jianzipufont.com/glyphs?view=typing&f=attention).
- Unsaved work survives a reload: the Builder offers to restore it.
- On a phone, the header is one row (the screen's name, its status, **Undo** **Redo** on Glyphs and Layouts, and **More**), the screens are tabs at the bottom, and **Save** sits in a bar above the tabs while something is unsaved.
- Online, your draft also saves itself 30 seconds after an edit, when you change screen, and when you leave the tab.
- On your own computer, Save writes `design.json` and `components.csv` in `builder/inputs/` (glyph files are saved from the editor). If a file changed on disk since you opened it, you choose: reload it, overwrite it, or export yours first. Then commit the files with git.
- On your own computer, **More** → **Export…** / **Import…** move the design (word types, areas, sample sets) as one JSON file; an import becomes unsaved changes you can look over first.

## Your draft (online)

Invited testers use the Builder online. You sign in with a link sent to your email (no password). Everything you change goes into your own **draft**: only you see it, and nothing you do changes the real font or anyone else's work.

- Your draft is compared with a **reference font**, a release such as 3.200: **Your changes** are what your draft does differently from it. The **Your draft** pill in the header shows your reference font and how much you've changed. **See my changes** lists the changes item by item.
- On that list, **Undo this change** puts one item back the way your reference font has it: a glyph, a glyph's spellings, an area or a word type. For a word type, **Show the spacing rules** lists each rule you changed, and each has its own Undo. Every undo is one step you can take back with **Undo**. To throw everything away at once, use **More** → **Discard my draft…**.
- To share your work, **More** → **Export my draft (.zip)…** and send the file. **Import a draft (.zip)…** opens one again.
- When a new release is out, a banner offers **Set reference font to 3.200 (latest)…** (with the new number). Your changes stay yours and are compared with the new release from then on: its changes come in, the ones it already has leave Your changes, and where you both changed the same thing you pick **Keep mine** or **Take the font's**.
- **Feedback** in the header goes to the font's maintainer. Confusing, broken or lovely, it's all useful.

## Change Requests

When some of your changes are ready for the real font, send them as a **Change Request** (a CR). The font's maintainer looks at each change, keeps or skips it, and replies.

- On [Your changes](https://builder.jianzipufont.com/review?mine), choose **Send Change Request…**. Every change is ticked to start with; untick any you want to keep working on. Give it a title, say what you changed and why, and how you'd like to be credited in the release notes: your name the way it should read, such as *Mei Chen* or *Mei Chen (Taipei Qin Society)*, or nothing for no credit.
- **Save as draft** keeps the request with your draft, ticks and notes included, so you can finish it later, on this computer or another. It shows on [Your Change Requests](https://builder.jianzipufont.com/requests) as **Draft · not sent**, with **Continue…** to pick it up again.
- Before it goes, the Builder saves your draft, checks the chosen spellings don't clash, and builds a font with just those changes.
- Once sent, those changes are **locked** in your draft: you can look at them and try words, but not edit or undo them. Everything else stays yours to change.
- [Your Change Requests](https://builder.jianzipufont.com/requests) shows each one's status, the maintainer's reply, and what you sent. You get an email when the status changes.
- Statuses: **Sent**, **In review**, **In a release candidate** (a test version of the next font), **Released**, **Declined**, **Withdrawn**. A request can be partly kept: "3 of 5 changes in v3.200".
- **Withdraw…** takes a request back, until the maintainer keeps one of its changes. Withdrawn and declined requests unlock their changes in your draft.
- When your changes are released, they fold away on Your changes under **In the font now**, and the request moves to **Released and closed** on Your Change Requests. **Set reference font to 3.200 (latest)…** compares your draft with the new release, and they drop out of Your changes. Released changes aren't locked: they're the font's now, and you can change them again like any other part.

## Reviewing Change Requests

On your own computer, signed in as an admin, [Review](https://builder.jianzipufont.com/review) lists the Change Requests testers sent, newest first. An email with a link to each one arrives when it's sent.

- Open a request to see its title, notes and how its author wants to be credited, then each change before and after: glyphs drawn over each other, spellings side by side, design changes with sample words and the JSON. **Keep** or **Skip** each one, or **Keep all**.
- Write a reply if you like, then **Save decisions**. Nothing goes into the font yet: the request becomes **In review** (or **Declined** if you skipped everything) and its author gets an email. Kept changes go into the next [release candidate](https://jianzipufont.com/help/#release).
- **Current drafts** below the requests shows what each tester is working on now. Opening a draft or a **.zip** and choosing **Apply** brings changes in directly, as one undoable step of unsaved changes. A **Conflict** means you changed the same thing since the draft started: pick whose version to use.

## Making a release

On your own computer, [Release](https://builder.jianzipufont.com/release) (from Review, or **More** → **Make a release…**) turns kept changes into a new version of the font. It runs git for you, with your own GitHub sign-in.

1. **Start a release candidate** with the next version number, such as 3.200. The Builder makes the branch `release/3.200` from main. A release branch holds only font files; Builder code goes to main on its own branch.
2. **Add kept changes** brings in every kept change from the reviewed requests, oldest first, as unsaved changes. Where two requests change the same thing, you pick which one wins.
3. Check the result in Layouts and Build & test, adjust, then Save.
4. **Build candidate** runs the tests, builds the font, writes the version and the changelog entry (it starts with any code changes queued under *Unreleased* in `CHANGELOG.md`), and tags `v3.200-rc.1`. GitHub publishes it as a pre-release, and the requests' authors get an email. Open the pull request from there. If testers find a problem, fix it and build again (`rc.2`).
5. Merge the pull request on GitHub with **Create a merge commit** (not squash or rebase, which would leave the candidate's tag off main), then **Publish**: main is tagged `v3.200`, GitHub publishes the release with the font attached, jianzipufont.com serves the new font, and the requests become **Released**.

Version numbers have a three-digit minor part (3.100, 3.200, 3.201), because the font stores the version as a number. Raise the first number only when existing documents would look different or break.

The full process, with testing a candidate and what to do when a step fails, is in `docs/maintainers/releasing.md` in the repository.

## Keyboard shortcuts

**Everywhere**

- `⌘S`: Save
- `⌘Z` / `⇧⌘Z`: Undo / redo (not while typing in a field)

**Glyphs → Typing**

- `Enter` / `⇧Enter`: Keep the cell, move down / up
- `Tab`: Next cell; accepts a suggestion in an empty Latin Entry
- `Esc`: Put the old value back

**Layouts**

- `Tab` / `⇧Tab`: Next / previous part
- arrows (`⇧` × 10): Nudge the selected part's gap
- `b`: Show or hide boxes
- `⇧1`, `+`, `−`: Fit, zoom in, zoom out
- `⌫`: Delete the selected rule arrow

**Glyph editor**

- `⌘S`, `⌘Z`: Save the glyph, undo in the glyph
- `V` `P` `⇧P` `R` `O` `H` `Z`: Select, Pen, Pencil, Rectangle, Ellipse, Hand, Zoom
- `D` `G` `L`: Reference dot, compare glyph, last saved
- `⇧1` / `⇧0` / `⇧2`: Fit / 100% / fit the selection
- `⇧G`: Grid
- `⌥⌘O`: Outline lines

## When something looks wrong

- **A character shows in red**: The font doesn't have it yet: a new glyph or spelling isn't in a build. **Build font** again. In Try it, red means "not in the font until the next build".
- **The live preview and the font differ**: The live preview includes unsaved changes; the font is only what was saved when it was built. Save and build.
- **warning under a word**: Some parts of the word matched no word type, so the font won't place them. Check the spelling, or the word type's parts in Layouts.
- **Save is waiting**: A spelling clashes with another glyph's or isn't valid. **Show them** lists the cells to fix.
- **A new glyph never appears in words**: It needs an area (**Unassigned** in Glyphs) and at least one spelling.
- **The build failed**: The first error is shown above the build log; the log has the rest. [Messages and errors](https://jianzipufont.com/help/#messages-build) lists the usual ones and their fixes.

## Messages and errors

What the Builder's messages say, word for word, and what to do about each. Words in *italics* stand for a name or number that changes.

### Signing in

- **“This email isn't on the pilot list”**: That address wasn't invited: the online Builder is for a few invited testers. If you were invited at another address, use that one; otherwise press **Ask for an invite**.
- **“This sign-in link has expired”**: A link works once, for an hour, in the browser you asked for it from. Press **Email me a new link** and open the new one in the same browser.
- **“We can't reach the sign-in service right now. Try again in a minute.”**: The sign-in service isn't answering. Check your connection and send the link again in a minute. “The sign-in service isn't answering. Try again in a minute.” is the same thing, seen from the server.
- **“For security purposes, you can only request this after *n* seconds.”**: Links were asked for too quickly (the sign-in service's own words; “Email rate limit exceeded” is another). Wait, then send again.
- **“You've been signed out. Your unsaved changes are kept in this browser.”**: The sign-in ran out. Press **Sign in again** and open the emailed link; your changes are still there afterwards. “Sign in first.” means the same.
- **“Sign-in is not set up on this server.”**: The server has no sign-in settings. Only whoever runs it can fix this (`SUPABASE_URL` and `SUPABASE_ANON_KEY`).

### Your draft (online)

- **“Your draft isn't saved. We can't reach the server.”**: You're offline, or the server can't be reached (the header says **Not saved · offline**). Your changes are kept in this browser and save by themselves when the connection is back; **Try again** retries now. Don't clear the browser's data or close a private window meanwhile.
- **“Your draft isn't saved. The server turned it down: …”**: The connection works, but the draft storage said no; the reason follows. Your changes are kept in this browser. Press **Try again**; if it fails again, **Export my draft** to keep a copy and **Send feedback** with the reason.
- **“The Builder is taking a break: we can't reach it right now. Your saved draft is safe.”**: The Builder's server didn't answer while loading; the reason is in brackets at the end. Press **Retry** in a minute.
- **“Your draft was saved by a newer version of the Builder than this page. Reload the page to get it.”**: You (or another tab) used a newer Builder since this page loaded. **Reload the page**.
- **“Your saved draft can't be opened: … It is still stored and nothing has been changed.”**: The stored draft is damaged; the reason follows. Retrying won't help, and nothing is lost yet: **Send feedback** so it can be recovered.
- **“Your draft was saved somewhere else”**: Another tab or computer saved (or discarded) your draft after you opened it here. Pick the version that stays; **Export this one first** keeps a copy of this tab's.
- **“Restored *n* changes from your last visit that hadn't reached your draft.”**: Edits from last time that hadn't been saved yet. **Save them** or **Discard them**. On your own computer it reads “Restored unsaved changes from your last session.”
- **“This Builder is read-only: your changes are kept in your own draft.”**: The page is an old copy of the Builder. Reload it.

### Saving

- **“Save is waiting”**: Some spellings would stop the font from building; the dialog lists them. **Show them** opens [Glyphs → Typing](https://builder.jianzipufont.com/glyphs?view=typing&f=attention) at the cells to fix, or **Undo last change**. Your changes are kept meanwhile.
- **“design.json changed on disk” / “components.csv changed on disk”**: On your own computer: the file changed since you opened it (a git pull, another tab, an editor). **Export mine first**, then **Reload from disk**; or **Overwrite** if yours should win.
- **“Not saved: …”**: On your own computer: the server couldn't write a file; the reason follows (“Not saved: *name*.svg: …” for a glyph file). Your changes are still here. Fix the cause, then **Try again**. “Not saved: can't reach the web server” means the server stopped: start it again (below) and press **Try again**.
- **“Can't reach the web server. Run: cd builder && python3 -m jzpbuild.webserver”**: On your own computer: the Builder's server isn't running. Start it with that command and reload.
- **“This Builder only answers on localhost.”**: Open it at `http://127.0.0.1:5713`, or start the server with `--host` and the address you use.
- **“unknown endpoint *path*”**: The page and the server are different versions. Restart the server and reload.

### Spellings

- **“*k*” types 2 glyphs (*a, b*). A spelling can make only one glyph.**: A clash (under the cell: “already used by …”): two glyphs share a spelling, and Save waits until it's fixed. Give one of them another spelling. If one is the vertical form of the other, link them in **Vertical form** instead of repeating the spelling.
- **“start with a letter: a leading digit is read as a string or position number”**: A Latin Entry must start with a letter; digits at the start mean strings and hui.
- **“use only letters a–z, A–Z and digits”**: Latin entries take no spaces, accents or symbols; symbols go in Number/Symbol.
- **“alone it marks a position; it can't type a glyph”**: 点, 點, 徽, 。 and ， on their own are kept for position numbers. In the Save is waiting list: “*x*” alone marks a position; it can't type a glyph.
- **“Chinese characters only”**: The 简体 and 繁體 columns take only Chinese characters.
- **“*name* doesn't exist” / “Vertical form *name* doesn't exist.”**: The Vertical form names a glyph with no drawing and no area. Make that glyph first, or fix the name.
- **“no glossary section “*9z: …*” on the font page: pick a title from the list”**: A warning: the Glossary column names a section the font page doesn't have, or spells its title differently. Save still works, but the next release can't put the glyph in the glossary; pick the title from the list the cell offers.
- **“joins *a* + *b*: typing *ab* gives this glyph instead of …”**: A warning: the spelling is two other spellings run together, so typing it no longer gives those two. Save still works; change it unless that's what you want.
- **Typing “*x*” gives *a + b*, not *glyph*.**: Typed alone, the spelling makes something else, because a longer or earlier spelling catches it. Change this spelling or the one that catches it. Save still works.
- **“not in the font yet. It arrives with the next Build.” / “isn't in the last build yet. Build to preview it.”**: The spelling or glyph is newer than the last build. **Build font** in [Build & test](https://builder.jianzipufont.com/test).
- **“Build the font once to preview spellings.”**: Try it needs one build first: **Build font**.
- **“Can't read *file*: no glyph_name column”**: A spellings CSV needs a header row that includes `glyph_name`. **Export spellings (CSV)** gives a file of the right shape to start from.

### The glyph editor

- **“Saved inputs/svg/*name*.svg · Layouts and the Tester use it now; the font needs a Build.” / “Saved *name* to your draft · …”**: The glyph is saved (to the file on your own computer, to your draft online). The font shows it after the next **Build font**.
- **“*name* is in your draft, not saved yet: …”**: Online: the outline is in your draft, but the draft itself didn't save; the reason follows (spelling problems to fix first, offline, or the server turned it down). It's kept in this browser, and the banner at the top says what to do.
- **“*name*.svg already exists on disk.” / “*name* already exists.”**: A new glyph's name is taken. Open that glyph instead, or pick another name.
- **“*name*.svg changed on disk”**: Someone, or another tab, wrote the file since you opened it. **Compare** shows the disk version as a dashed outline; then **Load disk version** or **Overwrite with mine**.
- **“the glyph is empty” / “Empty: nothing to save yet”**: There is nothing to save: draw or import something first.
- **“Sticks out of the box”**: Part of the drawing is outside the glyph's box, and Layouts places glyphs by their box. **Fit to box** or **Center** in the Selection panel, or change the area's box size in Layouts → Area Properties.
- **“*n* open lines: outlined on save”**: Pen or Pencil lines that aren't filled shapes yet. **Outline now**, or let Save do it.
- **“*n* specks under 6 units”**: Tiny bits, usually left by tracing. **Remove them**.
- **“the SVG needs a viewBox (or width and height)”**: The SVG file has no size. Export it again from the drawing program with a size or artboard.
- **“Unable to convert to picosvg: BadElement: …”**: The SVG holds something that isn't a shape, most often text. Convert text to outlines (paths) in the drawing program and import again.
- **“syntax error: line *n*, column *n*”**: The file isn't a valid SVG. Export it again from the drawing program.
- **“glyph names use letters, digits, '_', '-' and '.', e.g. md_9 or lg_gou”**: Rename the glyph with only those characters (the new-glyph dialog says “Letters, digits, _ - and. only.”).
- **“Can't trace *file*: it isn't an image this browser can read. Try a PNG or JPEG.”**: The file isn't an image, or is a kind the browser can't open (HEIC, TIFF, PDF…). Save it as PNG or JPEG and open that. “trace failed: …” means the image opened but couldn't be traced: try another image or a different Threshold.

### Layouts and areas

- **“Not placed: *part* has no vertical rule in this shape”**: Nothing tells the part where to sit in this word, so it's drawn at 0 in a red dashed box. Select it and add a rule in Spacing. If it already has one, look at the rule's rows: when none matches the glyphs in this word and there's no “otherwise” row, the rule doesn't apply. Add an otherwise row, or one for these glyphs.
- **“*n* skipped” / “Why *n* shapes are skipped”**: Some combinations of parts get no positioning rule, so the font won't place those words. The list gives the reason for each; usually “no rule row for … and no "otherwise"”: add an otherwise row to that rule.
- **“no unconditional last entry; words whose glyphs match no entry are not positioned”**: In Font budget: a spacing rule has only rows for particular glyphs. Add an otherwise row.
- **“Can't attach *A* to *B*: *B* is already placed relative to *A*”**: That would go round in a circle. Attach the other way round, or remove the existing rule first.
- **“Can't delete *area*”**: Only an empty area that no word type uses can be deleted. The banner lists what's left: remove its glyphs, and take it out of those word types in Structure (Advanced).
- **“The font can't be built from this design: …”**: The design names something that isn't there any more, such as “standard/hui: unknown area 'x'”, usually after an edit, an import or a merge renamed or removed an area or a part. The banner's **Undo** button takes back the last change; or fix the named word type in Layouts with **Advanced** on.
- **“Couldn't check the design: …”**: The server didn't answer the check run after each edit. **Check again**; if the server stopped, start it again.
- **“"*x*" is already a word type.” / “"*x*" can't be an id: use letters, digits and _ only, starting with a letter.”**: When adding or duplicating a word type: the question asks again with the reason. Type another id, or Cancel.

### Build & test

- **“ValidationError: input validation failed”**: The lines under it name the problem; usually a spelling claimed by two glyphs (“latin spelling 'k' is claimed by multiple glyphs”). Fix it in [Glyphs → Typing](https://builder.jianzipufont.com/glyphs?view=typing&f=attention) and build again.
- **“FeatureLibError: The following glyph names are referenced but are missing from the glyph set”**: A spelling names a glyph that has no drawing, or a vertical form is missing. Draw or import that glyph, or remove its spellings.
- **“FileNotFoundError: … src_font/TW-Kai-98.ttf”**: The base font is missing. On your own computer, copy `TW-Kai-98.ttf` into `builder/src_font/` (it isn't in git). Online, the server couldn't fetch it: send **Feedback**.
- **“a build is already running” / “Another font is being built right now; try again in a minute.” / “You just built a font; try again in *n* seconds.”**: Builds run one at a time, with a short pause between yours online. Wait, then **Build font** again.
- **“no build *id* (builds live only while this server runs)” / “could not load build …”**: Builds are kept only until the server restarts. Build again.
- **“too many words (*n*); at most 2000 at a time”**: Test fewer words at once.
- **“Something went wrong on the server. Try again, or send feedback.”**: An error the server didn't expect. Try again; if it happens again, send **Feedback** saying what you did just before.

### Drafts, review and import

- **“*file* isn't a Builder draft: it has no manifest.json.”**: The .zip wasn't made by **Export my draft**. A design file goes in through **More** → **Import…** instead.
- **“This draft was made with a newer Builder. Update this Builder first.”**: On your own computer: pull the latest code, rebuild the app (`npm run build` in `app/`) and restart the server.
- **“That file is not a .zip.” / “… in the zip is not valid JSON.” / “The draft has no usable design.json.” / “The draft lists … but has no file for it.”**: The file is damaged or was changed by hand. Ask for a fresh export.
- **“Pick *n* conflicts first”**: Apply waits until every **Conflict** has a side picked.
- **“This isn't a Builder design file (needs version 2, layouts[] and areas{}).”**: **Import…** takes a design.json exported by the Builder.
- **“Couldn't reach the form service. Check your connection and try again.” / “Not sent: …”**: **Feedback** or **Ask for an invite** didn't go. Check your connection (an ad blocker can stop it too) and send again.

### On a phone

- **“*The glyph editor* needs a computer. It's made for a mouse and a big screen. Open this page on a computer, or open it here anyway.”**: The same note stands in for Review, making a release, and importing and exporting the design. Press **Copy link** and open the link on a computer, or **Open anyway** to use the tool on the phone until you reload the page.

---

This is the help page of the JZP Font Builder (https://builder.jianzipufont.com) as plain text. The same page with screenshots: https://jianzipufont.com/help/. The JianZiPu font itself, with its typing guide: https://jianzipufont.com/.
