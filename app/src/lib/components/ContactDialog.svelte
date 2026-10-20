<script lang="ts">
  // "Ask for an invite" and "Feedback": a dialog that posts to Formspree (lib/forms.ts) and
  // thanks you in place. Feedback also sends the screen it was opened from and the app version.
  import { onMount } from 'svelte';
  import { sendForm, type FormKind } from '$lib/forms';

  let { kind, name: name0 = '', email: email0 = '', context = {}, onclose }: {
    kind: FormKind;
    /** Prefill, e.g. from the signed-in tester. */
    name?: string; email?: string;
    /** Extra fields sent along (feedback: page, version). */
    context?: Record<string, string>;
    onclose: () => void;
  } = $props();

  // svelte-ignore state_referenced_locally
  let name = $state(name0), email = $state(email0);
  let message = $state('');   // feedback: the message; invite: about yourself
  let gotcha = $state('');
  let busy = $state(false);
  let err = $state<string | null>(null);
  let sent = $state(false);
  let first: HTMLInputElement | HTMLTextAreaElement | undefined = $state();

  const emailOk = $derived(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()));
  const ready = $derived(emailOk && !!message.trim() && (kind === 'feedback' || !!name.trim()));
  const title = $derived(kind === 'invite' ? 'Ask for an invite' : 'Send feedback');

  onMount(() => first?.focus());

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    if (!ready || busy) return;
    busy = true; err = null;
    const fields: Record<string, string> = { name, email, _gotcha: gotcha, ...context };
    fields[kind === 'invite' ? 'about' : 'message'] = message;
    const r = await sendForm(kind, fields);
    busy = false;
    if (r.ok) sent = true; else err = r.error;
  }
</script>

<div class="modal-bg" role="presentation" onclick={onclose}>
  <div class="modal contact" role="dialog" aria-modal="true" aria-labelledby="contact-title" tabindex="-1"
    onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === 'Escape' && onclose()}>
    {#if sent}
      <h3 id="contact-title">{kind === 'invite' ? 'Thank you, request sent' : 'Thank you, feedback sent'}</h3>
      <p>{kind === 'invite' ? `Nancy will get back to you at ${email.trim()}.` : 'Nancy reads every note. If it needs an answer, it goes to the email you gave.'}</p>
      <div class="row end"><button class="primary" onclick={onclose}>Close</button></div>
    {:else}
      <h3 id="contact-title">{title}</h3>
      <p class="muted">{kind === 'invite' ? 'The pilot is open to a few testers. Leave your details and Nancy will be in touch.' : 'Confusing, broken or lovely: it all helps.'}</p>
      <form onsubmit={submit}>
        <label>Name<input bind:this={first} type="text" autocomplete="name" bind:value={name} required={kind === 'invite'} placeholder={kind === 'invite' ? '' : 'Optional'} /></label>
        <label>Email<input type="email" autocomplete="email" bind:value={email} required placeholder="you@example.com" /></label>
        {#if kind === 'invite'}
          <label>Tell me a bit about yourself <span class="hint">(e.g., whether you play Guqin, have an interest in font design, something else)</span>
            <textarea rows="4" bind:value={message} required></textarea></label>
        {:else}
          <label>Your message<textarea rows="6" bind:value={message} required></textarea></label>
        {/if}
        <!-- Formspree's spam trap: people never see or fill it -->
        <input class="trap" type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true" bind:value={gotcha} />
        {#if err}<p class="banner danger" role="alert"><span class="ic">×</span>{err}</p>{/if}
        <div class="row end">
          <button type="button" onclick={onclose}>Cancel</button>
          <button class="primary" disabled={!ready || busy}>{busy ? 'Sending…' : kind === 'invite' ? 'Ask for an invite' : 'Send feedback'}</button>
        </div>
      </form>
    {/if}
  </div>
</div>

<style>
  .contact { width: min(460px, calc(100vw - 32px)); display: flex; flex-direction: column; gap: var(--space-4); }
  .contact p { margin: 0; line-height: 1.5; }
  form { display: flex; flex-direction: column; gap: var(--space-4); }
  label { display: flex; flex-direction: column; gap: var(--space-2); font-weight: 600; font-size: var(--t-label); }
  .hint { font-weight: 400; color: var(--ink-muted); }
  input[type='text'], input[type='email'], textarea { font-weight: 400; padding: var(--space-3) var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-field); font: inherit; font-weight: 400; }
  input[type='text'], input[type='email'] { height: var(--control-md); padding-block: 0; }
  textarea { resize: vertical; }
  .trap { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }
  .end { justify-content: flex-end; gap: var(--space-3); }
</style>
