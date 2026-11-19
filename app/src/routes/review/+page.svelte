<script lang="ts">
  // Review (docs/PILOT-UX.md "Review"). Signed in as an admin (local, or online): testers' Change
  // Requests (Keep / Skip each change and reply; saved on the request, applied later in a release
  // candidate, see /release, which is local only), their current drafts, or a .zip, applied into your
  // unsaved changes (online: into your own draft).
  // Hosted, not an admin: a tester's Your changes (?mine) or an imported .zip (set by the ⋯ menu through `pilot.review`).
  // ?request=<id> opens one Change Request (the link in the admins' email).
  import * as I from '$lib/icons';
  import { page } from '$app/state';
  import { beforeNavigate, goto } from '$app/navigation';
  import { BundleError, fromZip } from '$lib/bundle';
  import { listDrafts, loadDraftOf, type DraftRow } from '$lib/drafts';
  import { hosted } from '$lib/hosted.svelte';
  import { diffBundle } from '$lib/merge';
  import { app } from '$lib/state.svelte';
  import { day, downloadZip, hhmm, markReviewed, pilot, reviewedMarks } from '$lib/pilot.svelte';
  import { allRequests, keptIds, OPEN, saveDecisions, STATUS_LABEL, type ChangeRequest, type RequestStatus } from '$lib/requests';
  import ReviewView from '$lib/components/ReviewView.svelte';
  import RequestStatusPill from '$lib/components/RequestStatus.svelte';
  import ComingDrafts from '$lib/components/ComingDrafts.svelte';
  import FeedbackInbox from '$lib/components/FeedbackInbox.svelte';
  import GlossaryDrafts from '$lib/components/GlossaryDrafts.svelte';

  let mine = $derived(page.url.searchParams.has('mine'));
  /** The admin's three lists: ?tab=feedback, ?tab=glossary (&u=<id> opens one), else Change Requests. */
  let tab = $derived<'requests' | 'feedback' | 'glossary'>(page.url.searchParams.get('tab') === 'feedback' ? 'feedback' : page.url.searchParams.get('tab') === 'glossary' ? 'glossary' : 'requests');
  let newFeedback = $state<number | null>(null);
  let coming = $state<number | null>(null);
  const toTab = (t: string, extra = '') => goto(`/review${t === 'requests' ? '' : `?tab=${t}${extra}`}`, { keepFocus: true, noScroll: true });
  let err = $state<string | null>(null);
  let fileInput = $state<HTMLInputElement | null>(null);

  // "See my changes" (hosted): the draft as it is now, unsaved edits included
  let myBundle = $derived(mine && hosted.isHosted && app.design ? app.bundle() : null);

  async function openZip(e: Event) {
    err = null;
    const f = (e.target as HTMLInputElement).files?.[0];
    (e.target as HTMLInputElement).value = '';
    if (!f) return;
    try {
      const b = fromZip(new Uint8Array(await f.arrayBuffer()));
      pilot.review = { bundle: b, source: { kind: 'zip', name: b.manifest.author.name || f.name } };
    } catch (ex) {
      err = ex instanceof BundleError
        ? (/no manifest/.test(ex.message) ? `"${f.name}" isn't a Builder draft: it has no manifest.json.` : /newer Builder/.test(ex.message) ? 'This draft was made with a newer Builder. Update this Builder first.' : ex.message)
        : (ex as Error).message;
    }
  }

  /** The admin's screen: Change Requests and testers' drafts (online too, for admins). */
  let owner = $derived(!hosted.isHosted || hosted.isAdmin);

  // ---- Change Requests (signed in as an admin)
  let requests = $state<ChangeRequest[] | null>(null);
  let reqErr = $state<string | null>(null);
  let show = $state<'open' | RequestStatus | 'all'>('open');
  let current = $state<ChangeRequest | null>(null);
  let reply = $state('');
  let shown = $derived((requests ?? []).filter((r) => show === 'all' || (show === 'open' ? OPEN.includes(r.status) : r.status === show)));
  $effect(() => {
    if (hosted.user && hosted.isAdmin && requests === null && app.design) void loadRequests();
  });
  async function loadRequests() {
    reqErr = null;
    try {
      requests = await allRequests(hosted.client!);
      const id = page.url.searchParams.get('request');
      if (id && !current) { const r = requests.find((x) => x.id === id); if (r) openRequest(r); }
    } catch (e) {
      reqErr = (e as Error).message;
      requests = [];
    }
  }
  function openRequest(r: ChangeRequest) {
    pilot.review = null;
    current = r;
    reply = r.reply;
  }
  async function decide(d: Record<string, 'keep' | 'skip'>): Promise<boolean> {
    const r = current!;
    try {
      await saveDecisions(hosted.client!, r, d, reply);
      const kept = Object.values(d).filter((v) => v === 'keep').length;
      pilot.say(kept ? `Saved: keeping ${kept} of ${r.item_ids.length} from "${r.title}". ${r.author_name} gets an email. Kept changes go into the next release candidate.` : `Declined "${r.title}". ${r.author_name} gets an email, and its changes unlock in their draft.`);
      current = null;
      requests = null;
      return true;
    } catch (e) {
      err = (e as Error).message;
      return false;
    }
  }

  // Keep / Skip and the reply live on this page until Save decisions: ask before leaving them.
  let edited = $state(false);
  let choices = $state<Record<string, 'keep' | 'skip'>>({});
  let unsaved = $derived(!!current && (edited || reply.trim() !== current.reply.trim()));
  /** Where to go after the question: a path, or null for the list of requests. */
  let leave = $state<{ to: string | null } | null>(null);
  let leaving = false;
  beforeNavigate((nav) => {
    // the app's own moves (Try in Build & test, after an Apply) aren't leaving the decisions behind
    if (!unsaved || leaving || nav.type === 'goto') return;
    nav.cancel();
    if (nav.type !== 'leave' && nav.to) leave = { to: nav.to.url.pathname + nav.to.url.search };
  });
  function backToList() {
    if (unsaved) leave = { to: null };
    else current = null;
  }
  async function doLeave(how: 'discard' | 'save') {
    if (!leave) return;
    const to = leave.to;
    if (how === 'save' && !(await decide(choices))) { leave = null; return; }
    leave = null;
    current = null;
    edited = false;
    if (to) { leaving = true; await goto(to); leaving = false; }
  }
  const changesText = (r: ChangeRequest) => {
    const k = keptIds(r).length, n = r.item_ids.length;
    return Object.keys(r.decisions).length ? `${n} · ${k} kept` : `${n}`;
  };

  // ---- testers' drafts (local Builder signed in as the admin)
  type Row = DraftRow & { changes: number | null; behind: boolean; based: string | null };
  let rows = $state<Row[] | null>(null);
  let listErr = $state<string | null>(null);
  let marks = $state(reviewedMarks());
  let email = $state('');
  let sent = $state<string | null>(null);

  $effect(() => {
    if (hosted.user && hosted.isAdmin && rows === null && app.design) void loadRows();
  });
  async function loadRows() {
    listErr = null;
    try {
      const list = await listDrafts(hosted.client!);
      rows = list.map((r) => ({ ...r, changes: null, behind: false, based: null }));
      for (const r of rows) {
        const got = await loadDraftOf(hosted.client!, r.uid).catch(() => null);
        if (!got) continue;
        const b = got.bundle;
        r.changes = diffBundle(b, { design: app.design!, typing: app.typing, svgs: app.svgs, glossary: app.glossary, glossaryLayout: app.glossaryLayout }).length;
        r.behind = b.manifest.base.design_hash !== app.diskHash || b.manifest.base.csv_hash !== app.csvHash;
        r.based = b.manifest.base.date ?? null;
      }
      rows = [...rows];
    } catch (e) {
      listErr = (e as Error).message;
      rows = [];
    }
  }
  async function openDraft(r: Row, zip = false) {
    const got = await loadDraftOf(hosted.client!, r.uid).catch((e) => { err = (e as Error).message; return null; });
    if (!got) return;
    if (zip) { downloadZip(got.bundle); return; }
    pilot.review = { bundle: got.bundle, source: { kind: 'draft', name: r.name, uid: r.uid, stamp: r.stamp } };
  }
  function status(r: Row) {
    const mk = marks[r.uid];
    if (!mk) return 'new';
    return mk.stamp === r.stamp ? `reviewed ${day(mk.at)}` : 'new since you looked';
  }
  async function sendLink() {
    const r = await hosted.sendLink(email);
    sent = r === 'sent' ? `Check your email: a sign-in link went to ${email}.` : r === 'not-invited' ? `${email} isn't a user of this Supabase project.` : r;
  }

  function applied(r: { count: number; message: string }) {
    const src = pilot.review?.source;
    if (src?.kind === 'draft') { markReviewed(src.uid, src.stamp); marks = reviewedMarks(); }
    if (hosted.isHosted) pilot.say(`Applied ${r.count} change${r.count === 1 ? '' : 's'} from ${src?.name}. They're unsaved until Save (or the next autosave).`, { undo: true });
    else pilot.say(`Applied ${r.count} change${r.count === 1 ? '' : 's'} from ${src?.name}'s draft. They're unsaved: look them over, then Save and commit.`, { undo: true, copy: r.message });
    pilot.review = null;
    goto(hosted.isHosted && !owner ? '/layouts' : '/review');
  }
</script>

<div class="page">
  <input type="file" accept=".zip,application/zip" bind:this={fileInput} onchange={openZip} hidden />
  {#if err}<div class="err">{err} <button onclick={() => { err = null; fileInput?.click(); }}>Choose another file</button></div>{/if}

  {#if current}
    <div class="back"><button class="link" onclick={backToList}><I.Back size={14} /> All Change Requests</button></div>
    <div class="crhead">
      <h2>{current.title}</h2>
      <RequestStatusPill status={current.status} release={current.release} />
    </div>
    <p class="muted">From {current.author_name}{#if current.author_email && current.author_email !== current.author_name} ({current.author_email}){/if} · sent {day(current.created_at)} {hhmm(current.created_at)} · {current.credit ? `credit as ${current.credit}` : 'no credit asked for'}</p>
    {#if current.notes}<p class="notes">{current.notes}</p>{/if}
    <label class="replybox">Your reply <span class="muted">(they see it on Your Change Requests and in the email)</span>
      <textarea id="cr-reply" bind:value={reply} rows="3" maxlength="20000"></textarea>
    </label>
    <ComingDrafts request={current} />
    <ReviewView bundle={current.bundle} mode="decide" name={current.title} decisions={current.decisions} ondecide={decide} bind:edited bind:choices />
  {:else if mine && myBundle}
    <ReviewView bundle={myBundle} mode="mine" name="You" onexport={() => (pilot.dialog = 'export')} send={page.url.searchParams.has('send')} />
  {:else if pilot.review}
    <div class="back"><button class="link" onclick={() => (pilot.review = null)}><I.Back size={14} /> {owner ? 'All drafts' : 'Cancel'}</button></div>
    <ReviewView bundle={pilot.review.bundle} mode={hosted.isHosted ? 'import' : 'owner'} name={pilot.review.source.name} onapplied={applied} />
  {:else if !owner}
    <h2>Import a draft</h2>
    <p class="muted">Open a draft .zip (yours, or one someone sent you). You'll see every change before anything goes into your draft.</p>
    <button class="primary" onclick={() => fileInput?.click()}>Choose a .zip…</button>
  {:else}
    <div class="row top">
      <h2>Review</h2>
      <span class="spacer"></span>
      {#if hosted.isHosted}
        <span class="muted small">Only on your own computer</span>
        <button aria-disabled="true" onclick={(e) => e.preventDefault()} data-tip="Releases run git and push to GitHub, so they're made in the Builder on your own computer. Your decisions here are saved in Supabase; its Release screen finds them.">Release</button>
      {:else}<a href="/release">Release <I.Opens size={14} /></a>{/if}
      <button onclick={() => fileInput?.click()}>Open a .zip…</button>
    </div>
    {#if !hosted.canSignIn}
      <p class="muted">Change Requests and testers' drafts appear here when this Builder runs with the Supabase settings (SUPABASE_URL, SUPABASE_ANON_KEY). Open a .zip works without them.</p>
    {:else if !hosted.user}
      <div class="signin">
        <p>Sign in to see testers' drafts (admin emails only). Open a .zip works without signing in.</p>
        <form class="row" onsubmit={(e) => { e.preventDefault(); sendLink(); }}>
          <input type="email" placeholder="your admin email" bind:value={email} required />
          <button class="primary">Email me a sign-in link</button>
        </form>
        {#if sent}<p class="muted">{sent}</p>{/if}
      </div>
    {:else if !hosted.isAdmin}
      <p class="muted">Signed in as {hosted.user.email}, which isn't an admin: only admins see testers' drafts. <button class="link" onclick={() => hosted.signOut()}>Sign out</button></p>
    {/if}
    {#if hosted.user && hosted.isAdmin}
      <div class="tabs" role="group" aria-label="What to review">
        <button class="chip" aria-pressed={tab === 'requests'} onclick={() => toTab('requests')}>Change Requests</button>
        <button class="chip" aria-pressed={tab === 'feedback'} onclick={() => toTab('feedback')}>Feedback{#if newFeedback}<span class="count">{newFeedback} new</span>{/if}</button>
        <button class="chip" aria-pressed={tab === 'glossary'} onclick={() => toTab('glossary')}>Glossary drafts{#if coming != null}<span class="count muted">{coming}</span>{/if}</button>
      </div>
    {/if}
    {#if !hosted.user || !hosted.isAdmin}
      <!-- not an admin: nothing more -->
    {:else if tab === 'feedback'}
      <FeedbackInbox focus={page.url.searchParams.get('f')} onupcoming={(id) => toTab('glossary', `&u=${encodeURIComponent(id)}`)} oncount={(n) => (newFeedback = n)} />
    {:else if tab === 'glossary'}
      <GlossaryDrafts focus={page.url.searchParams.get('u')} oncount={(n) => (coming = n)} />
    {:else}
      <div class="row top">
        <h3>Change Requests</h3>
        <span class="spacer"></span>
        <label class="muted small">Show
          <select id="cr-show" bind:value={show}>
            <option value="open">To review</option>
            {#each Object.entries(STATUS_LABEL) as [k, label]}<option value={k}>{label}</option>{/each}
            <option value="all">All</option>
          </select>
        </label>
      </div>
      {#if requests === null}
        <p class="muted">Loading Change Requests…</p>
      {:else if reqErr}
        <p class="err">Couldn't list Change Requests: {reqErr} <button onclick={loadRequests}>Try again</button></p>
      {:else if !shown.length}
        <p class="muted">{show === 'open' ? 'Nothing to review: no Change Request is waiting.' : 'None.'}</p>
      {:else}
        <table class="list">
          <thead><tr><th>From</th><th>Title</th><th>Sent</th><th>Changes</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {#each shown as r (r.id)}
              <tr>
                <td><b>{r.author_name}</b></td>
                <td>{r.title}</td>
                <td>{day(r.created_at)} {hhmm(r.created_at)}</td>
                <td>{changesText(r)}</td>
                <td><RequestStatusPill status={r.status} release={r.release} /></td>
                <td class="acts"><button class={OPEN.includes(r.status) ? 'primary' : ''} onclick={() => openRequest(r)}>{OPEN.includes(r.status) ? 'Review' : 'Open'}</button></td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
      <h3>Current drafts</h3>
      <p class="muted small">What each tester is working on now, sent or not. Applying a draft directly skips the Change Request; use it for a .zip or to look ahead.{#if hosted.isHosted}{' '}Here, Apply puts the changes into your own draft.{/if}</p>
    {/if}
    {#if !hosted.canSignIn || !hosted.user || !hosted.isAdmin || tab !== 'requests'}
      <!-- signed out, or another list: nothing more -->
    {:else if rows === null}
      <p class="muted">Loading drafts…</p>
    {:else if listErr}
      <p class="err">Couldn't list drafts: {listErr} <button onclick={loadRows}>Try again</button></p>
    {:else if !rows.length}
      <p class="muted">No tester has saved a draft yet. Drafts appear here after a tester's first save. You can still open a .zip.</p>
    {:else}
      <table class="list">
        <thead><tr><th>Tester</th><th>Last saved</th><th>Based on</th><th>Changes</th><th>Status</th><th></th></tr></thead>
        <tbody>
          {#each rows as r (r.uid)}
            <tr>
              <td><b>{r.name}</b>{#if r.email && r.email !== r.name}<br /><span class="muted small">{r.email}</span>{/if}</td>
              <td>{day(r.stamp)} {hhmm(r.stamp)}</td>
              <td>{r.based ? `the font of ${day(r.based)}` : '—'}{#if r.behind} <span class="tag">behind</span>{/if}</td>
              <td>{r.changes ?? '…'}</td>
              <td><span class:new={status(r) !== 'new' && status(r).startsWith('new')}>{status(r) === 'new' ? '' : status(r)}</span></td>
              <td class="acts"><button class="primary" onclick={() => openDraft(r)}>Review</button> <button onclick={() => openDraft(r, true)}>.zip</button></td>
            </tr>
          {/each}
        </tbody>
      </table>
      <p class="muted small">Signed in as {hosted.user.email} · <button class="link" onclick={() => hosted.signOut()}>Sign out</button></p>
    {/if}
  {/if}
</div>

{#if leave}
  <div class="modal-bg" role="presentation">
    <div class="modal" role="dialog" aria-labelledby="leave-title" tabindex="-1">
      <h3 id="leave-title" style="margin:0">Decisions not saved</h3>
      <p>Your Keep / Skip choices{reply.trim() !== (current?.reply ?? '').trim() ? ' and reply' : ''} on "{current?.title}" aren't saved on the request yet.</p>
      <div class="row"><button onclick={() => (leave = null)}>Keep reviewing</button><button onclick={() => doLeave('discard')}>Leave without saving</button><button class="primary" onclick={() => doLeave('save')}>Save decisions and leave</button></div>
    </div>
  </div>
{/if}

<style>
  .page { padding: var(--space-7) max(var(--space-6), env(safe-area-inset-left, 0px)); display: flex; flex-direction: column; gap: var(--space-5); }
  h2 { margin: 0; font-size: var(--t-heading); font-weight: 600; }
  .top { align-items: center; }
  .spacer { flex: 1; }
  button[aria-disabled='true'], button[aria-disabled='true']:hover { color: var(--ink-faint); border-color: var(--border); background: transparent; cursor: not-allowed; }
  .tabs { display: flex; gap: var(--space-3); flex-wrap: wrap; }
  .tabs .count { margin-left: var(--space-2); font-size: var(--t-caption); font-weight: 600; color: var(--status-info); }
  .tabs .count.muted { color: var(--ink-muted); }
  .err { color: var(--status-danger); display: flex; gap: var(--space-4); align-items: center; }
  .link { border: 0; background: none; color: var(--link); padding: 0; height: auto; }
  .signin { display: flex; flex-direction: column; gap: var(--space-4); max-width: 520px; }
  .signin input { height: var(--control-md); padding: 0 var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-field); flex: 1; }
  .list { border-collapse: collapse; max-width: 980px; }
  .list th, .list td { text-align: left; padding: var(--space-4); border-bottom: 1px solid var(--border); vertical-align: top; }
  .list th { font-weight: 500; color: var(--ink-muted); font-size: var(--t-small); }
  .acts { white-space: nowrap; }
  h3 { margin: var(--space-5) 0 0; }
  .crhead { display: flex; gap: var(--space-4); align-items: center; flex-wrap: wrap; }
  .notes { white-space: pre-wrap; max-width: 70ch; margin: 0; border-left: 2px solid var(--border-strong); padding-left: var(--space-4); }
  .replybox { display: flex; flex-direction: column; gap: var(--space-2); max-width: 70ch; font-weight: 600; }
  .replybox textarea { font: inherit; font-weight: 400; }
  .replybox .muted { font-weight: 400; }
  .tag { font-size: var(--t-caption); padding: 1px 6px; border-radius: 8px; background: var(--bg-hover); color: var(--status-draft); }
  .new { color: var(--link); }
  .small { font-size: var(--t-small); }
</style>
