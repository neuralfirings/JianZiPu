<script lang="ts">
  // Review › Feedback (admin): the font page's feedback as an inbox. Messages on the left, newest
  // first; the one you open on the right with its pictures (from the private bucket), its sender and
  // details, and your status, ticket link and note. Opening a new message marks it Read. Its coming
  // character (feedback.upcoming_id) shows as the font page will; link it to one, make a new one, or unlink.
  // Find looks for a message by its id (#a1b2c3d4, for "dup of …" notes) or its words.
  import * as I from '$lib/icons';
  import { hosted } from '$lib/hosted.svelte';
  import { day, hhmm, pilot } from '$lib/pilot.svelte';
  import { aboutOf, allFeedback, KIND_LABEL, OPEN, otherDetails, pictureBlobs, shortId, STATUSES, STATUS_LABEL, STATUS_PILL, updateFeedback, type Feedback, type FeedbackKind, type FeedbackStatus } from '$lib/feedback';
  import { allUpcoming, createUpcoming, drawingBlob, stageLabel, type UpcomingRow } from '$lib/upcoming';
  import GlossaryPreview from './GlossaryPreview.svelte';

  /** `focus`: a message to open (the admins' email links to it: ?tab=feedback&f=<id>). */
  let { focus = null, onupcoming, oncount }: { focus?: string | null; onupcoming?: (id: string) => void; oncount?: (n: number) => void } = $props();

  let list = $state<Feedback[] | null>(null);
  let err = $state<string | null>(null);
  let show = $state<'open' | FeedbackStatus | 'all'>('open');
  let kind = $state<'all' | FeedbackKind>('all');
  let openId = $state<string | null>(null);
  const byStatus = (f: Feedback, v: typeof show) => v === 'all' || (v === 'open' ? OPEN.includes(f.status) : f.status === v);
  const byKind = (f: Feedback, v: typeof kind) => v === 'all' || f.kind === v;
  /** Find: an id (with or without its #) or words from the message, its sender or what it's about. */
  let q = $state('');
  const byText = (f: Feedback) => {
    const t = q.trim().replace(/^#/, '').toLowerCase();
    return !t || f.id.startsWith(t) || [f.message, f.name, f.email, aboutOf(f), f.note].some((x) => (x ?? '').toLowerCase().includes(t));
  };
  let shown = $derived((list ?? []).filter((f) => byStatus(f, show) && byKind(f, kind) && byText(f)));
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
    try { upcoming = await allUpcoming(hosted.client!); } catch { upcoming = []; }
  }

  // ---- the open message's coming character
  let upcoming = $state<UpcomingRow[] | null>(null);
  let linked = $derived(current?.upcoming_id ? upcoming?.find((u) => u.id === current!.upcoming_id) ?? null : null);
  let linkable = $derived((upcoming ?? []).filter((u) => u.stage !== 'released'));
  let linking = $state(false);
  let pick = $state('');
  let ghostPic = $state<string | null>(null);
  let picFor = '';
  $effect(() => {
    const u = linked, key = u ? `${u.id}:${u.drawing}:${u.updated_at}` : '';
    if (key === picFor) return;
    picFor = key;
    if (ghostPic) URL.revokeObjectURL(ghostPic);
    ghostPic = null;
    if (u?.drawing) void drawingBlob(hosted.client!, u.drawing).then((url) => { if (picFor === key) ghostPic = url; else if (url) URL.revokeObjectURL(url); });
  });
  async function link(id: string | null) {
    await save({ upcoming_id: id }, true);
    linking = false;
    pilot.say(id ? `Linked to ${id}.` : 'Unlinked: no coming character.');
  }
  /** A new coming character from this message: its 中文 and pinyin (a request's, else what it's about), the message as the definition. */
  async function newGhost() {
    const f = current!, d = f.details ?? {};
    const s = (k: string) => (typeof d[k] === 'string' ? (d[k] as string).trim() : '');
    const zh = s('zh') || (f.kind === 'row' ? (f.glossary_row ?? '').split(' · ')[1] ?? '' : '');
    try {
      const u = await createUpcoming(hosted.client!, { zh, pinyin: s('pinyin') || null, meaning: f.kind === 'request' ? f.message : null, feedback_id: f.id });
      upcoming = [...(upcoming ?? []), u];
      await save({ upcoming_id: u.id }, true);
      linking = false;
      pilot.say(`Made ${u.id} and linked it. Give it a section in Glossary drafts to show it on the font page.`);
    } catch (e) {
      err = (e as Error).message;
    }
  }
  async function copyId(id: string) {
    try { await navigator.clipboard.writeText(shortId(id)); pilot.say(`Copied #${shortId(id)}.`); } catch { /* the id is on screen to copy by hand */ }
  }
  let focused = '';
  $effect(() => {
    // the full id (the email's link), or the short one from a note (6 characters or more)
    const f = focus && list?.find((x) => x.id === focus || (focus.length >= 6 && x.id.startsWith(focus.replace(/^#/, ''))));
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
    linking = false;
    pick = '';
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
  <label class="muted small">Find <input id="fb-find" type="search" placeholder="#a1b2c3d4, or words" bind:value={q} /></label>
  <span class="spacer"></span>
  <button class="quiet sm" onclick={() => { list = null; upcoming = null; }} data-tip="Load the messages again" aria-label="Reload"><I.Refresh /></button>
</div>

{#if err}<div class="banner danger"><span class="ic"><I.Problem /></span><span>{err}</span></div>{/if}

{#if list === null}
  <p class="muted">Loading feedback…</p>
{:else if !shown.length}
  <p class="muted">{q.trim() ? `Nothing matches "${q.trim()}" here.${show !== 'all' || kind !== 'all' ? ' Try Show: All and All kinds.' : ''}` : show === 'open' ? 'Nothing open: no message is New, Read or Need info.' : 'None.'}</p>
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
          <span class="spacer"></span>
          <code class="fid" title={current.id}>#{shortId(current.id)}</code>
          <button class="quiet sm" onclick={() => copyId(current!.id)} data-tip="Copy its id, for a note like “dup of feedback #{shortId(current.id)}”" aria-label="Copy its id">Copy</button>
        </div>
        {#if aboutOf(current)}<h3 class="cjk-about">{aboutOf(current)}</h3>{/if}
        <p class="body">{current.message}</p>

        <dl class="facts">
          <dt>From</dt>
          <dd>{current.name || 'No name given'}{#if current.email}{' · '}<a href={`mailto:${current.email}`}>{current.email}</a>{/if}</dd>
          {#if current.link}<dt>On the page</dt><dd><a href={current.link} target="_blank" rel="noopener">{current.link.replace(/^https?:\/\//, '')} <I.Opens size={12} /></a></dd>{/if}
          {#each otherDetails(current) as [k, v]}<dt>{k}</dt><dd>{v}</dd>{/each}
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

        <section class="ghost" aria-label="Coming character">
          <div class="ghead">
            <h4>Coming character</h4>
            {#if linked}
              <span class="muted small">{linked.id} · {stageLabel(linked)}</span>
              <span class="spacer"></span>
              <button class="sm" onclick={() => onupcoming?.(linked!.id)}><I.EditRow size={14} /> Edit in Glossary drafts</button>
              <button class="sm" onclick={() => { linking = !linking; pick = ''; }}>Change…</button>
              <button class="sm" onclick={() => link(null)}>Unlink</button>
            {:else if current.upcoming_id}
              <span class="muted small">{upcoming === null ? `${current.upcoming_id} · loading…` : `${current.upcoming_id} isn't in Glossary drafts any more`}</span>
              <span class="spacer"></span>
              <button class="sm" onclick={() => { linking = !linking; pick = ''; }}>Change…</button>
              <button class="sm" onclick={() => link(null)}>Unlink</button>
            {:else}
              <span class="muted small">None linked{current.kind === 'request' ? ': WIP makes one' : ''}</span>
              <span class="spacer"></span>
              <button class="sm" onclick={() => { linking = !linking; pick = ''; }}>Link…</button>
            {/if}
          </div>
          {#if linking}
            <div class="linkrow">
              <select id="fb-link" bind:value={pick} aria-label="Coming character to link">
                <option value="">Choose a coming character…</option>
                {#each linkable as u (u.id)}<option value={u.id}>{u.zh || '(no 中文)'}{u.pinyin ? ` · ${u.pinyin}` : ''} ({u.id}) · {stageLabel(u)}</option>{/each}
              </select>
              <button onclick={() => link(pick)} disabled={!pick || pick === current.upcoming_id}>Link</button>
              <span class="muted small">or</span>
              <button onclick={newGhost}><I.Plus size={14} /> New coming character</button>
              <button class="quiet" onclick={() => (linking = false)}>Cancel</button>
            </div>
            <p class="muted small">Link a duplicate request to the character the first one made. A new one starts as Planned, filled from this message, and isn't on the page until it has a section.</p>
          {/if}
          {#if linked && linked.stage !== 'released'}
            <GlossaryPreview g={linked} drawing={ghostPic} />
          {:else if linked}
            <p class="muted small">In the font{linked.version ? ` since ${linked.version}` : ''}: the page shows its own row now.</p>
          {/if}
        </section>

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
  .fid { font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-muted); }
  .ghost { display: flex; flex-direction: column; gap: var(--space-3); border-top: 1px solid var(--border); padding-top: var(--space-5); }
  .ghead { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; }
  .ghead h4 { margin: 0; font-size: var(--t-panel); }
  .linkrow { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; }
  .linkrow select { max-width: 420px; }
  .ghost p { margin: 0; }
  .ticket { display: flex; gap: var(--space-3); align-items: center; }
  .ticket input { flex: 1; }
  .row { display: flex; gap: var(--space-4); align-items: center; }
  .link { border: 0; background: none; color: var(--link); padding: 0; height: auto; font-weight: 400; }
  @media (max-width: 759.98px) { .inbox { grid-template-columns: 1fr; } }
</style>
