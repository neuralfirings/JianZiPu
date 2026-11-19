<script lang="ts">
  // Review › Feedback (admin): the font page's feedback as an inbox. Messages on the left, newest
  // first; the one you open on the right with its pictures (from the private bucket), its sender and
  // details, and your status, ticket link and note. Opening a new message marks it Read.
  import * as I from '$lib/icons';
  import { hosted } from '$lib/hosted.svelte';
  import { day, hhmm, pilot } from '$lib/pilot.svelte';
  import { aboutOf, allFeedback, KIND_LABEL, OPEN, otherDetails, pictureBlobs, STATUSES, STATUS_LABEL, STATUS_PILL, updateFeedback, type Feedback, type FeedbackKind, type FeedbackStatus } from '$lib/feedback';

  /** `focus`: a message to open (the admins' email links to it: ?tab=feedback&f=<id>). */
  let { focus = null, onupcoming, oncount }: { focus?: string | null; onupcoming?: (id: string) => void; oncount?: (n: number) => void } = $props();

  let list = $state<Feedback[] | null>(null);
  let err = $state<string | null>(null);
  let show = $state<'open' | FeedbackStatus | 'all'>('open');
  let kind = $state<'all' | FeedbackKind>('all');
  let openId = $state<string | null>(null);
  const byStatus = (f: Feedback, v: typeof show) => v === 'all' || (v === 'open' ? OPEN.includes(f.status) : f.status === v);
  const byKind = (f: Feedback, v: typeof kind) => v === 'all' || f.kind === v;
  let shown = $derived((list ?? []).filter((f) => byStatus(f, show) && byKind(f, kind)));
  /** How many each choice would show, given the other menu's choice (the Show counts are for the chosen kind). */
  const nStatus = (v: typeof show) => (list ?? []).filter((f) => byStatus(f, v) && byKind(f, kind)).length;
  const nKind = (v: typeof kind) => (list ?? []).filter((f) => byStatus(f, show) && byKind(f, v)).length;
  /** The statuses to offer: the menu's, and an old one (ticket) while any message still has it. */
  let showable = $derived([...STATUSES, ...[...new Set((list ?? []).map((f) => f.status))].filter((s) => !STATUSES.includes(s))]);
  let current = $derived(list?.find((f) => f.id === openId) ?? null);

  const ICON = { new: I.Info, read: I.Check, need_info: I.Help, wip: I.Draft, ticket: I.Link, done: I.Check, wont_do: I.Close };

  $effect(() => { if (list === null && hosted.client) void load(); });
  $effect(() => { if (list) oncount?.(list.filter((f) => f.status === 'new').length); });
  async function load() {
    err = null;
    try { list = await allFeedback(hosted.client!); } catch (e) { err = (e as Error).message; list = []; }
  }
  let focused = '';
  $effect(() => {
    const f = focus && list?.find((x) => x.id === focus);
    if (!f || focused === f.id) return;
    focused = f.id;
    if (!shown.includes(f)) { show = 'all'; kind = 'all'; }
    void open(f);
  });

  // the open message's form
  let status = $state<FeedbackStatus>('new');
  let ticket = $state('');
  let note = $state('');
  let pics = $state<Record<string, string>>({});
  let picErr = $state<string | null>(null);
  let saving = $state(false);
  let dirty = $derived(!!current && (status !== current.status || ticket.trim() !== (current.ticket ?? '') || note.trim() !== (current.note ?? '')));

  async function open(f: Feedback) {
    openId = f.id;
    status = f.status === 'new' ? 'read' : f.status;
    ticket = f.ticket ?? '';
    note = f.note ?? '';
    for (const u of Object.values(pics)) URL.revokeObjectURL(u);
    pics = {};
    picErr = null;
    if (f.pictures.length) pictureBlobs(hosted.client!, f.pictures).then((u) => { if (openId === f.id) pics = u; else for (const x of Object.values(u)) URL.revokeObjectURL(x); }, (e) => (picErr = (e as Error).message));
    if (f.status === 'new') await save({ status: 'read' }, true);
  }
  async function save(patch: Parameters<typeof updateFeedback>[2] = { status, ticket: ticket.trim() || null, note: note.trim() || null }, quiet = false) {
    if (!current) return;
    saving = true;
    try {
      const was = current.status;
      const row = await updateFeedback(hosted.client!, current.id, patch);
      list = list!.map((f) => (f.id === row.id ? { ...f, ...row, kind: row.kind ?? f.kind, pictures: row.pictures ?? f.pictures } : f));
      if (!quiet) pilot.say(row.kind === 'request' && row.status === 'wip' && was !== 'wip' && row.upcoming_id
        ? `Saved. ${aboutOf(row) || 'The character'} is in Glossary drafts now (Planned): give it a section there to show it on the font page.`
        : 'Saved.');
    } catch (e) {
      err = (e as Error).message;
    } finally {
      saving = false;
    }
  }
</script>

<div class="bar">
  <label class="muted small">Show
    <select id="fb-show" bind:value={show}>
      <option value="open">Open: New, Read, Need info ({nStatus('open')})</option>
      {#each showable as s}<option value={s}>{STATUS_LABEL[s]} ({nStatus(s)})</option>{/each}
      <option value="all">All ({nStatus('all')})</option>
    </select>
  </label>
  <label class="muted small">Kind
    <select id="fb-kind" bind:value={kind}>
      <option value="all">All kinds ({nKind('all')})</option>
      {#each Object.entries(KIND_LABEL) as [k, label]}<option value={k}>{label} ({nKind(k as FeedbackKind)})</option>{/each}
    </select>
  </label>
  <span class="spacer"></span>
  <button class="quiet sm" onclick={() => { list = null; }} data-tip="Load the messages again" aria-label="Reload"><I.Refresh /></button>
</div>

{#if err}<div class="banner danger"><span class="ic"><I.Problem /></span><span>{err}</span></div>{/if}

{#if list === null}
  <p class="muted">Loading feedback…</p>
{:else if !shown.length}
  <p class="muted">{show === 'open' ? 'Nothing open: no message is New, Read or Need info.' : 'None.'}</p>
{:else}
  <div class="inbox">
    <ul class="msgs" aria-label="Messages">
      {#each shown as f (f.id)}
        {@const Ic = ICON[f.status]}
        <li>
          <button class="msg" class:on={f.id === openId} class:unread={f.status === 'new'} onclick={() => open(f)}>
            <span class="top">
              <span class="tag">{KIND_LABEL[f.kind]}</span>
              {#if aboutOf(f)}<span class="about">{aboutOf(f)}</span>{/if}
              <span class="spacer"></span>
              <span class="when muted small">{day(f.created_at)}</span>
            </span>
            <span class="text">{f.message}</span>
            <span class="foot">
              <span class="pill {STATUS_PILL[f.status]} sm"><Ic size={12} />{STATUS_LABEL[f.status]}</span>
              <span class="muted small">{f.name || 'no name'}</span>
              {#if f.pictures.length}<span class="muted small"><I.Preview size={12} /> {f.pictures.length}</span>{/if}
              {#if f.note}<span class="muted small"><I.Description size={12} /> note</span>{/if}
              {#if f.ticket}<span class="muted small"><I.Link size={12} /> ticket</span>{/if}
            </span>
          </button>
        </li>
      {/each}
    </ul>

    <section class="detail" aria-label="Message">
      {#if !current}
        <p class="muted">Open a message to read it, see its pictures and set its status.</p>
      {:else}
        <div class="head">
          <span class="tag">{KIND_LABEL[current.kind]}</span>
          <span class="muted small">{day(current.created_at)} {hhmm(current.created_at)}</span>
        </div>
        {#if aboutOf(current)}<h3 class="cjk-about">{aboutOf(current)}</h3>{/if}
        <p class="body">{current.message}</p>

        <dl class="facts">
          <dt>From</dt>
          <dd>{current.name || 'No name given'}{#if current.email}{' · '}<a href={`mailto:${current.email}`}>{current.email}</a>{/if}</dd>
          {#if current.link}<dt>On the page</dt><dd><a href={current.link} target="_blank" rel="noopener">{current.link.replace(/^https?:\/\//, '')} <I.Opens size={12} /></a></dd>{/if}
          {#each otherDetails(current) as [k, v]}<dt>{k}</dt><dd>{v}</dd>{/each}
          {#if current.upcoming_id}
            <dt>Coming character</dt>
            <dd><button class="link" onclick={() => onupcoming?.(current!.upcoming_id!)}>{current.upcoming_id} in Glossary drafts</button></dd>
          {/if}
        </dl>

        {#if current.pictures.length}
          <div class="pics">
            {#each current.pictures as p (p)}
              {#if pics[p]}
                <a href={pics[p]} target="_blank" rel="noopener" data-tip="Open full size"><img src={pics[p]} alt={`Picture ${p.split('/').pop()}`} /></a>
              {:else}
                <span class="pic-wait muted small">{picErr ? 'Picture not loaded' : 'Loading…'}</span>
              {/if}
            {/each}
          </div>
          {#if picErr}<p class="muted small">Couldn't load the pictures: {picErr}</p>{/if}
        {/if}

        <div class="form">
          <label>Status
            <select id="fb-status" bind:value={status}>
              {#each STATUSES as s}<option value={s}>{STATUS_LABEL[s]}</option>{/each}
              {#if !STATUSES.includes(current.status)}<option value={current.status}>{STATUS_LABEL[current.status]}</option>{/if}
            </select>
          </label>
          {#if status === 'wip' && current.kind === 'request' && !current.upcoming_id}
            <p class="muted small">WIP adds this character to Glossary drafts as Planned.</p>
          {/if}
          <label>Ticket <span class="muted small">(a link, if it became one)</span>
            <span class="ticket"><input id="fb-ticket" type="url" placeholder="https://github.com/…/issues/…" bind:value={ticket} />
              {#if current.ticket}<a href={current.ticket} target="_blank" rel="noopener" data-tip="Open the ticket" aria-label="Open the ticket"><I.Opens /></a>{/if}</span>
          </label>
          <label>Your note <span class="muted small">(only admins see it)</span>
            <textarea id="fb-note" rows="3" bind:value={note}></textarea>
          </label>
          <div class="row">
            <span class="spacer"></span>
            {#if dirty}<span class="pill draft sm"><I.Unsaved size={12} />Not saved</span>{/if}
            <button class="primary" onclick={() => save()} disabled={!dirty || saving}>{saving ? 'Saving…' : 'Save'}</button>
          </div>
        </div>
      {/if}
    </section>
  </div>
{/if}

<style>
  .bar { display: flex; gap: var(--space-5); align-items: center; flex-wrap: wrap; }
  .spacer { flex: 1; }
  .inbox { display: grid; grid-template-columns: minmax(280px, 400px) 1fr; gap: var(--space-6); align-items: start; }
  .msgs { list-style: none; margin: 0; padding: 0; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); max-height: 70vh; overflow: auto; }
  .msgs li + li { border-top: 1px solid var(--border); }
  .msg { display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; gap: var(--space-2); width: 100%; height: auto; padding: var(--space-4) var(--space-5); border: 0; border-radius: 0; background: transparent; text-align: left; font-weight: 400; }
  .msg:hover { background: var(--bg-hover); }
  .msg.on { background: var(--sel-bg); box-shadow: inset 3px 0 0 var(--sel-border); }
  .msg.unread .text { font-weight: 600; color: var(--ink); }
  .top, .foot { display: flex; gap: var(--space-3); align-items: center; min-width: 0; }
  .top .tag, .foot .pill, .when { flex-shrink: 0; }
  .about { font-family: var(--font-serif); color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .text { color: var(--ink-muted); display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  .pill.sm { height: 20px; padding: 0 var(--space-3); font-size: var(--t-caption); }
  .detail { border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-panel); padding: var(--space-6); display: flex; flex-direction: column; gap: var(--space-4); min-height: 240px; }
  .head { display: flex; gap: var(--space-3); align-items: center; }
  .cjk-about { margin: 0; font-family: var(--font-serif); font-size: var(--t-heading); font-weight: 600; }
  .body { margin: 0; white-space: pre-wrap; font-size: var(--t-body); }
  .facts { display: grid; grid-template-columns: max-content 1fr; gap: var(--space-2) var(--space-5); margin: 0; font-size: var(--t-small); }
  .facts dt { color: var(--ink-muted); }
  .facts dd { margin: 0; overflow-wrap: anywhere; }
  .pics { display: flex; flex-wrap: wrap; gap: var(--space-4); }
  .pics img { display: block; max-width: 220px; max-height: 220px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-field); object-fit: contain; }
  .pic-wait { display: grid; place-items: center; width: 160px; height: 120px; border: 1px dashed var(--border); border-radius: var(--radius-md); }
  .form { display: flex; flex-direction: column; gap: var(--space-4); border-top: 1px solid var(--border); padding-top: var(--space-5); }
  .form label { display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--t-small); }
  .form select { max-width: 220px; }
  .ticket { display: flex; gap: var(--space-3); align-items: center; }
  .ticket input { flex: 1; }
  .row { display: flex; gap: var(--space-4); align-items: center; }
  .link { border: 0; background: none; color: var(--link); padding: 0; height: auto; font-weight: 400; }
  @media (max-width: 759.98px) { .inbox { grid-template-columns: 1fr; } }
</style>
