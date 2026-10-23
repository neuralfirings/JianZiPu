<script lang="ts">
  // Build & test: build the font, then type in it. Words view = one cell per word, the live
  // preview (boxes, unsaved rules) and/or the font; Text view = running text in one exact TTF
  // (a build or a file you open), with liga / kern switches, vertical columns and a second
  // font to compare. Each font is loaded into this page under a family of its own, so an
  // installed JianZiPu never stands in for it.
  import * as I from '$lib/icons';
  import { onMount } from 'svelte';
  import { phone } from '$lib/phone.svelte';
  import { page } from '$app/state';
  import { replaceState } from '$app/navigation';
  import { app } from '$lib/state.svelte';
  import { hosted } from '$lib/hosted.svelte';
  import { api, type Build, type BuildStatus, type WordPayload } from '$lib/api';
  import { anchorNames, wordPage } from '$lib/shape';
  import WordCanvas from '$lib/components/WordCanvas.svelte';
  import { SAMPLE_SETS } from '$lib/words';
  import { loadFontFrom, fmtBytes, fmtTime, type LoadedFont } from '$lib/fontload';
  import { segments } from '$lib/cmap';
  import { parseView, pickBuild, buildFailure, type TestView } from '$lib/buildtest';

  let view = $state<TestView>(parseView(page.url.searchParams.get('view')));
  let text = $state(page.url.searchParams.get('words') || (localStorage.getItem('jzp-test-words') ?? SAMPLE_SETS['Basic words'].join(' ')));
  let mode = $state<'live' | 'font' | 'both'>('live');
  let size = $state(96);
  let showBoxes = $state(false);
  let liga = $state(true);
  let kern = $state(true);
  let vertical = $state(false);
  let compare = $state(false);
  let composing = false;
  let result = $state<WordPayload | null>(null);
  let err = $state<string | null>(null);
  let status = $state<BuildStatus | null>(null);
  let font = $state<LoadedFont | null>(null);         // the font both views render with
  let secondFont = $state<LoadedFont | null>(null);   // Text view: compare with a second font
  let loading = $state(false);
  let logOpen = $state(false);
  let seenBuild: string | null | undefined = undefined;  // newest build id already shown (undefined = first load)
  let timer: ReturnType<typeof setTimeout> | null = null;

  let builds = $derived(status?.builds ?? []);
  let words = $derived(text.split(/\s+/).map((w) => w.trim()).filter(Boolean));
  let sets = $derived({ ...SAMPLE_SETS, ...(app.design?.test_sets ?? {}) });
  let features = $derived(`"liga" ${liga ? 1 : 0}, "kern" ${kern ? 1 : 0}`);

  $effect(() => { try { localStorage.setItem('jzp-test-words', text); } catch {} });
  $effect(() => {
    const ws = words, d = app.design;
    if (!d || view !== 'words') return;
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      if (composing) return;
      try {
        const r = await api.words(d, ws);
        if (r.ok) { result = r; err = null; } else err = r.error ?? 'preview failed';
      } catch (e) { err = (e as Error).message; }
    }, 150);
  });
  $effect(() => { if (!font && mode !== 'live') mode = 'live'; });

  function setView(v: TestView) {
    view = v;
    const u = new URL(page.url);
    u.searchParams.set('view', v);
    replaceState(u, {});
  }

  async function useBuild(b: Build, slot: 'main' | 'second' = 'main') {
    loading = true; err = null;
    try {
      const f = await loadFontFrom(b.url, `build ${b.id} · ${fmtTime(b.time)} · ${fmtBytes(b.bytes)}`, 'build', b.id);
      if (slot === 'main') font = f; else secondFont = f;
    } catch (e) { err = `could not load build ${b.id}: ${(e as Error).message}`; }
    finally { loading = false; }
  }
  async function useFile(e: Event, slot: 'main' | 'second' = 'main') {
    const f = (e.target as HTMLInputElement).files?.[0]; (e.target as HTMLInputElement).value = '';
    if (!f) return;
    loading = true; err = null;
    try {
      const lf = await loadFontFrom(f, `${f.name} · ${fmtBytes(f.size)}`, 'file');
      if (slot === 'main') font = lf; else secondFont = lf;
    } catch (ex) { err = `could not load ${f.name}: ${(ex as Error).message}`; }
    finally { loading = false; }
  }
  function pick(e: Event, slot: 'main' | 'second' = 'main') {
    const b = builds.find((x) => x.id === (e.target as HTMLSelectElement).value);
    if (b) useBuild(b, slot);
  }

  /** On first load show the build the link names (or the newest); after that, switch to each new build. */
  async function refreshStatus() {
    try { status = await api.buildStatus(); } catch (e) { err = (e as Error).message; return; }
    if (status.state === 'running') { setTimeout(refreshStatus, 700); return; }
    const newest = status.build?.id ?? null;
    if (seenBuild === undefined) {
      const b = pickBuild(status.builds, page.url.searchParams.get('build'));
      if (b) useBuild(b);
    } else if (newest && newest !== seenBuild && status.build) useBuild(status.build);
    seenBuild = newest;
  }
  async function build() {
    // hosted: the build takes the draft as it is now (unsaved edits too); local: Save writes the files first
    if (hosted.isHosted) app.flush();
    else if (app.dirty && !(await app.save())) return;
    logOpen = true;
    const r = await api.build(app.buildInputs());
    if (!r.ok && r.error) err = r.error;
    status = r.status ?? status;
    refreshStatus();
  }
  onMount(() => { refreshStatus(); });

  function saveSet() {
    const name = prompt('Name for this word set:', 'My set');
    if (!name) return;
    app.edit(`Save test set "${name}"`, (d) => { d.test_sets = { ...(d.test_sets ?? {}), [name]: words }; });
  }
  let failure = $derived(status && status.ok === false ? buildFailure(status.log) : null);
  const buildLabel = $derived(status?.state === 'running' ? 'Building…' : app.dirty && !hosted.isHosted ? 'Save & build' : 'Build font');
</script>

{#snippet buildLog()}
  <details class="log" bind:open={logOpen}>
    <summary>Build log {#if status?.state === 'running'}<span class="muted">(running…)</span>{/if}</summary>
    {#if failure}<p class="error">{failure}</p>{/if}
    <pre>{(status?.log ?? []).join('\n') || 'No build yet. Builds read the saved design.json and components.csv.'}</pre>
  </details>
{/snippet}
{#snippet controls()}
    <div class="row wrap">
      <span class="muted">
        {#if status?.build}Built {fmtTime(status.build.time)} from saved files{:else}No build yet{/if}
        {#if app.dirty} · <I.Warn size={14} /> {app.changes.length} unsaved change{app.changes.length === 1 ? '' : 's'} not in the font{/if}
      </span>
      <span class="spacer"></span>
      {#if status?.state === 'done'}
        <span class={status.ok ? 'badge-ok' : 'badge-danger'}>{#if status.ok}<I.Check size={14} /> last build ok{:else}<I.Problem size={14} /> last build failed{/if}{#if status.finished && status.started} · {(status.finished - status.started).toFixed(1)} s{/if}</span>
      {/if}
      <button class="primary" onclick={build} disabled={status?.state === 'running'}>{buildLabel}</button>
    </div>
    {#if status?.build}
      {@const b = status.build}
      <div class="row wrap built">
        <span><strong>{b.id}</strong> · JianZiPu.ttf · {fmtBytes(b.bytes)} · {fmtTime(b.time)}</span>
        <span class="muted small" title={b.file}>in a temporary folder on the web server, kept while it runs</span>
        <a href="{b.url}?download=1" download="JianZiPu.ttf"><button>Download JianZiPu.ttf</button></a>
        {#if builds.length > 1}
          <details class="older"><summary>{builds.length - 1} earlier build{builds.length > 2 ? 's' : ''}</summary>
            <table><tbody>{#each builds.slice(1) as o}<tr><td>{o.id}</td><td>{fmtTime(o.time)}</td><td>{fmtBytes(o.bytes)}</td><td><a href="{o.url}?download=1" download="JianZiPu.ttf">download</a></td></tr>{/each}</tbody></table>
          </details>
        {/if}
      </div>
    {/if}

    <div class="row wrap">
      <strong>Font</strong>
      {#if font}
        <span class="chip accent" title="Loaded into this page as its own font family; nothing installed on this computer is used"><I.Current size={14} />{font.label}</span>
      {:else}
        <span class="chip dashed">none loaded</span>
      {/if}
      {#if builds.length}
        <select onchange={(e) => pick(e)}>
          <option value="">Pick a build from this session…</option>
          {#each builds as o}<option value={o.id} selected={font?.id === o.id}>{o.id} · {fmtTime(o.time)} · {fmtBytes(o.bytes)}</option>{/each}
        </select>
      {/if}
      <label class="file"><input type="file" accept=".ttf,.otf,font/ttf" onchange={(e) => useFile(e)} /> Open a .ttf file…</label>
      <button class="quiet" onclick={refreshStatus} data-tip="Re-read the list of builds" aria-label="Refresh"><I.Refresh /></button>
      {#if loading}<span class="muted">loading…</span>{/if}
    </div>

    <div class="row wrap">
      <span class="views" role="group" aria-label="View">
        <button class="chip" aria-pressed={view === 'words'} onclick={() => setView('words')}>Test the design</button>
        <button class="chip" aria-pressed={view === 'text'} onclick={() => setView('text')}>Test the font file</button>
      </span>
      {#if view === 'words'}
        <span>Render with</span>
        <label><input type="radio" bind:group={mode} value="live" /> Live preview <span class="muted">(boxes, unsaved rules)</span></label>
        <label><input type="radio" bind:group={mode} value="font" disabled={!font} /> Font</label>
        <label><input type="radio" bind:group={mode} value="both" disabled={!font} /> Compare both</label>
        <label><input type="checkbox" bind:checked={showBoxes} /> show boxes</label>
      {:else}
        <label><input type="checkbox" bind:checked={liga} /> liga <span class="muted">(substitution)</span></label>
        <label><input type="checkbox" bind:checked={kern} /> kern <span class="muted">(positioning)</span></label>
        <label><input type="checkbox" bind:checked={vertical} /> vertical columns</label>
        <label><input type="checkbox" bind:checked={compare} /> compare with a second font</label>
      {/if}
    </div>
    <p class="muted small explain">
      {#if view === 'words'}
        Each word drawn from the glyph files and the design as it is now, unsaved changes included. No build needed. Choose Font or Compare both to check a build against it.
      {:else}
        Running text in one exact font file, the way a reader sees it. It changes only when you build again or open another file.
      {/if}
    </p>
    {#if view === 'text' && compare}
      <div class="row wrap">
        <strong>Second font</strong>
        {#if secondFont}<span class="chip"><I.Current size={14} />{secondFont.label}</span>{:else}<span class="chip dashed">none</span>{/if}
        {#if builds.length}<select onchange={(e) => pick(e, 'second')}>
          <option value="">Pick a build…</option>{#each builds as o}<option value={o.id}>{o.id} · {fmtTime(o.time)}</option>{/each}</select>{/if}
        <label class="file"><input type="file" accept=".ttf,.otf,font/ttf" onchange={(e) => useFile(e, 'second')} /> Open a .ttf file…</label>
      </div>
    {/if}

{/snippet}
{#snippet typeRow()}
    <div class="row wrap">
      <textarea class="type" rows={view === 'text' || phone.on ? 3 : 1} bind:value={text} spellcheck="false" placeholder="Type words: s7k5  名七勾五  :fenkai  C03|s6,5"
        oncompositionstart={() => (composing = true)} oncompositionend={() => { composing = false; text = text + ''; }}></textarea>
      <select onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) text = sets[v].join(' '); (e.target as HTMLSelectElement).value = ''; }}>
        <option value="">Sample set…</option>
        {#each Object.keys(sets) as s}<option value={s}>{s}</option>{/each}
      </select>
      <button onclick={saveSet} title="Store the current words as a named set in the design file">+ Save as set</button>
      <label>Size <input type="range" min="24" max="300" bind:value={size} /> {size} px</label>
    </div>
{/snippet}

<div class="page" class:phone={phone.on}>
  {#if phone.on}
    <!-- a phone: the words first, the typing field docked under them; building and fonts fold away -->
    <details class="top folded">
      <summary>{#if status?.build}Built {fmtTime(status.build.time)}{:else}No build yet{/if}{#if font} · {font.label}{/if} · {view === 'words' ? 'Test the design' : 'Test the font file'}</summary>
      {@render controls()}
      {@render buildLog()}
    </details>
  {:else}
  <div class="top">
{@render controls()}
{@render typeRow()}
  </div>
  {/if}

  {#if err}<p class="error">{err}</p>{/if}
  {#if view === 'words'}
    <div class="words">
      {#each result?.words ?? [] as w (w.word)}
        {@const pg = wordPage(w)}
        {@const cellW = Math.round((pg[1] / 1000) * size)}
        <div class="word">
          {#if mode !== 'font'}
            <a href="/layouts?word={encodeURIComponent(w.word)}" title="Open in Layouts">
              <WordCanvas elements={w.pieces.flatMap((p, pi) => { const an = anchorNames(p.elements, app.design!.areas); return p.elements.map((e) => ({ ...e, name: `${pi}:${e.name}`, anchor: an.has(e.name) })); })}
                width={cellW} height={Math.round(size * 1.6)} showBoxes={showBoxes} showPage={true} page={pg} fit={false} />
            </a>
          {/if}
          {#if mode !== 'live' && font}
            {#key font}
              <div class="font" style="font-family: '{font.family}'; font-size: {size}px; height: {Math.round(size * 1.6)}px; width: {cellW}px">{#each segments(w.word, font.chars) as s}{#if s.missing}<span class="miss" title="Not in this font: drawn by an installed font">{s.text}</span>{:else}{s.text}{/if}{/each}</div>
            {/key}
          {/if}
          <div class="keys muted">{w.word}{#if w.pieces.some((p) => p.layout === null && p.glyphs.some((g) => !['space', 'numbersign', 'advance'].includes(g)))} <span class="badge-warn" title="Some glyphs matched no word type"><I.Warn size={14} /></span>{/if}</div>
          <div class="id">{w.glyphs.join(' ')}</div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="sheets" class:two={compare}>
      <div class="sheet" class:vertical style="font-family: {font ? `'${font.family}'` : 'inherit'}; font-size: {size}px; font-feature-settings: {features}">
        {#if !font}<p class="muted hint">Build the font, pick a build or open a .ttf file to see the text in it.</p>{:else}{#each segments(text, font.chars) as s}{#if s.missing}<span class="miss" title="Not in this font: drawn by an installed font">{s.text}</span>{:else}{s.text}{/if}{/each}{/if}
      </div>
      {#if compare}
        <div class="sheet" class:vertical style="font-family: {secondFont ? `'${secondFont.family}'` : 'inherit'}; font-size: {size}px; font-feature-settings: {features}">
          {#if !secondFont}<p class="muted hint">Pick a second font to compare.</p>{:else}{#each segments(text, secondFont.chars) as s}{#if s.missing}<span class="miss" title="Not in this font: drawn by an installed font">{s.text}</span>{:else}{s.text}{/if}{/each}{/if}
        </div>
      {/if}
    </div>
    <p class="muted small note">Each font is loaded into this page under a name of its own, so an installed JianZiPu never stands in for it. A character the file doesn't have is drawn by an installed font <span class="miss">in red</span>, so it can't pass for part of the font.</p>
  {/if}

  {#if phone.on}<div class="dock">{@render typeRow()}</div>{/if}
  {#if !phone.on}{@render buildLog()}{/if}
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; }
  /* a phone: the folded controls on top, the words scroll, the typing field docked at the bottom */
  .phone .top.folded { padding: 0; gap: 0; }
  .phone .top.folded > summary { padding: var(--space-4); min-height: var(--control-md); cursor: pointer; font-weight: 600; }
  .phone .top.folded[open] { max-height: 60%; overflow: auto; padding: 0 var(--space-4) var(--space-4); gap: var(--space-4); }
  .phone .top.folded[open] > summary { padding: var(--space-4) 0; }
  .phone .top :global(.muted.small), .phone .top label .muted { display: none; }
  .phone .words { padding: var(--space-4); gap: var(--space-4); }
  .dock { flex: none; padding: var(--space-3) var(--space-4); border-top: 1px solid var(--border); background: var(--bg-panel); }
  .dock .type { min-width: 0; width: 100%; flex: 1 1 100%; resize: none; line-height: 22px; padding: var(--space-3) var(--space-4); }
  .dock :global(.row) { gap: var(--space-3); }
  .top { display: flex; flex-direction: column; gap: var(--space-4); padding: var(--space-5) var(--space-6); border-bottom: 1px solid var(--border); }
  .wrap { flex-wrap: wrap; gap: var(--space-5); }
  .spacer { flex: 1; }
  .views { display: inline-flex; gap: var(--space-2); }
  .views .chip { cursor: pointer; }
  .explain { margin: calc(-1 * var(--space-2)) 0 0; }
  .file { display: inline-flex; align-items: center; height: var(--control-md); padding: 0 var(--space-5); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-panel); cursor: pointer; }
  .file input { display: none; }
  .type { flex: 1; min-width: 300px; font-family: var(--font-mono); resize: vertical; }
  .words { flex: 1; overflow: auto; display: flex; flex-wrap: wrap; gap: var(--space-5); padding: var(--space-6); align-content: flex-start; }
  .word { display: flex; flex-direction: column; align-items: center; gap: 2px; }
  .word a { display: block; }
  .font { font-feature-settings: "kern", "liga"; line-height: 1.6; background: var(--bg-canvas); border-radius: var(--radius-md); display: flex; align-items: center; padding-left: 0; white-space: nowrap; overflow: visible; }
  .keys { font-family: var(--font-mono); }
  .sheets { flex: 1; min-height: 0; display: flex; gap: var(--space-5); padding: var(--space-5) var(--space-6); overflow: auto; }
  .sheet { flex: 1; min-width: 0; background: var(--bg-canvas); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-6); white-space: pre-wrap; line-height: 1.5; overflow: auto; }
  .sheet.vertical { writing-mode: vertical-rl; text-orientation: upright; white-space: pre; }
  .hint { font: var(--t-label) var(--font-serif); writing-mode: horizontal-tb; }
  .miss { color: var(--status-danger); }
  .error { color: var(--status-danger); margin: 0; padding: var(--space-4) var(--space-6) 0; white-space: pre-line; }
  .built { padding: var(--space-4) var(--space-5); background: var(--bg-panel); border-radius: var(--radius-md); }
  .small { font-size: var(--t-caption); }
  .note { padding: 0 var(--space-6) var(--space-5); margin: 0; }
  .older summary { cursor: pointer; font-size: var(--t-small); }
  .older td { padding: 2px 10px 2px 0; font-size: var(--t-small); }
  .log { border-top: 1px solid var(--border); padding: var(--space-4) var(--space-6); max-height: 40vh; overflow: auto; }
  pre { font: var(--t-caption)/1.4 var(--font-mono); white-space: pre-wrap; }
</style>
