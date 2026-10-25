<script lang="ts">
  // Glyphs: every glyph, as Tiles (drawings) or Typing (a spelling table, components.csv).
  // The sidebar groups by design.json area (a glyph in several areas is in each); the 130
  // position decimals fold inside 徽 position. The bottom panel shows what the view doesn't:
  // in Tiles it edits the spellings; in Typing the row is the editor, so it shows Try it,
  // What changes and Issues. View, group, filter and selection live in the URL. On a phone the
  // sidebar is two selects and the selected glyph's card covers the tiles until closed.
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import { typingCheck } from '$lib/typingcheck.svelte';
  import * as T from '$lib/typing';
  import Glyph from '$lib/components/Glyph.svelte';
  import NewGlyphDialog from '$lib/components/NewGlyphDialog.svelte';
  import TypingTable, { type Section } from '$lib/components/TypingTable.svelte';
  import TypingCards from '$lib/components/TypingCards.svelte';
  import TypingFields from '$lib/components/TypingFields.svelte';
  import TryIt from '$lib/components/TryIt.svelte';
  import GlyphFacts from '$lib/components/GlyphFacts.svelte';
  import AddGlyphsDialog from '$lib/components/AddGlyphsDialog.svelte';
  import { usedIn } from '$lib/areas';
  import { page } from '$app/state';
  import { goto, replaceState } from '$app/navigation';
  import { DEFAULT_WEIGHT } from '$lib/glyphed/editor.svelte';
  import { phone } from '$lib/phone.svelte';

  type View = 'tiles' | 'typing';
  type Filter = '' | 'attention' | 'clashes' | 'nospell' | 'pairs' | 'unsaved';
  const params = page.url.searchParams;
  const storedView = (() => { try { return localStorage.getItem('jzp-glyphs-view'); } catch { return null; } })();
  let view = $state<View>((params.get('view') ?? storedView) === 'typing' ? 'typing' : 'tiles');
  let group = $state(params.get('group') ?? 'all');
  let filter = $state<Filter>((params.get('f') as Filter) ?? '');
  let selected = $state<string | null>(params.get('g'));
  let q = $state('');
  let newDialog = $state(false);
  let menu = $state(false);
  let showAreas = $state(false);
  let notice = $state<{ text: string; undo: boolean } | null>(null);
  let noticeTimer: ReturnType<typeof setTimeout> | null = null;
  let importing = $state<{ name: string; t: T.Typing } | null>(null);
  let importMode = $state<'replace' | 'fill'>('replace');
  let fileInput: HTMLInputElement;

  function say(text: string, undo = false) {
    notice = { text, undo };
    if (noticeTimer) clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => (notice = null), 6000);
  }

  // keep the URL and the remembered view in step
  $effect(() => {
    const u = new URL(page.url);
    const set = (k: string, v: string | null) => (v ? u.searchParams.set(k, v) : u.searchParams.delete(k));
    set('view', view === 'typing' ? 'typing' : null);
    set('group', group === 'all' ? null : group);
    set('f', filter || null);
    set('g', selected);
    if (u.search !== page.url.search) replaceState(u, {});
    try { localStorage.setItem('jzp-glyphs-view', view); } catch {}
  });
  // the server's spelling check follows every edit
  $effect(() => { JSON.stringify(app.typing); JSON.stringify(app.design?.areas); typingCheck.schedule(); });

  const editUrl = (g: string, from?: string) => `/glyphs/${encodeURIComponent(g)}/edit${from ? `?from=${from}` : ''}`;
  function setWeight(v: number) { if (v > 0) app.edit(`Reference stroke weight ${Math.round(v)}`, (d) => { d.glyph_weight = Math.round(v); }); }

  let d = $derived(app.design!);
  let addTo = $state<string | null>(null);
  let areaNames = $derived(Object.keys(d.areas));
  let all = $derived(app.glyphs.map((r) => r.glyph));
  let areasOf = $derived(Object.fromEntries(app.glyphs.map((r) => [r.glyph, areaNames.filter((a) => d.areas[a].glyphs.includes(r.glyph))])));
  let decimals = $derived(all.filter(T.isDecimal));
  let unassigned = $derived(all.filter((g) => !areasOf[g]?.length));
  let partnerOf = $derived(T.partners(app.typing));
  let control = $derived(new Set(app.control));

  // filters
  let errGlyphs = $derived(new Set(app.typingErrors.flatMap((e) => (e.kind === 'clash' ? e.glyphs : [e.glyph]))));
  let clashGlyphs = $derived(new Set(app.typingErrors.flatMap((e) => (e.kind === 'clash' ? e.glyphs : []))));
  let warnGlyphs = $derived(new Set([...typingCheck.roundtrip.map((r) => r.glyph), ...Object.keys(typingCheck.missing), ...typingCheck.notBuilt]));
  let unsaved = $derived(new Set(T.changedGlyphs(app.savedTyping, app.typing)));
  const FILTERS: [Filter, string, string][] = [
    ['attention', 'Needs attention', 'Clashes, malformed spellings, and spellings that type something else'],
    ['clashes', 'Clashes', 'A spelling claimed by two glyphs that aren\'t a vertical pair: Save waits'],
    ['nospell', 'No spellings yet', 'Glyphs in an area that can\'t be typed yet'],
    ['pairs', 'Vertical pairs', 'Glyphs with a vertical form, and the forms themselves'],
    ['unsaved', 'Unsaved', 'Spellings changed since the last Save']
  ];
  const matchFilter: Record<Exclude<Filter, ''>, (g: string) => boolean> = {
    attention: (g) => errGlyphs.has(g) || warnGlyphs.has(g),
    clashes: (g) => clashGlyphs.has(g),
    nospell: (g) => !!areasOf[g]?.length && !T.isDecimal(g) && !control.has(g) && !partnerOf[g] && !T.firstSpelling(app.typing, g),
    pairs: (g) => !!T.get(app.typing, g).vert_variant || !!partnerOf[g],
    unsaved: (g) => unsaved.has(g)
  };
  let filterCounts = $derived(Object.fromEntries(FILTERS.map(([f]) => [f, all.filter((g) => matchFilter[f as Exclude<Filter, ''>](g)).length])));

  let needle = $derived(q.trim().toLowerCase());
  const keep = (g: string) => (!filter || matchFilter[filter](g)) && (!needle || T.searchText(app.typing, g).includes(needle));

  /** The glyphs of the current group (decimals separate, so they can fold). */
  let groupGlyphs = $derived.by(() => {
    if (group === 'decimals') return { main: [] as string[], deci: decimals };
    const base = group === 'all' ? all : group === 'unassigned' ? unassigned : d.areas[group]?.glyphs ?? [];
    return { main: base.filter((g) => !T.isDecimal(g)), deci: base.filter(T.isDecimal) };
  });
  let searching = $derived(!!needle || !!filter);
  let tiles = $derived([...groupGlyphs.main.filter(keep), ...(searching || group === 'decimals' ? groupGlyphs.deci.filter(keep) : [])]);
  let foldedDecimals = $derived(!searching && group !== 'decimals' ? groupGlyphs.deci.length : 0);

  let sections = $derived.by((): Section[] => {
    if (searching) return [{ key: 'flat', title: '', glyphs: tiles }];
    if (group === 'decimals') return [{ key: 'deci', title: 'Position decimals', glyphs: decimals, decimals: true }];
    const out: Section[] = [];
    if (group === 'all') {
      const placed = new Set<string>();
      for (const a of areaNames) {
        const gs = d.areas[a].glyphs.filter((g) => !T.isDecimal(g) && !placed.has(g) && all.includes(g));
        gs.forEach((g) => placed.add(g));
        if (gs.length) out.push({ key: a, title: app.areaLabel(a), sub: a, glyphs: gs });
      }
      const rest = groupGlyphs.main.filter((g) => !placed.has(g));
      if (rest.length) out.push({ key: '_un', title: 'Unassigned', glyphs: rest });
    } else {
      out.push({ key: group, title: group === 'unassigned' ? 'Unassigned' : app.areaLabel(group), sub: group === 'unassigned' ? '' : group, glyphs: groupGlyphs.main });
    }
    if (groupGlyphs.deci.length) out.push({ key: 'deci', title: 'Position decimals', glyphs: groupGlyphs.deci, decimals: true });
    return out;
  });

  let sel = $derived(app.glyphs.find((r) => r.glyph === selected) ?? null);

  // CSV import / export of the spellings
  function exportCsv() {
    const blob = new Blob([T.toCsv(app.typing, app.csvOrder)], { type: 'text/csv' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'components.csv' });
    a.click();
    URL.revokeObjectURL(a.href);
  }
  async function pickCsv(e: Event) {
    const f = (e.target as HTMLInputElement).files?.[0];
    (e.target as HTMLInputElement).value = '';
    if (!f) return;
    try { importing = { name: f.name, t: T.fromCsv(await f.text()) }; } catch (err) { say(`Can't read ${f.name}: ${(err as Error).message}`); }
  }
  let importDiff = $derived.by(() => {
    if (!importing) return null;
    const changed = Object.keys(importing.t).filter((g) => app.typing[g] && T.FIELDS.some((f) => importing!.t[g][f] !== app.typing[g][f]));
    const added = Object.keys(importing.t).filter((g) => !app.typing[g]);
    const unknown = Object.keys(importing.t).filter((g) => !app.known.has(g));
    return { changed, added, unknown };
  });
  function applyImport() {
    const src = importing!.t, mode = importMode;
    app.editTyping(`Import spellings from ${importing!.name}`, (t) => {
      for (const [g, s] of Object.entries(src)) {
        const cur = (t[g] ??= T.empty());
        for (const f of T.FIELDS) if (mode === 'replace' ? true : !cur[f]) cur[f] = s[f] || (mode === 'replace' ? '' : cur[f]);
      }
    });
    say(`Imported spellings from ${importing!.name}: unsaved until Save.`, true);
    importing = null;
  }
</script>

<datalist id="jzp-glyph-names">{#each all.filter((g) => !T.isDecimal(g)) as g}<option value={g}></option>{/each}</datalist>
<datalist id="jzp-glossary-sections">{#each app.glossarySections as s}<option value={s.title}></option>{/each}</datalist>

<div class="page">
  <input type="file" accept=".csv,text/csv" bind:this={fileInput} onchange={pickCsv} hidden />
  <div class="toolbar">
    <input type="text" placeholder="Search  k · 勾 · gou · lg_gou · 7.6" bind:value={q} style="width: 250px" />
    <span class="seg" role="tablist">
      <button role="tab" class:on={view === 'tiles'} aria-selected={view === 'tiles'} onclick={() => (view = 'tiles')}>Tiles</button>
      <button role="tab" class:on={view === 'typing'} aria-selected={view === 'typing'} onclick={() => (view = 'typing')}>Typing</button>
    </span>
    {#if view === 'typing' && !phone.on}<label class="small"><input type="checkbox" bind:checked={showAreas} /> Areas column</label>{/if}
    {#if typingCheck.busy}<span class="muted small">checking spellings…</span>{/if}
    {#if phone.on}
      <div class="picks">
        <select aria-label="Area" bind:value={group}>
          <option value="all">All glyphs ({all.length})</option>
          {#each areaNames as a}
            <option value={a}>{app.areaLabel(a)} ({d.areas[a].glyphs.length})</option>
            {#if d.areas[a].glyphs.some(T.isDecimal)}<option value="decimals">· position decimals ({decimals.length})</option>{/if}
          {/each}
          <option value="unassigned">Unassigned ({unassigned.length})</option>
        </select>
        <select aria-label="Typing filter" bind:value={filter}>
          <option value="">Any spelling</option>
          {#each FILTERS as [f, label]}<option value={f}>{label} ({filterCounts[f]})</option>{/each}
        </select>
      </div>
    {:else}
    <span class="spacer"></span>
    <label class="weight" title="The stroke thickness every glyph should sit around, in units (= font units). The editor's compare dot and new lines use it. Match the body of main strokes, not the tapers.">
      Reference weight <input type="number" min="1" max="200" value={app.design?.glyph_weight ?? DEFAULT_WEIGHT} onchange={(e) => setWeight(+(e.target as HTMLInputElement).value)} /> <span class="muted">units</span>
    </label>
    <span class="menu-wrap">
      <button onclick={(e) => { e.stopPropagation(); menu = !menu; }} aria-label="More glyph actions" data-tip="Import or export spellings (CSV)"><I.More /></button>
      {#if menu}
        <div class="menu" role="menu" tabindex="-1" onmouseleave={() => (menu = false)}>
          <button onclick={() => { menu = false; fileInput.click(); }}>Import spellings (CSV)…</button>
          <button onclick={() => { menu = false; exportCsv(); }}>Export spellings (CSV)</button>
        </div>
      {/if}
    </span>
    <button class="primary" onclick={() => (newDialog = true)}>+ New glyph</button>
    {/if}
  </div>

  {#if app.typingErrors.length}
    <div class="banner err"><span class="ic"><I.Problem /></span> {app.typingErrors.length} spelling problem{app.typingErrors.length === 1 ? '' : 's'}: {app.typingErrors[0].message}{app.typingErrors.length > 1 ? ' …' : ''} Save waits until {app.typingErrors.length === 1 ? 'it is' : 'they are'} fixed.
      <button onclick={() => { view = 'typing'; filter = 'attention'; group = 'all'; }}>Show</button></div>
  {:else if typingCheck.roundtrip.length}
    <div class="banner warn"><span class="ic"><I.Warn /></span> {typingCheck.roundtrip.length} spelling{typingCheck.roundtrip.length === 1 ? '' : 's'} type something else ({typingCheck.roundtrip.slice(0, 3).map((r) => r.value).join(', ')}). Save still works.
      <button onclick={() => { filter = 'attention'; group = 'all'; }}>Show</button></div>
  {/if}
  {#if typingCheck.error}<div class="banner warn"><span class="ic"><I.Warn /></span> Spelling check: {typingCheck.error}</div>{/if}

  <div class="body">
    {#if !phone.on}
    <aside class="groups">
      <button class:on={group === 'all'} onclick={() => (group = 'all')}><span>All</span><span class="muted">{all.length}</span></button>
      <div class="gh">Areas</div>
      {#each areaNames as a}
        {@const n = d.areas[a].glyphs.length}
        <button class:on={group === a} onclick={() => (group = a)} title={a}><span>{app.areaLabel(a)}</span><span class="muted">{n}</span></button>
        {#if d.areas[a].glyphs.some(T.isDecimal)}
          <button class="sub" class:on={group === 'decimals'} onclick={() => (group = 'decimals')}><span>position decimals</span><span class="muted">{decimals.length}</span></button>
        {/if}
      {/each}
      <hr />
      <button class:on={group === 'unassigned'} onclick={() => (group = 'unassigned')}><span>Unassigned</span><span class="muted">{unassigned.length}</span></button>
      <div class="gh">Typing</div>
      {#each FILTERS as [f, label, help]}
        <button class:on={filter === f} class:warnf={f === 'attention' && filterCounts[f] > 0} class:errf={f === 'clashes' && filterCounts[f] > 0} title={help}
          onclick={() => (filter = filter === f ? '' : f)}><span>{label}</span><span class="muted">{filterCounts[f]}</span></button>
      {/each}
    </aside>
    {/if}

    <section class="grid-wrap">
      {#if d.areas[group]}
        {@const ar = d.areas[group]}
        {@const uses = usedIn(d, group)}
        <div class="areahead">
          <strong>{ar.label || group}</strong><span class="id">{group}</span>
          <span class="muted">· {ar.glyphs.length} glyph{ar.glyphs.length === 1 ? '' : 's'} · box {ar.size[0]} × {ar.size[1]} · {uses.length ? `used in ${uses.length} word type${uses.length === 1 ? '' : 's'}` : 'not in any word type yet'}</span>
          <span class="spacer"></span>
          <button class="primary" onclick={() => (addTo = group)}>+ Add glyphs</button>
          <a href="/layouts?area={encodeURIComponent(group)}" title="Area Properties on the Layouts screen: name, box, word types">Edit box in Layouts →</a>
        </div>
      {/if}
      {#if tiles.length === 0 && !foldedDecimals}
        <div class="empty">
          {#if filter === 'nospell'}<p class="ok"><I.Check size={14} /> Every glyph in an area can be typed.</p>
          {:else if filter}<p class="muted">Nothing here{needle ? ` matching “${q}”` : ''}.</p>
          {:else}<p class="muted">No glyph is typed as “{q}”, and no character or reading matches it.</p>{/if}
          <button onclick={() => { q = ''; filter = ''; }}>Show all</button>
        </div>
      {:else if view === 'tiles'}
        <div class="grid">
          {#each tiles as g (g)}
            {@const fs = T.firstSpelling(app.typing, g)}
            <div class="tile" class:on={selected === g} class:unassigned={!areasOf[g]?.length} role="button" tabindex="0"
              onclick={() => (selected = g)} ondblclick={() => goto(editUrl(g))}
              onkeydown={(e) => { if (e.key === 'Enter') goto(editUrl(g)); }}>
              {#if errGlyphs.has(g)}<span class="mark e"><I.Problem size={14} /></span>{:else if warnGlyphs.has(g)}<span class="mark"><I.Warn size={14} /></span>{/if}
              <div class="art"><Glyph name={g} size={72} /></div>
              <div class="name">{g}</div>
              <div class="sub muted">{#if T.isDecimal(g)}{T.decimalPatterns(g)[0]}{:else if !areasOf[g]?.length}no area yet{:else}{fs?.text ?? '—'}{#if fs?.inherited || partnerOf[g] || T.get(app.typing, g).vert_variant} <span class="pair"><I.Pair size={12} /></span>{/if}{/if}</div>
              <a class="edit" href={editUrl(g)} title="Edit the outline" onclick={(e) => e.stopPropagation()}>Edit</a>
            </div>
          {/each}
          {#if foldedDecimals}
            <button class="tile fold" onclick={() => (group = 'decimals')}><span>{foldedDecimals} position decimals</span><span class="muted small">typed by pattern <I.Folded size={12} /></span></button>
          {/if}
        </div>
      {:else if phone.on}
        <TypingCards {sections} {selected} onselect={(g) => (selected = g)} />
      {:else}
        <TypingTable {sections} {selected} onselect={(g) => (selected = g)} flat={searching} {showAreas} onnotice={say} />
      {/if}
    </section>
  </div>

  {#if notice}
    <div class="toast">{notice.text} {#if notice.undo}<button onclick={() => { app.undo(); notice = null; }}>Undo</button>{/if}</div>
  {/if}
  {#if addTo}<AddGlyphsDialog area={addTo} onclose={() => (addTo = null)} />{/if}
  {#if newDialog}<NewGlyphDialog onclose={() => (newDialog = false)} initialArea={sel?.areas[0] ?? (areaNames.includes(group) ? group : '')} />{/if}

  {#if sel}
    <section class="inspector" class:typing={view === 'typing'} class:card={phone.on}>
      {#if phone.on}<div class="cardbar"><button class="quiet" onclick={() => (selected = null)}><I.Back /> All glyphs</button><span class="id">{sel.glyph}</span></div>{/if}
      <div class="big"><Glyph name={sel.glyph} size={view === 'typing' && !phone.on ? 84 : 120} /></div>
      <div class="facts col">
        <div class="colh">Glyph</div>
        <GlyphFacts glyph={sel.glyph} showBox={view === 'tiles' || phone.on} />
        {#if phone.on}
        <div class="row" style="margin-top: var(--space-4)">
          <a href={editUrl(sel.glyph)}><button><I.Computer /> Edit outline</button></a><span class="muted small">needs a computer</span>
        </div>
        {:else}
        <div class="row" style="margin-top: var(--space-4)">
          <a href={editUrl(sel.glyph)}><button class="primary">Edit outline</button></a>
          <a href={editUrl(sel.glyph, 'file')}><button title="Open the editor with a new SVG loaded (nothing is written until you save)">Replace…</button></a>
          <a href={editUrl(sel.glyph, 'image')}><button title="Open the editor in trace mode">Trace…</button></a>
          {#if sel.svg && view === 'tiles'}<a href="/inputs/svg/{sel.glyph}.svg" download><button>Download SVG</button></a>{/if}
        </div>
        {/if}
      </div>
      {#if view === 'tiles' || phone.on}
        <div class="col">
          <div class="colh">Typing {#if partnerOf[sel.glyph] || T.get(app.typing, sel.glyph).vert_variant}<span class="muted">· <I.Pair size={14} /> vertical pair</span>{/if}</div>
          <TypingFields glyph={sel.glyph} />
        </div>
        <div class="col">
          <div class="colh">Try it <span class="muted">· live, saved or not</span></div>
          <TryIt glyph={sel.glyph} />
        </div>
      {:else}
        <div class="col wide">
          <div class="colh">Try it · What changes · Issues</div>
          <TryIt glyph={sel.glyph} full />
        </div>
      {/if}
    </section>
  {/if}

  {#if importing && importDiff}
    <div class="modal-bg">
      <div class="modal">
        <h3>Import spellings from {importing.name}</h3>
        <p>{Object.keys(importing.t).length} rows. Against what's loaded: {importDiff.changed.length} changed · {importDiff.added.length} new{#if importDiff.unknown.length} · <span class="warn">{importDiff.unknown.length} name no glyph ({importDiff.unknown.slice(0, 4).join(', ')}{importDiff.unknown.length > 4 ? '…' : ''})</span>{/if}.</p>
        <label><input type="radio" bind:group={importMode} value="replace" /> Replace the spellings in these rows</label>
        <label><input type="radio" bind:group={importMode} value="fill" /> Only fill empty fields</label>
        <p class="muted small">Nothing is written until Save; one undo step.</p>
        <div class="row"><span class="spacer"></span><button onclick={() => (importing = null)}>Cancel</button><button class="primary" onclick={applyImport}>Import</button></div>
      </div>
    </div>
  {/if}
</div>

<style>
  .page { display: flex; flex-direction: column; height: 100%; position: relative; }
  .toolbar { display: flex; align-items: center; gap: var(--space-5); padding: var(--space-5) var(--space-6); border-bottom: 1px solid var(--border); }
  .toolbar button { white-space: nowrap; }
  .spacer { flex: 1; }
  .seg { display: inline-flex; border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
  .seg button { border: 0; border-radius: 0; height: 28px; padding: 0 12px; background: transparent; }
  .seg button + button { border-left: 1px solid var(--border); }
  .seg button.on { background: var(--sel-bg); color: var(--ink); }
  .banner { border-width: 0 0 1px; border-radius: 0; padding: var(--space-4) var(--space-6); font-size: var(--t-small); }
  .body { display: flex; flex: 1; min-height: 0; }
  .groups { width: 220px; flex: none; border-right: 1px solid var(--border); padding: var(--space-4); display: flex; flex-direction: column; gap: 2px; overflow: auto; }
  .groups button { display: flex; justify-content: space-between; border: 1px solid transparent; background: transparent; text-align: left; height: auto; min-height: 26px; gap: var(--space-4); font-weight: 400; }
  .groups button span:first-child { min-width: 0; }
  .groups button.sub { padding-left: 22px; font-size: var(--t-small); }
  .groups button.on { background: var(--sel-bg); color: var(--ink); border-color: var(--sel-border); }
  .groups button.warnf span:first-child { color: var(--status-draft); }
  .groups button.errf span:first-child { color: var(--status-danger); }
  .groups hr { border: 0; border-top: 1px solid var(--border); margin: var(--space-4) 0; width: 100%; }
  .gh { font-size: var(--t-caption); color: var(--ink-muted); margin: var(--space-4) 0 2px 8px; text-transform: uppercase; letter-spacing: .04em; }
  .grid-wrap { flex: 1; min-width: 0; overflow: auto; padding: var(--space-5); }
  .areahead { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; padding: 6px var(--space-5); margin-bottom: var(--space-5); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-panel); font-size: var(--t-small); }
  .areahead a { font-size: var(--t-small); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, 120px); gap: var(--space-4); }
  .tile { position: relative; height: auto; width: 120px; padding: var(--space-4) var(--space-4) 26px; display: flex; flex-direction: column; align-items: center; gap: 2px; background: var(--bg-field); border: 1px solid var(--border); border-radius: var(--radius-md); cursor: pointer; }
  .tile:hover { background: var(--bg-hover); }
  .tile.on { border-color: var(--link); box-shadow: 0 0 0 1px var(--link); }
  .tile.fold { justify-content: center; border-style: dashed; color: var(--ink-muted); padding: var(--space-4); min-height: 120px; }
  .tile .mark { position: absolute; top: 3px; right: 6px; color: var(--status-draft); font-size: var(--t-small); }
  .tile .mark.e { color: var(--status-danger); }
  .tile .edit { position: absolute; left: 50%; bottom: 4px; transform: translateX(-50%); display: none; height: 18px; line-height: 18px; padding: 0 10px; border-radius: 9px; background: var(--sel-bg); color: var(--ink); font-size: var(--t-caption); text-decoration: none; }
  .tile:hover .edit, .tile:focus-within .edit, .tile.on .edit { display: block; }
  .pair { color: var(--link); }
  .weight { display: flex; align-items: center; gap: var(--space-2); font-size: var(--t-small); }
  .weight input { width: 60px; }
  .tile.unassigned .art { outline: 1px dashed var(--border); outline-offset: 2px; border-radius: 4px; }
  .name { font-family: var(--font-mono); font-size: var(--t-caption); }
  .tile .sub { font-size: var(--t-caption); max-width: 104px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .empty { padding: var(--space-8); display: flex; flex-direction: column; align-items: center; gap: var(--space-5); }
  .ok { color: var(--status-saved); }
  .inspector { display: flex; flex-wrap: wrap; gap: var(--space-5) var(--space-7); padding: var(--space-5) var(--space-6); border-top: 1px solid var(--border); background: var(--bg-panel); max-height: 48vh; overflow: auto; align-items: flex-start; }
  .col { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; flex: 1 1 260px; }
  .col.facts { flex: 1 1 300px; }
  .col.wide { flex: 2 1 380px; }
  .facts .row { flex-wrap: wrap; }
  .colh { font-size: var(--t-caption); color: var(--ink-muted); border-bottom: 1px dashed var(--border); padding-bottom: 2px; margin-bottom: 2px; }
  .big { padding: var(--space-4); background: var(--bg-field); border: 1px solid var(--border); border-radius: var(--radius-md); }
  .small { font-size: var(--t-caption); }
  .warn { color: var(--status-draft); }
  .menu-wrap { position: relative; }
  .menu { position: absolute; right: 0; top: 100%; z-index: 30; margin-top: 4px; min-width: 220px; display: flex; flex-direction: column; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--radius-md); box-shadow: var(--shadow-float); padding: 4px; }
  .menu button { text-align: left; justify-content: flex-start; border: 0; background: transparent; }
  .menu button:hover { background: var(--bg-hover); }
  .toast { position: absolute; left: 50%; bottom: 16px; transform: translateX(-50%); padding: 6px 12px; font-size: var(--t-small); display: flex; gap: var(--space-4); align-items: center; }

  /* a phone: search, Tiles | Typing and the two selects wrap; the tiles fill the width; the card covers them */
  .picks { display: flex; gap: var(--space-3); flex: 1 1 100%; min-width: 0; }
  .picks select { flex: 1 1 0; min-width: 0; }
  @media (max-width: 759.98px) {
    .toolbar { flex-wrap: wrap; gap: var(--space-3); padding: var(--space-4); }
    .toolbar input[type=text] { width: auto !important; flex: 1 1 160px; min-width: 0; }
    .seg button { height: var(--control-md); }
    .grid-wrap { padding: var(--space-4); }
    .grid { grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: var(--space-3); }
    .tile { width: auto; padding-bottom: var(--space-4); }
    .tile .edit { display: none !important; }
    .tile .sub { max-width: 100%; }
    .inspector.card { position: absolute; inset: 0; z-index: 5; max-height: none; flex-direction: column; flex-wrap: nowrap; gap: var(--space-5); padding: 0 var(--space-4) var(--space-6); border-top: 0; }
    .card .cardbar { position: sticky; top: 0; z-index: 1; display: flex; align-items: center; gap: var(--space-4); width: calc(100% + 2 * var(--space-4)); margin: 0 calc(-1 * var(--space-4)); padding: var(--space-2) var(--space-4); background: var(--bg-panel); border-bottom: 1px solid var(--border); }
    .card .cardbar .quiet { padding-left: var(--space-2); }
    .card .big { align-self: center; }
    .card .col { flex: none; width: 100%; }
  }
  .modal { padding: var(--space-7); max-width: 560px; display: flex; flex-direction: column; gap: var(--space-4); }
</style>
