<script lang="ts">
  // The hosted pilot's dialogs (docs/PILOT-UX.md): welcome note, Export / Discard my draft,
  // "saved somewhere else", and Set reference font: the draft's changes, compared with the latest font.
  import * as I from '$lib/icons';
  import { goto } from '$app/navigation';
  import { hosted } from '$lib/hosted.svelte';
  import type { Item } from '$lib/merge';
  import { app } from '$lib/state.svelte';
  import { downloadZip, fontName, hhmm, markWelcomed, pilot } from '$lib/pilot.svelte';
  import SvgText from './SvgText.svelte';

  const close = () => (pilot.dialog = null);
  const plural = (n: number, w: string) => `${n} ${w}${n === 1 ? '' : 's'}`;
  let counts = $derived(pilot.dialog === 'discard' || pilot.dialog === 'export' ? app.draftCounts : null);
  const latest = $derived(fontName(app.main));    // "3.200", or "the font of 21 Oct"
  const Latest = $derived(latest.charAt(0).toUpperCase() + latest.slice(1));

  function exportZip() {
    downloadZip(app.bundle());
    close();
  }
  async function discard() {
    close();
    await app.discardDraft();
    pilot.say(`Your draft is gone. You're starting again from ${latest}.`);
  }

  // ---- update to the font
  let items = $state<Item[]>([]);
  let keep = $state<Record<string, boolean>>({});
  let showAuto = $state(false);
  $effect(() => {
    if (pilot.dialog !== 'update') return;
    const its = app.fontUpdate();
    items = its;
    keep = Object.fromEntries(its.map((i) => [i.id, !i.conflict]));   // conflicts: Keep mine
  });
  let conflicts = $derived(items.filter((i) => i.conflict));
  let auto = $derived(items.filter((i) => !i.conflict));
  async function update() {
    const label = `Set reference font to ${latest}`;
    close();
    const r = await app.updateToFont(items, keep, label);
    pilot.updateDismissed = true;
    const parts = [...(r.came ? [`${plural(r.came, 'change')} from it came in`] : []), ...(r.kept ? [`you kept yours in ${plural(r.kept, 'place')} you both changed`] : [])];
    const said = parts.join('; ');
    pilot.say(`Your reference font is now ${latest}.${said ? ` ${said[0].toUpperCase()}${said.slice(1)}.` : ''}`, { undo: true });
  }
  const what = (i: Item) => (i.kind === 'design' ? i.label : i.kind === 'spelling' ? `${i.key} spellings` : `glyph ${i.key}`);
</script>

{#if pilot.dialog}
  <div class="modal-bg" role="presentation" onclick={close}>
    <div class="modal" role="dialog" aria-modal="true" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && close()}>
      {#if pilot.dialog === 'welcome'}
        <h3>Welcome, {hosted.firstName || 'and thank you'}</h3>
        <p>Thank you for testing the JianZiPu Font Builder. Three things to know:</p>
        <ol class="three">
          <li><b>This is your own draft.</b> Change anything: glyphs, how they're typed, how words are laid out. Nothing you do changes the real font or anyone else's work.</li>
          <li><b>It saves itself</b> every 30 seconds, and when you press Save. <I.Undo class="inl" aria-label="Undo" /> undoes a step.</li>
          <li><b>Tell us what you think.</b> Confusing, broken or lovely: Feedback (top right) takes a minute. To share your work itself, <I.More class="inl" aria-label="More" /> → Export my draft.</li>
        </ol>
        <p class="muted small">Good places to start: Build & test (type a few words), then Glyphs → open a glyph → Edit.</p>
        <div class="row end">
          <button onclick={() => { markWelcomed(hosted.user!.id); close(); goto('/test?view=text'); }}>Open Build & test</button>
          <button class="primary" onclick={() => { markWelcomed(hosted.user!.id); close(); }}>Start</button>
        </div>
      {:else if pilot.dialog === 'export'}
        <h3>Export your draft</h3>
        <p>One .zip with everything in your draft. Send it to Nancy, or keep it as a backup: <I.More class="inl" aria-label="More" /> → Import opens it again.</p>
        {#if counts}<p class="muted">{plural(counts.glyphs, 'glyph')} · {plural(counts.spellings, 'spelling')} · {plural(counts.design, 'design item')}, with design.json and components.csv.</p>{/if}
        {#if app.dirty}<p class="muted small">Includes unsaved edits too ({app.unsavedCount} right now), so what you download is what you see.</p>{/if}
        <div class="row end">
          <button onclick={close}>Cancel</button>
          <button class="primary" onclick={exportZip}>Download .zip</button>
        </div>
      {:else if pilot.dialog === 'discard'}
        <h3>Discard your draft?</h3>
        <p>This deletes your draft and starts you again from {latest}.
          {#if counts}You'd lose {plural(counts.glyphs, 'glyph')}, {plural(counts.spellings, 'spelling')} and {plural(counts.design, 'design change')}.{/if} It can't be undone.</p>
        <p class="muted small">Want to keep a copy? Export it first.</p>
        <div class="row end">
          <button onclick={() => (pilot.dialog = 'export')}>Export first</button>
          <button onclick={close}>Cancel</button>
          <button class="danger" onclick={discard}>Discard my draft</button>
        </div>
      {:else if pilot.dialog === 'update'}
        <h3>Set your reference font to {app.latestFont}</h3>
        <p>Your reference font is {app.referenceFont}: Your changes are what your draft does differently from it. Your changes stay yours, compared with {latest} from now on, so the ones {latest} already has leave the list.</p>
        {#if !items.length}
          <p>Your draft already has everything {latest} changed.</p>
        {:else}
          <p>{Latest} has {plural(items.length, 'change')} since {app.referenceFont}. {auto.length} {auto.length === 1 ? 'is' : 'are'} in things you didn't change: they come in on their own.
            {#if conflicts.length}{conflicts.length} {conflicts.length === 1 ? 'is' : 'are'} in things you also changed: choose which to keep.{/if}</p>
        {/if}
        {#if conflicts.length}
          <div class="conflicts">
            {#each conflicts as it (it.id)}
              <div class="cf">
                <div class="row"><b>{what(it)}</b> <span class="badge">both changed</span></div>
                {#if it.kind === 'glyph'}
                  <div class="row pics">
                    <SvgText text={it.current} size={72} label="yours" />
                    <SvgText text={it.theirs} size={72} label="the font's new one" />
                    <SvgText text={it.base} size={72} label={`in ${app.referenceFont}`} />
                  </div>
                {:else if it.kind === 'spelling'}
                  <table class="cells"><tbody>
                    {#each it.fields.filter((f) => f.conflict) as f}<tr><th>{f.field}</th><td>yours: {f.current || '—'}</td><td>the font's: {f.theirs || '—'}</td></tr>{/each}
                  </tbody></table>
                {:else}
                  <p class="muted small">{it.summary.join(' · ')}</p>
                  {#if it.unit.type === 'layout'}<p class="muted small">A word type is one item: you keep one side whole. Export first if you want both and redo one by hand.</p>{/if}
                {/if}
                <div class="row">
                  <button class:on={!keep[it.id]} onclick={() => (keep = { ...keep, [it.id]: false })}>Keep mine</button>
                  <button class:on={keep[it.id]} onclick={() => (keep = { ...keep, [it.id]: true })}>Take the font's</button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
        {#if auto.length}
          <button class="link" onclick={() => (showAuto = !showAuto)}>{#if showAuto}<I.Unfolded size={14} />{:else}<I.Folded size={14} />{/if} {plural(auto.length, 'change')} that come in on their own</button>
          {#if showAuto}<ul class="auto">{#each auto as it}<li>{what(it)}{#if it.kind === 'design'} <span class="muted">· {it.summary.join(', ')}</span>{/if}</li>{/each}</ul>{/if}
        {/if}
        <div class="row end">
          <button onclick={() => (pilot.dialog = 'export')}>Export my draft first</button>
          <button onclick={() => { pilot.updateDismissed = true; close(); }}>Not now</button>
          <button class="primary" onclick={update}>Set reference font to {app.latestFont}</button>
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if app.savedElsewhere}
  <div class="modal-bg" role="presentation">
    <div class="modal" role="dialog" aria-modal="true">
      <h3>Your draft was saved somewhere else</h3>
      <p>{app.savedElsewhere === 'deleted'
        ? 'Another tab or computer discarded your draft after you opened it here. Which one should stay?'
        : `Another tab or computer saved your draft at ${hhmm(app.savedElsewhere)}, after you opened it here. Which one should stay?`}</p>
      <div class="row end">
        <button onclick={exportZip}>Export this one first</button>
        <button onclick={() => app.takeStoredDraft()}>{app.savedElsewhere === 'deleted' ? 'Start from the font' : `Load the ${hhmm(app.savedElsewhere)} version`}</button>
        <button class="primary" onclick={() => app.save(true)}>Keep this one</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-bg { padding: var(--space-6); }
  .modal { padding: var(--space-7); width: 100%; max-width: 600px; max-height: 90vh; overflow: auto; display: flex; flex-direction: column; gap: var(--space-5); }
  h3 { margin: 0; font-size: var(--t-panel); font-weight: 600; }
  p { margin: 0; line-height: 1.5; }
  .three { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: var(--space-4); line-height: 1.5; }
  .end { justify-content: flex-end; flex-wrap: wrap; }
  .small { font-size: var(--t-small); }
  .conflicts { display: flex; flex-direction: column; gap: var(--space-4); }
  .cf { border: 1px solid var(--status-draft); border-radius: var(--radius-md); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); }
  .pics { gap: var(--space-5); align-items: flex-start; }
  .badge { font-size: var(--t-caption); padding: 1px 6px; border-radius: 8px; background: var(--bg-hover); color: var(--status-draft); }
  button.on { background: var(--sel-bg); color: var(--ink); border-color: var(--link); }
  .cells { border-collapse: collapse; font-size: var(--t-small); }
  .cells th, .cells td { border: 1px solid var(--border); padding: 2px 8px; text-align: left; }
  .link { border: 0; background: none; color: var(--link); padding: 0; height: auto; text-align: left; }
  .auto { margin: 0; padding-left: 20px; font-size: var(--t-small); }
</style>
