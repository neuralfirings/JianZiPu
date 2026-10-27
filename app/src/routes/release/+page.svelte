<script lang="ts">
  // Release (local Builder, admin): from reviewed Change Requests to a released font, in the order
  // of builder/README.md "Releases". The git steps run on this machine's web server
  // (jzpbuild/release.py, with your git sign-in); request statuses are set from here, signed in
  // as the admin, which emails the testers (supabase/functions/notify).
  import * as I from '$lib/icons';
  import { onMount } from 'svelte';
  import { api, type ReleaseStatus } from '$lib/api';
  import { hosted } from '$lib/hosted.svelte';
  import { applyMerge } from '$lib/merge';
  import { day, pilot } from '$lib/pilot.svelte';
  import { commitMessage, forRelease, missing, nextVersion, releaseNotes } from '$lib/release';
  import { allRequests, keptIds, setStatus, snapshot, type ChangeRequest } from '$lib/requests';
  import { app } from '$lib/state.svelte';
  import ReviewView from '$lib/components/ReviewView.svelte';
  import RequestStatusPill from '$lib/components/RequestStatus.svelte';

  let st = $state<ReleaseStatus | null>(null);
  let err = $state<string | null>(null);
  let version = $state('');
  let requests = $state<ChangeRequest[] | null>(null);
  let notes = $state('');
  let notesFor: string | null = null;
  /** A request whose kept changes clash with what's already in: picked in Review's view. */
  let resolving = $state<{ r: ChangeRequest; bundle: ChangeRequest['bundle'] } | null>(null);
  /** Requests whose clashes you picked through by hand: in, whatever you picked. */
  let settled = $state<string[]>([]);

  const g = $derived(st?.git);
  const job = $derived(st?.job);
  const running = $derived(job?.state === 'running');
  const onRelease = $derived(!!g?.release);
  const rel = $derived(g?.release ?? version);
  const admin = $derived(!!hosted.user && hosted.isAdmin);
  let taking = $derived(requests && rel ? forRelease(requests, rel) : []);
  const cur = () => ({ design: app.design!, typing: app.typing, svgs: app.svgs });
  let waiting = $derived(app.design ? taking.filter((r) => !settled.includes(r.id) && missing(r, app.mainSvgs, cur()).length) : []);

  async function refresh() {
    try {
      st = await api.releaseStatus();
      if (!version) version = nextVersion(st.git.version);
      if (st.job.state === 'running') setTimeout(refresh, 1000);
    } catch (e) {
      err = (e as Error).message;
    }
  }
  async function loadRequests() {
    if (!admin) return;
    try { requests = await allRequests(hosted.client!); } catch (e) { err = (e as Error).message; }
  }
  onMount(() => { void refresh(); });
  $effect(() => { if (admin && requests === null) void loadRequests(); });
  $effect(() => {
    // the changelog entry starts from the last candidate's entry, the lines code changes queued
    // under Unreleased, and the requests in the release (edit it before building)
    const queued = g?.unreleased ?? '', previous = g?.previous_notes ?? '';
    const key = [taking.map((r) => r.id).join('|'), queued, previous].join('\0');
    if (key !== notesFor) { notesFor = key; notes = releaseNotes(taking, queued, previous); }
  });

  /** Run one step on the server, then follow its log until it's done. */
  async function step(s: 'start' | 'candidate' | 'publish', body: Parameters<typeof api.release>[1] = {}) {
    err = null;
    const r = await api.release(s, body);
    if (!r.ok) { err = r.error; return null; }
    st = r;
    while (st.job.state === 'running') {
      await new Promise((ok) => setTimeout(ok, 800));
      st = await api.releaseStatus();
    }
    if (st.job.error) { err = st.job.error; return null; }
    // a step can change the files under the Builder (Publish switches back to main): read them again
    if (!app.dirty) await app.load();
    return st.job.result;
  }

  async function startRelease() {
    if (await step('start', { version })) pilot.say(`Started release ${version} on the branch release/${version}.`);
  }

  /** Bring every kept change in, request by request (oldest first); stop at the first that clashes. */
  function addKept() {
    for (const r of waiting) {
      const todo = missing(r, app.mainSvgs, cur());
      if (!todo.length) continue;
      if (todo.some((i) => i.conflict)) {
        resolving = { r, bundle: snapshot(r.bundle, app.mainSvgs, keptIds(r)).bundle };
        return;
      }
      const m = applyMerge(todo, Object.fromEntries(todo.map((i) => [i.id, true])), cur());
      app.applyChanges(`From ${r.author_name}: ${r.title}`, m);
    }
    pilot.say(`The kept changes are in, as unsaved changes. Look them over, then Save.`, { undo: true });
  }
  function resolved() {
    if (resolving) settled = [...settled, resolving.r.id];
    resolving = null;
    addKept();
  }

  async function buildCandidate() {
    if (app.dirty && !(await app.save())) { err = 'Save the design first.'; return; }
    const res = await step('candidate', { notes, message: commitMessage(rel, taking) });
    if (!res) return;
    try {
      await setStatus(hosted.client!, taking.filter((r) => r.status !== 'in_candidate').map((r) => r.id), 'in_candidate', rel);
      requests = null;
    } catch (e) { err = `Tagged ${res.tag}, but the requests weren't updated: ${(e as Error).message}`; }
    pilot.say(`Built and tagged ${res.tag}. GitHub publishes it as a pre-release; open the pull request next.`);
  }

  async function publish() {
    const res = await step('publish');
    if (!res) return;
    try {
      const ids = (requests ?? []).filter((r) => r.status === 'in_candidate' && r.release === res.version).map((r) => r.id);
      await setStatus(hosted.client!, ids, 'released', res.version);
      requests = null;
    } catch (e) { err = `Released ${res.tag}, but the requests weren't updated: ${(e as Error).message}`; }
    pilot.say(`Released ${res.tag}. GitHub publishes it with the font attached, and the site updates from main.`);
  }
</script>

<div class="page">
  <div class="row top">
    <h2>Release</h2>
    <span class="spacer"></span>
    <button class="sm" onclick={refresh} disabled={running}><I.Refresh size={14} /> Refresh</button>
  </div>

  {#if hosted.isHosted}
    <p class="muted">Releases are made from the Builder on the maintainer's own computer.</p>
  {:else if !st}
    <p class="muted">{err ?? 'Reading the repository…'}</p>
  {:else}
    <p class="muted">
      On <code>{g?.branch}</code> · font version {g?.version ?? '—'}{#if g?.tags.length} · latest tags {g.tags.slice(0, 3).join(', ')}{/if}
      {#if g?.dirty.length} · <span class="warn">{g.dirty.length} file{g.dirty.length === 1 ? '' : 's'} not committed</span>{/if}
    </p>
    {#if err}<div class="banner danger" role="alert"><span class="ic"><I.Problem /></span><span>{err}</span></div>{/if}
    {#if !admin}
      <div class="banner info"><span class="ic"><I.Info /></span><span>Sign in as an admin on <a href="/review">Review</a> to see the Change Requests that go into a release.</span></div>
    {/if}

    <ol class="steps">
      <li class:done={onRelease}>
        <h3>Start a release candidate</h3>
        {#if onRelease}
          <p>Working on <b>{g?.release}</b> on the branch <code>{g?.branch}</code>.</p>
        {:else}
          <p class="muted">Makes the branch <code>release/{version}</code> from main as it is on GitHub, so the release holds only font changes.</p>
          <div class="row">
            <label>Version <input id="rel-version" class="ver" bind:value={version} pattern={'\\d+\\.\\d{3}'} /></label>
            <button class="primary" onclick={startRelease} disabled={running || !!g?.dirty.length}>Start release {version}</button>
          </div>
          {#if g?.dirty.length}<p class="muted small">Save and commit (or put aside) your changes first: a release starts from a clean copy.</p>{/if}
        {/if}
      </li>

      <li class:off={!onRelease}>
        <h3>Bring in the kept changes</h3>
        {#if !admin}
          <p class="muted">Needs the admin sign-in.</p>
        {:else if requests === null}
          <p class="muted">Loading Change Requests…</p>
        {:else if !taking.length}
          <p class="muted">No reviewed Change Request has kept changes yet. Review them on <a href="/review">Review</a> first.</p>
        {:else}
          <ul class="reqs">
            {#each taking as r (r.id)}
              {@const left = app.design && !settled.includes(r.id) ? missing(r, app.mainSvgs, cur()).length : 0}
              <li><RequestStatusPill status={r.status} release={r.release} /> <b>{r.title}</b> <span class="muted">· {r.author_name} · {keptIds(r).length} of {r.item_ids.length} kept · sent {day(r.created_at)}</span>
                {#if left}<span class="pill draft"><I.Draft size={14} />{left} not in yet</span>{:else}<span class="pill saved"><I.Check size={14} />in</span>{/if}</li>
            {/each}
          </ul>
          {#if resolving}
            <div class="banner draft"><span class="ic"><I.Warn /></span><span>Some of "{resolving.r.title}" changes things already changed here. Pick for each, then Apply.</span></div>
            <ReviewView bundle={resolving.bundle} mode="owner" name={resolving.r.author_name ?? 'the tester'} onapplied={resolved} />
          {:else}
            <div class="row"><button class="primary" onclick={addKept} disabled={!onRelease || !waiting.length}>Add kept changes</button>
              {#if !waiting.length}<span class="muted small">All kept changes are in.</span>{/if}</div>
          {/if}
        {/if}
      </li>

      <li class:off={!onRelease}>
        <h3>Check and adjust</h3>
        <p class="muted">Look at the result in <a href="/layouts">Layouts</a> and <a href="/test">Build & test</a>, and fix anything that doesn't sit right together. Then Save.</p>
        {#if app.dirty}<button onclick={() => app.save()}>Save {app.unsavedCount} change{app.unsavedCount === 1 ? '' : 's'}</button>{/if}
      </li>

      <li class:off={!onRelease}>
        <h3>Build the candidate</h3>
        <p class="muted">Runs the builder tests, commits the design, builds the font into <code>site/JianZiPu.ttf</code>, writes version {rel}, adds this entry to <code>CHANGELOG.md</code>, and tags <code>v{rel}-rc.{(g?.candidates.length ?? 0) + 1}</code>. GitHub publishes it as a pre-release, and the requests' authors get an email.</p>
        <label class="notes">Changelog entry (Markdown)
          <textarea id="rel-notes" rows="6" bind:value={notes}></textarea>
        </label>
        <div class="row">
          <button class="primary" onclick={buildCandidate} disabled={!onRelease || running || !admin || !!waiting.length}>Build candidate</button>
          {#if waiting.length}<span class="muted small">Bring in the kept changes first.</span>{/if}
        </div>
        {#if g?.candidates.length}<p class="small">Candidates so far: {g.candidates.join(', ')}{#if g.repo} · <a href={`https://github.com/${g.repo}/compare/main...${g.branch}?expand=1`} target="_blank" rel="noopener">Open the pull request <I.Opens size={14} /></a>{/if}</p>{/if}
      </li>

      <li class:off={!onRelease || !g?.candidates.length}>
        <h3>Publish</h3>
        <p class="muted">When testers are happy with the last candidate, merge its pull request on GitHub. Then Publish tags main as v{rel}; GitHub publishes the release with the font attached, the site serves the new font, the hosted Builder redeploys, and the requests become Released.</p>
        <button class="primary" onclick={publish} disabled={running || !g?.candidates.length || !admin}>Publish v{rel}</button>
      </li>
    </ol>

    {#if job?.log.length}
      <details open={running}>
        <summary>{running ? 'Working…' : `Last step: ${job.action}${job.error ? ' (failed)' : ''}`}</summary>
        <pre class="log">{job.log.join('\n')}</pre>
      </details>
    {/if}
  {/if}
</div>

<style>
  .page { padding: var(--space-7) max(var(--space-6), env(safe-area-inset-left, 0px)); display: flex; flex-direction: column; gap: var(--space-5); max-width: 1020px; }
  h2 { margin: 0; font-size: var(--t-heading); font-weight: 600; }
  h3 { margin: 0; font-family: var(--font-display); font-size: var(--t-panel); }
  .top { align-items: center; }
  .spacer { flex: 1; }
  .row { display: flex; gap: var(--space-4); align-items: center; flex-wrap: wrap; }
  .steps { margin: 0; padding-left: var(--space-6); display: flex; flex-direction: column; gap: var(--space-5); }
  .steps > li { border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-5); background: var(--bg-panel); display: flex; flex-direction: column; gap: var(--space-3); }
  .steps > li::marker { font-family: var(--font-mono); color: var(--ink-muted); }
  .steps > li.off { opacity: .6; }
  .steps p { margin: 0; }
  .ver { width: 6em; font-family: var(--font-mono); }
  .reqs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); }
  .reqs li { display: flex; gap: var(--space-3); align-items: center; flex-wrap: wrap; }
  .notes { display: flex; flex-direction: column; gap: var(--space-2); font-weight: 600; }
  .notes textarea { font-family: var(--font-mono); font-size: var(--t-small); font-weight: 400; }
  .log { max-height: 240px; overflow: auto; font-family: var(--font-mono); font-size: var(--t-caption); background: var(--bg-sunken); padding: var(--space-4); border-radius: var(--radius-sm); margin: 0; }
  .warn { color: var(--status-draft); }
  .small { font-size: var(--t-small); }
</style>
