<script lang="ts">
  // Beside a strip of test words (the glyph editor's Tester, Build & test's Test the design): the glyph
  // picked in a word, the word type that placed it, and links to edit either. Double-clicking a glyph in
  // the word opens its editor too (WordCanvas onopen).
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import type { WordPayload } from '$lib/api';
  import Glyph from './Glyph.svelte';

  type Word = WordPayload['words'][number];
  let { word, name, back, onclose }: {
    word: Word;
    /** The picked element: `<piece index>:<slot>`, as the word strips name them. */
    name: string;
    /** Where the glyph editor's back link returns to (this screen). */
    back: string;
    onclose: () => void;
  } = $props();

  let at = $derived(name.indexOf(':'));
  let piece = $derived(word.pieces[+name.slice(0, at)] ?? null);
  let el = $derived(piece?.elements.find((e) => e.name === name.slice(at + 1)) ?? null);
  let layout = $derived(piece?.layout ? app.design?.layouts.find((l) => l.name === piece!.layout) ?? null : null);
  let ch = $derived(el?.glyph ? app.charOf(el.glyph) : '');
</script>

<aside class="info" aria-label="The picked glyph">
  <div class="head">
    <span class="mono">{word.word}</span>
    <button class="ghost sm" onclick={onclose} data-tip="Close" aria-label="Close"><I.Close size={14} /></button>
  </div>
  {#if el?.glyph}
    <div class="sec">
      <span class="k">Glyph</span>
      <div class="g"><Glyph name={el.glyph} size={32} /><span><span class="mono">{el.glyph}</span>{#if ch} <span class="cjk">{ch}</span>{/if}<br /><span class="muted small">in {app.areaLabel(el.area)}</span></span></div>
      <a href="/glyphs/{encodeURIComponent(el.glyph)}/edit?back={encodeURIComponent(back)}">Edit outline</a>
    </div>
  {/if}
  <div class="sec">
    <span class="k">Word type</span>
    {#if layout}
      <span>{layout.label}</span>
      <a href="/layouts?word={encodeURIComponent(word.word)}">Edit in Layouts</a>
    {:else}
      <span class="muted">None: this part of the word matched no word type, so the font doesn't place it.</span>
    {/if}
  </div>
  <p class="muted small">Double-click a glyph to edit its outline.</p>
</aside>

<style>
  .info { display: flex; flex-direction: column; gap: var(--space-4); width: 220px; flex: none; padding: var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-panel); font-size: var(--t-small); align-self: flex-start; max-height: 100%; overflow: auto; }
  .head { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
  .head .mono { font-family: var(--font-mono); font-size: var(--t-label); }
  .sec { display: flex; flex-direction: column; gap: var(--space-2); }
  .k { color: var(--ink-muted); font-size: var(--t-caption); }
  .g { display: flex; align-items: center; gap: var(--space-3); }
  .mono { font-family: var(--font-mono); }
  .cjk { font-family: var(--font-cjk); }
  .small { font-size: var(--t-caption); }
  p { margin: 0; }
</style>
