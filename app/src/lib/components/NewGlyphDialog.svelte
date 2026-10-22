<script lang="ts">
  // New glyph: a name, an area (gives the box), and how to start. Opens the editor.
  import { goto } from '$app/navigation';
  import { app } from '$lib/state.svelte';
  import { glyphEditor } from '$lib/glyphed/editor.svelte';
  import { current } from '$lib/renames';
  let { onclose, initialArea = '' }: { onclose: () => void; initialArea?: string } = $props();
  let name = $state('');
  let area = $state(initialArea);
  let start = $state<'blank' | 'svg' | 'image'>('blank');
  let file = $state<File | null>(null);
  const NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
  let taken = $derived(app.glyphs.find((g) => g.glyph.toLowerCase() === name.trim().toLowerCase())?.glyph ?? null);
  let problem = $derived.by(() => {
    const n = name.trim();
    if (!n) return 'Give the glyph a name, e.g. md_9 or lg_gou.';
    if (!NAME.test(n) || n.endsWith('.')) return 'Letters, digits, _ - and . only.';
    if (taken) return `${taken} already exists.`;
    if (current(n) !== n) return `${n} was the name of ${current(n)} before a rename; pick another name.`;
    if (start !== 'blank' && !file) return start === 'svg' ? 'Choose an SVG file.' : 'Choose an image file.';
    return null;
  });
  let box = $derived(area && app.design?.areas[area] ? app.design.areas[area].size : [350, 350]);
  function create() {
    if (problem) return;
    glyphEditor.pendingStart = start === 'blank' ? null : { kind: start, file: file! };
    onclose();
    goto(`/glyphs/new?name=${encodeURIComponent(name.trim())}${area ? `&area=${encodeURIComponent(area)}` : ''}`);
  }
</script>

<div class="modal-bg" role="presentation" onclick={onclose}>
  <div class="modal" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => { if (e.key === 'Escape') onclose(); if (e.key === 'Enter' && !problem) create(); }}>
    <h3 style="margin:0">New glyph</h3>
    <label class="f"><span>Name</span><input type="text" bind:value={name} placeholder="md_9" style="font-family: var(--font-mono); width: 200px" /></label>
    {#if taken}<div class="muted small">Names are not reused. <a href="/glyphs/{encodeURIComponent(taken)}/edit" onclick={onclose}>Open {taken}</a> instead?</div>{/if}
    <label class="f"><span>Area</span>
      <select bind:value={area}>
        <option value="">No area yet (350 × 350)</option>
        {#each Object.keys(app.design?.areas ?? {}) as a}<option value={a}>{app.areaLabel(a)} ({a}) · {app.design!.areas[a].size.join(' × ')}</option>{/each}
      </select>
      <span class="muted small">box {box[0]} × {box[1]} units; joined on the first save</span>
    </label>
    <div class="f"><span>Start from</span>
      <div class="starts">
        <label><input type="radio" bind:group={start} value="blank" /> Blank</label>
        <label><input type="radio" bind:group={start} value="svg" /> SVG file</label>
        <label><input type="radio" bind:group={start} value="image" /> Image to trace</label>
      </div>
    </div>
    {#if start !== 'blank'}
      <label class="f"><span>File</span><input type="file" accept={start === 'svg' ? '.svg,image/svg+xml' : 'image/png,image/jpeg,image/webp,image/gif'} onchange={(e) => (file = (e.target as HTMLInputElement).files?.[0] ?? null)} /></label>
    {/if}
    <div class="row">
      <span class="muted small">{problem ?? ''}</span><span class="spacer"></span>
      <button onclick={onclose}>Cancel</button>
      <button class="primary" disabled={!!problem} onclick={create}>Open editor</button>
    </div>
  </div>
</div>

<style>
  .spacer { flex: 1; }
  .small { font-size: var(--t-caption); }

  .modal { padding: var(--space-6); width: min(520px, 92vw); display: flex; flex-direction: column; gap: var(--space-5); }
  .f { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .f > span:first-child { width: 80px; color: var(--ink-muted); }
  .starts { display: flex; gap: var(--space-5); }
</style>
