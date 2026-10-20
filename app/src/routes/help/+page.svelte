<script lang="ts">
  // How to use the Builder: one page, a contents list on the left (scroll-spied), a section per
  // screen. Sections and their order come from lib/help.ts; help.test.ts checks the links.
  import { onMount } from 'svelte';
  import { hosted } from '$lib/hosted.svelte';
  import { HELP_SECTIONS } from '$lib/help';

  let scroller: HTMLElement;
  let current = $state(HELP_SECTIONS[0].id);

  onMount(() => {
    const seen = new Map<string, boolean>();
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) seen.set(e.target.id, e.isIntersecting);
      const first = HELP_SECTIONS.find((s) => seen.get(s.id));
      if (first) current = first.id;
    }, { root: scroller, rootMargin: '0px 0px -70% 0px' });
    for (const s of HELP_SECTIONS) { const el = document.getElementById(s.id); if (el) io.observe(el); }
    if (location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
    return () => io.disconnect();
  });
</script>

<div class="page" bind:this={scroller}>
  <div class="layout">
    <nav class="toc" aria-label="Contents">
      <p class="toc-title">Contents</p>
      {#each HELP_SECTIONS as s}
        <a href="#{s.id}" aria-current={current === s.id ? 'true' : undefined}>{s.title}</a>
      {/each}
    </nav>

    <article>
      <h1>How to use the Builder</h1>
      <p class="lede">The JZP Font Builder is where the JianZiPu font is made: the drawings of its parts, how each part is typed, and how the parts sit together in a 减字 character. This page walks through each screen in the order you'd usually use them.</p>

      <!-- ─────────────────────────────────────────────── -->
      <section id="start">
        <h2>Getting started</h2>
        <p>A JianZiPu character is built from parts, much as an English word is built from letters. You type a short code such as <code>s7k5</code>, and the font swaps each piece for a drawn part (名, 七, 勾, 五) and stacks them into one character. The Builder has a screen for each of those steps:</p>
        <dl class="steps">
          <dt><a href="/glyphs">Glyphs</a></dt><dd>The drawn parts. Each one belongs to an area (finger, hui, string…), and each has spellings: what you type to get it.</dd>
          <dt><a href="/layouts">Layouts</a></dt><dd>How the parts of each kind of character sit together: which parts it has, the gaps between them, and how it's centred.</dd>
          <dt><a href="/test">Build & test</a></dt><dd>Build the real font file and type in it.</dd>
        </dl>
        <p>A usual round: change a glyph or a rule, watch it in the live preview, <strong>Save</strong>, then <strong>Build font</strong> and check the result in real text.</p>
        <div class="banner info"><span class="ic">◐</span><div>
          {#if hosted.isHosted}
            You're using the online Builder. Everything you do goes into <a href="#draft">your own draft</a>; the real font doesn't change until your draft is reviewed.
          {:else}
            You're using the Builder on your own computer (the <span class="chip dashed">Local files</span> chip in the header). Save writes the files in <code>builder/inputs/</code>, which you then commit.
          {/if}
        </div></div>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="typing">
        <h2>How words are typed</h2>
        <p>Every box where you type words in the Builder, and the font itself, read the same codes. A word is its parts in order, with no spaces; a space starts the next word.</p>
        <table class="ref">
          <thead><tr><th>Type</th><th>You get</th></tr></thead>
          <tbody>
            <tr><td><code>s7k5</code></td><td>名 (finger) + 七 (hui) + 勾 (right hand) + 五 (string). Typed in Chinese, <code>名七勾五</code> gives the same character.</td></tr>
            <tr><td><code>0k3</code></td><td>散 (open string) + 勾 + string 3.</td></tr>
            <tr><td><code>s7,5</code></td><td>A comma separates hui and string when there's no right-hand technique.</td></tr>
            <tr><td><code>s7.6k5</code></td><td>A dot makes a position decimal (七徽六分). <code>13+</code> is 徽外.</td></tr>
            <tr><td><code>s7&gt;\k5</code></td><td>Modifiers: <code>&gt;</code> 急, <code>/</code> 绰, <code>\</code> 注.</td></tr>
            <tr><td><code>fys9k5</code></td><td><code>fy</code> (or <code>fanyin</code>) adds 泛音.</td></tr>
            <tr><td><code>:fenkai</code> <code>:shang79</code></td><td>A colon starts a vertical word: one to four rows, each a character or a finger + hui. A glyph's vertical form is used after the colon.</td></tr>
            <tr><td><code>C03|s6,5</code></td><td>Chords: <code>C</code> 撮 (also <code>DC</code>, <code>FC</code>), the left note, <code>|</code>, the right note. <code>TT</code> 双弹 and <code>BL</code> 拨剌 work the same way.</td></tr>
            <tr><td><code>#</code> <code>+</code></td><td><code>#</code> starts a new word without a space; <code>+</code> adds an advance between words.</td></tr>
          </tbody>
        </table>
        <p>The exact keys for each part are its spellings, listed and edited in <a href="/glyphs?view=typing">Glyphs → Typing</a>. The <strong>Sample set…</strong> menus in Layouts and Build & test hold ready-made word lists (basic words, decimals, modifiers, chords, vertical words, Chinese input, edge cases).</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="glyphs">
        <h2>Glyphs</h2>
        <p><a href="/glyphs">Glyphs</a> lists every drawn part. The sidebar groups them by <strong>area</strong> (all glyphs in an area share a box size and can stand in for each other in a word); <strong>Unassigned</strong> holds drawings that aren't in an area yet, so the font can't place them.</p>
        <figure><a href="/help/glyphs.jpg" target="_blank"><img src="/help/glyphs.jpg" alt="The Glyphs screen: areas in the sidebar, the Right hand area as tiles, and the inspector for 勾 below" width="1280" height="800" loading="lazy" /></a><figcaption>The Right hand area as tiles, with 勾 (<code>lg_gou</code>) selected: its areas, file and spellings below, and Try it on the right.</figcaption></figure>
        <h3>Finding and adding</h3>
        <ul>
          <li><strong>Search</strong> finds a glyph by spelling, character, pinyin, name or decimal: <code>k</code>, <code>勾</code>, <code>gou</code>, <code>lg_gou</code> and <code>7.6</code> all work.</li>
          <li><strong>+ New glyph</strong> opens a new drawing: give it a name (such as <code>md_9</code>), pick its area, and start blank, from an SVG file, or from an image to trace.</li>
          <li>With an area picked, <strong>+ Add glyphs</strong> puts existing drawings into it. One glyph can be in several areas.</li>
          <li>Click a tile to select it; double-click it (or press Enter, or its <strong>Edit</strong> pill) to open the <a href="#editor">glyph editor</a>.</li>
        </ul>
        <p>Below the tiles, the inspector shows the selected glyph: its areas, its file, buttons for <strong>Edit outline</strong>, <strong>Replace…</strong> and <strong>Trace…</strong>, its spellings, and <strong>Try it</strong>, which types each spelling and any word you enter through the unsaved spellings, live.</p>

        <h3>Typing: spellings</h3>
        <p>The <strong>Tiles | Typing</strong> switch turns the screen into a table of every glyph's spellings. Each column is one way to type the glyph:</p>
        <figure><a href="/help/typing.jpg" target="_blank"><img src="/help/typing.jpg" alt="The Typing table for the Left hand area: glyph names with their Latin entries, 简体 characters and pinyin" width="1280" height="800" loading="lazy" /></a><figcaption>Typing, showing the Left hand area: <code>s</code> types 名, <code>d</code> types 中.</figcaption></figure>
        <table class="ref">
          <tbody>
            <tr><th>Latin Entry</th><td>What you type on an English keyboard: a one-letter shortcut (<code>k</code>) or the pinyin (<code>lun</code>). On an empty cell, Tab accepts the greyed suggestion made from the pinyin.</td></tr>
            <tr><th>Latin Entry (Alt)</th><td>A second way to type it (<code>bl</code>, <code>fy</code>).</td></tr>
            <tr><th>Number/Symbol</th><td>Digits and symbols typed the same in any input mode (<code>7</code>, <code>13+</code>, <code>/</code>). Shown, not edited here.</td></tr>
            <tr><th>简体 / 繁體</th><td>The characters as typed with a Chinese input method. 繁體 only when it differs from 简体.</td></tr>
            <tr><th>Vertical form</th><td>The glyph the font swaps in after a colon (the centred version).</td></tr>
            <tr><th>PinYin</th><td>For search and labels only; never typed.</td></tr>
          </tbody>
        </table>
        <ul>
          <li>Enter keeps a cell and moves down (⇧Enter moves up), Tab moves right, Esc puts the old value back.</li>
          <li>Paste a range copied from a spreadsheet to fill down and across in one step.</li>
          <li>⋯ → <strong>Import spellings (CSV)…</strong> and <strong>Export spellings (CSV)</strong> move the whole table in and out. An import only changes the screen until you Save.</li>
          <li>Each spelling is checked as you type. Two glyphs can't share a spelling (except a glyph and its own vertical form): a <span class="pill danger">× clash</span> holds Save until it's fixed. A spelling that types something else gets a warning, but Save still works.</li>
          <li>The <strong>Typing</strong> filters in the sidebar (Needs attention, Clashes, No spellings yet, Vertical pairs, Unsaved) narrow the table to what needs work.</li>
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="editor">
        <h2>The glyph editor</h2>
        <p>Opening a glyph, or <a href="/glyphs/new">+ New glyph</a>, brings up the editor: a drawing canvas with the glyph's box, a tool rail on the left and panels around it.</p>
        <figure><a href="/help/editor.jpg" target="_blank"><img src="/help/editor.jpg" alt="The glyph editor with 勾 on the canvas, tools on the left, Selection, Compare and Glyph panels on the right and the Tester below" width="1280" height="800" loading="lazy" /></a><figcaption>勾 in the editor: tools on the left, panels on the right, and the Tester showing it in words below.</figcaption></figure>
        <h3>Drawing</h3>
        <ul>
          <li>Tools: Select <kbd>V</kbd>, Pen <kbd>P</kbd>, Pencil <kbd>⇧P</kbd>, Rectangle <kbd>R</kbd>, Ellipse <kbd>O</kbd>, Hand <kbd>H</kbd> (or hold Space), Zoom <kbd>Z</kbd>. <strong>?</strong> on the rail lists every shortcut.</li>
          <li>Combine two selected shapes with ∪ − ∩ ⊕ (hover to preview). <strong>Simplify…</strong> removes points; <strong>Thicken…</strong> makes strokes heavier or lighter; <strong>Clean up</strong> fixes overlaps.</li>
          <li>Lines drawn with the Pen or Pencil are strokes until <strong>Outline line(s)</strong> turns them into filled shapes. Save does this for you.</li>
          <li><strong>SVG file…</strong> imports a drawing (fit to the box, or keep its size; replace or add). You can also drop a file on the canvas or paste SVG text.</li>
          <li><strong>Image to trace…</strong> turns a scan or photo into an outline: adjust Threshold, Corners and Simplify in the Trace panel, then <strong>Use this outline</strong>. The image itself stays in your browser.</li>
        </ul>
        <h3>Checking</h3>
        <ul>
          <li><strong>Compare</strong> shows a reference dot (<kbd>D</kbd>) at the stroke weight to aim for, another glyph to match (<kbd>G</kbd>), or the last saved outline (<kbd>L</kbd>).</li>
          <li><strong>Checks</strong> flags an empty glyph, parts outside the box, open lines and specks, with a button to fix each.</li>
          <li><strong>Tester</strong> and <strong>Try it</strong> show the glyph in real words as you draw.</li>
        </ul>
        <h3>Saving a glyph</h3>
        <p>The editor has its own <strong>Save glyph</strong> (<kbd>⌘S</kbd>) and its own undo. Edits that aren't saved yet are kept in the browser, and leaving asks whether to save or discard them. {#if hosted.isHosted}Saving puts the glyph into your draft.{:else}Saving writes <code>builder/inputs/svg/&lt;name&gt;.svg</code> at once; if the file changed on disk meanwhile, you're asked which version to keep.{/if} A new glyph joins its area on its first save. The font picks up the new drawing at the next <strong>Build font</strong>.</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="layouts">
        <h2>Layouts</h2>
        <p><a href="/layouts">Layouts</a> is where the parts are arranged. A <strong>word type</strong> is one kind of character (a standard note, a chord, a vertical word…): which parts it has, in which order, and how they're spaced. The canvas shows one example word; the panels around it edit it.</p>
        <figure><a href="/help/layouts.jpg" target="_blank"><img src="/help/layouts.jpg" alt="The Layouts screen: word types and structure on the left, the standard word on the canvas with part boxes, area properties and tester below" width="1280" height="800" loading="lazy" /></a><figcaption>The standard word type: its parts on the left, an example word with its part boxes in the middle.</figcaption></figure>
        <h3>The canvas</h3>
        <ul>
          <li>Click a part to select it (Tab cycles through parts). Drag it, or nudge it with the arrow keys, to change its gap.</li>
          <li>Arrows show spacing rules: click one to edit it. Drag a part's ○ handle onto another part's edge to attach it there.</li>
          <li><strong>boxes</strong> and <strong>glyphs</strong> switch the outlines; <kbd>b</kbd> toggles boxes, <kbd>⇧1</kbd> fits the word.</li>
        </ul>
        <h3>The panels</h3>
        <p>Panels can be docked left, right or below, folded and resized; ⋯ → <strong>Reset panel layouts</strong> puts them back.</p>
        <dl class="panels">
          <dt>Word types</dt><dd>Pick the word type to edit. Each shows how many positioning rules it makes.</dd>
          <dt>Structure</dt><dd>The parts of the word type. Tick a part to include it in the example word, and pick which glyph it shows.</dd>
          <dt>Spacing</dt><dd>How the selected part sits against the others, vertically and horizontally. A rule reads as a sentence ("its top edge sits at the bottom of 七 + gap"), with rows that change the gap when certain glyphs are present, and an <em>otherwise</em> row for the rest. <strong>+ new rule</strong> picks the glyphs it applies to; the canvas previews every combination.</dd>
          <dt>Centering</dt><dd>Which parts the word is centred on, and where.</dd>
          <dt>Area Properties</dt><dd>The shared areas: box size (type to preview, Enter applies, Esc cancels), which word types use the area, and its glyphs (<strong>Manage</strong> to add or remove). <strong>+ New area</strong> makes one; <strong>Delete area</strong> works only on an empty area nothing uses.</dd>
          <dt>Font budget</dt><dd>How many positioning rules each word type makes and how big they are. The <span class="pill saved">✓ rules · KB</span> pill in the header opens it.</dd>
          <dt>Tester</dt><dd>A strip of words drawn by the live preview. Click a word to put it on the canvas; <strong>Build & test ↗</strong> opens the same words there.</dd>
        </dl>
        <p>Structural edits (adding, removing or reordering parts, new word types, recognition rules) are behind the <strong>Advanced</strong> checkbox in the header, so they aren't changed by accident. It's off again after a reload.</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="build">
        <h2>Build & test</h2>
        <p><a href="/test">Build & test</a> makes the real font file and shows text in it.</p>
        <ul>
          <li><strong>Build font</strong> builds from the saved files. {#if hosted.isHosted}Online, it builds from your draft as it is now, unsaved edits included.{:else}With unsaved changes the button reads <strong>Save & build</strong> and saves first.{/if} It takes about half a minute; the build log opens below.</li>
          <li>Each build is a separate file. <strong>Download JianZiPu.ttf</strong> saves it; earlier builds from this session stay in the list.</li>
          <li><strong>Font</strong> is the font the page shows: the newest build, an earlier one, or any <strong>.ttf file</strong> you open (the released font, say). It's loaded into the page under its own name, so a JianZiPu installed on your computer never stands in for it.</li>
        </ul>
        <figure><a href="/help/build-design.jpg" target="_blank"><img src="/help/build-design.jpg" alt="Build and test, Test the design view: each word drawn live above the same word in the built font" width="1280" height="800" loading="lazy" /></a><figcaption><strong>Test the design</strong> with Compare both: the live drawing on top, the built font below. Under each word, what was typed and the glyphs it became.</figcaption></figure>
        <h3>Two views</h3>
        <dl class="panels">
          <dt>Test the design</dt><dd>One cell per word, to check your design without building. <strong>Live preview</strong> draws from the design as it is now, unsaved changes included, with optional boxes; <strong>Font</strong> shows the built font; <strong>Compare both</strong> puts them one above the other. Click a live word to open it in Layouts. <strong>+ Save as set</strong> keeps the current words as a sample set.</dd>
          <dt>Test the font file</dt><dd>Running text in the font file, as a reader sees it. Switch <strong>liga</strong> (substitution) and <strong>kern</strong> (positioning) off to see the raw parts, try <strong>vertical columns</strong>, or <strong>compare with a second font</strong> side by side.</dd>
        </dl>
        <figure><a href="/help/build-font.jpg" target="_blank"><img src="/help/build-font.jpg" alt="Build and test, Test the font file view: the same words as running text in the built font" width="1280" height="800" loading="lazy" /></a><figcaption><strong>Test the font file</strong>: the same words as running text in the built font.</figcaption></figure>
        <p>A character the font doesn't have is drawn by another font <span class="miss">in red</span>, so it can't pass for part of the font. In Test the design, <span class="badge-warn">⚠</span> under a word means some of its parts matched no word type.</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="saving">
        <h2>Saving and undo</h2>
        <ul>
          <li>Edits to the design and the spellings stay in the browser until you <strong>Save</strong> (<kbd>⌘S</kbd>). The header shows <span class="pill draft">● unsaved</span> with a count; click it to see the list or <strong>Discard all</strong>.</li>
          <li>↶ ↷ in the header (<kbd>⌘Z</kbd>, <kbd>⇧⌘Z</kbd>) undo and redo whole steps, such as one rule change or one paste. Hover them to see which step.</li>
          <li>Save waits while a spelling clashes, and says which ones; fix them in <a href="/glyphs?view=typing&f=attention">Glyphs → Typing</a>.</li>
          <li>Unsaved work survives a reload: the Builder offers to restore it.</li>
          {#if hosted.isHosted}
            <li>Online, your draft also saves itself 30 seconds after an edit, when you change screen, and when you leave the tab.</li>
          {:else}
            <li>Save writes <code>design.json</code> and <code>components.csv</code> in <code>builder/inputs/</code> (glyph files are saved from the editor). If a file changed on disk since you opened it, you choose: reload it, overwrite it, or export yours first. Then commit the files with git.</li>
            <li>⋯ → <strong>Export…</strong> / <strong>Import…</strong> move the design (word types, areas, sample sets) as one JSON file; an import becomes unsaved changes you can look over first.</li>
          {/if}
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="draft">
        <h2>Your draft (online)</h2>
        <p>Invited testers use the Builder online. You sign in with a link sent to your email (no password). Everything you change goes into your own <strong>draft</strong>: only you see it, and nothing you do changes the real font or anyone else's work.</p>
        <ul>
          <li>The <span class="pill draft">◌ Your draft</span> pill in the header shows what your draft is based on and how much you've changed. <strong>See my changes</strong> lists them item by item.</li>
          <li>To share your work, ⋯ → <strong>Export my draft (.zip)…</strong> and send the file. <strong>Import a draft (.zip)…</strong> opens one again.</li>
          <li>When the font is updated, a banner offers <strong>Update my draft…</strong>: the font's changes come in, and where you both changed the same thing you pick <strong>Keep mine</strong> or <strong>Take the font's</strong>.</li>
          <li><strong>Feedback</strong> in the header goes to the font's maintainer. Confusing, broken or lovely, it's all useful.</li>
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="review">
        <h2>Reviewing a draft</h2>
        <p>On your own computer, <a href="/review">Review</a> brings a tester's draft into the font. Open a draft from the list (once signed in) or a <strong>.zip</strong> someone sent.</p>
        <ul>
          <li>Each change is shown before and after: glyphs drawn over each other, spellings side by side, design changes with sample words and the JSON. <strong>Keep</strong> or <strong>Skip</strong> each one, or <strong>Keep all</strong>.</li>
          <li>A <span class="pill danger">× Conflict</span> means you changed the same thing since the draft started: pick whose version to use.</li>
          <li><strong>Apply</strong> turns the kept changes into one undoable step of unsaved changes. Look them over in Layouts and Build & test, Save, then commit with the message the toast offers to copy.</li>
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="keys">
        <h2>Keyboard shortcuts</h2>
        <table class="ref keys">
          <tbody>
            <tr><th colspan="2">Everywhere</th></tr>
            <tr><td><kbd>⌘S</kbd></td><td>Save</td></tr>
            <tr><td><kbd>⌘Z</kbd> / <kbd>⇧⌘Z</kbd></td><td>Undo / redo (not while typing in a field)</td></tr>
            <tr><th colspan="2">Glyphs → Typing</th></tr>
            <tr><td><kbd>Enter</kbd> / <kbd>⇧Enter</kbd></td><td>Keep the cell, move down / up</td></tr>
            <tr><td><kbd>Tab</kbd></td><td>Next cell; accepts a suggestion in an empty Latin Entry</td></tr>
            <tr><td><kbd>Esc</kbd></td><td>Put the old value back</td></tr>
            <tr><th colspan="2">Layouts</th></tr>
            <tr><td><kbd>Tab</kbd> / <kbd>⇧Tab</kbd></td><td>Next / previous part</td></tr>
            <tr><td>arrows (<kbd>⇧</kbd> × 10)</td><td>Nudge the selected part's gap</td></tr>
            <tr><td><kbd>b</kbd></td><td>Show or hide boxes</td></tr>
            <tr><td><kbd>⇧1</kbd>, <kbd>+</kbd>, <kbd>−</kbd></td><td>Fit, zoom in, zoom out</td></tr>
            <tr><td><kbd>⌫</kbd></td><td>Delete the selected rule arrow</td></tr>
            <tr><th colspan="2">Glyph editor</th></tr>
            <tr><td><kbd>⌘S</kbd>, <kbd>⌘Z</kbd></td><td>Save the glyph, undo in the glyph</td></tr>
            <tr><td><kbd>V</kbd> <kbd>P</kbd> <kbd>⇧P</kbd> <kbd>R</kbd> <kbd>O</kbd> <kbd>H</kbd> <kbd>Z</kbd></td><td>Select, Pen, Pencil, Rectangle, Ellipse, Hand, Zoom</td></tr>
            <tr><td><kbd>D</kbd> <kbd>G</kbd> <kbd>L</kbd></td><td>Reference dot, compare glyph, last saved</td></tr>
            <tr><td><kbd>⇧1</kbd> / <kbd>⇧0</kbd> / <kbd>⇧2</kbd></td><td>Fit / 100% / fit the selection</td></tr>
            <tr><td><kbd>⇧G</kbd></td><td>Grid</td></tr>
            <tr><td><kbd>⌥⌘O</kbd></td><td>Outline lines</td></tr>
          </tbody>
        </table>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="trouble">
        <h2>When something looks wrong</h2>
        <dl class="panels">
          <dt>A character shows in red</dt><dd>The font doesn't have it yet: a new glyph or spelling isn't in a build. <strong>Build font</strong> again. In Try it, red means "not in the font until the next build".</dd>
          <dt>The live preview and the font differ</dt><dd>The live preview includes unsaved changes; the font is only what was saved when it was built. Save and build.</dd>
          <dt>⚠ under a word</dt><dd>Some parts of the word matched no word type, so the font won't place them. Check the spelling, or the word type's parts in Layouts.</dd>
          <dt>Save is waiting</dt><dd>A spelling clashes with another glyph's or isn't valid. <strong>Show them</strong> lists the cells to fix.</dd>
          <dt>A new glyph never appears in words</dt><dd>It needs an area (<strong>Unassigned</strong> in Glyphs) and at least one spelling.</dd>
          <dt>The build failed</dt><dd>The first error is shown above the build log; the log has the rest. A spelling clash or an over-large set of rules (see Font budget) are the usual causes.</dd>
        </dl>
      </section>
    </article>
  </div>
</div>

<style>
  .page { height: 100%; overflow: auto; }
  .layout { display: grid; grid-template-columns: 200px minmax(0, 720px); gap: var(--space-8); padding: var(--space-7) var(--space-6) var(--space-9); justify-content: center; }
  .toc { position: sticky; top: var(--space-7); align-self: start; display: flex; flex-direction: column; gap: var(--space-1); }
  .toc-title { font: 600 var(--t-panel) var(--font-display); margin: 0 0 var(--space-3); }
  .toc a { display: block; padding: var(--space-2) var(--space-4); border-left: 2px solid transparent; color: var(--ink-muted); text-decoration: none; }
  .toc a:hover { color: var(--ink); background: var(--bg-hover); }
  .toc a[aria-current="true"] { color: var(--ink); border-left-color: var(--sel-border); background: var(--sel-bg); }
  article { font-size: var(--t-body); line-height: 22px; }
  h1 { margin: 0 0 var(--space-4); }
  .lede { font-size: var(--t-panel); line-height: 24px; color: var(--ink-muted); margin: 0 0 var(--space-7); }
  section { padding-top: var(--space-6); margin-bottom: var(--space-7); border-top: 1px solid var(--border); scroll-margin-top: var(--space-5); }
  h2 { margin: 0 0 var(--space-4); }
  h3 { margin: var(--space-6) 0 var(--space-3); }
  p { margin: 0 0 var(--space-4); }
  ul { margin: 0 0 var(--space-4); padding-left: var(--space-6); }
  li { margin-bottom: var(--space-2); }
  code { font: var(--t-label) var(--font-mono); background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0 4px; white-space: nowrap; }
  dl { margin: 0 0 var(--space-4); display: grid; grid-template-columns: max-content 1fr; gap: var(--space-3) var(--space-6); }
  dt { font-weight: 600; }
  dd { margin: 0; }
  table.ref { width: 100%; border-collapse: collapse; margin: 0 0 var(--space-5); }
  table.ref th, table.ref td { text-align: left; vertical-align: top; padding: var(--space-3) var(--space-4); border-bottom: 1px solid var(--border); }
  table.ref thead th { font-size: var(--t-small); color: var(--ink-muted); }
  table.ref tbody th { width: 150px; font-weight: 600; }
  table.ref td:first-child { white-space: nowrap; }
  table.keys th[colspan] { padding-top: var(--space-5); font: 600 var(--t-panel) var(--font-display); }
  figure { margin: var(--space-5) 0 var(--space-6); }
  figure img { display: block; width: 100%; height: auto; border: 1px solid var(--border); border-radius: var(--radius-md); }
  figcaption { margin-top: var(--space-3); font-size: var(--t-label); color: var(--ink-muted); }
  .banner { margin-top: var(--space-5); flex-wrap: nowrap; }
  .banner > div { flex: 1; min-width: 0; }
  .miss { color: var(--status-danger); }
  @media (max-width: 760px) {
    .layout { grid-template-columns: minmax(0, 1fr); gap: var(--space-5); padding: var(--space-5) var(--space-5) var(--space-8); }
    .toc { position: static; flex-direction: row; flex-wrap: wrap; }
    .toc-title { width: 100%; }
    .toc a { border-left: 0; border: 1px solid var(--border); border-radius: var(--radius-md); }
    dl { grid-template-columns: 1fr; gap: var(--space-1); }
    dd { margin-bottom: var(--space-3); }
    table.ref td:first-child { white-space: normal; }
  }
</style>
