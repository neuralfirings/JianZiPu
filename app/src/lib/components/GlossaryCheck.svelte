<script lang="ts">
  // More > Check the glossary: the glossary on jianzipufont.com as the next release would write it
  // from the spellings as they are now (online: the tester's draft), unsaved ones included, with what
  // it would leave out and the examples that type another glyph. Nothing is written; a release rewrites the page.
  import { onMount } from 'svelte';
  import * as I from '$lib/icons';
  import { api, GLOSSARY_FONT, type GlossaryCheck } from '$lib/api';
  import { hosted } from '$lib/hosted.svelte';
  import { withChanges } from '$lib/merge';
  import { filterTables } from '$lib/glossarySearch';
  import { loadFontFrom } from '$lib/fontload';
  import { openedAnyway, phone } from '$lib/phone.svelte';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';
  import NeedsComputer from './NeedsComputer.svelte';
  let { onclose }: { onclose: () => void } = $props();

  let res = $state<GlossaryCheck | null>(null);
  let err = $state<string | null>(null);
  let busy = $state(false);
  let family = $state<string | null>(null);
  let runs = 0;
  let q = $state('');
  let gloss = $state<HTMLDivElement | null>(null);
  let shown = $state<number | null>(null);
  // after each check and each keystroke: hide the rows that don't match (the tables are HTML strings)
  $effect(() => {
    void res; const query = q;
    shown = gloss ? filterTables(gloss, query) : null;
  });

  async function run() {
    if (!app.design) return;
    busy = true; err = null;
    try {
      // online: the font as it is now with all of the draft's changes, the way a release would take them
      // (a column the draft is older than comes from the font, not as the draft's empty one)
      const merged = hosted.isHosted && app.mainDesign
        ? withChanges(app.bundle(), { design: app.mainDesign, typing: app.mainTyping, svgs: app.mainSvgs, glossary: app.mainGlossary, glossaryLayout: app.mainLayout }) : null;
      res = await api.glossaryCheck(T.toRecords(merged?.typing ?? app.typing), merged?.design ?? app.design, app.extraSvgs, merged?.glossary ?? app.glossary, merged?.glossaryLayout ?? app.glossaryLayout);
      if (!res.ok && !res.error) err = 'The check failed.';
      // the font the examples were typed in: a new build since the last check replaces it
      try { family = (await loadFontFrom(res.font_url ?? GLOSSARY_FONT, 'glossary', 'build', `glossary${++runs}`)).family; } catch { family = null; }
    } catch (e) { err = (e as Error).message; }
    finally { busy = false; }
  }
  onMount(run);

  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;
  let clean = $derived(!!res?.ok && !res.problems?.length && !res.typing?.length);
</script>

<div class="modal-bg" role="presentation" onclick={onclose}>
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="gloss-title" tabindex="-1"
    onclick={(e) => e.stopPropagation()} onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}>
    {#if phone.on && !openedAnyway['glossary-check']}
      <NeedsComputer tool="Checking the glossary" key="glossary-check" {onclose} />
    {:else}
      <header>
        <h3 id="gloss-title">Check the glossary</h3>
        <span class="spacer"></span>
        <button onclick={run} disabled={busy}><I.Refresh /> Check again</button>
        <button class="quiet" onclick={onclose} aria-label="Close" data-tip="Close"><I.Close /></button>
      </header>
      <p class="muted">
        {#if hosted.isHosted}
          The glossary on jianzipufont.com as it would be if a release took all of your draft's changes{app.typingDirty ? ', unsaved ones included' : ''}.
          Nothing is sent: the page changes only when a release includes your changes.
        {:else}
          The glossary on jianzipufont.com as the next release would write it, from the spellings as they are now{app.typingDirty ? ', unsaved changes included' : ''}.
          Nothing is written: a release rewrites the page.
        {/if}
        {#if res?.font}Examples are typed and drawn in {res.font === 'build' ? 'the last build' : 'the released font, since there is no build yet'}, with these spellings and any glyph drawn since. No Build needed.{/if}
      </p>

      {#if busy && !res}
        <div class="banner info"><span class="ic"><I.Working /></span><span>Checking…</span></div>
      {:else if err}
        <div class="banner danger"><span class="ic"><I.Problem /></span><span><b>The check failed.</b> {err}</span></div>
      {:else if res}
        {#if res.error}
          <div class="banner danger"><span class="ic"><I.Problem /></span>
            <span><b>The glossary can't be made, so a release would stop here.</b> {res.error}</span></div>
        {/if}
        {#if res.problems?.length}
          <div class="banner danger"><span class="ic"><I.Problem /></span>
            <span><b>{plural(res.problems.length, 'thing')} to fix before a release</b>
              <ul>{#each res.problems as p}<li>{p}</li>{/each}</ul></span></div>
        {/if}
        {#if res.typing?.length}
          <div class="banner draft"><span class="ic"><I.Warn /></span>
            <span><b>{plural(res.typing.length, 'example')} type another glyph</b> than the rest of the row:
              <ul class="mono">{#each res.typing as t}<li>{t}</li>{/each}</ul></span></div>
        {/if}
        {#if res.not_built?.length}
          <div class="banner info"><span class="ic"><I.Info /></span>
            <span><b>No drawing yet:</b> <code>{res.not_built.join(', ')}</code>. Their rows show below; draw them in the glyph editor, then check again to type their examples.</span></div>
        {/if}
        {#if res.drawn?.length}
          <div class="banner info"><span class="ic"><I.Info /></span>
            <span><b>New since the last build:</b> <code>{res.drawn.join(', ')}</code>. Drawn in from {res.drawn.length === 1 ? 'its drawing' : 'their drawings'} for this check, so {res.drawn.length === 1 ? 'its examples are' : 'their examples are'} typed and shown below.</span></div>
        {/if}
        {#if res.missing_chars?.length}
          <div class="banner info"><span class="ic"><I.Info /></span>
            <span><b>Chinese characters not in the font yet:</b> {res.missing_chars.join(' ')}. Only a Build adds characters, from the base font; until then the examples that use them aren't checked.</span></div>
        {/if}
        {#if clean}
          <div class="banner saved"><span class="ic"><I.Check /></span>
            <span><b>Nothing to fix.</b> Every glyph with a spelling has a row, and every example types what it shows.</span></div>
        {/if}
        {#if res.tables?.length}
          <div class="search" role="search">
            <input type="search" placeholder="Search  k · 勾 · gou · a definition · chords" aria-label="Search the glossary"
              bind:value={q} autocomplete="off" spellcheck="false" />
            {#if q.trim() && shown !== null}<span class="muted" aria-live="polite">{shown ? `${shown} ${shown === 1 ? 'row' : 'rows'}` : 'No row matches. Try the pinyin without tones, or one character.'}</span>{/if}
          </div>
          <div bind:this={gloss} class="gloss" style:--jzp-family={family ? `'${family}'` : 'serif'} class:stale={busy}>
            {#each res.tables as t (t.id)}
              <h4>{t.title}</h4>
              <!-- generated by jzpbuild/glossary.py from components.csv, every value escaped there -->
              {@html t.html}
            {/each}
          </div>
        {/if}
      {/if}
    {/if}
  </div>
</div>

<style>
  .modal { padding: var(--space-7); width: min(1000px, 94vw); max-height: 88vh; overflow: auto; display: flex; flex-direction: column; gap: var(--space-4); }
  header { display: flex; align-items: center; gap: var(--space-3); }
  h3 { margin: 0; }
  p { margin: 0; }
  .spacer { flex: 1; }
  ul { margin: var(--space-2) 0 0; padding-left: 20px; }
  ul.mono { font-family: var(--font-mono); font-size: var(--t-caption); }
  .banner ul { max-height: 180px; overflow: auto; }
  .stale { opacity: 0.5; }
  .search { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
  .search input { width: 320px; max-width: 100%; }
  .gloss :global([hidden]) { display: none; }
  h4 { margin: var(--space-6) 0 var(--space-2); font: 600 var(--t-heading)/1.2 var(--font-display); }
  /* the font page's tables, drawn the way site/index.html draws them */
  .gloss :global(table) { width: 100%; border-collapse: collapse; }
  .gloss :global(th), .gloss :global(td) { text-align: left; vertical-align: top; padding: var(--space-2) var(--space-3); border-bottom: 1px solid var(--hairline); }
  .gloss :global(th) { font-weight: 600; }
  .gloss :global(td.gid a) { pointer-events: none; color: var(--ink-muted); font-family: var(--font-mono); font-size: var(--t-caption); text-decoration: none; }
  .gloss :global(.nw) { white-space: nowrap; }
  .gloss :global(jzp) { font-family: var(--jzp-family), var(--font-cjk), serif; font-size: 2.25rem; line-height: 1.5; word-break: keep-all; white-space: pre-wrap; }
  .gloss :global(txs) { display: block; font-family: var(--font-mono); font-size: var(--t-caption); }
  .gloss :global(r) { color: var(--accent); }
</style>
