<script lang="ts">
  // One spelling field of one glyph, edited in place. Checked as you type in a line under the
  // field; Enter (or leaving the field) saves it as one undo step; Esc puts the old value back.
  // A vertical form shows its partner's spelling greyed out as the placeholder. The Glossary field
  // is a picker instead: every section on the font page, one or two ticked (a browser's own
  // suggestion list showed only the sections matching what the cell already held).
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';
  let {
    glyph, field, cell = false, onenter, onpastegrid
  }: {
    glyph: string; field: T.SpellField; cell?: boolean;
    onenter?: (dir: 1 | -1) => void;
    onpastegrid?: (grid: string[][]) => void;
  } = $props();

  let own = $derived(T.get(app.typing, glyph)[field]);
  let inherited = $derived(T.shown(app.typing, glyph, field).inherited);
  // a Latin Entry suggestion from the PinYin, only when the glyph has no Latin or number spelling yet, and only if free
  let suggestion = $derived.by(() => {
    const sp = T.get(app.typing, glyph);
    if (field !== 'latin' || own || inherited || sp.latin_alt || sp.common || T.partners(app.typing)[glyph]) return '';
    const c = T.pinyinToLatin(T.get(app.typing, glyph).pinyin);
    return c && T.cellNote(app.typing, glyph, 'latin', c)?.level === 'free' ? c : '';
  });
  let placeholder = $derived(inherited ? T.shown(app.typing, glyph, field).value : suggestion);
  let draft = $state<string | null>(null);
  let focused = $state(false);
  let note = $derived(focused && draft !== null ? T.cellNote(app.typing, glyph, field, draft, app.known, (g) => app.charOf(g), app.glossarySections.map((s) => s.title)) : null);
  let bad = $derived(app.typingErrors.some((e) => (e.kind === 'clash' ? e.fields.some((f) => f.glyph === glyph && f.field === field) : e.glyph === glyph && e.field === field)));
  let changed = $derived(T.get(app.savedTyping, glyph)[field] !== own);
  let zh = $derived(field === 'simplified' || field === 'traditional');
  /** In a sent Change Request: shown, not editable. */
  let locked = $derived(!!app.lockOf(`spelling:${glyph}`));
  let input = $state<HTMLInputElement>() as HTMLInputElement;

  function commit() {
    if (draft === null) return;
    const v = draft;
    draft = null;
    app.setSpelling(glyph, field, v);
  }
  function onkeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); draft = input.value; commit(); onenter?.(e.shiftKey ? -1 : 1); }
    else if (e.key === 'Escape') { e.preventDefault(); draft = null; input.value = own; input.blur(); }
    else if (e.key === 'Tab' && !e.shiftKey && !input.value && suggestion) { e.preventDefault(); input.value = suggestion; draft = suggestion; }
  }
  // ---- the Glossary picker
  let open = $state(false);
  let pickBtn = $state<HTMLButtonElement>();
  /** Where the menu goes: under the cell, or over it when there's more room above, never past the
   *  window's edge (it scrolls instead). Fixed to the window, so a panel's edge doesn't cut it off. */
  let place = $state('');
  function reposition() {
    const r = pickBtn?.getBoundingClientRect();
    if (!r || r.bottom < 0 || r.top > window.innerHeight) { open = false; return; }   // scrolled out of sight
    const below = window.innerHeight - r.bottom - 8, above = r.top - 8;
    const down = below >= 220 || below >= above;
    const h = Math.max(120, Math.min(360, down ? below : above));
    const left = Math.max(8, Math.min(r.left, window.innerWidth - 320 - 8));
    place = `left:${left}px;max-height:${h}px;` + (down ? `top:${r.bottom + 2}px` : `bottom:${window.innerHeight - r.top + 2}px`);
  }
  function openClose() {
    if (open) { open = false; return; }
    open = true;
    reposition();
  }
  let picker = $state<HTMLElement>();
  let chosen = $derived(own.split(';').map((x) => x.trim()).filter(Boolean));
  let sections = $derived(app.glossarySections.map((s) => s.title));
  let unknown = $derived(chosen.filter((c) => !sections.includes(c)));
  function toggle(title: string) {
    const next = chosen.includes(title) ? chosen.filter((c) => c !== title) : [...chosen, title];
    // in the font page's order, a section the page doesn't have (a warning) kept at the end
    const ordered = [...sections.filter((s) => next.includes(s)), ...next.filter((c) => !sections.includes(c))];
    app.setSpelling(glyph, 'glossary', ordered.join('; '));
  }
  $effect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => { if (picker && !picker.contains(e.target as Node)) open = false; };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') open = false; };
    // the page scrolled or resized under it: follow the cell (closed once the cell is out of sight)
    const shut = (e: Event) => { if (!picker?.contains(e.target as Node)) reposition(); };
    window.addEventListener('scroll', shut, true);
    window.addEventListener('resize', shut);
    window.addEventListener('pointerdown', away, true);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('pointerdown', away, true); window.removeEventListener('keydown', esc);
      window.removeEventListener('scroll', shut, true); window.removeEventListener('resize', shut);
    };
  });

  function onpaste(e: ClipboardEvent) {
    const text = e.clipboardData?.getData('text/plain') ?? '';
    if (onpastegrid && /[\t\n]/.test(text.replace(/\n$/, ''))) { e.preventDefault(); onpastegrid(T.parseGrid(text)); }
  }
</script>

<span class="si" class:cell>
  {#if field === 'common'}
    <span class="ro" title={T.HELP.common}>{own}</span>
  {:else if field === 'glossary'}
    <span class="gp" bind:this={picker}>
      <button type="button" class="pick" bind:this={pickBtn} class:changed class:warn={unknown.length > 0} disabled={locked} aria-haspopup="listbox" aria-expanded={open}
        data-tip={locked ? app.lockMessage(`spelling:${glyph}`) : undefined} title={locked || open ? undefined : T.HELP.glossary}
        onclick={openClose}>
        <span class="val">{#if chosen.length}{chosen.join('; ')}{:else}<span class="muted">none</span>{/if}</span>
        <I.Unfolded size={12} />
      </button>
      {#if open}
        <div class="float menu" style={place} role="listbox" aria-multiselectable="true" aria-label="Glossary sections">
          <button type="button" role="option" aria-selected={!chosen.length} onclick={() => { app.setSpelling(glyph, 'glossary', ''); open = false; }}>
            <span class="tick">{#if !chosen.length}<I.Check size={14} />{/if}</span>None (no row of its own)</button>
          {#each sections as s (s)}
            <button type="button" role="option" aria-selected={chosen.includes(s)} onclick={() => toggle(s)}>
              <span class="tick">{#if chosen.includes(s)}<I.Check size={14} />{/if}</span>{s}</button>
          {/each}
          {#each unknown as s (s)}
            <button type="button" role="option" aria-selected="true" class="bad" onclick={() => toggle(s)} title="The font page has no such section: click to take it off">
              <span class="tick"><I.Warn size={14} /></span>{s}</button>
          {/each}
          {#if !sections.length}<p class="muted small">This Builder has no font page to read the sections from.</p>{/if}
        </div>
      {/if}
    </span>
  {:else}
    <input bind:this={input} type="text" value={own} {placeholder} class:zh class:bad class:changed class:inh={!!inherited && !own}
      readonly={locked} data-tip={locked ? app.lockMessage(`spelling:${glyph}`) : undefined}
      list={field === 'vert_variant' ? 'jzp-glyph-names' : undefined}
      title={inherited && !own ? `${T.LABEL[field]} of ${inherited}, its partner: typed after a colon` : T.HELP[field]}
      onfocus={() => { focused = true; draft = own; }}
      onblur={() => { focused = false; if (!locked) commit(); }}
      oninput={(e) => (draft = (e.target as HTMLInputElement).value)}
      {onkeydown} {onpaste} spellcheck="false" autocomplete="off" />
    {#if note && (note.level !== 'free' || (draft !== own && draft))}
      <span class="note {note?.level}" role="status">{#if note?.level === 'error'}<I.Problem size={12} /> {:else if note?.level === 'shared'}<I.Pair size={12} /> {:else if note?.level === 'free'}<I.Check size={12} /> {:else if note?.level === 'warn'}<I.Warn size={12} /> {/if}{note?.text}{#if note?.level === 'error'}<span class="muted"> · Enter keeps it; Save waits until it's fixed</span>{/if}</span>
    {/if}
  {/if}
</span>

<style>
  .si { position: relative; display: inline-block; width: 100%; }
  input { width: 100%; min-width: 0; height: 26px; font-family: var(--font-mono); font-size: var(--t-small); }
  input.zh { font-family: var(--font-serif); font-size: 15px; }
  .cell input { border-color: transparent; background: transparent; border-radius: 3px; }
  .cell input:hover { border-color: var(--border); }
  .cell input:focus { border-color: var(--link); background: var(--bg-field); }
  input.changed { background: color-mix(in srgb, var(--status-draft) 14%, transparent); }
  input.bad { border-color: var(--status-danger) !important; color: var(--status-danger); }
  input.inh::placeholder { color: var(--ink-muted); font-style: italic; }
  .ro { display: inline-block; padding: 0 6px; font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-muted); border-bottom: 1px dotted var(--border); }
  .note { position: absolute; left: 0; top: 100%; z-index: 20; margin-top: 2px; white-space: nowrap; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 4px; padding: 2px 8px; font-size: var(--t-caption); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
  .note.error { border-color: var(--status-danger); color: var(--status-danger); }
  .note.shared { color: var(--link); }
  .note.free { color: var(--status-saved); }
  .note.warn { border-color: var(--status-draft); }
  .note.warn :global(svg) { color: var(--status-draft); }
  .gp { position: relative; display: block; }
  .pick { display: flex; align-items: center; gap: var(--space-1); width: 100%; height: 26px; padding: 0 6px; font-family: var(--font-mono); font-size: var(--t-small); text-align: left; }
  .cell .pick { border-color: transparent; background: transparent; }
  .cell .pick:hover { border-color: var(--border); }
  .pick .val { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pick.changed { background: color-mix(in srgb, var(--status-draft) 14%, transparent); }
  .pick.warn { border-color: var(--status-draft); }
  .menu { position: fixed; z-index: 60; min-width: 280px; max-width: 320px; overflow: auto; display: flex; flex-direction: column; padding: var(--space-1); }
  .menu button { display: flex; align-items: center; justify-content: flex-start; gap: var(--space-2); border: 0; background: transparent; text-align: left; padding: var(--space-1) var(--space-2); white-space: nowrap; font-size: var(--t-small); }
  .menu button:hover { background: var(--sel-bg); }
  .menu .tick { width: 14px; display: inline-flex; }
  .menu .bad { color: var(--status-draft); }
</style>
