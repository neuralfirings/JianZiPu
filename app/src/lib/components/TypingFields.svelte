<script lang="ts">
  // The bottom panel's Typing column (Tiles view): this glyph's spellings as fields.
  // A vertical form shows its partner's spellings greyed; a position decimal its pattern.
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';
  import SpellInput from './SpellInput.svelte';
  let { glyph }: { glyph: string } = $props();
  const FIELDS: T.SpellField[] = ['latin', 'latin_alt', 'simplified', 'traditional', 'vert_variant', 'pinyin', 'glossary', 'common'];
  let partner = $derived(T.partners(app.typing)[glyph]);
  let hasAny = $derived(!T.isEmpty(app.typing[glyph]));
  function clear() {
    app.editTyping(`${glyph} · clear spellings`, (t) => { const v = t[glyph]?.vert_variant; delete t[glyph]; if (v) (t[glyph] = T.empty()).vert_variant = v; });
  }
</script>

<div class="tf">
  {#if T.isDecimal(glyph)}
    <p>Typed by pattern, nothing to fill:</p>
    <p class="mono">{T.decimalPatterns(glyph).join(' · ')}</p>
    <p class="muted small">The same for all 130 position decimals.</p>
  {:else}
    {#if partner}
      <p class="small">Vertical form of <a href="/glyphs?g={encodeURIComponent(partner)}">{partner}</a> <I.Pair size={12} />. Typed after a colon (<span class="mono">:{T.shown(app.typing, glyph, 'latin').value || T.shown(app.typing, glyph, 'simplified').value}</span>). Greyed values come from {partner}; edit them there. A spelling of its own can go here.</p>
    {/if}
    <div class="grid">
      {#each FIELDS as f}
        {#if !(f === 'vert_variant' && partner) && !(f === 'common' && !T.get(app.typing, glyph).common)}
          <label for="sp-{f}" title={T.HELP[f]}>{T.LABEL[f]}</label>
          <span id="sp-{f}"><SpellInput {glyph} field={f} /></span>
        {/if}
      {/each}
    </div>
    {#if hasAny}<button class="lnk" onclick={clear} title="Empties this glyph's spellings (one undo step); the glyph, its file and its areas stay">Clear spellings</button>{/if}
  {/if}
</div>

<style>
  .tf { display: flex; flex-direction: column; gap: var(--space-4); min-width: 0; }
  .grid { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 4px 8px; align-items: center; }
  label { color: var(--ink-muted); font-size: var(--t-caption); }
  p { margin: 0; }
  .small { font-size: var(--t-caption); }
  .mono { font-family: var(--font-mono); }
  .lnk { align-self: flex-start; height: 22px; padding: 0 8px; border-style: dashed; background: transparent; font-size: var(--t-caption); }
  @media (max-width: 759.98px) { .lnk { min-height: var(--control-sm); } }
</style>
