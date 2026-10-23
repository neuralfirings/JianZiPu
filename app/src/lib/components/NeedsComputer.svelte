<script lang="ts">
  // On a phone, in place of a tool that needs a mouse and a big screen (lib/phone.svelte.ts SCREENS):
  // what it is, a way to take the link to a computer, and a quiet way through for this visit.
  import * as I from '$lib/icons';
  import { goto } from '$app/navigation';
  import { openedAnyway } from '$lib/phone.svelte';
  import { pilot } from '$lib/pilot.svelte';
  import Glyph from './Glyph.svelte';
  // onclose: in a dialog, Close takes the place of Back
  let { tool, key, glyph = null, onclose, onanyway }:
    { tool: string; key: string; glyph?: string | null; onclose?: () => void; onanyway?: () => void } = $props();

  async function copy() {
    try { await navigator.clipboard.writeText(location.href); pilot.say('Link copied. Open it on a computer.'); }
    catch { prompt('The link to this page:', location.href); }
  }
  function goBack() { if (history.length > 1) history.back(); else goto('/glyphs'); }
  function anyway() { openedAnyway[key] = true; onanyway?.(); }
</script>

<section class="needs" data-needs-computer>
  {#if glyph}<div class="glyph"><Glyph name={glyph} size={120} /></div>{/if}
  <div class="banner info">
    <span class="ic"><I.Computer /></span>
    <span><b>{tool} needs a computer.</b> It's made for a mouse and a big screen. Open this page on a computer, or open it here anyway.</span>
  </div>
  <div class="acts">
    <button class="primary" onclick={copy}><I.Link /> Copy link</button>
    {#if onclose}<button onclick={onclose}>Close</button>{:else}<button onclick={goBack}><I.Back /> Back</button>{/if}
    <span class="spacer"></span>
    <button class="quiet" onclick={anyway}>Open anyway</button>
  </div>
</section>

<style>
  .needs { display: flex; flex-direction: column; gap: var(--space-5); max-width: 560px; margin: 0 auto; padding: var(--space-6); }
  .glyph { display: flex; justify-content: center; padding: var(--space-6); background: var(--bg-canvas); border: 1px solid var(--border); border-radius: var(--radius-lg); }
  .acts { display: flex; flex-wrap: wrap; gap: var(--space-4); align-items: center; }
  .spacer { flex: 1; }
</style>
