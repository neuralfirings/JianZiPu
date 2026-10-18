<script lang="ts">
  import { onMount } from 'svelte';
  import { app } from '$lib/state.svelte';
  import { api, type BuildStatus, type WordPayload } from '$lib/api';
  import { anchorNames, wordPage } from '$lib/shape';
  import WordCanvas from '$lib/components/WordCanvas.svelte';
  import { SAMPLE_SETS, DEFAULT_STRIP } from '$lib/words';
  import { loadFontFrom, fmtBytes, fmtTime, type LoadedFont } from '$lib/fontload';
  import { segments } from '$lib/cmap';

  let text = $state(localStorage.getItem('jzp-test-words') ?? SAMPLE_SETS['Basic words'].join(' '));
  let mode = $state<'live' | 'font' | 'both'>('live');
  let size = $state(96);
  let showBoxes = $state(false);
  let composing = false;
  let result = $state<WordPayload | null>(null);
  let err = $state<string | null>(null);
  let status = $state<BuildStatus | null>(null);
  let fontVersion = $state(0);
  let fontLoaded = $state(false);
  let font = $state<LoadedFont | null>(null);     // the exact build rendered in "Built font" mode
  let logOpen = $state(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  let words = $derived(text.split(/\s+/).map((w) => w.trim()).filter(Boolean));
  let sets = $derived({ ...SAMPLE_SETS, ...(app.design?.test_sets ?? {}) });

  $effect(() => {
    const ws = words, d = app.design;
    if (!d) return;
    try { localStorage.setItem('jzp-test-words', text); } catch {}
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      if (composing) return;
      try {
        const r = await api.words(d, ws);
        if (r.ok) { result = r; err = null; } else err = r.error ?? 'preview failed';
      } catch (e) { err = (e as Error).message; }
    }, 150);
  });

  async function loadFont() {
    const b = status?.build;
    if (!b) { fontLoaded = false; font = null; return; }
    try {
      font = await loadFontFrom(b.url, `build ${b.id}`, 'build', b.id);
      fontLoaded = true; fontVersion++;
    } catch { fontLoaded = false; font = null; }
  }
  async function refreshStatus() {
    status = await api.buildStatus();
    if (status.state === 'running') setTimeout(refreshStatus, 700);
    else if (status.build && font?.id !== status.build.id) loadFont();
  }
  async function build() {
    if (app.dirty && !(await app.save())) return;
    logOpen = true;
    const r = await api.build();
    status = r.status;
    refreshStatus();
  }
  onMount(() => { refreshStatus(); loadFont(); });

  function saveSet() {
    const name = prompt('Name for this word set:', 'My set');
    if (!name) return;
    app.edit(`Save test set "${name}"`, (d) => { d.test_sets = { ...(d.test_sets ?? {}), [name]: words }; });
  }
  let failure = $derived.by(() => {
    if (!status || status.ok !== false) return null;
    const log = status.log.join('\n');
    const m = log.match(/OverflowError.*?(?=\n|$)|.*too large.*|.*Error.*/);
    return m ? m[0] : 'Build failed — see the log.';
  });
  const buildLabel = $derived(status?.state === 'running' ? 'Building…' : app.dirty ? 'Save & build' : 'Build font');
</script>

<div class="page">
  <div class="top">
    <div class="row wrap">
      <span>Render with</span>
      <label><input type="radio" bind:group={mode} value="live" /> Live preview <span class="muted">(boxes, unsaved rules)</span></label>
      <label><input type="radio" bind:group={mode} value="font" disabled={!fontLoaded} /> Built font {#if font}<span class="muted">{font.label}</span>{/if}</label>
      <label><input type="radio" bind:group={mode} value="both" disabled={!fontLoaded} /> Compare both</label>
      <span class="muted">
        {#if status?.build}built {fmtTime(status.build.time)} from saved files{:else}no build yet{/if}
        {#if app.dirty} · ⚠ {app.changes.length} unsaved change{app.changes.length === 1 ? '' : 's'} not in the font{/if}
      </span>
      <span class="spacer"></span>
      <button class="primary" onclick={build} disabled={status?.state === 'running'}>{buildLabel}</button>
      {#if status?.state === 'done'}
        <span class={status.ok ? 'badge-ok' : 'badge-danger'}>{status.ok ? '✓ last build ok' : '✗ last build failed'}{#if status.finished && status.started} · {(status.finished - status.started).toFixed(1)} s{/if}</span>
      {/if}
    </div>
    {#if status?.build}
      {@const b = status.build}
      <div class="row wrap built">
        <span><strong>{b.id}</strong> · JianZiPu.ttf · {fmtBytes(b.bytes)} · {fmtTime(b.time)}</span>
        <span class="muted small" title={b.file}>in a temporary folder on the dev server, kept while it runs</span>
        <a href="{b.url}?download=1" download="JianZiPu.ttf"><button>Download JianZiPu.ttf</button></a>
        <a href="/tester?build={b.id}"><button>Open in Tester ↗</button></a>
        {#if status.builds.length > 1}
          <details class="older"><summary>{status.builds.length - 1} earlier build{status.builds.length > 2 ? 's' : ''}</summary>
            <table><tbody>{#each status.builds.slice(1) as o}<tr><td>{o.id}</td><td>{fmtTime(o.time)}</td><td>{fmtBytes(o.bytes)}</td><td><a href="{o.url}?download=1" download="JianZiPu.ttf">download</a></td><td><a href="/tester?build={o.id}">test</a></td></tr>{/each}</tbody></table>
          </details>
        {/if}
      </div>
    {/if}
    <div class="row wrap">
      <input type="text" style="flex: 1; min-width: 300px; font-family: var(--mono)" bind:value={text} placeholder="type words: s7k5 名七勾五 :fenkai C03|s6,5"
        oncompositionstart={() => (composing = true)} oncompositionend={() => { composing = false; text = text + ''; }} />
      <select onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) text = sets[v].join(' '); (e.target as HTMLSelectElement).value = ''; }}>
        <option value="">Sample set…</option>
        {#each Object.keys(sets) as s}<option value={s}>{s}</option>{/each}
      </select>
      <button onclick={saveSet} title="Store the current words as a named set in the design file">+ Save as set</button>
      <label>Size <input type="range" min="48" max="240" bind:value={size} /> {size} px</label>
      <label><input type="checkbox" bind:checked={showBoxes} /> show boxes</label>
    </div>
  </div>

  {#if err}<p class="error" style="padding: 0 var(--s-4)">{err}</p>{/if}
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
        {#if mode !== 'live'}
          {#key fontVersion}
            <div class="font" style="font-family: {font ? `'${font.family}'` : 'inherit'}; font-size: {size}px; height: {Math.round(size * 1.6)}px; width: {cellW}px">{#each segments(w.word, font?.chars ?? null) as s}{#if s.missing}<span class="miss" title="Not in the built font: drawn by an installed font">{s.text}</span>{:else}{s.text}{/if}{/each}</div>
          {/key}
        {/if}
        <div class="keys muted">{w.word}{#if w.pieces.some((p) => p.layout === null && p.glyphs.some((g) => !['space', 'numbersign', 'advance'].includes(g)))} <span class="badge-warn" title="Some glyphs matched no word type">⚠</span>{/if}</div>
        <div class="id">{w.glyphs.join(' ')}</div>
      </div>
    {/each}
  </div>

  <details class="log" bind:open={logOpen}>
    <summary>Build log {#if status?.state === 'running'}<span class="muted">(running…)</span>{/if}</summary>
    {#if failure}<p class="error">{failure}</p>{/if}
    <pre>{(status?.log ?? []).join('\n') || 'No build yet. Builds read the saved design.json and components.csv.'}</pre>
  </details>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; }
  .top { display: flex; flex-direction: column; gap: var(--s-2); padding: var(--s-3) var(--s-4); border-bottom: 1px solid var(--line); }
  .wrap { flex-wrap: wrap; gap: var(--s-3); }
  .spacer { flex: 1; }
  .words { flex: 1; overflow: auto; display: flex; flex-wrap: wrap; gap: var(--s-3); padding: var(--s-4); align-content: flex-start; }
  .word { display: flex; flex-direction: column; align-items: center; gap: 2px; }
  .word a { display: block; }
  .font { font-feature-settings: "kern", "liga"; line-height: 1.6; background: var(--canvas); border-radius: var(--radius); display: flex; align-items: center; padding-left: 0; white-space: nowrap; overflow: visible; }
  .keys { font-family: var(--mono); }
  .miss { color: var(--danger); }
  .built { padding: var(--s-2) var(--s-3); background: var(--bg-2); border-radius: var(--radius); }
  .small { font-size: var(--t-xs); }
  .older summary { cursor: pointer; font-size: var(--t-sm); }
  .older td { padding: 2px 10px 2px 0; font-size: var(--t-sm); }
  .log { border-top: 1px solid var(--line); padding: var(--s-2) var(--s-4); max-height: 40vh; overflow: auto; }
  pre { font: var(--t-xs)/1.4 var(--mono); white-space: pre-wrap; }
</style>
