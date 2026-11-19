<script lang="ts">
  // Review › Glossary drafts (admin): the font page's coming characters, one row each in the
  // `upcoming` table, grouped by stage. Each shows its drawing (the public upcoming bucket) and what
  // the page writes for it; Edit changes the words, section, place, stage or the public note; Delete
  // takes it off the page for good. Drawings come from a Change Request (Publish draft to glossary).
  import * as I from '$lib/icons';
  import { hosted } from '$lib/hosted.svelte';
  import { day, pilot } from '$lib/pilot.svelte';
  import { app } from '$lib/state.svelte';
  import { sectionList } from '$lib/glossary';
  import GlossaryPreview from './GlossaryPreview.svelte';
  import { allUpcoming, deleteUpcoming, drawingBlob, stageLabel, updateUpcoming, type Stage, type UpcomingPatch, type UpcomingRow } from '$lib/upcoming';

  let { focus = null, oncount }: { focus?: string | null; oncount?: (n: number) => void } = $props();

  let rows = $state<UpcomingRow[] | null>(null);
  let err = $state<string | null>(null);
  let releasedOpen = $state(false);
  const STAGES: Stage[] = ['planned', 'draft', 'test', 'released'];
  const STAGE_HELP: Record<Stage, string> = {
    planned: 'Set to WIP, not drawn yet: the page shows the character with a Planned badge.',
    draft: 'A drawing on the page for people to comment on (Draft design).',
    test: 'In a release candidate: the page offers its test font (In release …).',
    released: 'In the font: the page shows its real row instead.'
  };
  const PILL: Record<Stage, string> = { planned: '', draft: 'draft', test: 'info', released: 'saved' };
  const ICON = { planned: I.Plus, draft: I.Draft, test: I.Info, released: I.Check };

  let sections = $derived(sectionList(app.mainLayout.groups.length ? app.mainLayout : app.glossaryLayout));
  const titleOf = (id: string | null) => (id ? sections.find((s) => s.id === id)?.title ?? id : null);
  let groups = $derived(STAGES.map((s) => ({ stage: s, rows: (rows ?? []).filter((r) => r.stage === s) })));

  $effect(() => { if (rows === null && hosted.client) void load(); });
  $effect(() => { if (rows) oncount?.(rows.filter((r) => r.stage !== 'released').length); });
  // the drawings, as blob: URLs (row id → URL); read again with the list
  let pics = $state<Record<string, string>>({});
  async function load() {
    err = null;
    try { rows = await allUpcoming(hosted.client!); } catch (e) { err = (e as Error).message; rows = []; }
    for (const u of Object.values(pics)) URL.revokeObjectURL(u);
    pics = {};
    const got = await Promise.all(rows.filter((r) => r.drawing).map(async (r) => [r.id, await drawingBlob(hosted.client!, r.drawing!)] as const));
    pics = Object.fromEntries(got.filter(([, u]) => u)) as Record<string, string>;
  }
  // a link from a message (Coming character) opens its row
  let focused = '';
  $effect(() => {
    if (!focus || !rows || focused === focus) return;
    focused = focus;
    const r = rows.find((x) => x.id === focus);
    if (!r) return;
    if (r.stage === 'released') releasedOpen = true;
    edit(r);
    setTimeout(() => document.getElementById(`u-${r.id}`)?.scrollIntoView({ block: 'center' }), 50);
  });

  // the row being edited
  let editing = $state<string | null>(null);
  let form = $state<Required<{ [K in keyof UpcomingPatch]: string }>>({ zh: '', pinyin: '', ascii: '', meaning: '', section: '', after: '', stage: 'planned', note: '', version: '' });
  let saving = $state(false);
  function edit(r: UpcomingRow) {
    editing = r.id;
    form = { zh: r.zh, pinyin: r.pinyin ?? '', ascii: r.ascii ?? '', meaning: r.meaning ?? '', section: r.section ?? '', after: r.after ?? '', stage: r.stage, note: r.note ?? '', version: r.version ?? '' };
  }
  async function save(r: UpcomingRow) {
    saving = true;
    const t = (s: string) => s.trim() || null;
    try {
      const row = await updateUpcoming(hosted.client!, r.id, {
        zh: form.zh.trim(), pinyin: t(form.pinyin), ascii: t(form.ascii), meaning: t(form.meaning), section: t(form.section),
        after: t(form.after), stage: form.stage as Stage, note: t(form.note), version: t(form.version)
      });
      rows = rows!.map((x) => (x.id === row.id ? row : x));
      editing = null;
      pilot.say(`Saved ${row.zh || row.id}. The font page shows the change within a minute.`);
    } catch (e) {
      err = (e as Error).message;
    } finally {
      saving = false;
    }
  }
  async function remove(r: UpcomingRow) {
    if (!confirm(`Take ${r.zh || r.id} off the font page for good? Its row and its drawing are deleted.`)) return;
    try {
      await deleteUpcoming(hosted.client!, r);
      rows = rows!.filter((x) => x.id !== r.id);
      editing = null;
      pilot.say(`Deleted ${r.zh || r.id}.`);
    } catch (e) {
      err = (e as Error).message;
    }
  }
  /** The form's empty fields as null, as they're saved. */
  const nul = (f: typeof form) => Object.fromEntries(Object.entries(f).map(([k, v]) => [k, k === 'zh' ? v : v.trim() || null])) as unknown as Partial<UpcomingRow>;
  /** Why the page doesn't show a row that isn't released. */
  const hiddenWhy = (r: UpcomingRow) => (r.stage !== 'released' && !r.section ? 'Not on the page: no section' : null);
</script>

<div class="bar">
  <p class="muted small">The font page's coming characters. A request set to WIP in Feedback adds one; Publish draft to glossary on a Change Request gives it a drawing; releases move it on.</p>
  <span class="spacer"></span>
  <button class="quiet sm" onclick={() => { rows = null; }} data-tip="Load the list again" aria-label="Reload"><I.Refresh /></button>
</div>

{#if err}<div class="banner danger"><span class="ic"><I.Problem /></span><span>{err}</span></div>{/if}

{#if rows === null}
  <p class="muted">Loading coming characters…</p>
{:else if !rows.length}
  <p class="muted">No coming characters yet.</p>
{:else}
  {#each groups as g (g.stage)}
    {#if g.rows.length || g.stage !== 'released'}
      {@const Ic = ICON[g.stage]}
      <section class="stage">
        <h3>
          {#if g.stage === 'released'}
            <button class="fold" onclick={() => (releasedOpen = !releasedOpen)} aria-expanded={releasedOpen}>{#if releasedOpen}<I.Unfolded />{:else}<I.Folded />{/if} Released <span class="muted">{g.rows.length}</span></button>
          {:else}
            {g.stage === 'planned' ? 'Planned' : g.stage === 'draft' ? 'Draft design' : 'In a release candidate'} <span class="muted">{g.rows.length}</span>
          {/if}
        </h3>
        <p class="muted small">{STAGE_HELP[g.stage]}</p>
        {#if g.stage !== 'released' || releasedOpen}
          {#if !g.rows.length}<p class="muted small">None.</p>{/if}
          <div class="cards">
            {#each g.rows as r (r.id)}
              <article class="card" id={`u-${r.id}`} class:on={editing === r.id}>
                {#if editing === r.id}
                  <div class="form">
                    <div class="grid">
                      <label>中文 <input bind:value={form.zh} placeholder="不动, or 索铃 · 索鈴" /></label>
                      <label>Pinyin <input bind:value={form.pinyin} /></label>
                      <label>Spelling <input class="mono" bind:value={form.ascii} placeholder="budong" /></label>
                      <label>Stage
                        <select bind:value={form.stage}>{#each STAGES as s}<option value={s}>{stageLabel({ stage: s, version: form.version })}</option>{/each}</select>
                      </label>
                      <label class="wide">Definition <textarea rows="2" bind:value={form.meaning}></textarea></label>
                      <label>Section
                        <select bind:value={form.section}>
                          <option value="">None (not on the page)</option>
                          {#each sections as s}<option value={s.id}>{s.title}</option>{/each}
                        </select>
                      </label>
                      <label>After <input bind:value={form.after} placeholder="the row's 中文; empty: the end" /></label>
                      {#if form.stage === 'test' || form.stage === 'released' || form.version}
                        <label>Version <input class="mono" bind:value={form.version} placeholder="3.400-rc.1" /></label>
                      {/if}
                      <label class="wide">Note on the page <input bind:value={form.note} placeholder="Redrawn Nov 24: the hook is shorter" /></label>
                    </div>
                  </div>
                  {#if form.stage !== 'released'}
                    <p class="muted small">As the font page will show it:</p>
                    <GlossaryPreview g={{ ...r, ...nul(form), stage: form.stage as Stage }} drawing={pics[r.id] ?? null} />
                  {/if}
                  <div class="row">
                    <button class="danger sm" onclick={() => remove(r)}>Delete…</button>
                    <span class="spacer"></span>
                    <button onclick={() => (editing = null)}>Cancel</button>
                    <button class="primary" onclick={() => save(r)} disabled={saving || !form.zh.trim()}>{saving ? 'Saving…' : 'Save'}</button>
                  </div>
                {:else}
                  <div class="foot">
                    <span class="zh">{r.zh || '—'}</span>
                    <span class="pill {PILL[r.stage]} sm"><Ic size={12} />{stageLabel(r)}</span>
                    {#if hiddenWhy(r)}<span class="pill danger sm"><I.Hidden size={12} />{hiddenWhy(r)}</span>{/if}
                    <span class="muted small">{r.id} · {r.section ? titleOf(r.section) : 'no section'} · changed {day(r.updated_at)}</span>
                    {#if r.change_request_id}<a class="small" href={`/review?request=${r.change_request_id}`}>Change Request</a>{/if}
                    <span class="spacer"></span>
                    <button class="sm" onclick={() => edit(r)}><I.EditRow size={14} /> Edit</button>
                  </div>
                  {#if r.stage === 'released'}
                    <p class="muted small">In the font{r.version ? ` since ${r.version}` : ''}: the page shows its own row now.</p>
                  {:else}
                    <GlossaryPreview g={r} drawing={pics[r.id] ?? null} />
                  {/if}
                {/if}
              </article>
            {/each}
          </div>
        {/if}
      </section>
    {/if}
  {/each}
{/if}

<style>
  .bar { display: flex; gap: var(--space-5); align-items: center; }
  .bar p { margin: 0; }
  .spacer { flex: 1; }
  .stage { display: flex; flex-direction: column; gap: var(--space-3); }
  .stage h3 { margin: var(--space-4) 0 0; font-size: var(--t-panel); }
  .stage > p { margin: 0; }
  .fold { border: 0; background: none; padding: 0; height: auto; font: inherit; display: inline-flex; gap: var(--space-2); align-items: center; }
  .card p { margin: 0; }
  .cards { display: flex; flex-direction: column; gap: var(--space-4); }
  .card { display: flex; flex-direction: column; gap: var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); padding: var(--space-5); }
  .card.on { border-color: var(--sel-border); }
  .cjk { font-family: var(--font-cjk); }
  .zh { font-family: var(--font-serif); font-size: var(--t-panel); font-weight: 600; }
  .zh { font-size: var(--t-heading); }
  .foot { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; margin-top: auto; }
  .pill.sm { height: 20px; padding: 0 var(--space-3); font-size: var(--t-caption); }
  .form { display: flex; flex-direction: column; gap: var(--space-4); }
  .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-4); }
  .grid label { display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--t-small); }
  .grid .wide { grid-column: span 2; }
  .mono { font-family: var(--font-mono); }
  .row { display: flex; gap: var(--space-4); align-items: center; }
  @media (max-width: 759.98px) { .grid { grid-template-columns: 1fr 1fr; } }
</style>
