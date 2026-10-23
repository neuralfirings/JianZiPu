<script lang="ts">
  // How to use the Builder: one page, a contents list on the left (scroll-spied), a section per
  // screen. Sections and their order come from lib/help.ts; help.test.ts checks the links.
  import { onMount } from 'svelte';
  import * as I from '$lib/icons';
  import { hosted } from '$lib/hosted.svelte';
  import { HELP_SECTIONS, LAYOUTS_HELP, EDITOR_HELP, helpAnchor, type PanelHelp } from '$lib/help';

  // everyone: the copy for the public help (scripts/help-export.mjs), with both the online and the
  // own-computer wording; in the app only the one that applies shows.
  let { everyone = false }: { everyone?: boolean } = $props();
  let online = $derived(everyone || hosted.isHosted);
  let local = $derived(everyone || !hosted.isHosted);
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

{#snippet panelList(h: PanelHelp<string>)}
  <dl class="panels">
    {#each Object.entries(h.topics) as [id, t] (id)}
      <dt id={helpAnchor(h.section, id)}>{t.title}</dt><dd>{@html t.html}</dd>
    {/each}
  </dl>
{/snippet}

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
        <div class="banner info"><span class="ic"><I.Info /></span><div>
          {#if everyone}
            The Builder runs in two ways. <strong>Online</strong>, for invited testers, everything you do goes into <a href="#draft">your own draft</a>; the real font doesn't change until your draft is reviewed. <strong>On your own computer</strong> (the <span class="chip dashed">Local files</span> chip in the header), Save writes the files in <code>builder/inputs/</code>, which you then commit.
          {:else if hosted.isHosted}
            You're using the online Builder. Everything you do goes into <a href="#draft">your own draft</a>; the real font doesn't change until your draft is reviewed.
          {:else}
            You're using the Builder on your own computer (the <span class="chip dashed">Local files</span> chip in the header). Save writes the files in <code>builder/inputs/</code>, which you then commit.
          {/if}
        </div></div>
        <h3 id="phone">On a phone</h3>
        <p>The Builder is made for a computer, but it opens on a phone too. Controls are larger there, the screens are tabs along the bottom, and tapping a button that shows only an icon also shows its name for a moment. Drawing glyphs, Review (apart from your own changes), making a release and importing or exporting the design need a mouse and a big screen, so on a phone they say so first: <strong>Copy link</strong> copies the page's address to open on a computer, and <strong>Open anyway</strong> opens the tool on the phone until you reload the page.</p>
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
        <p>On a phone, two menus above the tiles pick the area and a spelling filter, and tapping a tile opens the glyph's card over the tiles: its areas, its spellings to edit, and Try it. <strong>All glyphs</strong> goes back. Drawing needs a computer, and so do <strong>+ New glyph</strong>, the reference weight and the CSV import and export.</p>
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
          <li><I.More class="inl" aria-label="More" /> → <strong>Import spellings (CSV)…</strong> and <strong>Export spellings (CSV)</strong> move the whole table in and out. An import only changes the screen until you Save.</li>
          <li>Each spelling is checked as you type. Two glyphs can't share a spelling (except a glyph and its own vertical form): a <span class="pill danger"><I.Problem size={14} />clash</span> holds Save until it's fixed. A spelling that types something else gets a warning, but Save still works.</li>
          <li>The <strong>Typing</strong> filters in the sidebar (Needs attention, Clashes, No spellings yet, Vertical pairs, Unsaved) narrow the table to what needs work.</li>
        </ul>
        <p>On a phone, Typing is a list of cards, one per glyph: its spellings and anything wrong with them. Tap a card to edit its spellings on the glyph's card. Pasting a range and the CSV import and export need the table, on a computer.</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="editor">
        <h2>The glyph editor</h2>
        <p>Opening a glyph, or <a href="/glyphs/new">+ New glyph</a>, brings up the editor: a drawing canvas with the glyph's box, a tool rail on the left and panels around it.</p>
        <figure><a href="/help/editor.jpg" target="_blank"><img src="/help/editor.jpg" alt="The glyph editor with 勾 on the canvas, tools on the left, Selection, Compare and Glyph panels on the right and the Tester below" width="1280" height="800" loading="lazy" /></a><figcaption>勾 in the editor: tools on the left, panels on the right, and the Tester showing it in words below.</figcaption></figure>
        <h3>Drawing</h3>
        <ul>
          <li>Tools: Select <kbd>V</kbd>, Pen <kbd>P</kbd>, Pencil <kbd>⇧P</kbd>, Rectangle <kbd>R</kbd>, Ellipse <kbd>O</kbd>, Hand <kbd>H</kbd> (or hold Space), Zoom <kbd>Z</kbd>. <I.Shortcuts class="inl" aria-label="Keyboard shortcuts" /> on the rail lists every shortcut.</li>
          <li>To edit points, use Select (<kbd>V</kbd>): click a shape to show its points, then click a point and drag it (arrow keys nudge it, <kbd>⇧</kbd> × 10). A selected point shows its curve handles; drag a handle's round end to bend the curve. On a smooth point the opposite handle follows; <kbd>⌥</kbd>-drag moves one handle alone. Double-click a point to switch it between corner and smooth. <kbd>⇧</kbd>-click adds points to the selection, and <kbd>⇧</kbd>-drag a box around them picks several. With the Pen, click the outline to add a point, or click a point to remove it.</li>
          <li>Combine two selected shapes with Union <I.Union class="inl" />, Subtract <I.Subtract class="inl" />, Intersect <I.Intersect class="inl" /> or Exclude <I.Exclude class="inl" /> (hover to preview). <strong>Simplify…</strong> removes points; <strong>Thicken…</strong> makes strokes heavier or lighter; <strong>Clean up</strong> fixes overlaps.</li>
          <li>Lines drawn with the Pen or Pencil are strokes until <strong>Outline line(s)</strong> turns them into filled shapes. Save does this for you.</li>
          <li><strong>SVG file…</strong> imports a drawing (fit to the box, or keep its size; replace or add). You can also drop a file on the canvas or paste SVG text.</li>
          <li><strong>Image to trace…</strong> turns a scan or photo into an outline: adjust Threshold, Corners and Simplify in the Trace panel, then <strong>Use this outline</strong>. The image itself stays in your browser.</li>
        </ul>
        <h3>The panels</h3>
        <p>Each panel's <I.Help class="inl" aria-label="?" /> shows the same text as below.</p>
        {@render panelList(EDITOR_HELP)}
        <h3>Saving a glyph</h3>
        <p>The editor has its own <strong>Save glyph</strong> (<kbd>⌘S</kbd>) and its own undo. Edits that aren't saved yet are kept in the browser, and leaving asks whether to save or discard them. {#if online}Online, saving puts the glyph into your draft.{/if} {#if local}On your own computer, saving writes <code>builder/inputs/svg/&lt;name&gt;.svg</code> at once; if the file changed on disk meanwhile, you're asked which version to keep.{/if} A new glyph joins its area on its first save. The font picks up the new drawing at the next <strong>Build font</strong>.</p>
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
          <li>On a phone: a swipe scrolls, even when it starts on the canvas; a tap selects a part or an arrow; press and hold a part (or a ○ handle): a ring fills around your finger, then the part lifts with a thicker outline and a shadow. Drag it; the rule's arrow and the line under the canvas show the gap, and letting go is one undo step.</li>
        </ul>
        <h3>The panels</h3>
        <p>Panels can be docked left, right or below, folded and resized; <I.More class="inl" aria-label="More" /> → <strong>Reset panel layouts</strong> puts them back. Each panel's <I.Help class="inl" aria-label="?" /> shows the same text as below.</p>
        {@render panelList(LAYOUTS_HELP)}
        <p>Structural edits (adding, removing or reordering parts, new word types, recognition rules) are behind the <strong>Advanced</strong> checkbox in the header, so they aren't changed by accident. It's off again after a reload.</p>
        <p>On a phone, the canvas stays at the top and the panels are sections under it, in a fixed order: tapping a part opens its <strong>Spacing</strong> just below the canvas, and pressing and holding it drags it. In Spacing, drag a rule row by its grip to change the order. The <strong>Advanced</strong> edits need a computer.</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="build">
        <h2>Build & test</h2>
        <p><a href="/test">Build & test</a> makes the real font file and shows text in it.</p>
        <ul>
          <li><strong>Build font</strong> builds from the saved files. {#if online}Online, it builds from your draft as it is now, unsaved edits included.{/if} {#if local}On your own computer, with unsaved changes the button reads <strong>Save & build</strong> and saves first.{/if} It takes about half a minute; the build log opens below.</li>
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
        <p>On a phone, the words come first and the box you type in sits under them, above the keyboard. The line at the top (<strong>No build yet</strong>, or when the last build was made) opens the build, font and view settings and the build log.</p>
        <p>A character the font doesn't have is drawn by another font <span class="miss">in red</span>, so it can't pass for part of the font. In Test the design, <I.Warn class="inl badge-warn" aria-label="warning" /> under a word means some of its parts matched no word type.</p>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="saving">
        <h2>Saving and undo</h2>
        <ul>
          <li>Edits to the design and the spellings stay in the browser until you <strong>Save</strong> (<kbd>⌘S</kbd>). The header shows <span class="pill draft"><I.Unsaved size={14} />unsaved</span> with a count; click it to see the list or <strong>Discard all</strong>.</li>
          <li><I.Undo class="inl" aria-label="Undo" /> <I.Redo class="inl" aria-label="Redo" /> in the header (<kbd>⌘Z</kbd>, <kbd>⇧⌘Z</kbd>) undo and redo whole steps, such as one rule change or one paste. Hover them to see which step.</li>
          <li>Save waits while a spelling clashes, and says which ones; fix them in <a href="/glyphs?view=typing&f=attention">Glyphs → Typing</a>.</li>
          <li>Unsaved work survives a reload: the Builder offers to restore it.</li>
          <li>On a phone, the header is one row (the screen's name, its status, <I.Undo class="inl" aria-label="Undo" /> <I.Redo class="inl" aria-label="Redo" /> on Glyphs and Layouts, and <I.More class="inl" aria-label="More" />), the screens are tabs at the bottom, and <strong>Save</strong> sits in a bar above the tabs while something is unsaved.</li>
          {#if online}
            <li>Online, your draft also saves itself 30 seconds after an edit, when you change screen, and when you leave the tab.</li>
          {/if}
          {#if local}
            <li>On your own computer, Save writes <code>design.json</code> and <code>components.csv</code> in <code>builder/inputs/</code> (glyph files are saved from the editor). If a file changed on disk since you opened it, you choose: reload it, overwrite it, or export yours first. Then commit the files with git.</li>
            <li>On your own computer, <I.More class="inl" aria-label="More" /> → <strong>Export…</strong> / <strong>Import…</strong> move the design (word types, areas, sample sets) as one JSON file; an import becomes unsaved changes you can look over first.</li>
          {/if}
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="draft">
        <h2>Your draft (online)</h2>
        <p>Invited testers use the Builder online. You sign in with a link sent to your email (no password). Everything you change goes into your own <strong>draft</strong>: only you see it, and nothing you do changes the real font or anyone else's work.</p>
        <ul>
          <li>Your draft is compared with a <strong>reference font</strong>, a release such as 3.200: <strong>Your changes</strong> are what your draft does differently from it. The <span class="pill draft"><I.Draft size={14} />Your draft</span> pill in the header shows your reference font and how much you've changed. <strong>See my changes</strong> lists the changes item by item.</li>
          <li>On that list, <strong>Undo this change</strong> puts one item back the way your reference font has it: a glyph, a glyph's spellings, an area or a word type. For a word type, <strong>Show the spacing rules</strong> lists each rule you changed, and each has its own Undo. Every undo is one step you can take back with <I.Undo class="inl" aria-label="Undo" />. To throw everything away at once, use <I.More class="inl" aria-label="More" /> → <strong>Discard my draft…</strong>.</li>
          <li>To share your work, <I.More class="inl" aria-label="More" /> → <strong>Export my draft (.zip)…</strong> and send the file. <strong>Import a draft (.zip)…</strong> opens one again.</li>
          <li>When a new release is out, a banner offers <strong>Set reference font to 3.200 (latest)…</strong> (with the new number). Your changes stay yours and are compared with the new release from then on: its changes come in, the ones it already has leave Your changes, and where you both changed the same thing you pick <strong>Keep mine</strong> or <strong>Take the font's</strong>.</li>
          <li><strong>Feedback</strong> in the header goes to the font's maintainer. Confusing, broken or lovely, it's all useful.</li>
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="requests">
        <h2>Change Requests</h2>
        <p>When some of your changes are ready for the real font, send them as a <strong>Change Request</strong> (a CR). The font's maintainer looks at each change, keeps or skips it, and replies.</p>
        <ul>
          <li>On <a href="/review?mine">Your changes</a>, choose <strong>Send Change Request…</strong>. Every change is ticked to start with; untick any you want to keep working on. Give it a title, say what you changed and why, and how you'd like to be credited in the release notes: your name the way it should read, such as <em>Mei Chen</em> or <em>Mei Chen (Taipei Qin Society)</em>, or nothing for no credit.</li>
          <li><strong>Save as draft</strong> keeps the request with your draft, ticks and notes included, so you can finish it later, on this computer or another. It shows on <a href="/requests">Your Change Requests</a> as <strong>Draft · not sent</strong>, with <strong>Continue…</strong> to pick it up again.</li>
          <li>Before it goes, the Builder saves your draft, checks the chosen spellings don't clash, and builds a font with just those changes.</li>
          <li>Once sent, those changes are <strong>locked</strong> in your draft <I.Lock class="inl" aria-label="locked" />: you can look at them and try words, but not edit or undo them. Everything else stays yours to change.</li>
          <li><a href="/requests">Your Change Requests</a> shows each one's status, the maintainer's reply, and what you sent. You get an email when the status changes.</li>
          <li>Statuses: <strong>Sent</strong>, <strong>In review</strong>, <strong>In a release candidate</strong> (a test version of the next font), <strong>Released</strong>, <strong>Declined</strong>, <strong>Withdrawn</strong>. A request can be partly kept: "3 of 5 changes in v3.200".</li>
          <li><strong>Withdraw…</strong> takes a request back, until the maintainer keeps one of its changes. Withdrawn and declined requests unlock their changes in your draft.</li>
          <li>When your changes are released, they fold away on Your changes under <strong>In the font now</strong>, and the request moves to <strong>Released and closed</strong> on Your Change Requests. <strong>Set reference font to 3.200 (latest)…</strong> compares your draft with the new release, and they drop out of Your changes. Released changes aren't locked: they're the font's now, and you can change them again like any other part.</li>
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="review">
        <h2>Reviewing Change Requests</h2>
        <p>On your own computer, signed in as an admin, <a href="/review">Review</a> lists the Change Requests testers sent, newest first. An email with a link to each one arrives when it's sent.</p>
        <ul>
          <li>Open a request to see its title, notes and how its author wants to be credited, then each change before and after: glyphs drawn over each other, spellings side by side, design changes with sample words and the JSON. <strong>Keep</strong> or <strong>Skip</strong> each one, or <strong>Keep all</strong>.</li>
          <li>Write a reply if you like, then <strong>Save decisions</strong>. Nothing goes into the font yet: the request becomes <strong>In review</strong> (or <strong>Declined</strong> if you skipped everything) and its author gets an email. Kept changes go into the next <a href="#release">release candidate</a>.</li>
          <li><strong>Current drafts</strong> below the requests shows what each tester is working on now. Opening a draft or a <strong>.zip</strong> and choosing <strong>Apply</strong> brings changes in directly, as one undoable step of unsaved changes. A <span class="pill danger"><I.Problem size={14} />Conflict</span> means you changed the same thing since the draft started: pick whose version to use.</li>
        </ul>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="release">
        <h2>Making a release</h2>
        <p>On your own computer, <a href="/release">Release</a> (from Review, or <I.More class="inl" aria-label="More" /> → <strong>Make a release…</strong>) turns kept changes into a new version of the font. It runs git for you, with your own GitHub sign-in.</p>
        <ol>
          <li><strong>Start a release candidate</strong> with the next version number, such as 3.200. The Builder makes the branch <code>release/3.200</code> from main. A release branch holds only font files; Builder code goes to main on its own branch.</li>
          <li><strong>Add kept changes</strong> brings in every kept change from the reviewed requests, oldest first, as unsaved changes. Where two requests change the same thing, you pick which one wins.</li>
          <li>Check the result in Layouts and Build & test, adjust, then Save.</li>
          <li><strong>Build candidate</strong> runs the tests, builds the font, writes the version and the changelog entry, and tags <code>v3.200-rc.1</code>. GitHub publishes it as a pre-release, and the requests' authors get an email. Open the pull request from there. If testers find a problem, fix it and build again (<code>rc.2</code>).</li>
          <li>Merge the pull request on GitHub with <strong>Create a merge commit</strong> (not squash or rebase, which would leave the candidate's tag off main), then <strong>Publish</strong>: main is tagged <code>v3.200</code>, GitHub publishes the release with the font attached, jianzipufont.com serves the new font, and the requests become <strong>Released</strong>.</li>
        </ol>
        <p>Version numbers have a three-digit minor part (3.100, 3.200, 3.201), because the font stores the version as a number. Raise the first number only when existing documents would look different or break.</p>
        <p>The full process, with testing a candidate and what to do when a step fails, is in <code>docs/maintainers/releasing.md</code> in the repository.</p>
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
          <dt><I.Warn class="inl badge-warn" aria-label="warning" /> under a word</dt><dd>Some parts of the word matched no word type, so the font won't place them. Check the spelling, or the word type's parts in Layouts.</dd>
          <dt>Save is waiting</dt><dd>A spelling clashes with another glyph's or isn't valid. <strong>Show them</strong> lists the cells to fix.</dd>
          <dt>A new glyph never appears in words</dt><dd>It needs an area (<strong>Unassigned</strong> in Glyphs) and at least one spelling.</dd>
          <dt>The build failed</dt><dd>The first error is shown above the build log; the log has the rest. <a href="#messages-build">Messages and errors</a> lists the usual ones and their fixes.</dd>
        </dl>
      </section>

      <!-- ─────────────────────────────────────────────── -->
      <section id="messages">
        <h2>Messages and errors</h2>
        <p>What the Builder's messages say, word for word, and what to do about each. Words in <em>italics</em> stand for a name or number that changes.</p>

        <h3 id="messages-signin">Signing in</h3>
        <dl class="panels messages">
          <dt>“This email isn't on the pilot list”</dt><dd>That address wasn't invited: the online Builder is for a few invited testers. If you were invited at another address, use that one; otherwise press <strong>Ask for an invite</strong>.</dd>
          <dt>“This sign-in link has expired”</dt><dd>A link works once, for an hour, in the browser you asked for it from. Press <strong>Email me a new link</strong> and open the new one in the same browser.</dd>
          <dt>“We can't reach the sign-in service right now. Try again in a minute.”</dt><dd>The sign-in service isn't answering. Check your connection and send the link again in a minute. “The sign-in service isn't answering. Try again in a minute.” is the same thing, seen from the server.</dd>
          <dt>“For security purposes, you can only request this after <em>n</em> seconds.”</dt><dd>Links were asked for too quickly (the sign-in service's own words; “Email rate limit exceeded” is another). Wait, then send again.</dd>
          <dt>“You've been signed out. Your unsaved changes are kept in this browser.”</dt><dd>The sign-in ran out. Press <strong>Sign in again</strong> and open the emailed link; your changes are still there afterwards. “Sign in first.” means the same.</dd>
          <dt>“Sign-in is not set up on this server.”</dt><dd>The server has no sign-in settings. Only whoever runs it can fix this (<code>SUPABASE_URL</code> and <code>SUPABASE_ANON_KEY</code>).</dd>
        </dl>

        <h3 id="messages-draft">Your draft (online)</h3>
        <dl class="panels messages">
          <dt>“Your draft isn't saved. We can't reach the server.”</dt><dd>You're offline, or the server can't be reached (the header says <strong>Not saved · offline</strong>). Your changes are kept in this browser and save by themselves when the connection is back; <strong>Try again</strong> retries now. Don't clear the browser's data or close a private window meanwhile.</dd>
          <dt>“Your draft isn't saved. The server turned it down: …”</dt><dd>The connection works, but the draft storage said no; the reason follows. Your changes are kept in this browser. Press <strong>Try again</strong>; if it fails again, <strong>Export my draft</strong> to keep a copy and <strong>Send feedback</strong> with the reason.</dd>
          <dt>“The Builder is taking a break: we can't reach it right now. Your saved draft is safe.”</dt><dd>The Builder's server didn't answer while loading; the reason is in brackets at the end. Press <strong>Retry</strong> in a minute.</dd>
          <dt>“Your draft was saved by a newer version of the Builder than this page. Reload the page to get it.”</dt><dd>You (or another tab) used a newer Builder since this page loaded. <strong>Reload the page</strong>.</dd>
          <dt>“Your saved draft can't be opened: … It is still stored and nothing has been changed.”</dt><dd>The stored draft is damaged; the reason follows. Retrying won't help, and nothing is lost yet: <strong>Send feedback</strong> so it can be recovered.</dd>
          <dt>“Your draft was saved somewhere else”</dt><dd>Another tab or computer saved (or discarded) your draft after you opened it here. Pick the version that stays; <strong>Export this one first</strong> keeps a copy of this tab's.</dd>
          <dt>“Restored <em>n</em> changes from your last visit that hadn't reached your draft.”</dt><dd>Edits from last time that hadn't been saved yet. <strong>Save them</strong> or <strong>Discard them</strong>. On your own computer it reads “Restored unsaved changes from your last session.”</dd>
          <dt>“This Builder is read-only: your changes are kept in your own draft.”</dt><dd>The page is an old copy of the Builder. Reload it.</dd>
        </dl>

        <h3 id="messages-saving">Saving</h3>
        <dl class="panels messages">
          <dt>“Save is waiting”</dt><dd>Some spellings would stop the font from building; the dialog lists them. <strong>Show them</strong> opens <a href="/glyphs?view=typing&f=attention">Glyphs → Typing</a> at the cells to fix, or <strong>Undo last change</strong>. Your changes are kept meanwhile.</dd>
          <dt>“design.json changed on disk” / “components.csv changed on disk”</dt><dd>On your own computer: the file changed since you opened it (a git pull, another tab, an editor). <strong>Export mine first</strong>, then <strong>Reload from disk</strong>; or <strong>Overwrite</strong> if yours should win.</dd>
          <dt>“Not saved: …”</dt><dd>On your own computer: the server couldn't write a file; the reason follows (“Not saved: <em>name</em>.svg: …” for a glyph file). Your changes are still here. Fix the cause, then <strong>Try again</strong>. “Not saved: can't reach the web server” means the server stopped: start it again (below) and press <strong>Try again</strong>.</dd>
          <dt>“Can't reach the web server. Run: cd builder && python3 -m jzpbuild.webserver”</dt><dd>On your own computer: the Builder's server isn't running. Start it with that command and reload.</dd>
          <dt>“This Builder only answers on localhost.”</dt><dd>Open it at <code>http://127.0.0.1:5713</code>, or start the server with <code>--host</code> and the address you use.</dd>
          <dt>“unknown endpoint <em>path</em>”</dt><dd>The page and the server are different versions. Restart the server and reload.</dd>
        </dl>

        <h3 id="messages-typing">Spellings</h3>
        <dl class="panels messages">
          <dt>“<em>k</em>” types 2 glyphs (<em>a, b</em>). A spelling can make only one glyph.</dt><dd>A clash (under the cell: “already used by …”): two glyphs share a spelling, and Save waits until it's fixed. Give one of them another spelling. If one is the vertical form of the other, link them in <strong>Vertical form</strong> instead of repeating the spelling.</dd>
          <dt>“start with a letter: a leading digit is read as a string or position number”</dt><dd>A Latin Entry must start with a letter; digits at the start mean strings and hui.</dd>
          <dt>“use only letters a–z, A–Z and digits”</dt><dd>Latin entries take no spaces, accents or symbols; symbols go in Number/Symbol.</dd>
          <dt>“alone it marks a position; it can't type a glyph”</dt><dd>点, 點, 徽, 。 and ， on their own are kept for position numbers. In the Save is waiting list: “<em>x</em>” alone marks a position; it can't type a glyph.</dd>
          <dt>“Chinese characters only”</dt><dd>The 简体 and 繁體 columns take only Chinese characters.</dd>
          <dt>“<em>name</em> doesn't exist” / “Vertical form <em>name</em> doesn't exist.”</dt><dd>The Vertical form names a glyph with no drawing and no area. Make that glyph first, or fix the name.</dd>
          <dt>“joins <em>a</em> + <em>b</em>: typing <em>ab</em> gives this glyph instead of …”</dt><dd>A warning: the spelling is two other spellings run together, so typing it no longer gives those two. Save still works; change it unless that's what you want.</dd>
          <dt>Typing “<em>x</em>” gives <em>a + b</em>, not <em>glyph</em>.</dt><dd>Typed alone, the spelling makes something else, because a longer or earlier spelling catches it. Change this spelling or the one that catches it. Save still works.</dd>
          <dt>“not in the font yet. It arrives with the next Build.” / “isn't in the last build yet. Build to preview it.”</dt><dd>The spelling or glyph is newer than the last build. <strong>Build font</strong> in <a href="/test">Build & test</a>.</dd>
          <dt>“Build the font once to preview spellings.”</dt><dd>Try it needs one build first: <strong>Build font</strong>.</dd>
          <dt>“Can't read <em>file</em>: no glyph_name column”</dt><dd>A spellings CSV needs a header row that includes <code>glyph_name</code>. <strong>Export spellings (CSV)</strong> gives a file of the right shape to start from.</dd>
        </dl>

        <h3 id="messages-editor">The glyph editor</h3>
        <dl class="panels messages">
          <dt>“Saved inputs/svg/<em>name</em>.svg · Layouts and the Tester use it now; the font needs a Build.” / “Saved <em>name</em> to your draft · …”</dt><dd>The glyph is saved (to the file on your own computer, to your draft online). The font shows it after the next <strong>Build font</strong>.</dd>
          <dt>“<em>name</em> is in your draft, not saved yet: …”</dt><dd>Online: the outline is in your draft, but the draft itself didn't save; the reason follows (spelling problems to fix first, offline, or the server turned it down). It's kept in this browser, and the banner at the top says what to do.</dd>
          <dt>“<em>name</em>.svg already exists on disk.” / “<em>name</em> already exists.”</dt><dd>A new glyph's name is taken. Open that glyph instead, or pick another name.</dd>
          <dt>“<em>name</em>.svg changed on disk”</dt><dd>Someone, or another tab, wrote the file since you opened it. <strong>Compare</strong> shows the disk version as a dashed outline; then <strong>Load disk version</strong> or <strong>Overwrite with mine</strong>.</dd>
          <dt>“the glyph is empty” / “Empty: nothing to save yet”</dt><dd>There is nothing to save: draw or import something first.</dd>
          <dt>“Sticks out of the box”</dt><dd>Part of the drawing is outside the glyph's box, and Layouts places glyphs by their box. <strong>Fit to box</strong> or <strong>Center</strong> in the Selection panel, or change the area's box size in Layouts → Area Properties.</dd>
          <dt>“<em>n</em> open lines: outlined on save”</dt><dd>Pen or Pencil lines that aren't filled shapes yet. <strong>Outline now</strong>, or let Save do it.</dd>
          <dt>“<em>n</em> specks under 6 units”</dt><dd>Tiny bits, usually left by tracing. <strong>Remove them</strong>.</dd>
          <dt>“the SVG needs a viewBox (or width and height)”</dt><dd>The SVG file has no size. Export it again from the drawing program with a size or artboard.</dd>
          <dt>“Unable to convert to picosvg: BadElement: …”</dt><dd>The SVG holds something that isn't a shape, most often text. Convert text to outlines (paths) in the drawing program and import again.</dd>
          <dt>“syntax error: line <em>n</em>, column <em>n</em>”</dt><dd>The file isn't a valid SVG. Export it again from the drawing program.</dd>
          <dt>“glyph names use letters, digits, '_', '-' and '.', e.g. md_9 or lg_gou”</dt><dd>Rename the glyph with only those characters (the new-glyph dialog says “Letters, digits, _ - and . only.”).</dd>
          <dt>“Can't trace <em>file</em>: it isn't an image this browser can read. Try a PNG or JPEG.”</dt><dd>The file isn't an image, or is a kind the browser can't open (HEIC, TIFF, PDF…). Save it as PNG or JPEG and open that. “trace failed: …” means the image opened but couldn't be traced: try another image or a different Threshold.</dd>
        </dl>

        <h3 id="messages-layouts">Layouts and areas</h3>
        <dl class="panels messages">
          <dt>“Not placed: <em>part</em> has no vertical rule in this shape”</dt><dd>Nothing tells the part where to sit in this word, so it's drawn at 0 in a red dashed box. Select it and add a rule in Spacing. If it already has one, look at the rule's rows: when none matches the glyphs in this word and there's no “otherwise” row, the rule doesn't apply. Add an otherwise row, or one for these glyphs.</dd>
          <dt>“<em>n</em> skipped” / “Why <em>n</em> shapes are skipped”</dt><dd>Some combinations of parts get no positioning rule, so the font won't place those words. The list gives the reason for each; usually “no rule row for … and no "otherwise"”: add an otherwise row to that rule.</dd>
          <dt>“no unconditional last entry; words whose glyphs match no entry are not positioned”</dt><dd>In Font budget: a spacing rule has only rows for particular glyphs. Add an otherwise row.</dd>
          <dt>“Can't attach <em>A</em> to <em>B</em>: <em>B</em> is already placed relative to <em>A</em>”</dt><dd>That would go round in a circle. Attach the other way round, or remove the existing rule first.</dd>
          <dt>“Can't delete <em>area</em>”</dt><dd>Only an empty area that no word type uses can be deleted. The banner lists what's left: remove its glyphs, and take it out of those word types in Structure (Advanced).</dd>
          <dt>“The font can't be built from this design: …”</dt><dd>The design names something that isn't there any more, such as “standard/hui: unknown area 'x'”, usually after an edit, an import or a merge renamed or removed an area or a part. The banner's <strong>Undo</strong> button takes back the last change; or fix the named word type in Layouts with <strong>Advanced</strong> on.</dd>
          <dt>“Couldn't check the design: …”</dt><dd>The server didn't answer the check run after each edit. <strong>Check again</strong>; if the server stopped, start it again.</dd>
          <dt>“"<em>x</em>" is already a word type.” / “"<em>x</em>" can't be an id: use letters, digits and _ only, starting with a letter.”</dt><dd>When adding or duplicating a word type: the question asks again with the reason. Type another id, or Cancel.</dd>
        </dl>

        <h3 id="messages-build">Build & test</h3>
        <dl class="panels messages">
          <dt>“ValidationError: input validation failed”</dt><dd>The lines under it name the problem; usually a spelling claimed by two glyphs (“latin spelling 'k' is claimed by multiple glyphs”). Fix it in <a href="/glyphs?view=typing&f=attention">Glyphs → Typing</a> and build again.</dd>
          <dt>“FeatureLibError: The following glyph names are referenced but are missing from the glyph set”</dt><dd>A spelling names a glyph that has no drawing, or a vertical form is missing. Draw or import that glyph, or remove its spellings.</dd>
          <dt>“FileNotFoundError: … src_font/TW-Kai-98.ttf”</dt><dd>The base font is missing. On your own computer, copy <code>TW-Kai-98.ttf</code> into <code>builder/src_font/</code> (it isn't in git). Online, the server couldn't fetch it: send <strong>Feedback</strong>.</dd>
          <dt>“a build is already running” / “Another font is being built right now; try again in a minute.” / “You just built a font; try again in <em>n</em> seconds.”</dt><dd>Builds run one at a time, with a short pause between yours online. Wait, then <strong>Build font</strong> again.</dd>
          <dt>“no build <em>id</em> (builds live only while this server runs)” / “could not load build …”</dt><dd>Builds are kept only until the server restarts. Build again.</dd>
          <dt>“too many words (<em>n</em>); at most 2000 at a time”</dt><dd>Test fewer words at once.</dd>
          <dt>“Something went wrong on the server. Try again, or send feedback.”</dt><dd>An error the server didn't expect. Try again; if it happens again, send <strong>Feedback</strong> saying what you did just before.</dd>
        </dl>

        <h3 id="messages-review">Drafts, review and import</h3>
        <dl class="panels messages">
          <dt>“<em>file</em> isn't a Builder draft: it has no manifest.json.”</dt><dd>The .zip wasn't made by <strong>Export my draft</strong>. A design file goes in through <I.More class="inl" aria-label="More" /> → <strong>Import…</strong> instead.</dd>
          <dt>“This draft was made with a newer Builder. Update this Builder first.”</dt><dd>On your own computer: pull the latest code, rebuild the app (<code>npm run build</code> in <code>app/</code>) and restart the server.</dd>
          <dt>“That file is not a .zip.” / “… in the zip is not valid JSON.” / “The draft has no usable design.json.” / “The draft lists … but has no file for it.”</dt><dd>The file is damaged or was changed by hand. Ask for a fresh export.</dd>
          <dt>“Pick <em>n</em> conflicts first”</dt><dd>Apply waits until every <span class="pill danger"><I.Problem size={14} />Conflict</span> has a side picked.</dd>
          <dt>“This isn't a Builder design file (needs version 2, layouts[] and areas&#123;&#125;).”</dt><dd><strong>Import…</strong> takes a design.json exported by the Builder.</dd>
          <dt>“Couldn't reach the form service. Check your connection and try again.” / “Not sent: …”</dt><dd><strong>Feedback</strong> or <strong>Ask for an invite</strong> didn't go. Check your connection (an ad blocker can stop it too) and send again.</dd>
        </dl>

        <h3 id="messages-phone">On a phone</h3>
        <dl class="panels messages">
          <dt>“<em>The glyph editor</em> needs a computer. It's made for a mouse and a big screen. Open this page on a computer, or open it here anyway.”</dt><dd>The same note stands in for Review, making a release, and importing and exporting the design. Press <strong>Copy link</strong> and open the link on a computer, or <strong>Open anyway</strong> to use the tool on the phone until you reload the page.</dd>
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
  dt[id] { scroll-margin-top: var(--space-5); }
  /* messages are long: the quote above, what to do below */
  dl.messages { grid-template-columns: minmax(0, 1fr); gap: var(--space-1); }
  dl.messages dd { margin-bottom: var(--space-4); }
  h3[id] { scroll-margin-top: var(--space-5); }
  dt:target, dt:target + dd { background: var(--sel-bg); }
  @media (max-width: 759.98px) {
    .layout { grid-template-columns: minmax(0, 1fr); gap: var(--space-5); padding: var(--space-5) var(--space-5) var(--space-8); }
    .toc { position: static; flex-direction: row; flex-wrap: wrap; }
    .toc-title { width: 100%; }
    .toc a { border-left: 0; border: 1px solid var(--border); border-radius: var(--radius-md); }
    dl { grid-template-columns: 1fr; gap: var(--space-1); }
    dd { margin-bottom: var(--space-3); }
    table.ref td:first-child { white-space: normal; }
  }
</style>
