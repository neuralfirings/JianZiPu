<script lang="ts">
  // Your Change Requests (hosted): each one's status, what the maintainer said, which release its
  // changes went into, and what was sent (read-only). Withdraw while nothing in it has been kept.
  import * as I from '$lib/icons';
  import { onMount } from 'svelte';
  import { hosted } from '$lib/hosted.svelte';
  import { day, hhmm, pilot } from '$lib/pilot.svelte';
  import { canWithdraw, keptIds, withdraw, type ChangeRequest } from '$lib/requests';
  import { app } from '$lib/state.svelte';
  import ReviewView from '$lib/components/ReviewView.svelte';
  import RequestStatus from '$lib/components/RequestStatus.svelte';

  let err = $state<string | null>(null);
  let open = $state<Record<string, boolean>>({});
  let asking = $state<string | null>(null);

  onMount(() => {
    if (hosted.isHosted) app.refreshRequests().catch((e) => (err = (e as Error).message));
    const id = location.hash.slice(1);
    if (id) open = { [id]: true };
  });

  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;
  function outcome(r: ChangeRequest): string {
    const n = r.item_ids.length, kept = keptIds(r).length;
    if (r.status === 'released') return `${kept} of ${plural(n, 'change')} in v${r.release}`;
    if (r.status === 'in_candidate') return `${kept} of ${plural(n, 'change')} in the v${r.release} release candidate`;
    if (r.status === 'in_review' && Object.keys(r.decisions).length) return `${kept} of ${plural(n, 'change')} kept so far`;
    return plural(n, 'change');
  }
  async function dropDraft() {
    asking = null;
    try {
      await app.keepRequestDraft(null);
      pilot.say('Deleted the draft request. Your changes are still in your draft.');
    } catch (e) {
      err = (e as Error).message;
    }
  }
  async function takeBack(r: ChangeRequest) {
    asking = null;
    try {
      const ok = await withdraw(hosted.client!, r.id);
      await app.refreshRequests();
      pilot.say(ok ? `Withdrew "${r.title}". Its changes are unlocked in your draft.` : `"${r.title}" can't be withdrawn any more: the maintainer has kept some of its changes.`);
    } catch (e) {
      err = (e as Error).message;
    }
  }
</script>

<div class="page">
  <div class="row top">
    <h2>Your Change Requests</h2>
    <span class="spacer"></span>
    {#if hosted.isHosted}<a href="/review?mine">Your changes</a>{/if}
  </div>
  {#if !hosted.isHosted}
    <p class="muted">Testers send Change Requests from the online Builder. On your own computer, the requests you receive are on <a href="/review">Review</a>.</p>
  {:else}
    <p class="muted">Each request is a set of changes from your draft that you sent for the font. While it's being looked at, its changes are locked in your draft. You get an email when its status changes.</p>
    {#if err}<div class="banner danger" role="alert"><span class="ic"><I.Problem /></span><span>{err}</span></div>{/if}
    {#if app.requestDraft}
      {@const d = app.requestDraft}
      <article class="req unsent">
        <div class="rhead">
          <h3>{d.title.trim() || 'Untitled Change Request'}</h3>
          <span class="pill draft"><I.Draft size={14} />Draft · not sent</span>
          <span class="spacer"></span>
          {#if asking === 'draft'}
            <span class="muted small">Delete this draft request? Your changes stay in your draft.</span>
            <button class="sm" onclick={() => (asking = null)}>Keep it</button>
            <button class="sm danger" onclick={dropDraft}>Delete</button>
          {:else}
            <button class="sm" onclick={() => (asking = 'draft')}>Delete…</button>
          {/if}
          <a class="btnlink" href="/review?mine&send">Continue…</a>
        </div>
        <p class="muted small">Saved {day(d.saved_at)} {hhmm(d.saved_at)} · {plural(d.chosen.length, 'change')} ticked{d.credit ? ` · credited as ${d.credit}` : ''}</p>
        {#if d.notes}<p class="notes">{d.notes}</p>{/if}
      </article>
    {/if}
    {#if !app.requests.length && !app.requestDraft}
      <p class="empty">None yet. On <a href="/review?mine">Your changes</a>, choose <strong>Send Change Request…</strong> when some of your changes are ready.</p>
    {/if}
    {#each app.requests as r (r.id)}
      <article class="req" id={r.id}>
        <div class="rhead">
          <h3>{r.title}</h3>
          <RequestStatus status={r.status} release={r.release} />
          <span class="spacer"></span>
          {#if canWithdraw(r)}
            {#if asking === r.id}
              <span class="muted small">Withdraw it? Its changes unlock in your draft.</span>
              <button class="sm" onclick={() => (asking = null)}>Keep it</button>
              <button class="sm danger" onclick={() => takeBack(r)}>Withdraw</button>
            {:else}
              <button class="sm" onclick={() => (asking = r.id)}><I.Withdraw size={14} /> Withdraw…</button>
            {/if}
          {/if}
        </div>
        <p class="muted small">Sent {day(r.created_at)} {hhmm(r.created_at)} · {outcome(r)}{r.credit ? ` · credited as ${r.credit}` : ''}</p>
        {#if r.notes}<p class="notes">{r.notes}</p>{/if}
        {#if r.reply}
          <div class="reply"><b>The maintainer replied{r.reviewed_at ? ` on ${day(r.reviewed_at)}` : ''}</b><p>{r.reply}</p></div>
        {/if}
        <button class="link" onclick={() => (open = { ...open, [r.id]: !open[r.id] })}>
          {#if open[r.id]}<I.Unfolded size={14} />{:else}<I.Folded size={14} />{/if} {open[r.id] ? 'Hide' : 'Show'} what was sent
        </button>
        {#if open[r.id] && app.design}
          <ReviewView bundle={r.bundle} mode="sent" name={r.title} />
        {/if}
      </article>
    {/each}
  {/if}
</div>

<style>
  .page { padding: var(--space-7) max(var(--space-6), env(safe-area-inset-left, 0px)); display: flex; flex-direction: column; gap: var(--space-5); max-width: 1020px; }
  h2 { margin: 0; font-size: var(--t-heading); font-weight: 600; }
  h3 { margin: 0; font-family: var(--font-display); }
  .top { align-items: center; }
  .spacer { flex: 1; }
  .req { border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-5); background: var(--bg-panel); display: flex; flex-direction: column; gap: var(--space-3); }
  .req p { margin: 0; }
  .rhead { display: flex; align-items: center; gap: var(--space-4); flex-wrap: wrap; }
  .req.unsent { border-style: dashed; }
  .btnlink { font-weight: 600; }
  .notes { white-space: pre-wrap; max-width: 70ch; }
  .reply { border-left: 2px solid var(--link); padding: var(--space-2) var(--space-4); background: var(--bg-sunken); }
  .reply p { white-space: pre-wrap; margin-top: var(--space-2); }
  .link { border: 0; background: none; color: var(--link); padding: 0; height: auto; align-self: flex-start; display: inline-flex; gap: var(--space-2); align-items: center; }
  .small { font-size: var(--t-small); }
  .empty { color: var(--ink-muted); }
</style>
