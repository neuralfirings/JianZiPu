<script lang="ts">
  // Send Change Request (Your changes, hosted): pick which of the draft's changes go, say what
  // you changed and why, and how you'd like to be credited. Before it goes: the draft is saved,
  // the chosen spellings mustn't clash, and a font built from just those changes must build.
  // Once sent, those changes are locked in the draft until the request is withdrawn or declined.
  // Save as draft keeps the form (ticks, title, notes, credit) with the tester's draft in Supabase,
  // to finish later, here or on another computer; it opens again from where it was.
  import * as I from '$lib/icons';
  import { api } from '$lib/api';
  import { hosted } from '$lib/hosted.svelte';
  import type { Item } from '$lib/merge';
  import { pilot } from '$lib/pilot.svelte';
  import { buildInputs, myCredit, sendRequest, setCredit, snapshot, startingTicks } from '$lib/requests';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';

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

  const nameOf = (i: Item) => (i.kind === 'design' ? i.label : i.kind === 'spelling' ? `Spellings · ${i.key}` : `Glyph · ${i.key}`);
  let picked = $derived(items.filter((i) => chosen[i.id]));
  /** A new glyph and its spellings go together (Review keeps them together too). */
  function toggle(it: Item, v: boolean) {
    const next = { ...chosen, [it.id]: v };
    if (it.kind === 'glyph' && it.status === 'added' && `spelling:${it.key}` in next) next[`spelling:${it.key}`] = v;
    if (it.kind === 'spelling' && v && `glyph:${it.key}` in next && items.find((i) => i.id === `glyph:${it.key}`)?.status === 'added') next[`glyph:${it.key}`] = true;
    chosen = next;
  }

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
      const clash = T.issues(bundle.typing, app.known);
      if (clash.length) { problem = `${clash.length} spelling problem${clash.length === 1 ? '' : 's'} in the chosen changes. Fix them in Glyphs → Typing, or leave those spellings out.`; return; }
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
      <ul class="pick">
        {#each items as it (it.id)}
          <li><label><input type="checkbox" checked={chosen[it.id]} onchange={(e) => toggle(it, (e.target as HTMLInputElement).checked)} />
            <span class="mono">{nameOf(it)}</span> <span class="tag {it.status}">{it.status}</span>
            {#if it.kind === 'design'}<span class="muted small">{it.summary.join(' · ')}</span>{/if}</label></li>
        {/each}
      </ul>
    </fieldset>

    <label class="field">Title
      <input id="cr-title" type="text" bind:value={title} maxlength="200" placeholder="Tighter spacing for 勾 over 七" />
    </label>
    <label class="field">What you changed and why
      <textarea id="cr-notes" bind:value={notes} rows="5" maxlength="20000" placeholder="Which words look better now, what you tried, anything you're unsure about."></textarea>
    </label>
    <label class="field">How would you like to be credited?
      <input id="cr-credit" type="text" bind:value={credit} maxlength="200" placeholder="Mei Chen" />
      <span class="muted small">Your name the way it should read in the release notes, which say "thanks to" before it. For example <b>Mei Chen</b>, or with a group: <b>Mei Chen (Taipei Qin Society)</b>. Leave it empty for no credit. It's remembered for next time.</span>
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
  .pick { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--space-2); max-height: 220px; overflow: auto; }
  .pick label { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
  .mono { font-family: var(--font-mono); font-size: var(--t-small); }
  .small { font-size: var(--t-small); }
  .field { display: flex; flex-direction: column; gap: var(--space-2); font-weight: 600; }
  .field input, .field textarea { font: inherit; font-weight: 400; }
  .field .muted { font-weight: 400; }
  .tag.added { color: var(--status-saved); border-color: currentColor; }
  .tag.deleted { color: var(--status-danger); border-color: currentColor; }
  .row.end { display: flex; justify-content: flex-end; gap: var(--space-4); }
</style>
