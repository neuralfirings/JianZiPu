<script lang="ts">
  // Rename… and Delete… for one glyph (the Builder on your own computer only): the server changes
  // every place that names it at once (PUT /api/glyph/<name>/rename, DELETE /api/glyph/<name>,
  // glyph_edit.py) and keeps character codes stable (glyph_ids.json). Unsaved edits have to be
  // saved or discarded first, because the files are rewritten and the app loads them again.
  import { api, type GlyphUses } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { current } from '$lib/renames';
  import * as I from '$lib/icons';

  let { glyph, busy = null, onrenamed, ondeleted }: {
    glyph: string;
    /** Why it can't be done right now (unsaved edits to the outline in the editor), or null. */
    busy?: string | null;
    onrenamed?: (to: string) => void;
    ondeleted?: () => void;
  } = $props();

  const NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
  let mode = $state<null | 'rename' | 'delete'>(null);
  let uses = $state<GlyphUses | null>(null);
  let to = $state('');
  let working = $state(false);
  let error = $state<string | null>(null);
  let conflict = $state(false);

  let waitFor = $derived(busy ?? (app.dirty ? 'Save or discard your unsaved changes first: this rewrites the saved files.' : null));
  let problem = $derived.by(() => {
    const n = to.trim();
    if (!n) return 'Give it a new name.';
    if (n === glyph) return 'That is already its name.';
    if (!NAME.test(n) || n.endsWith('.')) return 'Letters, digits, _ - and . only.';
    if (app.known.has(n) || app.control.includes(n)) return `${n} is already a glyph.`;
    if (current(n) !== n && current(n) !== glyph) return `${n} was the name of a glyph before a rename; drafts may still use it for that glyph.`;
    return null;
  });
  const code = (c: string | null) => (c ? `U+${c}` : 'its next free code');
  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;

  async function open(m: 'rename' | 'delete') {
    mode = m; uses = null; error = null; conflict = false; to = glyph;
    const r = await api.glyphUses(glyph).catch((e: Error) => ({ ok: false, error: e.message }) as GlyphUses & { ok: boolean; error?: string });
    if (!r.ok) error = r.error ?? 'Could not read where the glyph is used.';
    else uses = r;
  }
  function close() { if (!working) mode = null; }

  async function go() {
    if (!uses || waitFor || (mode === 'rename' && problem)) return;
    working = true; error = null; conflict = false;
    try {
      const r = mode === 'rename'
        ? await api.renameGlyph(glyph, to.trim(), app.diskHash, app.csvHash)
        : await api.deleteGlyph(glyph, app.diskHash, app.csvHash);
      if (!r.ok) { error = r.error ?? 'It did not work.'; conflict = !!r.conflict; return; }
      const was = mode, name = to.trim(), renamed = onrenamed, deleted = ondeleted;
      mode = null;
      await app.load(true);
      if (was === 'rename') renamed?.(name); else deleted?.();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      working = false;
    }
  }
</script>

<div class="row">
  <span class="k">Name</span><span class="mono">{glyph}</span>
  <button class="sm quiet" onclick={() => open('rename')}>Rename…</button>
  <button class="sm quiet" onclick={() => open('delete')}>Delete…</button>
</div>

{#if mode}
  <div class="modal-bg" role="presentation" onclick={close}>
    <div class="modal" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => { if (e.key === 'Escape') close(); if (e.key === 'Enter' && mode === 'rename') void go(); }}>
      <h3>{mode === 'rename' ? `Rename ${glyph}` : `Delete ${glyph}?`}</h3>
      {#if !uses && !error}
        <p class="muted">Looking up where {glyph} is used…</p>
      {:else if uses?.locked}
        <div class="banner danger"><span class="ic"><I.Problem /></span><div>{uses.locked}</div></div>
      {:else if uses}
        {#if mode === 'rename'}
          <label class="f"><span>New name</span><input type="text" class="mono" bind:value={to} style="width: 220px" /></label>
          {#if problem && to.trim() !== glyph}<p class="small error">{problem}</p>{/if}
        {/if}
        <div>
          <p class="small">{mode === 'rename' ? 'Changes, all at once:' : 'Removes, all at once:'}</p>
          <ul class="small">
            <li>the file inputs/svg/{glyph}.svg{#if mode === 'rename'}{' '}(becomes {to.trim() || '…'}.svg){/if}</li>
            {#if uses.spelling}<li>its spellings in components.csv</li>{/if}
            {#if uses.vertical_of.length}<li>{mode === 'rename' ? 'the vertical-form link' : 'the vertical form of'} {uses.vertical_of.join(', ')}</li>{/if}
            {#if uses.areas.length}<li>{mode === 'rename' ? 'its place in' : 'it from'} {uses.areas.map((a) => app.areaLabel(a)).join(', ')}</li>{/if}
            {#if uses.spacing_rows}<li>{plural(uses.spacing_rows, 'spacing row')} that name it{#if mode === 'delete'}{#if uses.spacing_rows_only}; {uses.spacing_rows_only} of them only apply to it and go{/if}{/if}</li>{/if}
            {#if uses.edge_cases && mode === 'rename'}<li>inputs/edge_cases.fea</li>{/if}
          </ul>
        </div>
        {#if mode === 'rename'}
          <p class="small muted">It keeps its character code, {code(uses.code)}. Drafts and Change Requests that still say {glyph} are read with the new name when they're opened, so {glyph} can't name another glyph later.</p>
        {:else}
          <p class="small muted">Its character code, {code(uses.code)}, is retired and never given to another glyph. Text that holds this glyph itself, rather than its spelling, will show a missing glyph. There's no undo: git has the files.</p>
        {/if}
        <p class="small muted">Best done last in a release, once the kept changes are in. Commit the files it changes, glyph_ids.json included.</p>
        {#if waitFor}<div class="banner draft"><span class="ic"><I.Unsaved /></span><div>{waitFor}</div></div>{/if}
      {/if}
      {#if error}
        <div class="banner danger" role="alert"><span class="ic"><I.Problem /></span>
          <div>{error}{#if conflict} Load the files again, then try once more.{/if}</div>
          {#if conflict}<button class="sm" onclick={async () => { await app.load(true); mode = null; }}>Load again</button>{/if}
        </div>
      {/if}
      <div class="row">
        <span class="spacer"></span>
        <button class="quiet" onclick={close} disabled={working}>Cancel</button>
        {#if uses && !uses.locked}
          {#if mode === 'rename'}
            <button class="primary" disabled={working || !!problem || !!waitFor} onclick={go}>{working ? 'Renaming…' : 'Rename'}</button>
          {:else}
            <button class="danger" disabled={working || !!waitFor} onclick={go}>{working ? 'Deleting…' : 'Delete glyph'}</button>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .row { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
  .k { display: inline-block; width: 70px; color: var(--ink-muted); }
  .mono { font-family: var(--font-mono); }
  .modal { padding: var(--space-6); width: min(520px, 92vw); display: flex; flex-direction: column; gap: var(--space-4); text-align: left; }
  .modal h3 { margin: 0; }
  .modal p { margin: 0; }
  .modal ul { margin: var(--space-2) 0 0; padding-left: var(--space-6); }
  .f { display: flex; align-items: center; gap: var(--space-4); }
  .spacer { flex: 1; }
</style>
