<script lang="ts">
  // New glyph: a name, an area (gives the box), and how to start. Opens the editor. Or several
  // at once from SVG files (dropped on the dialog or chosen): each named after its file, made safe
  // (svg.ts sanitizeSvg) and checked the way the build reads it (/api/svg/check), then added
  // together as one undo step (app.addGlyphs).
  import { goto } from '$app/navigation';
  import { app } from '$lib/state.svelte';
  import { glyphEditor } from '$lib/glyphed/editor.svelte';
  import * as I from '$lib/icons';
  import { api } from '$lib/api';
  import { hosted } from '$lib/hosted.svelte';
  import { pilot } from '$lib/pilot.svelte';
  import { nameFromFile, renameProblem } from '$lib/rename';
  import { sanitizeSvg } from '$lib/svg';
  let { onclose, initialArea = '' }: { onclose: () => void; initialArea?: string } = $props();
  let name = $state('');
  let area = $state(initialArea);
  let start = $state<'blank' | 'svg' | 'image' | 'many'>('blank');
  let file = $state<File | null>(null);
  const NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
  let taken = $derived(app.glyphs.find((g) => g.glyph.toLowerCase() === name.trim().toLowerCase())?.glyph ?? null);
  let problem = $derived.by(() => {
    if (start === 'many') return batchProblem;
    const n = name.trim();
    if (!n) return 'Give the glyph a name, e.g. md_9 or lg_gou.';
    if (!NAME.test(n) || n.endsWith('.')) return 'Letters, digits, _ - and . only.';
    if (taken) return `${taken} already exists.`;
    if (start !== 'blank' && !file) return start === 'svg' ? 'Choose an SVG file.' : 'Choose an image file.';
    return null;
  });
  let box = $derived(area && app.design?.areas[area] ? app.design.areas[area].size : [350, 350]);
  // ---- several from SVG files
  type Item = { file: string; name: string; svg: string | null; state: 'checking' | 'ok' | 'bad'; note: string };
  let items = $state<Item[]>([]);
  let over = $state(false);
  let picker = $state<HTMLInputElement>();
  async function addFiles(list: FileList | File[] | null | undefined) {
    const files = [...(list ?? [])].filter((f) => /\.svg$/i.test(f.name) || f.type === 'image/svg+xml');
    if (!files.length) return;
    start = 'many';
    for (const f of files) {
      const it: Item = { file: f.name, name: nameFromFile(f.name), svg: null, state: 'checking', note: 'checking…' };
      items = [...items, it];
      const i = items.length - 1;
      let svg: string;
      try { svg = sanitizeSvg(await f.text()); } catch { items[i] = { ...it, state: 'bad', note: 'not an SVG' }; continue; }
      try {
        const r = await api.checkSvg(svg);
        items[i] = !r.ok ? { ...it, svg, state: 'bad', note: r.error ?? "the build can't read it" }
          : !r.contours ? { ...it, svg, state: 'bad', note: 'nothing to draw: no filled shapes' }
          : { ...it, svg, state: 'ok', note: `${r.contours} shape${r.contours === 1 ? '' : 's'}` };
      } catch (e) { items[i] = { ...it, svg, state: 'bad', note: (e as Error).message }; }
    }
  }
  const existing = $derived(new Set([...app.known, ...Object.keys(app.svgs), ...Object.keys(app.typing)]));
  /** Why one row can't be added: its file, or its name (taken, malformed, or twice in this list). */
  function rowProblem(i: number): string | null {
    const it = items[i];
    if (it.state !== 'ok') return it.state === 'checking' ? null : it.note;
    const twice = items.slice(0, i).find((o) => o.name.trim().toLowerCase() === it.name.trim().toLowerCase());
    if (twice) return `${twice.name} is in this list already.`;
    return renameProblem('', it.name, existing);
  }
  let batchProblem = $derived.by(() => {
    if (!items.length) return 'Drop SVG files here, or choose them.';
    if (items.some((it) => it.state === 'checking')) return 'Checking the files…';
    const bad = items.filter((_, i) => rowProblem(i)).length;
    return bad ? `${bad} to fix or take off the list.` : null;
  });
  function addAll() {
    if (batchProblem) return;
    const add = items.map((it) => ({ name: it.name.trim(), svg: it.svg! }));
    app.addGlyphs(add, area || null);
    onclose();
    const where = area ? ` to ${app.areaLabel(area)}` : '';
    pilot.say(`Added ${add.length} glyph${add.length === 1 ? '' : 's'}${where}.${hosted.isHosted ? '' : ' Their files are written when you Save.'}`, { undo: true });
  }
  function drop(e: DragEvent) {
    e.preventDefault(); over = false;
    void addFiles(e.dataTransfer?.files);
  }

  function create() {
    if (start === 'many') return addAll();
    if (problem) return;
    glyphEditor.pendingStart = start === 'blank' ? null : { kind: start, file: file! };
    onclose();
    goto(`/glyphs/new?name=${encodeURIComponent(name.trim())}${area ? `&area=${encodeURIComponent(area)}` : ''}`);
  }
</script>

<div class="modal-bg" role="presentation" onclick={onclose}>
  <div class="modal" class:over role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => { if (e.key === 'Escape') onclose(); if (e.key === 'Enter' && !problem && start !== 'many') create(); }}
    ondragover={(e) => { e.preventDefault(); over = true; }} ondragleave={(e) => { if (e.currentTarget === e.target) over = false; }} ondrop={drop}>
    <h3 style="margin:0">{start === 'many' ? 'New glyphs from SVG files' : 'New glyph'}</h3>
    {#if start !== 'many'}
      <label class="f"><span>Name</span><input type="text" bind:value={name} placeholder="md_9" style="font-family: var(--font-mono); width: 200px" /></label>
      {#if taken}<div class="muted small">Names are not reused. <a href="/glyphs/{encodeURIComponent(taken)}/edit" onclick={onclose}>Open {taken}</a> instead?</div>{/if}
    {/if}
    <label class="f"><span>Area</span>
      <select bind:value={area}>
        <option value="">No area yet (350 × 350)</option>
        {#each Object.keys(app.design?.areas ?? {}) as a}<option value={a}>{app.areaLabel(a)} ({a}) · {app.design!.areas[a].size.join(' × ')}</option>{/each}
      </select>
      <span class="muted small">box {box[0]} × {box[1]} units; {start === 'many' ? 'all of them join it' : 'joined on the first save'}</span>
    </label>
    <div class="f"><span>Start from</span>
      <div class="starts">
        <label><input type="radio" bind:group={start} value="blank" /> Blank</label>
        <label><input type="radio" bind:group={start} value="svg" /> SVG file</label>
        <label><input type="radio" bind:group={start} value="image" /> Image to trace</label>
        <label><input type="radio" bind:group={start} value="many" /> Several SVG files</label>
      </div>
    </div>
    {#if start === 'many'}
      <input type="file" accept=".svg,image/svg+xml" multiple hidden bind:this={picker} onchange={(e) => { void addFiles((e.target as HTMLInputElement).files); (e.target as HTMLInputElement).value = ''; }} />
      <div class="drop" class:over>
        <I.Upload size={18} />
        <span>Drop SVG files here, or <button class="link" onclick={() => picker?.click()}>choose files…</button></span>
        <span class="muted small">Each becomes a glyph named after its file; change a name below if you like.</span>
      </div>
      {#if items.length}
        <div class="list">
          {#each items as it, i (i)}
            {@const why = rowProblem(i)}
            <div class="item" class:bad={!!why}>
              <span class="st">{#if it.state === 'checking'}<I.Working size={14} />{:else if why}<I.Problem size={14} />{:else}<I.Check size={14} />{/if}</span>
              <input type="text" class="mono" bind:value={items[i].name} aria-label="Glyph name for {it.file}" spellcheck="false" />
              <span class="small muted file" title={it.file}>{it.file} · {it.note}</span>
              <button class="quiet x" onclick={() => (items = items.filter((_, j) => j !== i))} aria-label="Take {it.file} off the list" data-tip="Take it off the list"><I.Close size={14} /></button>
              {#if why && it.state === 'ok'}<span class="why small">{why}</span>{/if}
            </div>
          {/each}
        </div>
        <span class="muted small">{hosted.isHosted ? 'They go into your draft.' : 'Their files are written to builder/inputs/svg/ when you Save.'} One step: Undo takes them all back.</span>
      {/if}
    {:else if start !== 'blank'}
      <label class="f"><span>File</span><input type="file" accept={start === 'svg' ? '.svg,image/svg+xml' : 'image/png,image/jpeg,image/webp,image/gif'} onchange={(e) => (file = (e.target as HTMLInputElement).files?.[0] ?? null)} /></label>
    {/if}
    <div class="row">
      <span class="muted small">{problem ?? ''}</span><span class="spacer"></span>
      <button onclick={onclose}>Cancel</button>
      <button class="primary" disabled={!!problem} onclick={create}>{start === 'many' ? `Add ${items.length || ''} glyph${items.length === 1 ? '' : 's'}`.replace('  ', ' ') : 'Open editor'}</button>
    </div>
  </div>
</div>

<style>
  .spacer { flex: 1; }
  .small { font-size: var(--t-caption); }

  .modal { padding: var(--space-6); width: min(520px, 92vw); display: flex; flex-direction: column; gap: var(--space-5); }
  .f { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .f > span:first-child { width: 80px; color: var(--ink-muted); }
  .starts { display: flex; gap: var(--space-5); flex-wrap: wrap; }
  .modal.over { outline: 2px dashed var(--sel-border); outline-offset: -6px; }
  .drop { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-6); border: 1px dashed var(--border); border-radius: var(--radius-md); background: var(--bg-field); text-align: center; color: var(--ink-muted); }
  .drop.over { border-color: var(--sel-border); background: var(--sel-bg); color: var(--ink); }
  .drop .link { border: 0; background: transparent; padding: 0; height: auto; color: var(--link); text-decoration: underline; }
  .list { display: flex; flex-direction: column; gap: var(--space-2); max-height: 260px; overflow: auto; }
  .item { display: grid; grid-template-columns: 18px 160px 1fr auto; align-items: center; gap: var(--space-3); }
  .item .st { color: var(--status-saved); display: inline-flex; }
  .item.bad .st, .item .why { color: var(--status-danger); }
  .item .why { grid-column: 2 / -1; }
  .item .file { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .item .x { padding: 0 var(--space-2); }
</style>
