<script lang="ts">
  import { page } from '$app/state';
  import { app } from '$lib/state.svelte';
  import GlyphEditor from '$lib/components/GlyphEditor.svelte';
  let name = $derived(decodeURIComponent(page.params.name ?? ''));
  let from = $derived((page.url.searchParams.get('from') as 'file' | 'image' | null) ?? null);
  let back = $derived(page.url.searchParams.get('back'));
</script>

{#if app.design && !app.loading}
  {#key name}<GlyphEditor {name} isNew={false} area={null} {from} {back} />{/key}
{:else}
  <p class="muted" style="padding: 16px">Loading…</p>
{/if}
