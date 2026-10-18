<script lang="ts">
  import { searchText } from '$lib/typing';
  // All glyphs of the selected part's area, under the canvas: click = preview glyph;
  // Manage = remove / add (edits the area, shared by every word type that uses it).
  import { app } from '$lib/state.svelte';
  import { editor } from '$lib/editor.svelte';
  import { elementLabel } from '$lib/shape';
  import Glyph from './Glyph.svelte';
  import AddGlyphsDialog from './AddGlyphsDialog.svelte';

  let el = $derived(editor.selected ? editor.elements.find((e) => e.name === editor.selected) ?? null : null);
  let area = $derived(el ? app.design!.areas[el.area] : null);
  let glyphs = $derived(area?.glyphs ?? []);
  let manage = $state(false);
  let q = $state('');
  let showAll = $state(false);
  let adding = $state(false);
  const LIMIT = 28;
  let sharedBy = $derived(el ? app.design!.layouts.filter((l) => l.slots.some((s) => s.alternatives.some((a) => a.some((t) => (t.includes(':') ? t.split(':')[1] : t) === el!.area)))).map((l) => l.label ?? l.name) : []);
  function matches(g: string) {
    if (!q) return true;
    return searchText(app.typing, g).includes(q.toLowerCase());
  }
  let filtered = $derived(glyphs.filter(matches));
  let shown = $derived(showAll || filtered.length <= LIMIT ? filtered : filtered.slice(0, LIMIT));
  function remove(g: string) {
    if (!el) return;
    if (app.removeFromArea(el.area, g)) editor.ensurePins();
  }
</script>

{#if el && area}
  <div class="tray" class:tall={showAll}>
    <div class="hd">
      <span class="muted meta" title="area {el.area}{sharedBy.length > 1 ? `, shared by ${sharedBy.join(', ')}` : ''}">({glyphs.length}) · area <span class="id">{el.area}</span>{#if sharedBy.length > 1} · shared by {sharedBy.join(', ')}{/if}</span>
      <span class="spacer"></span>
      {#if glyphs.length > LIMIT}<input type="text" placeholder="search name / key / pinyin" bind:value={q} style="width: 180px" />{/if}
      <label class="muted"><input type="checkbox" bind:checked={manage} /> Manage</label>
    </div>
    <div class="chips">
      {#each shown as g (g)}
        <button class="chip" class:on={editor.pinned[el.name] === g} title={g} onclick={() => editor.pin(el!.name, g)}>
          <Glyph name={g} size={30} />
          {#if manage}<span class="x" role="button" tabindex="-1" title="Remove from {el.area}" onclick={(e) => { e.stopPropagation(); remove(g); }} onkeydown={() => {}}>×</span>{/if}
        </button>
      {/each}
      {#if glyphs.length === 1}<span class="muted">preview fixed: this part has one glyph</span>{/if}
      {#if filtered.length > LIMIT}
        <button class="small" onclick={() => (showAll = !showAll)}>{showAll ? 'show less ▴' : `show all ${filtered.length} ▾`}</button>
      {/if}
      {#if manage}
        <button class="primary small" onclick={() => (adding = true)}>+ Add glyphs</button>
        <a href="/areas?area={el.area}&g={editor.pinned[el.name] ?? ''}" class="muted">Typing keys, box size → Areas</a>
      {/if}
    </div>
  </div>
  {#if adding}<AddGlyphsDialog area={el.area} onclose={() => { adding = false; editor.ensurePins(); }} />{/if}
{:else}
  <div class="tray muted">Click a part on the canvas to see its glyphs.</div>
{/if}

<style>
  .tray { display: flex; flex-direction: column; gap: 4px; }
  .hd { display: flex; align-items: center; gap: var(--s-2); font-size: var(--t-sm); }
  .nowrap { white-space: nowrap; }
  .meta { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex: 0 1 auto; }
  .spacer { flex: 1; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; max-height: 84px; overflow: hidden; }
  .tall .chips { max-height: 30vh; overflow: auto; }
  .chip { position: relative; height: 36px; width: 36px; padding: 2px; display: inline-flex; align-items: center; justify-content: center; background: var(--bg); }
  .chip.on { border-color: var(--accent); box-shadow: 0 0 0 1.5px var(--accent); }
  .x { position: absolute; top: -6px; right: -6px; width: 16px; height: 16px; border-radius: 50%; background: var(--bg); border: 1px solid var(--line); font-size: 11px; line-height: 13px; text-align: center; color: var(--fg-2); }
  .small { height: 24px; font-size: var(--t-sm); }
</style>
