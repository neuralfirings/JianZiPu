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
  import { allUpcoming, drawingBlob, draftRows, exampleSvg, fitToInk, placedGhosts, publishDrafts, stageLabel, type DraftRow, type UpcomingRow } from '$lib/upcoming';
  import GlossaryPreview from './GlossaryPreview.svelte';
  import { api } from '$lib/api';
  import * as T from '$lib/typing';

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
    // a glyph already on the page (published before, from this request or another) goes back to its own
    // row, not a new one: publishing again updates it
    const placed = placedGhosts(upcoming ?? [], request.bundle.manifest.svgs.added, request.id);
    tags = { ...placed, ...tags };
  }

  let plan = $derived(draftRows(request.bundle, tags, app.mainLayout));
  // a row with its own example: the whole word, laid out by the request's design and spellings, as the
  // drawing the page shows (glyph → SVG); drawn once per request
  let pictures = $state<Record<string, string>>({});
  let drewFor = '';
  let drawing: Promise<Record<string, string>> = Promise.resolve({});
  /** Draw the examples (once per request and set of examples); Publish waits for this, so a quick press
   *  never puts the glyph alone on the page where the example word belongs. */
  function drawPictures(): Promise<Record<string, string>> {
    const b = request.bundle, rows = plan.rows.filter((r) => r.example);
    const key = request.id + rows.map((r) => r.glyph + (r.example ?? []).join('|')).join(',');
    if (key === drewFor) return drawing;
    drewFor = key;
    if (!rows.length) return (drawing = Promise.resolve({}));
    const words = rows.map((r) => plain(r.example![1] || r.example![0]));   // the red marks are for the page, not to type
    drawing = api.words(b.design, words, { rows: T.toRecords(b.typing), svgs: b.svgs }).then((res) => {
      if (!res.ok) return {};
      const svgs = { ...app.svgs, ...b.svgs }, out: Record<string, string> = {};
      rows.forEach((r, i) => {
        const w = res.words[i];
        // red only when the example has more in it than the row (引上九), as Glyphs › Glossary marks it
        const mark = r.marked ? [r.glyph, T.get(b.typing, r.glyph).vert_variant].filter(Boolean) : [];
        const svg = w && exampleSvg(w.pieces, svgs, mark, app.control);
        if (svg) out[r.glyph] = fitToInk(svg);
      });
      return out;
    }).catch(() => ({}));
    void drawing.then((out) => { if (drewFor === key) pictures = out; });
    return drawing;
  }
  $effect(() => { void drawPictures(); });
  let open = $derived((upcoming ?? []).filter((u) => u.stage !== 'released'));
  // Now and After as the font page shows them (GlossaryPreview): the drawings as blob: URLs, since the
  // Builder's content policy loads images only from itself. Now: the row's drawing on the page.
  let nowPics = $state<Record<string, string>>({});
  const nowFor: Record<string, string> = {};
  $effect(() => {
    for (const u of upcoming ?? []) {
      const key = `${u.drawing}:${u.updated_at}`;
      if (!u.drawing || nowFor[u.id] === key) continue;
      nowFor[u.id] = key;
      void drawingBlob(hosted.client!, u.drawing).then((url) => { if (url && nowFor[u.id] === key) nowPics = { ...nowPics, [u.id]: url }; });
    }
  });
  // After: what Publish puts there, the example word when the row has one, else the glyph alone
  let afterPics = $derived(Object.fromEntries(plan.rows.map((r) => {
    const svg = (r.example ? pictures[r.glyph] : undefined) ?? request.bundle.svgs[r.glyph];
    return [r.glyph, svg ? URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' })) : null];
  })));
  $effect(() => { const m = afterPics; return () => { for (const u of Object.values(m)) if (u) URL.revokeObjectURL(u); }; });
  $effect(() => () => { for (const u of Object.values(nowPics)) URL.revokeObjectURL(u); });
  /** The row as Publish writes it: the request's words over the entry's (what they leave empty stays). */
  const afterOf = (r: DraftRow, now: UpcomingRow | undefined) => ({
    zh: r.zh, pinyin: r.pinyin || now?.pinyin || null, ascii: r.ascii || now?.ascii || null, meaning: r.meaning || now?.meaning || null,
    section: r.section, after: r.after, stage: 'draft' as const, note: now?.note ?? null, version: null,
    example: r.example && pictures[r.glyph] ? r.example : null
  });
  /** "1.4. Vibratos and Slides" for 1e: the request's own subtitles, else the font's. */
  const sectionName = (id: string) => request.bundle.glossaryLayout?.sections[id]?.title ?? app.mainLayout?.sections[id]?.title ?? id;
  const rowOf = (id: string | null) => (id ? (upcoming ?? []).find((u) => u.id === id) : undefined);
  /** Every row already shows this request's drawing: the button updates them. */
  let published = $derived(plan.rows.length > 0 && plan.rows.every((r) => rowOf(r.ghost)?.change_request_id === request.id));

  const plain = (t: string) => t.replace(/<\/?r>/g, '');

  async function publish() {
    busy = true; err = null;
    try {
      // an example's whole word must be drawn first: without it the page would show the glyph alone
      const pics = await drawPictures();
      const missing = plan.rows.filter((r) => r.example && !pics[r.glyph]).map((r) => r.glyph);
      if (missing.length) throw new Error(`Couldn't draw the example word for ${missing.join(', ')}, so nothing was published. Check that it types in Build & test, then try again.`);
      const ids = await publishDrafts(hosted.client!, request.id, plan.rows, request.bundle.svgs, pics);
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
        <p class="when"><b>Now</b> <span class="muted small">· on the font page today</span></p>
        {#if now}
          <GlossaryPreview g={now} drawing={nowPics[now.id] ?? null} />
        {:else}
          <p class="muted small">Nothing on the page: a new row is added.</p>
        {/if}
        <p class="when"><b>After</b> <span class="muted small">· once you publish{r.example && !pictures[r.glyph] ? ' (drawing its example word…)' : ''}</span></p>
        <GlossaryPreview g={afterOf(r, now)} drawing={afterPics[r.glyph] ?? null} />
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
  .when { margin: var(--space-2) 0 0; }
  .item { display: flex; flex-direction: column; gap: var(--space-3); border-top: 1px solid var(--hairline); padding-top: var(--space-4); }
  .pick { display: inline-flex; align-items: center; gap: var(--space-2); }
  .pick select { max-width: 100%; }
  .mono { font-family: var(--font-mono); font-size: var(--t-small); }
  .small { font-size: var(--t-small); }
</style>
