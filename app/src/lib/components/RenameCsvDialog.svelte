<script lang="ts">
  // Rename from CSV (the Builder on your own computer): the glyph names list (Glyphs → … →
  // Download glyph names) with new_name filled in where a name should change. The server vets
  // the whole set first (POST /api/glyphs/rename/check); every row is shown old → new with what's
  // wrong, and nothing changes until all of them are fine and you press Rename. Then they're
  // renamed at once (PUT /api/glyphs/rename), swaps included, and the files load again.
  import { onMount } from 'svelte';
  import { api, type RenameCheck } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import * as I from '$lib/icons';
  import Glyph from './Glyph.svelte';

  let { file, text, onclose, ondone }: {
    file: string; text: string; onclose: () => void;
    /** After the rename, with old -> new for each glyph. */
    ondone: (renamed: Record<string, string>) => void;
  } = $props();

  let check = $state<RenameCheck | null>(null);
  let working = $state(false);
  let error = $state<string | null>(null);
  let conflict = $state(false);

  let bad = $derived(check?.pairs.filter((p) => p.problem).length ?? 0);
  let n = $derived(check?.pairs.length ?? 0);
  let waitFor = $derived(app.dirty ? 'Save or discard your unsaved changes first: this rewrites the saved files.' : null);
  const plural = (k: number, w: string) => `${k} ${w}${k === 1 ? '' : 's'}`;

  onMount(async () => {
    try { check = await api.checkRenames({ csv: text }); } catch (e) { error = (e as Error).message; }
  });

  async function go() {
    if (!check?.ok || !n || waitFor) return;
    working = true; error = null; conflict = false;
    try {
      const names = Object.fromEntries(check.pairs.map((p) => [p.from, p.to]));
      const r = await api.renameMany(names, app.diskHash, app.csvHash);
      if (!r.ok) { error = r.error ?? 'It did not work.'; conflict = !!r.conflict; return; }
      const done = ondone;
      await app.load(true);
      done(r.renamed ?? names);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      working = false;
    }
  }
</script>

<div class="modal-bg" role="presentation" onclick={() => !working && onclose()}>
  <div class="modal" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && !working && onclose()}>
    <h3>Rename from {file}</h3>
    {#if !check && !error}
      <p class="muted">Checking the names…</p>
    {:else if check}
      {#if check.error}
        <div class="banner danger"><span class="ic"><I.Problem /></span><div>{check.error}</div></div>
      {:else if !n}
        <div class="banner info"><span class="ic"><I.Info /></span><div>No names to change: fill in <code>new_name</code> for the glyphs to rename (an empty cell, or the same name, leaves a glyph as it is).</div></div>
      {:else}
        {#if bad}
          <div class="banner danger"><span class="ic"><I.Problem /></span><div>{plural(bad, 'row')} can't be renamed as written. Fix {bad === 1 ? 'it' : 'them'} in the file and choose it again; nothing has changed.</div></div>
        {:else if check.problems.length}
          <div class="banner danger"><span class="ic"><I.Problem /></span><div>{check.problems[0]}</div></div>
        {/if}
        <p class="small">{plural(n, 'glyph')} to rename, all at once. Each keeps its drawing, spellings, areas, spacing rows and character code; drafts and Change Requests that use the old names are read with the new ones.</p>
        <div class="list">
          <table class="small">
            <thead><tr><th></th><th>Now</th><th></th><th>New name</th><th></th></tr></thead>
            <tbody>
              {#each [...check.pairs].sort((a, b) => +!!b.problem - +!!a.problem) as p (p.from)}
                <tr class:bad={p.problem}>
                  <td>{#if app.svgs[p.from]}<Glyph name={p.from} size={20} />{/if}</td>
                  <td class="mono">{p.from}</td><td><I.Gives size={12} /></td><td class="mono">{p.to}</td>
                  <td>{#if p.problem}<span class="err"><I.Problem size={12} /> {p.problem}</span>{/if}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if waitFor}<div class="banner draft"><span class="ic"><I.Unsaved /></span><div>{waitFor}</div></div>{/if}
      {/if}
    {/if}
    {#if error}
      <div class="banner danger" role="alert"><span class="ic"><I.Problem /></span>
        <div>{error}{#if conflict} Load the files again, then choose the file once more.{/if}</div>
        {#if conflict}<button class="sm" onclick={async () => { await app.load(true); onclose(); }}>Load again</button>{/if}
      </div>
    {/if}
    <div class="row">
      <span class="spacer"></span>
      <button class="quiet" onclick={onclose} disabled={working}>Cancel</button>
      {#if check?.ok && n}
        <button class="primary" disabled={working || !!waitFor} onclick={go}>{working ? 'Renaming…' : `Rename ${plural(n, 'glyph')}`}</button>
      {/if}
    </div>
  </div>
</div>

<style>
  .modal { padding: var(--space-6); width: min(720px, 94vw); max-height: 90vh; display: flex; flex-direction: column; gap: var(--space-4); }
  .modal h3, .modal p { margin: 0; }
  .list { overflow: auto; min-height: 0; flex: 1; border: 1px solid var(--border); border-radius: var(--radius-md); }
  table { width: 100%; border-collapse: collapse; }
  th { position: sticky; top: 0; background: var(--bg-panel); text-align: left; font-weight: normal; color: var(--ink-muted); }
  th, td { padding: var(--space-2) var(--space-4); border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr.bad td { background: var(--status-danger-bg); }
  .mono { font-family: var(--font-mono); }
  .err { color: var(--status-danger); }
  .row { display: flex; align-items: center; gap: var(--space-4); }
  .spacer { flex: 1; }
</style>
