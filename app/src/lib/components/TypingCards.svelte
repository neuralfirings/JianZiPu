<script lang="ts">
  // The Typing view on a phone: one card per glyph with its spellings and anything wrong with
  // them, the same fields as the table (T.FIELDS). Look only; a tap opens the glyph's card, where
  // its spellings are edited. Paste and CSV need the table, on a computer.
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import { typingCheck } from '$lib/typingcheck.svelte';
  import * as T from '$lib/typing';
  import Glyph from './Glyph.svelte';
  import type { Section } from './TypingTable.svelte';

  let { sections, selected, onselect }: { sections: Section[]; selected: string | null; onselect: (g: string) => void } = $props();
  let partnerOf = $derived(T.partners(app.typing));
</script>

<div class="cards">
  {#each sections as s (s.key)}
    <h3 class="sec">{s.title} <span class="muted">{s.sub ?? ''} · {s.glyphs.length}</span></h3>
    {#if s.decimals}
      <p class="muted small">Typed by pattern, nothing to fill: {T.decimalPatterns(s.glyphs[0] ?? '')[0] ?? ''} …</p>
    {:else}
      {#each s.glyphs as g (g)}
        {@const st = typingCheck.statusOf(g)}
        {@const issues = typingCheck.issuesFor(g)}
        <button class="card {st}" class:on={selected === g} onclick={() => onselect(g)}>
          <span class="art"><Glyph name={g} size={40} /></span>
          <span class="what">
            <span class="gn">{g}{#if partnerOf[g]} <span class="muted"><I.PartnerOf size={12} /> of {partnerOf[g]}</span>{/if}</span>
            <span class="spells">
              {#each T.FIELDS as f}
                {@const v = T.shown(app.typing, g, f)}
                {#if v.value && !(f === 'vert_variant' && partnerOf[g])}<span class="sp" class:inh={!!v.inherited}><span class="lbl">{T.LABEL[f]}</span> {v.value}</span>{/if}
              {/each}
              {#if T.isEmpty(app.typing[g]) && !partnerOf[g]}<span class="muted">no spellings yet</span>{/if}
            </span>
            {#if issues.length}<span class="issue">{#if st === 'err'}<I.Problem size={14} />{:else}<I.Warn size={14} />{/if} {issues.join(' · ')}</span>{/if}
          </span>
        </button>
      {/each}
    {/if}
  {/each}
</div>

<style>
  .cards { display: flex; flex-direction: column; gap: var(--space-3); }
  .sec { margin: var(--space-5) 0 0; font-size: var(--t-panel); }
  .sec:first-child { margin-top: 0; }
  .card { display: flex; gap: var(--space-4); align-items: flex-start; justify-content: flex-start; height: auto; padding: var(--space-4); text-align: left; font-weight: 400; border-color: var(--border); background: var(--bg-field); }
  .card.on { border-color: var(--sel-border); background: var(--sel-bg); }
  .card.err { border-color: var(--status-danger); }
  .art { flex: none; display: inline-flex; width: 44px; height: 44px; align-items: center; justify-content: center; }
  .what { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
  .gn { font-family: var(--font-mono); font-size: var(--t-small); }
  .spells { display: flex; flex-wrap: wrap; gap: var(--space-2) var(--space-4); }
  .sp { font-family: var(--font-mono); }
  .sp.inh { color: var(--ink-muted); }
  .lbl { font-family: var(--font-serif); font-size: var(--t-caption); color: var(--ink-muted); }
  .issue { font-size: var(--t-small); color: var(--ink-muted); }
  .err .issue :global(svg) { color: var(--status-danger); }
  .warn .issue :global(svg) { color: var(--status-draft); }
  .small { font-size: var(--t-small); }
</style>
