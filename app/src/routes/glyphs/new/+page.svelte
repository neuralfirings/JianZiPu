<script lang="ts">
  import { page } from '$app/state';
  import { app } from '$lib/state.svelte';
  import GlyphEditor from '$lib/components/GlyphEditor.svelte';
  let name = $derived(page.url.searchParams.get('name') ?? '');
  let area = $derived(page.url.searchParams.get('area') || null);
</script>

{#if !name}
  <p class="muted" style="padding: 16px">No glyph name. <a href="/glyphs">Back to Glyphs</a></p>
{:else if app.design && !app.loading}
  {#key name}<GlyphEditor {name} isNew={true} {area} />{/key}
{:else}
  <p class="muted" style="padding: 16px">Loading…</p>
{/if}
