<script lang="ts">
  // Review › a Change Request › On the glossary (local Builder, admin): the request's new glyphs that
  // have a glossary row, each with the coming character it draws (the tester's tag, or a new one),
  // and how its row will look on the font page. Publish draft to glossary uploads each drawing to the
  // upcoming bucket and writes the row (stage draft), so the page shows it within a minute, before
  // the release. Nothing is written until you press it; a later redraw is published the same way.
  import * as I from '$lib/icons';
  import { hosted } from '$lib/hosted.svelte';
  import { pilot } from '$lib/pilot.svelte';
  import { app } from '$lib/state.svelte';
  import type { ChangeRequest } from '$lib/requests';
  import { allUpcoming, draftRows, exampleSvg, fitToInk, publishDrafts, stageLabel, type UpcomingRow } from '$lib/upcoming';
  import { api } from '$lib/api';
  import * as T from '$lib/typing';
  import SvgText from './SvgText.svelte';

  let { request }: { request: ChangeRequest } = $props();

  const SITE = 'https://jianzipufont.com/';
  let upcoming = $state<UpcomingRow[] | null>(null);
  let err = $state<string | null>(null);
  let busy = $state(false);
  let tags = $state<Record<string, string>>({});
  let loadedFor = '';
  $effect(() => {
    if (request.id === loadedFor || !hosted.client) return;
    loadedFor = request.id;
    tags = { ...(request.bundle.manifest.upcoming ?? {}) };
    void load();
  });
  async function load() {
    err = null;
    try { upcoming = await allUpcoming(hosted.client!); } catch (e) { err = (e as Error).message; upcoming = []; }
  }

  let plan = $derived(draftRows(request.bundle, tags));
  // a row with its own example: the whole word, laid out by the request's design and spellings, as the
  // drawing the page shows (glyph → SVG); drawn once per request
  let pictures = $state<Record<string, string>>({});
  let drewFor = '';
  $effect(() => {
    const b = request.bundle, rows = plan.rows.filter((r) => r.example);
    const key = request.id + rows.map((r) => r.glyph + (r.example ?? []).join('|')).join(',');
    if (!rows.length || key === drewFor) return;
    drewFor = key;
    const words = rows.map((r) => r.example![1] || r.example![0]);
    void api.words(b.design, words, { rows: T.toRecords(b.typing), svgs: b.svgs }).then((res) => {
      if (!res.ok) return;
      const svgs = { ...app.svgs, ...b.svgs }, out: Record<string, string> = {};
      rows.forEach((r, i) => {
        const w = res.words[i];
        // red only when the example has more in it than the row (引上九), as Glyphs › Glossary marks it
        const mark = r.marked ? [r.glyph, T.get(b.typing, r.glyph).vert_variant].filter(Boolean) : [];
        const svg = w && exampleSvg(w.pieces, svgs, mark, app.control);
        if (svg) out[r.glyph] = fitToInk(svg);
      });
      pictures = out;
    }).catch(() => { /* the glyph alone is shown and published */ });
  });
  let open = $derived((upcoming ?? []).filter((u) => u.stage !== 'released'));
  /** "1.4. Vibratos and Slides" for 1e: the request's own subtitles, else the font's. */
  const sectionName = (id: string) => request.bundle.glossaryLayout?.sections[id]?.title ?? app.mainLayout?.sections[id]?.title ?? id;
  const rowOf = (id: string | null) => (id ? (upcoming ?? []).find((u) => u.id === id) : undefined);
  /** Every row already shows this request's drawing: the button updates them. */
  let published = $derived(plan.rows.length > 0 && plan.rows.every((r) => rowOf(r.ghost)?.change_request_id === request.id));

  const plain = (t: string) => t.replace(/<\/?r>/g, '');
  /** At Glyphs › Glossary's size for an example (GlossaryExample, 0.04 px per font unit), from its width in units. */
  const picWidth = (svg: string) => Math.max(16, Math.round(Number(/width="([\d.]+)"/.exec(svg)?.[1] ?? 400) * 0.04));

  async function publish() {
    busy = true; err = null;
    try {
      const ids = await publishDrafts(hosted.client!, request.id, plan.rows, request.bundle.svgs, pictures);
      // new ghosts take the ids they were given, so a second press updates them
      const fresh = plan.rows.filter((r) => !r.ghost);
      await load();
      for (const r of fresh) {
        const u = (upcoming ?? []).find((x) => x.change_request_id === request.id && x.glyphs.includes(r.glyph));
        if (u) tags = { ...tags, [r.glyph]: u.id };
      }
      pilot.say(`On the glossary as ${ids.length === 1 ? 'a draft' : `${ids.length} drafts`}: ${ids.join(', ')}. The font page shows ${ids.length === 1 ? 'it' : 'them'} within a minute.`);
    } catch (e) {
      err = (e as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

{#if plan.rows.length || plan.unplaced.length}
  <section class="coming">
    <div class="head">
      <h3>On the glossary</h3>
      <span class="spacer"></span>
      {#if plan.rows.length}
        <button onclick={publish} disabled={busy || upcoming === null}><I.Upload size={14} /> {busy ? 'Publishing…' : published ? 'Update the draft on the glossary' : 'Publish draft to glossary'}</button>
      {/if}
    </div>
    <p class="muted small">Show this request's drawings on the font page now, as drafts experts can comment on, before you decide on the release. Building a release candidate turns them to In release; publishing the release makes them ordinary rows.</p>
    {#if err}<div class="banner danger" role="alert"><span class="ic"><I.Problem /></span><span>{err}</span></div>{/if}
    {#each plan.rows as r (r.glyph)}
      {@const now = rowOf(r.ghost)}
      <div class="item">
        <div class="ihead">
          <b class="mono">{r.glyph}</b>
          <label class="pick">draws
            <select value={r.ghost ?? ''} onchange={(e) => (tags = { ...tags, [r.glyph]: (e.target as HTMLSelectElement).value })}>
              <option value="">A new row on the page</option>
              {#each open as u (u.id)}<option value={u.id}>{u.zh}{u.pinyin ? ` · ${u.pinyin}` : ''} ({u.id}) · {stageLabel(u)}</option>{/each}
            </select>
          </label>
          {#if request.bundle.manifest.upcoming?.[r.glyph]}<span class="muted small">tagged by the tester: {request.bundle.manifest.upcoming[r.glyph]}</span>{/if}
          {#if now}<span class="spacer"></span><a href="{SITE}#coming-{now.id}" target="_blank" rel="noopener">On the font page <I.Opens size={14} /></a>{/if}
        </div>
        <div class="rows">
          <div class="when">Now</div>
          {#if now}
            <div class="grow now">
              <span class="zh">{now.zh}{#if now.pinyin}<small>{now.pinyin}</small>{/if}</span>
              <span class="mono muted">{now.ascii ?? 'to come'}</span>
              <span class="tag">{stageLabel(now)}</span>
              <span>{now.meaning ?? ''}{#if !now.section} <span class="muted small">· not on the page yet (no section)</span>{/if}</span>
            </div>
          {:else}
            <div class="grow none muted small">Nothing on the page: a new row is added.</div>
          {/if}
          <div class="when">After</div>
          <div class="grow after">
            <span class="zh">{r.zh}{#if r.pinyin}<small>{r.pinyin}</small>{/if}</span>
            <span class="mono">{r.ascii ?? ''}</span>
            {#if r.example && pictures[r.glyph]}
              <span class="exin"><span class="zh">{plain(r.example[0])}</span><span class="mono">{plain(r.example[1])}</span></span>
              <span class="pic" style="width: {picWidth(pictures[r.glyph])}px">{@html pictures[r.glyph]}</span>
            {:else}<SvgText text={request.bundle.svgs[r.glyph]} size={56} />{/if}
            <span><span class="tag">Draft design</span> {r.meaning ?? ''} <span class="muted small">· in {sectionName(r.section)}{r.after ? `, after ${r.after}` : ''}</span></span>
          </div>
        </div>
      </div>
    {/each}
    {#if plan.unplaced.length}
      <p class="muted small">{plan.unplaced.join(', ')} {plan.unplaced.length === 1 ? 'has' : 'have'} no glossary row in this request, so {plan.unplaced.length === 1 ? 'it' : 'they'} can't be shown on the page.</p>
    {/if}
  </section>
{/if}

<style>
  .coming { display: flex; flex-direction: column; gap: var(--space-4); margin: var(--space-6) 0; padding: var(--space-5); border: 1px dashed var(--border-strong); border-radius: var(--radius-lg); background: var(--bg-panel); }
  .coming p { margin: 0; }
  .head, .ihead { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); }
  .head h3 { margin: 0; }
  .spacer { flex: 1; }
  .item { display: flex; flex-direction: column; gap: var(--space-3); border-top: 1px solid var(--hairline); padding-top: var(--space-4); }
  .pick { display: inline-flex; align-items: center; gap: var(--space-2); }
  .pick select { max-width: 100%; }
  .rows { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: var(--space-2) var(--space-4); align-items: center; }
  .when { font-size: var(--t-small); font-weight: 600; color: var(--ink-muted); }
  .grow { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, .7fr) auto minmax(0, 2fr); gap: var(--space-4); align-items: center; padding: var(--space-2) var(--space-3);
    border: 1px dashed var(--border); border-radius: var(--radius-md); background: var(--bg-field); }
  .grow.none { display: block; }
  .grow.after:has(.exin) { grid-template-columns: minmax(0, 1fr) minmax(0, .7fr) auto auto minmax(0, 2fr); }
  .exin { display: flex; flex-direction: column; align-items: center; }
  .pic { display: block; }
  .pic :global(svg) { display: block; width: 100%; height: auto; }
  .grow.after { border-color: var(--border-strong); }
  .zh { font-family: var(--font-cjk); }
  .zh small { display: block; font-family: var(--font-serif); color: var(--ink-muted); }
  .mono { font-family: var(--font-mono); font-size: var(--t-small); }
  .small { font-size: var(--t-small); }
  @media (max-width: 759.98px) { .grow { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); } }
</style>
