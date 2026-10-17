<script lang="ts">
  let { label, hint = 'Coming soon' }: { label: string; hint?: string } = $props();
</script>

<button class="soon" aria-disabled="true" title={hint} onclick={(e) => e.preventDefault()}>
  <span aria-hidden="true">🔒</span> {label} <span class="muted">soon</span>
</button>
