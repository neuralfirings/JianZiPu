<script lang="ts">
  // The font portal: type anything and see it in one exact TTF, loaded into this page
  // from a build on the dev server or from a file you choose. Nothing installed on the
  // computer is used; the text falls back to nothing.
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { api, type Build } from '$lib/api';
  import { loadFontFrom, fmtBytes, fmtTime, type LoadedFont } from '$lib/fontload';
  import { SAMPLE_SETS } from '$lib/words';

  let builds = $state<Build[]>([]);
  let font = $state<LoadedFont | null>(null);
  let err = $state<string | null>(null);
  let loading = $state(false);
  let text = $state(localStorage.getItem('jzp-tester-text') ?? '名七勾五 s7k5 fys9k5 s7>\\k5 0k3 :shang79 Cv9,6|03\n大九挑五 中十点二抹一 散挑三');
  let size = $state(72);
  let liga = $state(true);
  let kern = $state(true);
  let vertical = $state(false);
  let compare = $state(false);
  let secondFont = $state<LoadedFont | null>(null);
  let wanted = $derived(page.url.searchParams.get('build'));

  $effect(() => { try { localStorage.setItem('jzp-tester-text', text); } catch {} });

  async function refresh() {
    try { const s = await api.buildStatus(); builds = s.builds; } catch (e) { err = (e as Error).message; }
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
  onMount(async () => {
    await refresh();
    const b = (wanted && builds.find((x) => x.id === wanted)) || builds[0];
    if (b) useBuild(b);
  });
  let features = $derived(`"liga" ${liga ? 1 : 0}, "kern" ${kern ? 1 : 0}`);
</script>

<div class="page">
  <div class="top">
    <div class="row wrap">
      <strong>Font</strong>
      {#if font}
        <span class="chip accent" title="Loaded into this page as its own font family; nothing installed on this computer is used">● {font.label}</span>
      {:else}
        <span class="chip">none loaded</span>
      {/if}
      {#if builds.length}
        <select onchange={(e) => { const b = builds.find((x) => x.id === (e.target as HTMLSelectElement).value); if (b) useBuild(b); }}>
          <option value="">Pick a build from this session…</option>
          {#each builds as b}<option value={b.id} selected={font?.id === b.id}>{b.id} · {fmtTime(b.time)} · {fmtBytes(b.bytes)}</option>{/each}
        </select>
      {:else}
        <span class="muted">no builds this session · <a href="/test">build one</a></span>
      {/if}
      <label class="file"><input type="file" accept=".ttf,.otf,font/ttf" onchange={(e) => useFile(e)} /> Open a .ttf file…</label>
      {#if font?.source === 'build' && font.id}<a href="/api/builds/{font.id}/JianZiPu.ttf?download=1" download="JianZiPu.ttf"><button>Download this font</button></a>{/if}
      <button onclick={refresh} title="Re-read the list of builds">↻</button>
      {#if loading}<span class="muted">loading…</span>{/if}
    </div>
    <div class="row wrap">
      <label>Size <input type="range" min="24" max="300" bind:value={size} /> {size} px</label>
      <label><input type="checkbox" bind:checked={liga} /> liga <span class="muted">(substitution)</span></label>
      <label><input type="checkbox" bind:checked={kern} /> kern <span class="muted">(positioning)</span></label>
      <label><input type="checkbox" bind:checked={vertical} /> vertical columns</label>
      <label><input type="checkbox" bind:checked={compare} /> compare with a second font</label>
      <select onchange={(e) => { const v = (e.target as HTMLSelectElement).value; if (v) text = SAMPLE_SETS[v].join(' '); (e.target as HTMLSelectElement).value = ''; }}>
        <option value="">Sample set…</option>{#each Object.keys(SAMPLE_SETS) as s}<option value={s}>{s}</option>{/each}
      </select>
    </div>
    {#if compare}
      <div class="row wrap">
        <strong>Second font</strong>
        {#if secondFont}<span class="chip">● {secondFont.label}</span>{:else}<span class="chip">none</span>{/if}
        {#if builds.length}<select onchange={(e) => { const b = builds.find((x) => x.id === (e.target as HTMLSelectElement).value); if (b) useBuild(b, 'second'); }}>
          <option value="">Pick a build…</option>{#each builds as b}<option value={b.id}>{b.id} · {fmtTime(b.time)}</option>{/each}</select>{/if}
        <label class="file"><input type="file" accept=".ttf,.otf,font/ttf" onchange={(e) => useFile(e, 'second')} /> Open a .ttf file…</label>
      </div>
    {/if}
    {#if err}<p class="error">{err}</p>{/if}
  </div>

  <textarea bind:value={text} rows="3" placeholder="Type words: s7k5  名七勾五  :fenkai  C03|s6,5" spellcheck="false"></textarea>

  <div class="sheets" class:two={compare}>
    <div class="sheet" class:vertical style="font-family: {font ? `'${font.family}'` : 'inherit'}; font-size: {size}px; font-feature-settings: {features}">
      {#if !font}<p class="muted" style="font: var(--t-md) var(--font)">Load a build or a .ttf file to see the text in it.</p>{:else}{text}{/if}
    </div>
    {#if compare}
      <div class="sheet" class:vertical style="font-family: {secondFont ? `'${secondFont.family}'` : 'inherit'}; font-size: {size}px; font-feature-settings: {features}">
        {#if !secondFont}<p class="muted" style="font: var(--t-md) var(--font)">Pick a second font to compare.</p>{:else}{text}{/if}
      </div>
    {/if}
  </div>
  <p class="muted small">Each font is loaded into this page under a name of its own, so an installed JianZiPu never stands in for it. A character the file doesn't have is still drawn by a system font, so check new characters against a build.</p>
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; }
  .top { display: flex; flex-direction: column; gap: var(--s-2); padding: var(--s-3) var(--s-4); border-bottom: 1px solid var(--line); }
  .wrap { flex-wrap: wrap; gap: var(--s-3); }
  .file { display: inline-flex; align-items: center; height: var(--control); padding: 0 var(--s-3); border: 1px solid var(--line); border-radius: var(--radius); background: var(--bg-2); cursor: pointer; }
  .file input { display: none; }
  textarea { margin: var(--s-3) var(--s-4) 0; font-family: var(--mono); resize: vertical; }
  .sheets { flex: 1; min-height: 0; display: flex; gap: var(--s-3); padding: var(--s-3) var(--s-4); overflow: auto; }
  .sheet { flex: 1; min-width: 0; background: var(--canvas); border: 1px solid var(--line); border-radius: var(--radius); padding: var(--s-4); white-space: pre-wrap; line-height: 1.5; overflow: auto; }
  .sheet.vertical { writing-mode: vertical-rl; text-orientation: upright; white-space: pre; }
  .small { font-size: var(--t-xs); padding: 0 var(--s-4) var(--s-3); }
  .error { color: var(--danger); margin: 0; }
</style>
