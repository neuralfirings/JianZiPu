<script lang="ts">
  // Send Change Request (Your changes, hosted): pick which of the draft's changes go, say what
  // you changed and why, and how you'd like to be credited. Before it goes: the draft is saved,
  // the chosen spellings mustn't clash, and a font built from just those changes must build.
  // Once sent, those changes are locked in the draft until the request is withdrawn or declined.
  // A new glyph can be tagged with the coming character it draws (the font page's ghost rows,
  // lib/upcoming.ts): suggested from its spelling, saved in the request's manifest.upcoming.
  // Save as draft keeps the form (ticks, title, notes, credit) with the tester's draft in Supabase,
  // to finish later, here or on another computer; it opens again from where it was.
  import * as I from '$lib/icons';
  import { api } from '$lib/api';
  import { hosted } from '$lib/hosted.svelte';
  import { companions, glyphOf, itemName, type Item } from '$lib/merge';
  import { pilot } from '$lib/pilot.svelte';
  import { buildInputs, myCredit, sendRequest, setCredit, snapshot, startingTicks } from '$lib/requests';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';
  import { draftRows, exampleSvg, fitToInk, publicGhosts, stageLabel, suggestGhost, type Ghost } from '$lib/upcoming';
  import GlossaryPreview from './GlossaryPreview.svelte';

  let { items, onclose }: { items: Item[]; onclose: () => void } = $props();

  // everything ticked to start with, or where a saved draft request left off (the list doesn't
  // change while the dialog is open)
  const saved = () => app.requestDraft;
  const ticks = () => startingTicks(items.map((i) => i.id), saved());
  let chosen = $state<Record<string, boolean>>(ticks());
  let title = $state(saved()?.title ?? '');
  let notes = $state(saved()?.notes ?? '');
  let credit = $state(saved()?.credit ?? '');
  let keeping = $state(false);
  let savedCredit = '';
  let step = $state<'form' | 'checking' | 'sending'>('form');
  let problem = $state<string | null>(null);
  let log = $state<string[]>([]);

  $effect(() => {
    const c = hosted.client, uid = hosted.user?.id;
    if (c && uid) void myCredit(c, uid).then((v) => { savedCredit = v; if (!credit) credit = v; });
  });

  // coming characters: the font page's list, and which one each new glyph draws ('' for none)
  let ghosts = $state<Ghost[]>([]);
  let tags = $state<Record<string, string>>({});
  $effect(() => {
    const url = hosted.config?.supabase_url;
    if (url) void publicGhosts(url).then((g) => (ghosts = g));
  });
  const tagOf = (g: string) => (g in tags ? tags[g] : suggestGhost(app.typing[g], ghosts) ?? '');
  const ghostById = (id: string) => ghosts.find((x) => x.id === id);
  const nameOf = itemName;
  let picked = $derived(items.filter((i) => chosen[i.id]));
  /** The new glyphs whose glossary entry goes in this request: each can be for a coming character (the
   *  entry is what the font page shows). A glyph row, not a word; the glyph must be new in the draft. */
  let fresh = $derived([...new Set(picked.flatMap((i) => (i.kind === 'glossary-row' && i.status === 'added' && i.row.startsWith('g:') ? [i.row.slice(2)] : []))
    .filter((g) => items.find((x) => x.id === `glyph:${g}`)?.status === 'added'))]);
  // what the page will show once the maintainer publishes your drawing for the coming character you picked
  // (Review's Publish draft to glossary): your glossary row's words over the entry's, and your drawing
  let plan = $derived(fresh.length && app.design ? draftRows(app.bundle(), Object.fromEntries(fresh.map((g) => [g, tagOf(g) || null])), app.mainLayout) : { rows: [], unplaced: [] });
  const rowFor = (g: string) => plan.rows.find((r) => r.glyph === g);
  function after(gh: Ghost, g: string) {
    const r = rowFor(g);
    if (!r) return { ...gh, version: gh.release };
    const set = (v: string | null, old: string | null) => v || old;
    return { ...gh, version: null, stage: 'draft' as const, zh: r.zh, pinyin: set(r.pinyin, gh.pinyin), ascii: set(r.ascii, gh.ascii),
      meaning: set(r.meaning, gh.meaning), section: r.section, after: r.after, example: r.example };
  }
  // the chosen entries' drawings as they are on the page now (a public address; fetched, since the content
  // policy loads images only from the Builder itself), entry id → blob: URL
  let nowPics = $state<Record<string, string>>({});
  const fetching = new Set<string>();
  $effect(() => {
    for (const g of fresh) {
      const gh = ghostById(tagOf(g));
      if (!gh?.drawing || fetching.has(gh.id)) continue;
      fetching.add(gh.id);
      void fetch(gh.drawing).then((r) => (r.ok ? r.blob() : null)).then((b) => { if (b) nowPics = { ...nowPics, [gh.id]: URL.createObjectURL(b) }; }).catch(() => {});
    }
  });
  $effect(() => () => { for (const u of Object.values(nowPics)) URL.revokeObjectURL(u); });
  // your drawings as blob: URLs (the Builder's content policy loads images only from itself): an entry with
  // an example is drawn as the whole example word, laid out by your draft as the font will set it (what
  // Publish draft to glossary puts on the page); else the glyph on its own. Drawn once per glyph and example.
  let myPics = $state<Record<string, string>>({});
  const drawnFor: Record<string, string> = {};
  const plainLine = (t: string) => t.replace(/<\/?r>/g, '');
  $effect(() => {
    const design = app.design;
    if (!design) return;
    for (const g of fresh) {
      const r = rowFor(g), key = JSON.stringify(r?.example ?? null);
      if (drawnFor[g] === key || !app.svgs[g]) continue;
      drawnFor[g] = key;
      const put = (svg: string) => {
        if (drawnFor[g] !== key) return;
        if (myPics[g]) URL.revokeObjectURL(myPics[g]);
        myPics = { ...myPics, [g]: URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' })) };
      };
      if (!r?.example) { put(app.svgs[g]); continue; }
      const mark = r.marked ? [g, T.get(app.typing, g).vert_variant].filter(Boolean) : [];
      void api.words(design, [plainLine(r.example[1] || r.example[0])], app.typedWith).then((res) => {
        const w = res.ok ? res.words[0] : null;
        const svg = w && exampleSvg(w.pieces, app.svgs, mark, app.control);
        put(svg ? fitToInk(svg) : app.svgs[g]);
      }).catch(() => put(app.svgs[g]));
    }
  });
  $effect(() => () => { for (const u of Object.values(myPics)) URL.revokeObjectURL(u); });

  /** A new glyph, its spellings and its place in an area go together (Review keeps them together too). */
  function toggle(it: Item, v: boolean) {
    const next = { ...chosen, [it.id]: v };
    if (it.kind === 'glyph' && it.status === 'added') for (const id of companions(items, it.key)) if (id in next) next[id] = v;
    const g = v ? glyphOf(items, it) : null;
    if (g && `glyph:${g}` in next) next[`glyph:${g}`] = true;
    chosen = next;
  }
  /** Tick or untick every change (a new glyph and its spellings stay together either way). */
  const setAll = (v: boolean) => (chosen = Object.fromEntries(items.map((i) => [i.id, v])));

  /** Build a font from the chosen changes only; resolves with the failure, or null. */
  async function buildCheck(inputs: ReturnType<typeof buildInputs>): Promise<string | null> {
    const r = await api.build(inputs);
    if (!r.ok) return r.error ?? 'The check build could not start.';
    let s = r.status;
    while (s.state === 'running') {
      await new Promise((ok) => setTimeout(ok, 800));
      s = await api.buildStatus();
      log = s.log.slice(-4);
    }
    return s.ok ? null : (s.log.join('\n').match(/.*Error.*/)?.[0] ?? 'The font did not build with these changes.');
  }

  /** Keep the form to finish later (the draft is saved first, so the request has a row to sit on). */
  async function saveAsDraft() {
    problem = null;
    keeping = true;
    try {
      if (app.dirty && !(await app.save())) { problem = "Your draft couldn't be saved first. Try again in a moment."; return; }
      await app.keepRequestDraft({ title, notes, credit, chosen: picked.map((i) => i.id), seen: items.map((i) => i.id), saved_at: new Date().toISOString() });
      pilot.say(`Saved "${title.trim() || 'your Change Request'}" as a draft. Finish it from Your Change Requests, or here.`);
      onclose();
    } catch (e) {
      problem = (e as Error).message;
    } finally {
      keeping = false;
    }
  }

  async function send() {
    problem = null;
    const c = hosted.client;
    if (!c || !hosted.user) { problem = 'Sign in again to send.'; return; }
    if (!title.trim()) { problem = 'Give it a title: a few words on what it changes.'; return; }
    if (!picked.length) { problem = 'Tick at least one change to send.'; return; }
    step = 'checking';
    try {
      if (app.dirty && !(await app.save())) { problem = "Your draft couldn't be saved first. Try again in a moment."; return; }
      const { bundle, itemIds } = snapshot(app.bundle(), app.mainSvgs, picked.map((i) => i.id));
      const tagged = Object.fromEntries(fresh.map((g) => [g, tagOf(g)]).filter(([, id]) => id));
      if (Object.keys(tagged).length) bundle.manifest.upcoming = tagged;
      const clash = T.issues(bundle.typing, app.known);
      if (clash.length) { problem = `${clash.length} spelling problem${clash.length === 1 ? '' : 's'} in the chosen changes. Fix them in Glyphs → List view, or leave those spellings out.`; return; }
      const failed = await buildCheck(buildInputs(bundle, app.mainSvgs));
      if (failed) { problem = `The font didn't build with just these changes: ${failed}`; return; }
      step = 'sending';
      if (credit.trim() !== savedCredit) await setCredit(c, credit).catch(() => {});
      const r = await sendRequest(c, { title, notes, credit, bundle, itemIds });
      app.requestSent(r);
      if (app.requestDraft) await app.keepRequestDraft(null).catch(() => {});
      pilot.say(`Sent "${r.title}". Its changes are locked in your draft while it's reviewed.`);
      onclose();
    } catch (e) {
      problem = (e as Error).message;
    } finally {
      step = 'form';
    }
  }
</script>

<div class="modal-bg" role="presentation" onclick={() => step === 'form' && onclose()}>
  <div class="modal send" role="dialog" aria-modal="true" aria-labelledby="send-h" tabindex="-1"
    onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && step === 'form' && onclose()}>
    <h3 id="send-h">Send a Change Request</h3>
    {#if app.requestDraft}<p class="muted small">Your draft from {new Date(app.requestDraft.saved_at).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}. Changes you made since are ticked.</p>{/if}
    <p class="muted">The font's maintainer reviews it and keeps or skips each change. Once it's sent, these changes are locked in your draft: you can read them, but not edit or undo them, unless you withdraw the request or it's declined.</p>

    <fieldset>
      <legend>Changes to send <span class="muted">{picked.length} of {items.length}</span></legend>
      <div class="all">
        <button class="quiet sm" onclick={() => setAll(true)} disabled={step !== 'form' || picked.length === items.length}>Select all</button>
        <button class="quiet sm" onclick={() => setAll(false)} disabled={step !== 'form' || !picked.length}>Clear all</button>
      </div>
      <ul class="pick">
        {#each items as it (it.id)}
          <li><label><input type="checkbox" checked={chosen[it.id]} onchange={(e) => toggle(it, (e.target as HTMLInputElement).checked)} />
            <span class="mono">{nameOf(it)}</span> <span class="tag {it.status}">{it.status}</span>
            {#if it.kind === 'design'}<span class="muted small">{it.summary.join(' · ')}</span>{/if}</label></li>
        {/each}
      </ul>
    </fieldset>

    {#if ghosts.length && fresh.length}
      <fieldset class="coming">
        <legend>Is this for a coming character?</legend>
        <p class="muted small">A glossary entry you're sending can be for a character on the font page's Coming next. The maintainer confirms it, then can show your entry and drawing there for comments.</p>
        {#each fresh as g (g)}
          {@const gh = ghostById(tagOf(g))}
          <div class="tagrow">
            <label class="tagpick"><span><span class="mono">Glossary · {g}</span> is for</span>
              <select value={tagOf(g)} onchange={(e) => (tags = { ...tags, [g]: (e.target as HTMLSelectElement).value })}>
                <option value="">None of these</option>
                {#each ghosts as x (x.id)}<option value={x.id}>{x.zh}{x.pinyin ? ` · ${x.pinyin}` : ''} · {stageLabel(x)}</option>{/each}
              </select>
            </label>
            {#if gh}
              <p class="when"><b>Before</b> <span class="muted small">· the coming character on the font page today</span></p>
              <GlossaryPreview g={{ ...gh, version: gh.release }} drawing={nowPics[gh.id] ?? null} />
              {#if rowFor(g)}
                <p class="when"><b>After</b> <span class="muted small">· your glossary entry, once the maintainer shows it: its words replace {gh.zh.split(' · ')[0]}'s (what it leaves empty stays), and your drawing replaces the old one</span></p>
                <GlossaryPreview g={after(gh, g)} drawing={myPics[g] ?? null} />
              {:else}
                <p class="muted small">{g} has no row in Glyphs › Glossary, so the maintainer can't show it for {gh.zh.split(' · ')[0]}: add its row there first.</p>
              {/if}
            {:else}
              <p class="muted small">Not tagged: nothing about a coming character changes.</p>
            {/if}
          </div>
        {/each}
      </fieldset>
    {/if}

    <label class="field">Title
      <span class="muted small hint">Its line in the release notes.</span>
      <input id="cr-title" type="text" bind:value={title} maxlength="200" placeholder="Tighter spacing for 勾 over 七" />
    </label>
    <label class="field">What you changed and why
      <span class="muted small hint">For the reviewer only, never published.</span>
      <textarea id="cr-notes" bind:value={notes} rows="5" maxlength="20000" placeholder="Which words look better now, what you tried, anything you're unsure about."></textarea>
    </label>
    <label class="field">How would you like to be credited?
      <span class="muted small hint">After "thanks to" in the release notes; empty for none.</span>
      <input id="cr-credit" type="text" bind:value={credit} maxlength="200" placeholder="Your name here" />
    </label>

    {#if problem}<div class="banner danger" role="alert"><span class="ic"><I.Problem /></span><span>{problem}</span></div>{/if}
    {#if step === 'checking'}
      <div class="banner info" role="status"><span class="ic"><I.Working /></span><span>Saving your draft and building a font with just these changes{log.length ? `: ${log.at(-1)}` : '…'}</span></div>
    {/if}

    <div class="row end">
      <button onclick={onclose} disabled={step !== 'form' || keeping}>Cancel</button>
      <button onclick={saveAsDraft} disabled={step !== 'form' || keeping}>{keeping ? 'Saving…' : 'Save as draft'}</button>
      <button class="primary" onclick={send} disabled={step !== 'form' || keeping || !picked.length}><I.Send size={14} /> {step === 'sending' ? 'Sending…' : step === 'checking' ? 'Checking…' : 'Send'}</button>
    </div>
  </div>
</div>

<style>
  .send { width: min(640px, calc(100vw - 2 * var(--space-6))); max-height: calc(100vh - 2 * var(--space-6)); overflow: auto; display: flex; flex-direction: column; gap: var(--space-5); }
  .send h3, .send p { margin: 0; }
  fieldset { border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-4) var(--space-5); margin: 0; }
  legend { padding: 0 var(--space-2); font-weight: 600; }
  .all { display: flex; gap: var(--space-2); margin: 0 0 var(--space-3) calc(-1 * var(--space-3)); }
  .pick { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); max-height: 220px; overflow: auto; }
  .pick label { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
  .mono { font-family: var(--font-mono); font-size: var(--t-small); }
  .small { font-size: var(--t-small); }
  .field { display: flex; flex-direction: column; gap: var(--space-2); font-weight: 600; }
  .field input, .field textarea { font: inherit; font-weight: 400; }
  .field .muted { font-weight: 400; }
  .field .hint { margin-top: calc(-1 * var(--space-1)); }   /* close under its label */
  .tag.added { color: var(--status-saved); border-color: currentColor; }
  .tag.deleted { color: var(--status-danger); border-color: currentColor; }
  .row.end { display: flex; justify-content: flex-end; gap: var(--space-4); }
  .coming { display: flex; flex-direction: column; gap: var(--space-3); }
  .coming p { margin: 0; }
  .when { margin: var(--space-3) 0 0; }
  .tagrow { display: flex; flex-direction: column; gap: var(--space-2); }
  .tagpick { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-3); }
  .tagpick select { font: inherit; max-width: 100%; }
</style>
