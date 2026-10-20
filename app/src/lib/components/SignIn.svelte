<script lang="ts">
  // Hosted pilot: invite-only sign-in with an emailed link (docs/PILOT-UX.md "Sign-in").
  import { onDestroy } from 'svelte';
  import { hosted } from '$lib/hosted.svelte';
  import ContactDialog from './ContactDialog.svelte';

  let email = $state('');
  let step = $state<'form' | 'sent' | 'not-invited' | 'expired'>(hosted.linkExpired ? 'expired' : 'form');
  let busy = $state(false);
  let err = $state<string | null>(null);
  let wait = $state(0);
  let timer: ReturnType<typeof setInterval> | null = null;
  let asking = $state(false);   // the "Ask for an invite" form

  async function send() {
    if (!email.trim() || busy) return;
    busy = true; err = null;
    try {
      const r = await hosted.sendLink(email);
      if (r === 'sent') { step = 'sent'; countdown(); }
      else if (r === 'not-invited') step = 'not-invited';
      else err = r;
    } finally { busy = false; }
  }
  function countdown() {
    wait = 30;
    if (timer) clearInterval(timer);
    timer = setInterval(() => { wait = Math.max(0, wait - 1); if (!wait && timer) clearInterval(timer); }, 1000);
  }
  onDestroy(() => { if (timer) clearInterval(timer); });
  const fmt = (s: number) => `0:${String(s).padStart(2, '0')}`;
</script>

<div class="wrap">
  <div class="card">
    <figure class="art"><img src="/signin-word.webp" alt="A guqin character being laid out in the Builder: 名, 七, 勾 and 五 in their part boxes, with a spacing rule between them" width="441" height="689" /></figure>
    <div class="body">
    <div class="title">JianZiPu Font Builder <span class="muted">· pilot</span></div>
    {#if step === 'form'}
      <p>For invited testers. Type the email Nancy invited, and we'll send you a link to sign in. No password needed.</p>
      <form onsubmit={(e) => { e.preventDefault(); send(); }}>
        <!-- svelte-ignore a11y_autofocus -->
        <input type="email" required autocomplete="email" placeholder="you@example.com" bind:value={email} autofocus />
        <button class="primary" disabled={busy || !email.trim()}>{busy ? 'Sending…' : 'Email me a sign-in link'}</button>
      </form>
      {#if err}<p class="error">{err}</p>{/if}
      <p class="foot"><button class="linkish" onclick={() => (asking = true)}>Want to try it? Ask for an invite</button></p>
    {:else if step === 'sent'}
      <h2>Check your email</h2>
      <p>We sent a sign-in link to <b>{email}</b>. Open it on this computer, in this browser.</p>
      <p class="muted">The link works once, for 1 hour. Nothing there? Look in spam, or send it again.</p>
      <div class="row">
        <button onclick={send} disabled={wait > 0 || busy}>Send again{wait ? ` (${fmt(wait)})` : ''}</button>
        <button onclick={() => (step = 'form')}>Use a different email</button>
      </div>
    {:else if step === 'not-invited'}
      <h2>This email isn't on the pilot list</h2>
      <p><b>{email}</b> wasn't invited. The pilot is for a few invited testers for now. If Nancy invited you at another address, use that one.</p>
      <div class="row">
        <button class="primary" onclick={() => (step = 'form')}>Try another email</button>
        <button onclick={() => (asking = true)}>Ask for an invite</button>
      </div>
    {:else}
      <h2>This sign-in link has expired</h2>
      <p>Links work once, for 1 hour. Send yourself a new one.</p>
      <button class="primary" onclick={() => { hosted.linkExpired = false; step = 'form'; }}>Email me a new link</button>
    {/if}
    </div>
  </div>
</div>
{#if asking}<ContactDialog kind="invite" email={step === 'not-invited' ? email : ''} onclose={() => (asking = false)} />{/if}

<style>
  .wrap { min-height: 100%; box-sizing: border-box; display: flex; align-items: center; justify-content: center; padding: var(--space-8) var(--space-6); }
  .card { width: 100%; max-width: 720px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-8); display: flex; gap: var(--space-8); align-items: center; }
  .body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--space-5); }
  .art { flex: none; width: 220px; margin: 0; }
  .art img { display: block; width: 100%; height: auto; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-canvas); }
  @media (max-width: 640px) {
    .card { flex-direction: column; align-items: stretch; gap: var(--space-6); padding: var(--space-6); }
    .art { width: auto; }
    .art img { width: auto; max-width: 100%; max-height: 220px; margin: 0 auto; }
  }
  .title { font-weight: 600; font-size: var(--t-panel); }
  h2 { margin: 0; font-size: var(--t-panel); font-weight: 600; }
  p { margin: 0; line-height: 1.5; }
  form { display: flex; flex-direction: column; gap: var(--space-4); }
  input { height: var(--control-md); padding: 0 var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-field); }
  .foot { font-size: var(--t-small); }
  .linkish { height: auto; padding: 0; border: 0; background: none; color: var(--link); text-decoration: underline; font: inherit; cursor: pointer; }
  .row { flex-wrap: wrap; }
</style>
