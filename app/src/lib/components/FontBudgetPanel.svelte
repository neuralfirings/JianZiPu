<script lang="ts">
  // Rule counts and size estimate per word type.
  import { app } from '$lib/state.svelte';
  let perLayout = $derived(app.stats?.per_layout ?? {});
</script>

{#if app.stats}
  <div class="muted small">One rule per word shape and glyph bucket, all in one positioning lookup. The font tools split it automatically; the number to watch is how many rules each word type adds.</div>
  <table><tbody>
    {#each Object.entries(perLayout) as [n, s]}<tr><td>{n}</td><td class="num">{s.shapes} shapes</td><td class="num">{s.rules} rules</td><td class="num">{(s.est_bytes / 1024).toFixed(1)} KB</td></tr>{/each}
    <tr><td><strong>total</strong></td><td></td><td class="num"><strong>{app.stats.rules}</strong></td><td class="num"><strong>{(app.stats.est_bytes / 1024).toFixed(0)} KB</strong></td></tr>
  </tbody></table>
  {#if app.stats.skipped}<div class="badge-warn small">{app.stats.skipped} shape/glyph combinations skipped. Click "N skipped" under a word type to see why.</div>{/if}
  {#if app.warnings.length}<details><summary class="muted small">{app.warnings.length} design warnings</summary><ul class="small">{#each app.warnings as w}<li>{w}</li>{/each}</ul></details>{/if}
{:else}
  <div class="muted small">No stats yet.</div>
{/if}

<style>
  table { font-size: var(--t-sm); border-collapse: collapse; }
  td { padding: 1px 6px 1px 0; } .num { text-align: right; font-family: var(--mono); }
  .small { font-size: var(--t-xs); }
</style>
