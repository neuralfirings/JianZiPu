<script lang="ts">
  // The Glossary cell: a button showing the section(s), and a menu of every section on the font
  // page to tick (one or two, or None). Fixed to the window: it opens under the cell, or over it when
  // there's more room above, and follows the cell when the page scrolls. Spellings (SpellInput) and
  // the glossary's words (Glyphs > Words) use it.
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  let { value, onchange, cell = false, changed = false, locked = false, lockTip, tip }: {
    value: string; onchange: (v: string) => void; cell?: boolean; changed?: boolean; locked?: boolean; lockTip?: string; tip?: string;
  } = $props();
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
  let chosen = $derived(value.split(';').map((x) => x.trim()).filter(Boolean));
  let sections = $derived(app.glossarySections.map((s) => s.title));
  let unknown = $derived(chosen.filter((c) => !sections.includes(c)));
  function toggle(title: string) {
    const next = chosen.includes(title) ? chosen.filter((c) => c !== title) : [...chosen, title];
    // in the font page's order, a section the page doesn't have (a warning) kept at the end
    const ordered = [...sections.filter((s) => next.includes(s)), ...next.filter((c) => !sections.includes(c))];
    onchange(ordered.join('; '));
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

</script>

    <span class="gp" class:cell bind:this={picker}>
      <button type="button" class="pick" bind:this={pickBtn} class:changed class:warn={unknown.length > 0} disabled={locked} aria-haspopup="listbox" aria-expanded={open}
        data-tip={locked ? lockTip : undefined} title={locked || open ? undefined : tip}
        onclick={openClose}>
        <span class="val">{#if chosen.length}{chosen.join('; ')}{:else}<span class="muted">none</span>{/if}</span>
        <I.Unfolded size={12} />
      </button>
      {#if open}
        <div class="float menu" style={place} role="listbox" aria-multiselectable="true" aria-label="Glossary sections">
          <button type="button" role="option" aria-selected={!chosen.length} onclick={() => { onchange(''); open = false; }}>
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

<style>
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
