<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import { app } from '$lib/state.svelte';
  import ImportExport from '$lib/components/ImportExport.svelte';
  import { editor } from '$lib/editor.svelte';
  import { panels } from '$lib/panels.svelte';
  let { children } = $props();
  let menu = $state(false);
  let dialog = $state<'import' | 'export' | null>(null);
  let showChanges = $state(false);

  const nav = [
    ['/glyphs', 'Glyphs'],
    ['/areas', 'Areas'],
    ['/layouts', 'Layouts'],
    ['/test', 'Test & Build'],
    ['/tester', 'Tester']
  ];

  onMount(() => {
    app.load();
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (/^\/glyphs\/(new$|[^/]+\/edit)/.test(location.pathname)) return;   // the glyph editor handles ⌘S / ⌘Z itself
      if (e.key === 's') { e.preventDefault(); app.save(); }
      else if (e.key === 'z') {
        const t = e.target as HTMLElement;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
        e.preventDefault();
        if (e.shiftKey) app.redo(); else app.undo();
      }
    };
    window.addEventListener('keydown', onKey);
    const onClick = () => (menu = false);
    window.addEventListener('click', onClick);
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('click', onClick); };
  });

  // on the glyph editor routes the glyph owns undo and ⌘S; the header keeps only the design's Save
  let inGlyphEditor = $derived(/^\/glyphs\/(new$|[^/]+\/edit)/.test(page.url.pathname));
  let budget = $derived.by(() => {
    const s = app.stats;
    if (!s) return null;
    const kb = s.est_bytes / 1024;
    return { kb, rules: s.rules, skipped: s.skipped, level: s.skipped > 0 ? 'warn' : 'ok' };
  });
</script>

<div class="shell">
  <header>
    <div class="brand">JZP Font Builder</div>
    <nav>
      {#each nav as [href, label]}
        <a {href} class:active={page.url.pathname === href || page.url.pathname.startsWith(href + '/')}>{label}</a>
      {/each}
    </nav>
    <div class="spacer"></div>
    {#if page.url.pathname.startsWith('/layouts')}
      <label class="adv" title="Structural edits: add, remove, reorder parts; new / delete word types; recognition rules"><input type="checkbox" bind:checked={editor.advanced} /> Advanced</label>
    {/if}
    {#if budget}
      <a class="chip" href="/layouts?budget=1" title="GPOS rules generated from this design">
        <span class="badge-{budget.level}">●</span> {budget.rules} rules · {budget.kb.toFixed(0)} KB
      </a>
    {/if}
    {#if !inGlyphEditor}
      <button class="ghost" onclick={() => app.undo()} disabled={app.undoStack.length === 0}
        title={app.undoStack.length ? `Undo: ${app.undoStack.at(-1)?.label}` : 'Nothing to undo'}>↶</button>
      <button class="ghost" onclick={() => app.redo()} disabled={app.redoStack.length === 0}
        title={app.redoStack.length ? `Redo: ${app.redoStack.at(-1)?.label}` : 'Nothing to redo'}>↷</button>
    {/if}
    <span class="status" role="status">
      {#if app.dirty}
        <button class="chip accent" onclick={(e) => { e.stopPropagation(); showChanges = !showChanges; }}>● {inGlyphEditor ? 'Design: ' : ''}{app.changes.length} unsaved</button>
      {:else if app.lastSaved}
        <span class="chip">{inGlyphEditor ? 'Design: saved' : `Saved ${app.lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}</span>
      {:else if !app.loading}
        <span class="chip">{inGlyphEditor ? 'Design: saved' : 'Saved'}</span>
      {/if}
    </span>
    <button class="primary" onclick={() => app.save()} disabled={!app.dirty || app.saving} title={inGlyphEditor ? 'Write design.json (the glyph has its own Save, ⌘S)' : 'Write design.json (⌘S)'}>
      {app.saving ? 'Saving…' : inGlyphEditor ? 'Save design' : 'Save'}
    </button>
    <span class="menu-wrap">
      <button onclick={(e) => { e.stopPropagation(); menu = !menu; }} aria-label="More">⋯</button>
      {#if menu}
        <div class="menu" role="menu">
          <button onclick={() => (dialog = 'import')}>Import…</button>
          <button onclick={() => (dialog = 'export')}>Export…</button>
          <button onclick={() => app.reloadFromDisk()}>Reload from disk</button>
          <button onclick={() => app.discard()} disabled={!app.dirty}>Discard unsaved changes</button>
          <hr />
          <button onclick={() => panels.reset()} disabled={panels.isDefault} title="Put the Layouts panels back where they started">Reset panel layout</button>
        </div>
      {/if}
    </span>
  </header>

  {#if showChanges && app.dirty}
    <div class="changes">
      <strong>Unsaved changes</strong>
      <ol>{#each app.changes as c}<li>{c}</li>{/each}</ol>
      <button onclick={() => { app.discard(); showChanges = false; }}>Discard all</button>
    </div>
  {/if}
  {#if app.draftRestored}
    <div class="banner">
      Restored unsaved changes from your last session.
      <button onclick={() => (app.draftRestored = false)}>Keep</button>
      <button onclick={() => { app.discard(); app.draftRestored = false; }}>Discard</button>
    </div>
  {/if}
  {#if app.error}
    <div class="banner error">{app.error} <button onclick={() => app.load()}>Retry</button></div>
  {/if}
  {#if app.conflict}
    <div class="modal-bg">
      <div class="modal">
        <h3>design.json changed on disk</h3>
        <p>{app.conflict}</p>
        <div class="row">
          <button onclick={() => { app.conflict = null; app.reloadFromDisk(); }}>Reload from disk (lose my {app.changes.length} changes)</button>
          <button class="primary" onclick={() => app.save(true)}>Overwrite</button>
          <button onclick={() => { app.conflict = null; dialog = 'export'; }}>Export mine first</button>
        </div>
      </div>
    </div>
  {/if}

  <main>
    {#if app.loading}
      <p class="muted" style="padding: var(--s-6)">Loading design…</p>
    {:else if app.design}
      {@render children()}
    {/if}
  </main>

  {#if dialog}
    <ImportExport mode={dialog} onclose={() => (dialog = null)} />
  {/if}
</div>

<style>
  .shell { display: flex; flex-direction: column; height: 100vh; }
  header { display: flex; align-items: center; gap: var(--s-2); height: 44px; padding: 0 var(--s-4); border-bottom: 1px solid var(--line); background: var(--bg-2); }
  .brand { font-weight: 600; margin-right: var(--s-4); }
  nav { display: flex; gap: var(--s-1); }
  nav a { padding: 4px 10px; border-radius: var(--radius); color: var(--fg); text-decoration: none; }
  nav a.active { background: var(--accent-bg); color: var(--accent); }
  .spacer { flex: 1; }
  .ghost { border-color: transparent; background: transparent; }
  .menu-wrap { position: relative; }
  .menu { position: absolute; right: 0; top: 100%; z-index: 30; margin-top: 4px; min-width: 220px; display: flex; flex-direction: column; background: var(--bg); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: 0 8px 24px rgba(0,0,0,.18); padding: 4px; }
  .menu button { text-align: left; border: 0; background: transparent; }
  .menu button:hover:not(:disabled) { background: var(--bg-3); }
  .menu hr { border: 0; border-top: 1px solid var(--line); margin: 3px 0; }
  .adv { display: inline-flex; align-items: center; gap: 4px; font-size: var(--t-sm); color: var(--fg-2); margin-right: var(--s-2); }
  .changes, .banner { padding: var(--s-2) var(--s-4); border-bottom: 1px solid var(--line); background: var(--bg-2); display: flex; gap: var(--s-3); align-items: center; }
  .changes ol { margin: 0; padding-left: 20px; max-height: 120px; overflow: auto; flex: 1; }
  .banner.error { color: var(--danger); }
  main { flex: 1; min-height: 0; overflow: auto; }
  .modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 50; }
  .modal { background: var(--bg); border-radius: var(--radius); padding: var(--s-5); max-width: 560px; }
  .chip { text-decoration: none; color: inherit; border: 0; }
</style>
