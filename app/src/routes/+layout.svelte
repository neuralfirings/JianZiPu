<script lang="ts">
  import '@fontsource-variable/literata/wght.css';
  import '@fontsource-variable/eb-garamond/wght.css';
  import '../app.css';
  import { onMount } from 'svelte';
  import { setLucideProps } from '@lucide/svelte/context';
  import * as I from '$lib/icons';
  import { installTooltips } from '$lib/tooltip';
  import { installPhone, openedAnyway, phone, screenOnPhone, screenTitle } from '$lib/phone.svelte';
  import NeedsComputer from '$lib/components/NeedsComputer.svelte';
  import { page } from '$app/state';
  import { app } from '$lib/state.svelte';
  import { beforeNavigate, goto } from '$app/navigation';
  import ImportExport from '$lib/components/ImportExport.svelte';
  import PilotDialogs from '$lib/components/PilotDialogs.svelte';
  import SignIn from '$lib/components/SignIn.svelte';
  import ContactDialog from '$lib/components/ContactDialog.svelte';
  import { editor } from '$lib/editor.svelte';
  import { hosted } from '$lib/hosted.svelte';
  import { day, dismissUpdate, downloadZip, hhmm, pilot, updateDismissedFor, welcomed } from '$lib/pilot.svelte';
  import { panels, editorPanels } from '$lib/panels.svelte';
  let { children } = $props();
  // Icons: Lucide, drawn the design system's way (16px, 1.5px line; caps in app.css).
  setLucideProps({ size: 16, strokeWidth: 1.5, absoluteStrokeWidth: true });
  let menu = $state(false);
  let person = $state(false);
  let pill = $state(false);
  let dialog = $state<'import' | 'export' | null>(null);
  let showChanges = $state(false);
  let feedback = $state(false);

  let nav = $derived([
    ['/glyphs', 'Glyphs'],
    ['/layouts', 'Layouts'],
    ['/test', 'Build & test'],
    ...(hosted.ready && !hosted.isHosted ? [['/review', 'Review']] : []),
    ['/help', 'Help']
  ]);

  /** Hosted: wait for sign-in, then load the tester's draft (and greet them the first time). */
  async function start() {
    await hosted.init();
    hosted.onSignIn(() => { pilot.updateDismissed = false; void app.load().then(greet); });
    if (!hosted.isHosted || hosted.user) { await app.load(); greet(); }
  }
  function greet() {
    if (hosted.isHosted && hosted.user && updateDismissedFor(hosted.user.id, app.latestRelease)) pilot.updateDismissed = true;
    if (hosted.isHosted && hosted.user && !welcomed(hosted.user.id)) pilot.dialog = 'welcome';
  }
  beforeNavigate(() => app.flush());

  onMount(() => {
    void start();
    const offTips = installTooltips();
    const offPhone = installPhone();
    // a phone's keyboard: while a field has it, the tabs and Save bar step aside, and (iOS, which
    // doesn't shrink the page for it) the Builder shrinks to the part of the screen still visible
    const FIELD = 'input:not([type=checkbox], [type=radio], [type=range], [type=file], [type=color]), textarea, [contenteditable]';
    const onFocusIn = (e: FocusEvent) => { keyboard = e.target instanceof Element && e.target.matches(FIELD); };
    const onFocusOut = () => queueMicrotask(() => { keyboard = !!document.activeElement?.matches(FIELD); });
    document.addEventListener('focusin', onFocusIn); document.addEventListener('focusout', onFocusOut);
    const vv = window.visualViewport;
    const onViewport = () => { visible = vv && innerHeight - vv.height > 80 ? Math.round(vv.height) : null; };
    vv?.addEventListener('resize', onViewport);
    const onHide = () => { if (document.visibilityState === 'hidden') app.flush(); };
    document.addEventListener('visibilitychange', onHide);
    const onUnload = (e: BeforeUnloadEvent) => { if (hosted.isHosted && app.dirty) { app.flush(); e.preventDefault(); } };
    window.addEventListener('beforeunload', onUnload);
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (/^\/glyphs\/(new$|[^/]+\/edit)/.test(location.pathname)) return;   // the glyph editor handles ⌘S / ⌘Z itself
      if (e.key === 's') { e.preventDefault(); app.save(); }
      else if (e.key === 'z') {
        const t = e.target as HTMLElement;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
        e.preventDefault();
        if (e.shiftKey) app.redo(); else app.undo();
      }
    };
    window.addEventListener('keydown', onKey);
    const onClick = () => { menu = false; person = false; pill = false; };
    window.addEventListener('click', onClick);
    return () => {
      offTips(); offPhone();
      document.removeEventListener('focusin', onFocusIn); document.removeEventListener('focusout', onFocusOut);
      vv?.removeEventListener('resize', onViewport);
      window.removeEventListener('keydown', onKey); window.removeEventListener('click', onClick);
      document.removeEventListener('visibilitychange', onHide); window.removeEventListener('beforeunload', onUnload);
    };
  });

  // toasts leave after 5 s (20 s when they offer a commit message to copy), held while hovered or focused
  let toastTimer: ReturnType<typeof setTimeout> | null = null;
  function releaseToast() {
    const t = pilot.toast;
    if (toastTimer) clearTimeout(toastTimer);
    if (t) toastTimer = setTimeout(() => (pilot.toast = null), t.copy ? 20000 : 5000);
  }
  function holdToast() { if (toastTimer) clearTimeout(toastTimer); }
  $effect(() => { void pilot.toast; releaseToast(); });
  async function copyMessage(text: string) {
    try { await navigator.clipboard.writeText(text); pilot.say('Commit message copied.'); } catch { prompt('Commit message:', text); }
  }
  // on a phone, a screen that needs a computer says so in place of the tool, until opened anyway
  let needs = $derived.by(() => {
    if (!phone.on) return null;
    const s = screenOnPhone(page.route.id, page.url.searchParams);
    return s === 'phone' || openedAnyway[page.route.id ?? ''] ? null : s;
  });
  // a phone's top bar: the screen's name, undo and redo where you edit; Save in a bar of its own
  let title = $derived(screenTitle(page.route.id, page.url.searchParams, page.params as Record<string, string>));
  let undoHere = $derived(page.url.pathname === '/layouts' || page.url.pathname === '/glyphs');
  let tabs = $derived<[string, string, typeof I.Help][]>([
    ['/glyphs', 'Glyphs', I.TabGlyphs],
    ['/layouts', 'Layouts', I.TabLayouts],
    ['/test', 'Try', I.TabTry],
    ...(hosted.isHosted ? [['/requests', 'Requests', I.TabRequests] as [string, string, typeof I.Help]] : []),
    ['/help', 'Help', I.Help]
  ]);
  let gate = $derived(hosted.ready && hosted.isHosted && !hosted.user);
  let keyboard = $state(false);
  let visible = $state<number | null>(null);
  let tabsShown = $derived(phone.on && !gate && hosted.ready && !keyboard);
  let saveBar = $derived(tabsShown && (app.dirty || (hosted.isHosted && (app.offline || app.saveRefused))));
  let counts = $derived(pill && hosted.isHosted ? app.draftCounts : null);
  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;

  // on the glyph editor routes the glyph owns undo and ⌘S; the header keeps only the design's Save
  let inGlyphEditor = $derived(/^\/glyphs\/(new$|[^/]+\/edit)/.test(page.url.pathname));
  let budget = $derived.by(() => {
    const s = app.stats;
    if (!s) return null;
    const kb = s.est_bytes / 1024;
    return { kb, rules: s.rules, skipped: s.skipped, level: s.skipped > 0 ? 'warn' : 'ok' };
  });
</script>

{#snippet statusPill(short: boolean)}
<span class="status" role="status">
  {#if hosted.isHosted && (app.offline || app.saveRefused)}
    <button class="pill danger" onclick={(e) => { e.stopPropagation(); showChanges = !showChanges; }}><I.Alert size={14} />{app.offline && !short ? 'Not saved · offline' : 'Not saved'}</button>
  {:else if hosted.isHosted && app.saving}
    <span class="pill info"><I.Working size={14} />Saving…</span>
  {:else if app.dirty}
    <button class="pill draft" onclick={(e) => { e.stopPropagation(); showChanges = !showChanges; }}><I.Unsaved size={14} />{inGlyphEditor ? 'Design: ' : ''}{app.changes.length} unsaved</button>
  {:else if hosted.isHosted && app.lastSaved}
    <span class="pill saved"><I.Check size={14} />{short ? 'Saved' : `Saved to your draft · ${hhmm(app.lastSaved)}`}</span>
  {:else if app.lastSaved}
    <span class="pill saved"><I.Check size={14} />{inGlyphEditor ? 'Design: saved' : short ? 'Saved' : `Saved ${app.lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}</span>
  {:else if !app.loading}
    <span class="pill saved"><I.Check size={14} />{inGlyphEditor ? 'Design: saved' : 'Saved'}</span>
  {/if}
</span>
{/snippet}
{#snippet saveButton()}
{#if hosted.isHosted}
  <button class="primary" onclick={() => app.save()} disabled={!app.dirty || app.saving || hosted.signedOut} title="Save to your draft (⌘S). It also saves itself every 30 seconds.">
    {app.saving ? 'Saving…' : app.offline || app.saveRefused ? 'Try again' : 'Save'}
  </button>
{:else}
  <button class="primary" onclick={() => app.save()} disabled={!app.dirty || app.saving} title={inGlyphEditor ? 'Write design.json, components.csv and merged glyph files (the glyph has its own Save, ⌘S)' : 'Write design.json, components.csv and merged glyph files (⌘S)'}>
    {app.saving ? 'Saving…' : inGlyphEditor ? 'Save design' : 'Save'}
  </button>
{/if}
{/snippet}
{#snippet moreItems()}
{#if hosted.isHosted}
  <button onclick={() => goto('/review?mine')}>See my changes and send them…</button>
  <button onclick={() => goto('/requests')}>Your Change Requests</button>
  <button onclick={() => (pilot.dialog = 'export')}>Export my draft (.zip)…</button>
  <button onclick={() => { pilot.review = null; goto('/review'); }}>Import a draft (.zip)…</button>
  <button onclick={() => (pilot.dialog = 'update')} disabled={!app.fontMoved}>{app.fontMoved ? `Set reference font to ${app.latestFont}…` : `Reference font: ${app.latestFont}`}</button>
  <button onclick={() => (feedback = true)}>Send feedback…</button>
  <button onclick={() => (pilot.dialog = 'welcome')}>Welcome note</button>
  <hr />
  <button onclick={() => { panels.reset(); editorPanels.reset(); }} disabled={panels.isDefault && editorPanels.isDefault}>Reset panel layouts</button>
  <button onclick={() => app.discard()} disabled={!app.dirty}>Discard unsaved changes</button>
  <button class="danger-item" onclick={() => (pilot.dialog = 'discard')}>Discard my draft…</button>
{:else}
  <button onclick={() => (dialog = 'import')}>Import…</button>
  <button onclick={() => (dialog = 'export')}>Export…</button>
  <button onclick={() => downloadZip(app.bundle())} title="design.json, components.csv and changed glyph files as a draft .zip, for the Review screen">Download as draft .zip</button>
  <button onclick={() => { pilot.review = null; goto('/review'); }}>Review a draft…</button>
  <button onclick={() => goto('/release')}>Make a release…</button>
  <button onclick={() => app.reloadFromDisk()}>Reload from disk</button>
  <button onclick={() => app.discard()} disabled={!app.dirty}>Discard unsaved changes</button>
  <hr />
  <button onclick={() => { panels.reset(); editorPanels.reset(); }} disabled={panels.isDefault && editorPanels.isDefault} title="Put the panels of Layouts and the glyph editor back where they started">Reset panel layouts</button>
{/if}
{/snippet}

<div class="shell" style:height={phone.on && visible ? `${visible}px` : null} style:--phone-bottom="{(tabsShown ? 56 : 0) + (saveBar ? 52 : 0)}px">
  {#if !phone.on}
    <header>
      <div class="brand"><img class="seal" src="/android-chrome-192x192.png" alt="" width="26" height="26" />JianZiPu Font Builder</div>
      {#if hosted.isHosted && hosted.user}
        <span class="pill-wrap">
          <button class="pill draft" onclick={(e) => { e.stopPropagation(); pill = !pill; }} title="Only you see your draft. The font itself doesn't change.">
            <I.Draft size={14} />Your draft{#if app.newRelease && pilot.updateDismissed}<span class="moved"> · {app.main?.version ? `${app.main.version} is out` : 'font updated'}</span>{/if}
          </button>
          {#if pill}
            <div class="pop float" role="dialog" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && (pill = false)}>
              <strong>Your draft</strong>
              <p>Only you see it. Your builds use it. The font itself doesn't change.</p>
              <p class="muted">{#if app.draftBase}Reference font: {app.referenceFont}{/if}{#if app.lastSaved} · last saved {hhmm(app.lastSaved)}{/if}</p>
              {#if counts}<p>Your changes: {plural(counts.glyphs, 'glyph')} · {plural(counts.spellings, 'spelling')} · {plural(counts.design, 'design item')}</p>{/if}
              <div class="row">
                <button class="sm" onclick={() => { pill = false; goto('/review?mine'); }}>See my changes</button>
                <button class="sm" onclick={() => { pill = false; goto('/requests'); }}>Change Requests{app.requests.length ? ` · ${app.requests.length}` : ''}</button>
                <button class="sm" onclick={() => { pill = false; pilot.dialog = 'export'; }}>Export…</button>
              </div>
            </div>
          {/if}
        </span>
      {:else if hosted.ready && !hosted.isHosted}
        <span class="chip dashed local" title="Save writes design.json, components.csv and glyph files in this repo.">Local files</span>
      {/if}
      {#if !gate && hosted.ready}
      <nav>
        {#each nav as [href, label]}
          <a {href} aria-current={page.url.pathname === href || page.url.pathname.startsWith(href + '/') ? 'page' : undefined}>{label}</a>
        {/each}
      </nav>
      <div class="spacer"></div>
      {#if page.url.pathname.startsWith('/layouts')}
        <label class="adv" title="Structural edits: add, remove, reorder parts; new / delete word types; recognition rules"><input type="checkbox" bind:checked={editor.advanced} /> Advanced</label>
      {/if}
      {#if budget}
        <a class="pill {budget.level === 'warn' ? 'draft' : 'saved'} budget" href="/layouts?budget=1" title={budget.skipped ? `GPOS rules generated from this design; ${budget.skipped} skipped` : 'GPOS rules generated from this design'}>
          {#if budget.level === 'warn'}<I.Warn size={14} />{:else}<I.Check size={14} />{/if}{budget.rules} rules · {budget.kb.toFixed(0)} KB
        </a>
      {/if}
      {#if !inGlyphEditor}
        <button class="quiet" onclick={() => app.undo()} disabled={app.undoStack.length === 0}
          data-tip={app.undoStack.length ? `Undo: ${app.undoStack.at(-1)?.label} (⌘Z)` : 'Nothing to undo'} aria-label="Undo"><I.Undo /></button>
        <button class="quiet" onclick={() => app.redo()} disabled={app.redoStack.length === 0}
          data-tip={app.redoStack.length ? `Redo: ${app.redoStack.at(-1)?.label} (⇧⌘Z)` : 'Nothing to redo'} aria-label="Redo"><I.Redo /></button>
      {/if}
      {@render statusPill(false)}
      {@render saveButton()}
      {#if hosted.isHosted}
        <button class="fb" onclick={() => (feedback = true)}>Feedback</button>
      {/if}
      <span class="menu-wrap">
        <button class="quiet" onclick={(e) => { e.stopPropagation(); menu = !menu; }} aria-label="More" data-tip="More: import, export, reset panels"><I.More /></button>
        {#if menu}
          <div class="menu float" role="menu">
            {@render moreItems()}
          </div>
        {/if}
      </span>
      {#if hosted.isHosted && hosted.user}
        <span class="menu-wrap">
          <button class="who" onclick={(e) => { e.stopPropagation(); person = !person; }} aria-label="Account" title={hosted.user.email}>{(hosted.firstName || '?').slice(0, 1).toUpperCase()}</button>
          {#if person}
            <div class="menu float" role="menu">
              <span class="muted signed">Signed in as {hosted.user.email}</span>
              <button onclick={async () => { app.flush(); await hosted.signOut(); }}>Sign out</button>
            </div>
          {/if}
        </span>
      {/if}
      {/if}
    </header>
  {:else}
    <!-- a phone: one row (seal, screen, status, undo where you edit, More); the screens are tabs at the bottom -->
    <header class="ph">
      <img class="seal" src="/android-chrome-192x192.png" alt="" width="26" height="26" />
      <span class="title">{title}</span>
      {#if !gate && hosted.ready}
        {#if !saveBar}{@render statusPill(true)}{/if}
        <span class="spacer"></span>
        {#if undoHere}
          <button class="quiet ic" onclick={() => app.undo()} disabled={app.undoStack.length === 0}
            data-tip={app.undoStack.length ? `Undo: ${app.undoStack.at(-1)?.label}` : 'Nothing to undo'} aria-label="Undo"><I.Undo /></button>
          <button class="quiet ic" onclick={() => app.redo()} disabled={app.redoStack.length === 0}
            data-tip={app.redoStack.length ? `Redo: ${app.redoStack.at(-1)?.label}` : 'Nothing to redo'} aria-label="Redo"><I.Redo /></button>
        {/if}
        <span class="menu-wrap">
          <button class="quiet ic" onclick={(e) => { e.stopPropagation(); menu = !menu; }} aria-label="More" data-tip="More"><I.More /></button>
          {#if menu}
            <div class="menu float" role="menu">
              {#if hosted.isHosted && hosted.user}
                <span class="muted signed"><I.Draft size={14} /> Your draft: only you see it. The font itself doesn't change.</span>
              {:else if !hosted.isHosted}
                <span class="muted signed">Local files: Save writes design.json, components.csv and glyph files in this repo.</span>
              {/if}
              {#if budget}<a class="item" href="/layouts?budget=1">{#if budget.level === 'warn'}<I.Warn size={14} />{:else}<I.Check size={14} />{/if}Font budget: {budget.rules} rules · {budget.kb.toFixed(0)} KB</a>{/if}
              <hr />
              {@render moreItems()}
              {#if hosted.isHosted && hosted.user}
                <hr />
                <span class="muted signed">Signed in as {hosted.user.email}</span>
                <button onclick={async () => { app.flush(); await hosted.signOut(); }}>Sign out</button>
              {/if}
            </div>
          {/if}
        </span>
      {/if}
    </header>
  {/if}

  {#if showChanges && app.dirty}
    <div class="changes">
      <strong>Unsaved changes</strong>
      <ol>{#each app.changes as c}<li>{c}</li>{/each}</ol>
      <button onclick={() => { app.discard(); showChanges = false; }}>Discard all</button>
    </div>
  {/if}
  {#if hosted.isHosted && hosted.signedOut}
    <div class="banner danger"><span class="ic"><I.Alert /></span> <b>You've been signed out.</b> Your unsaved changes are kept in this browser. <button onclick={() => hosted.signOut()}>Sign in again</button></div>
  {:else if hosted.isHosted && app.offline}
    <div class="banner danger"><span class="ic"><I.Alert /></span> <b>Your draft isn't saved.</b> We can't reach the server. Your changes are kept in this browser and will save when you're back online. Don't close this browser's private window or clear its data.
      <button onclick={() => app.save()}>Try again</button> <button onclick={() => (pilot.dialog = 'export')}>Export my draft</button></div>
  {:else if hosted.isHosted && app.saveRefused}
    <div class="banner danger"><span class="ic"><I.Alert /></span> <b>Your draft isn't saved.</b> The server turned it down: {app.saveRefused}. Your changes are kept in this browser. If trying again doesn't work, export your draft so you have a copy, and send feedback.
      <button onclick={() => app.save()}>Try again</button> <button onclick={() => (pilot.dialog = 'export')}>Export my draft</button> <button onclick={() => (feedback = true)}>Send feedback</button></div>
  {/if}
  {#if hosted.isHosted && app.newRelease && !pilot.updateDismissed && !app.loading}
    <div class="banner info">
      <span class="ic"><I.Info /></span>
      <span><b>{app.main?.version ? `JianZiPu ${app.main.version} is out.` : `The font was updated${app.main?.date ? ` on ${day(app.main.date)}` : ''}.`}</b> Your reference font is {app.referenceFont}.</span>
      <span class="spacer"></span>
      <button onclick={() => dismissUpdate(hosted.user?.id, app.latestRelease)}>Not now</button>
      <button class="primary" onclick={() => (pilot.dialog = 'update')}>Set reference font to {app.latestFont}…</button>
    </div>
  {/if}
  {#if app.draftRestored}
    <div class="banner draft"><span class="ic"><I.Unsaved /></span>
      {#if hosted.isHosted}
        Restored {plural(app.unsavedCount, 'change')} from your last visit that hadn't reached your draft.
        <button onclick={() => { app.draftRestored = false; app.save(); }}>Save them</button>
      {:else}
        Restored unsaved changes from your last session.
        <button onclick={() => (app.draftRestored = false)}>Keep</button>
      {/if}
      <button onclick={() => { app.discard(); app.draftRestored = false; }}>Discard{hosted.isHosted ? ' them' : ''}</button>
    </div>
  {/if}
  {#if app.error}
    <div class="banner danger"><span class="ic"><I.Problem /></span> {app.error}
      {#if app.errorFix === 'load'}<button onclick={() => app.load()}>Retry</button>
      {:else if app.errorFix === 'save'}<button onclick={() => app.save()}>Try again</button>
      {:else if app.errorFix === 'check'}<button onclick={() => app.recheck()}>Check again</button>
      {:else if app.errorFix === 'undo' && app.undoStack.length}<button onclick={() => app.undo()}>Undo: {app.undoStack.at(-1)?.label}</button>
      {:else if app.errorFix === 'reload'}<button onclick={() => location.reload()}>Reload the page</button>
      {:else if app.errorFix === 'feedback' && hosted.isHosted}<button onclick={() => (feedback = true)}>Send feedback</button>{/if}
    </div>
  {/if}
  {#if app.paused}
    <div class="scrim">
      <div class="dialog modal" role="dialog" aria-modal="true">
        <h3>Save is waiting</h3>
        <p>{app.paused.length === 1 ? 'This spelling problem' : `These ${app.paused.length} spelling problems`} must be fixed first: the font can't build with {app.paused.length === 1 ? 'it' : 'them'}.</p>
        <ul class="paused">
          {#each app.paused.slice(0, 6) as e}<li>{e.message}</li>{/each}
          {#if app.paused.length > 6}<li class="muted">… and {app.paused.length - 6} more</li>{/if}
        </ul>
        <p class="muted">{app.changes.length === 1 ? 'Your unsaved change is kept in this browser and stays undoable.' : `Your ${app.changes.length} unsaved changes are kept in this browser and stay undoable.`}</p>
        <div class="row">
          <button onclick={() => { app.paused = null; app.undo(); }} disabled={!app.undoStack.length} title={app.undoStack.at(-1)?.label}>Undo last change</button>
          <span class="spacer"></span>
          <button onclick={() => (app.paused = null)}>Close</button>
          <button class="primary" onclick={() => { app.paused = null; goto('/glyphs?view=typing&f=attention'); }}>Show {app.paused.length === 1 ? 'it' : 'them'}</button>
        </div>
      </div>
    </div>
  {/if}
  {#if app.conflict}
    <div class="scrim">
      <div class="dialog modal" role="dialog" aria-modal="true">
        <h3>{app.conflictFile} changed on disk</h3>
        <p>{app.conflict}</p>
        <div class="row">
          <button onclick={() => { app.conflict = null; app.reloadFromDisk(); }}>Reload from disk (lose my {app.changes.length} changes)</button>
          <button class="danger" onclick={() => app.save(true)}>Overwrite</button>
          <button onclick={() => { app.conflict = null; dialog = 'export'; }}>Export mine first</button>
        </div>
      </div>
    </div>
  {/if}

  <main>
    {#if gate}
      <SignIn />
    {:else if app.loading || !hosted.ready}
      <p class="muted" style="padding: var(--space-8)">{hosted.isHosted ? 'Loading your draft…' : 'Loading design…'}</p>
    {:else if app.design}
      {#if needs}
        <NeedsComputer tool={needs.computer} key={page.route.id ?? ''} glyph={page.route.id === '/glyphs/[name]/edit' ? page.params.name : null} />
      {:else}
        {@render children()}
      {/if}
    {/if}
  </main>

  {#if saveBar}
    <div class="savebar">{@render statusPill(true)}<span class="spacer"></span>{@render saveButton()}</div>
  {/if}
  {#if tabsShown}
    <nav class="tabs" aria-label="Screens">
      {#each tabs as [href, label, Icon]}
        <a {href} aria-current={page.url.pathname === href || page.url.pathname.startsWith(href + '/') ? 'page' : undefined}><Icon size={20} /><span>{label}</span></a>
      {/each}
    </nav>
  {/if}

  {#if dialog}
    <ImportExport mode={dialog} onclose={() => (dialog = null)} />
  {/if}
  <PilotDialogs />
  {#if feedback}
    <ContactDialog kind="feedback" name={hosted.user?.name ?? ''} email={hosted.user?.email ?? ''}
      context={{ page: page.url.pathname, version: hosted.config?.commit ?? '' }} onclose={() => (feedback = false)} />
  {/if}
  {#if pilot.toast}
    <div class="toast" role="status" onmouseenter={holdToast} onmouseleave={releaseToast} onfocusin={holdToast} onfocusout={releaseToast}>
      <span>{pilot.toast.text}</span>
      {#if pilot.toast.copy}<button onclick={() => copyMessage(pilot.toast!.copy!)}>Copy commit message</button>{/if}
      {#if pilot.toast.undo}<button onclick={() => { app.undo(); pilot.toast = null; }}>Undo</button>{/if}
      <button class="x" onclick={() => (pilot.toast = null)} aria-label="Close"><I.Close /></button>
    </div>
  {/if}
</div>

<style>
  .shell { display: flex; flex-direction: column; width: 100%; height: 100vh; height: 100dvh; overflow: hidden; }
  /* wraps instead of running off the edge when the controls do not fit on one line */
  header button { white-space: nowrap; }
  header { display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2) var(--space-4); min-height: 48px; padding: var(--space-3) var(--space-6); border-bottom: 1px solid var(--border); background: var(--bg-panel); flex: none; min-width: 0; }
  .brand { display: inline-flex; align-items: center; gap: var(--space-4); font: 600 20px/1 var(--font-display); margin-right: var(--space-5); white-space: nowrap; }
  .seal { display: block; width: 26px; height: 26px; border-radius: var(--radius-sm); }
  nav { display: flex; gap: var(--space-2); min-width: 0; overflow-x: auto; }
  nav a { display: inline-flex; align-items: center; height: var(--control-md); padding: 0 var(--space-5); border: 1px solid transparent; border-radius: var(--radius-md); color: var(--ink); font-weight: 600; text-decoration: none; white-space: nowrap; transition: background 120ms ease-out; }
  nav a:hover { background: var(--bg-hover); }
  nav a[aria-current="page"] { background: var(--sel-bg); border-color: var(--sel-border); }
  .spacer { flex: 1; }
  .menu-wrap { position: relative; }
  .menu { position: absolute; right: 0; top: 100%; z-index: var(--z-popover); margin-top: 4px; min-width: 220px; display: flex; flex-direction: column; padding: var(--space-2); }
  .menu button { justify-content: flex-start; text-align: left; border: 0; background: transparent; font-weight: 400; }
  .menu button:hover:not(:disabled) { background: var(--bg-hover); }
  .menu hr { border: 0; border-top: 1px solid var(--hairline); margin: var(--space-1) 0; }
  .adv { display: inline-flex; align-items: center; gap: 4px; font-size: var(--t-small); color: var(--ink-muted); margin-right: var(--space-4); }
  .changes { padding: var(--space-4) var(--space-6); border-bottom: 1px solid var(--border); background: var(--bg-panel); display: flex; gap: var(--space-5); align-items: center; }
  .changes ol { margin: 0; padding-left: 20px; max-height: 120px; overflow: auto; flex: 1; }
  /* Banner: tinted ground and edge in the state colour, the words in ink */
  /* banners under the top bar run full width */
  .banner { border-width: 0 0 1px; border-radius: 0; padding: var(--space-4) var(--space-6); }
  main { flex: 1; min-height: 0; min-width: 0; overflow: auto; }
  .modal { max-width: 560px; }
  .modal h3 { margin-bottom: var(--space-4); }
  .budget { text-decoration: none; }
  .status .pill { cursor: default; }
  .status button.pill { cursor: pointer; }
  .pill-wrap { position: relative; margin-right: var(--space-5); }
  .pill.draft:hover { filter: brightness(.97); }
  .local { margin-right: var(--space-5); white-space: nowrap; }
  .moved { opacity: .8; }
  .pop { position: absolute; left: 0; top: 100%; margin-top: 6px; z-index: var(--z-popover); width: 300px; padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); }
  .pop p { margin: 0; font-size: var(--t-small); line-height: 16px; }
  .pop .row { flex-wrap: wrap; gap: var(--space-3); }
  .fb { height: auto; border: 0; background: none; font-size: var(--t-small); color: var(--link); padding: 0 var(--space-2); cursor: pointer; }
  .who { width: var(--control-md); padding: 0; border-radius: 50%; }
  .signed { padding: 4px 8px; font-size: var(--t-small); }
  .danger-item { color: var(--accent); }
  .toast { position: fixed; left: 50%; transform: translateX(-50%); bottom: max(var(--space-6), env(safe-area-inset-bottom, 0px)); max-width: min(720px, calc(100vw - 32px)); }
  .toast button { white-space: nowrap; }
  .toast .x { text-decoration: none; font-size: 16px; }
  .paused { margin: 0 0 var(--space-4); padding-left: 20px; color: var(--status-danger); }
  /* narrow: the tabs take their own scrolling row under the name and the controls */
  @media (max-width: 1100px) {
    nav { order: 10; flex: 1 0 100%; padding: var(--space-3) 0; }
  }
  /* a phone: one row on top, Save in a bar while something is unsaved, the screens as tabs at the bottom */
  header.ph { flex-wrap: nowrap; gap: var(--space-3); padding: var(--space-2) var(--space-4); padding-top: max(var(--space-2), env(safe-area-inset-top, 0px)); }
  .ph .title { min-width: 0; flex: 0 1 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 600 var(--t-heading)/1.2 var(--font-display); }
  .ph .ic { width: var(--control-touch); padding: 0; }
  .ph .menu { width: min(320px, calc(100vw - 2 * var(--space-4))); max-height: calc(100dvh - 140px); overflow: auto; }
  .ph .menu .signed { display: flex; gap: var(--space-3); align-items: center; padding: var(--space-3) var(--space-4); line-height: 16px; }
  .menu .item { display: flex; align-items: center; gap: var(--space-3); min-height: var(--control-md); padding: 0 var(--space-5); color: var(--ink); text-decoration: none; }
  .savebar { display: flex; align-items: center; gap: var(--space-4); flex: none; padding: var(--space-2) var(--space-4); min-height: 52px; border-top: 1px solid var(--border); background: var(--bg-panel); }
  .tabs { display: flex; flex: none; border-top: 1px solid var(--border); background: var(--bg-panel); padding-bottom: env(safe-area-inset-bottom, 0px); }
  .tabs a { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-1); min-height: 56px; color: var(--ink-muted); font-size: var(--t-caption); font-weight: 600; text-decoration: none; }
  .tabs a[aria-current="page"] { color: var(--ink); background: var(--sel-bg); border-top: 2px solid var(--sel-border); margin-top: -1px; }
  @media (max-width: 759.98px) {
    .toast { bottom: calc(var(--phone-bottom) + var(--space-4) + env(safe-area-inset-bottom, 0px)); }
  }
</style>
