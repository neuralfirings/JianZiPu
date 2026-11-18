<script lang="ts">
  // One glossary section's rows side by side (Review, Your changes, a font update's conflicts):
  // before, the draft, and (on a conflict) what the Builder has now. A row the other side hasn't got is marked.
  // A row's own example shows under it, filled from `typing` (the draft's spellings over the Builder's).
  import { rowExample, rowKey, rowName, type GRow } from '$lib/glossary';
  import type * as T from '$lib/typing';
  let { columns, typing = {} }: { columns: { title: string; rows: GRow[] }[]; typing?: T.Typing } = $props();
  const keys = (rows: GRow[]) => new Set(rows.map(rowKey));
  let all = $derived(columns.map((c) => keys(c.rows)));
</script>

<div class="cols">
  {#each columns as c, n (c.title)}
    <div>
      <div class="h">{c.title}</div>
      <ol>
        {#each c.rows as r, i (rowKey(r) + i)}
          {@const ex = rowExample(r, typing)}
          <li class:new={n > 0 && !all[0].has(rowKey(r))}>{rowName(r)}{#if r.meaning} <span class="muted">· {r.meaning}</span>{/if}
            {#if ex}<div class="ex">example: <span class="zh">{ex[0]}</span> · <span class="mono">{ex[1]}</span></div>{/if}</li>
        {:else}<li class="muted">none</li>{/each}
      </ol>
    </div>
  {/each}
</div>

<style>
  .cols { display: flex; gap: var(--space-5); flex-wrap: wrap; font-size: var(--t-caption); }
  .h { font-weight: 600; color: var(--ink-muted); margin-bottom: 2px; }
  ol { margin: 0; padding-left: 2em; font-family: var(--font-serif); }
  li.new { color: var(--status-saved); font-weight: 600; }
  .ex { font-weight: 400; color: var(--ink-muted); }
  .ex .zh { font-family: var(--font-cjk); color: var(--ink); }
  .ex .mono { font-family: var(--font-mono); color: var(--ink); }
</style>
