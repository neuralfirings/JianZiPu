<script lang="ts">
  // Beside a strip of test words (the Testers, Build & test's Test the design): the glyph picked in a word,
  // compactly: its name with Edit (its outline), and the area it sits in with Edit (Layouts, on this word,
  // with that area's properties). Double-clicking a glyph in the word opens its editor too (WordCanvas onopen).
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import type { WordPayload } from '$lib/api';
  import Glyph from './Glyph.svelte';

  type Word = WordPayload['words'][number];
  let { word, name, back, onclose, onedit }: {
    word: Word;
    /** The picked element: `<piece index>:<slot>`, as the word strips name them. */
    name: string;
    /** Where the glyph editor's back link returns to (this screen). */
    back: string;
    onclose: () => void;
    /** On the Layouts screen: load the word into its canvas and show the area there, rather than open /layouts again. */
    onedit?: () => void;
  } = $props();

  let at = $derived(name.indexOf(':'));
  let piece = $derived(word.pieces[+name.slice(0, at)] ?? null);
  let el = $derived(piece?.elements.find((e) => e.name === name.slice(at + 1)) ?? null);
  let layoutHref = $derived(el ? `/layouts?word=${encodeURIComponent(word.word)}&area=${encodeURIComponent(el.area)}${el.glyph ? `&g=${encodeURIComponent(el.glyph)}` : ''}` : '');
</script>

<aside class="info" aria-label="The picked glyph">
  <div class="head">
    <span class="mono">{word.word}</span>
    <button class="ghost sm" onclick={onclose} data-tip="Close" aria-label="Close"><I.Close size={14} /></button>
  </div>
  {#if el}
    <div class="g">
      {#if el.glyph}<Glyph name={el.glyph} size={32} />{/if}
      <div class="lines">
        {#if el.glyph}<div><span class="mono">{el.glyph}</span> <a href="/glyphs/{encodeURIComponent(el.glyph)}/edit?back={encodeURIComponent(back)}">Edit</a></div>{/if}
        <div>
          <span class="muted">in Layouts › {app.areaLabel(el.area)}</span>
          {#if !piece?.layout}<span class="muted"> · no word type matched</span>{/if}
          {#if onedit}<button class="link" onclick={onedit}>Edit</button>{:else}<a href={layoutHref}>Edit</a>{/if}
        </div>
      </div>
    </div>
  {/if}
</aside>

<style>
  .info { display: flex; flex-direction: column; gap: var(--space-3); width: 220px; flex: none; padding: var(--space-3) var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-panel); font-size: var(--t-small); align-self: flex-start; max-height: 100%; overflow: auto; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
  .head .mono { font-family: var(--font-mono); font-size: var(--t-label); }
  .g { display: flex; align-items: center; gap: var(--space-3); }
  .lines { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .mono { font-family: var(--font-mono); overflow-wrap: anywhere; }
  button.link { height: auto; padding: 0; border: 0; background: none; color: var(--link); text-decoration: underline; font: inherit; cursor: pointer; }
</style>
