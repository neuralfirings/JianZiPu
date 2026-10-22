<script lang="ts">
  // Try it: every spelling of `glyph`, typed alone, through the *unsaved* spellings compiled
  // into the last build; then a free word with a breakdown. A character the font doesn't have
  // shows in red; leftover letters (a spelling that didn't match) show as plain letters.
  // With `full`, also What changes (sample words that type differently than with the saved
  // spellings) and Issues.
  import * as I from '$lib/icons';
  import { api, type TypingPreview } from '$lib/api';
  import { app } from '$lib/state.svelte';
  import { typingCheck } from '$lib/typingcheck.svelte';
  import { anchorNames, wordPage } from '$lib/shape';
  import * as T from '$lib/typing';
  import Glyph from './Glyph.svelte';
  import WordCanvas from './WordCanvas.svelte';
  let { glyph, full = false }: { glyph: string; full?: boolean } = $props();

  let free = $state(localStorage.getItem('jzp-tryit-word') ?? '');
  $effect(() => { try { localStorage.setItem('jzp-tryit-word', free); } catch {} });
  let result = $state<TypingPreview | null>(null);
  let err = $state<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;

  /** The checks: each own spelling alone, and a vertical form after a colon from its partner. */
  let checks = $derived.by(() => {
    const out: { label: string; word: string; want: string[] }[] = [];
    const s = T.get(app.typing, glyph);
    for (const f of T.TYPED) if (s[f]) out.push({ label: s[f], word: s[f], want: [glyph] });
    const partner = T.partners(app.typing)[glyph];
    if (partner) {
      const first = T.TYPED.map((f) => T.get(app.typing, partner)[f]).find(Boolean);
      if (first) out.push({ label: ':' + first, word: ':' + first, want: ['blank_colon', glyph] });
    }
    if (s.vert_variant) {
      const first = T.TYPED.map((f) => s[f]).find(Boolean);
      if (first) out.push({ label: ':' + first, word: ':' + first, want: ['blank_colon', s.vert_variant] });
    }
    if (T.isDecimal(glyph)) for (const p of T.decimalPatterns(glyph)) out.push({ label: p, word: p, want: [glyph] });
    // one check per word: 泛音 can be both the 简体 and the 繁體 spelling
    return out.filter((c, i) => out.findIndex((x) => x.word === c.word) === i);
  });
  let words = $derived([...checks.map((c) => c.word), ...free.split(/\s+/).filter(Boolean)]);

  $effect(() => {
    const d = app.design, rows = T.toRecords(app.typing), ws = words;
    if (!d || !ws.length) { result = null; return; }
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        const r = await api.typingPreview({ design: d, rows, words: ws, roundtrip: false, svg_names: app.extraGlyphs });
        if (r.ok) { result = r; err = null; } else err = r.error ?? 'preview failed';
      } catch (e) { err = (e as Error).message; }
    }, 200);
  });
  let byWord = $derived(new Map((result?.words ?? []).map((w) => [w.word, w])));
  let freeWords = $derived([...new Set(free.split(/\s+/).filter(Boolean))].map((w) => byWord.get(w)).filter(Boolean));
  const same = (a: string[], b: string[]) => a.length === b.length && a.every((x, i) => x === b[i]);
  const name = (g: string) => app.charOf(g) || g;

  let errors = $derived(app.typingErrors.filter((e) => (e.kind === 'clash' ? e.glyphs.includes(glyph) : e.glyph === glyph)));
  let warnings = $derived(typingCheck.warningsFor(glyph));
</script>

{#snippet out(glyphs: string[], texts: string[])}
  <span class="out">
    {#each glyphs as g, i}
      {#if g === '.notdef'}<span class="miss" title="Not in the font yet: it arrives with the next Build">{texts[i]}</span>
      {:else if app.svgs[g]}<Glyph name={g} size={30} />
      {:else if g === 'blank_colon'}<span class="sym">:</span>
      {:else}<span class="stray" title="Not a notation glyph: typed letters or a character that didn't match">{texts[i] || g}</span>{/if}
    {/each}
  </span>
{/snippet}

<div class="try">
  {#if err}<p class="muted small">{err}</p>{/if}
  <div class="checks">
    {#each checks as c (c.word)}
      {@const w = byWord.get(c.word)}
      <div class="chk" class:ok={w && same(w.glyphs, c.want)} class:bad={w && !same(w.glyphs, c.want)} title={w && !same(w.glyphs, c.want) ? `gives ${w.glyphs.join(' + ')}` : ''}>
        {#if w}{@render out(w.glyphs, w.texts)}{:else}<span class="muted">…</span>{/if}
        <small class="mono">{c.label} {#if w}{#if same(w.glyphs, c.want)}<I.Check size={12} />{:else}<I.Warn size={12} />{/if}{/if}</small>
      </div>
    {:else}
      <span class="muted small">No spellings yet: type one and it previews here at once.</span>
    {/each}
  </div>
  <input type="text" bind:value={free} placeholder="Try a word: s7lun5" class="free" spellcheck="false" />
  {#each freeWords as w (w!.word)}
    <div class="word">
      <WordCanvas elements={w!.pieces.flatMap((p, pi) => { const an = anchorNames(p.elements, app.design!.areas); return p.elements.map((e) => ({ ...e, name: `${pi}:${e.name}`, anchor: an.has(e.name) })); })} width={44} height={70} showBoxes={false} showGlyphs={true} showPage={true} page={wordPage(w!)} fit={false} />
      <span class="brk">
        {#each w!.glyphs as g, i}{i ? ' ' : ''}<span class:miss={g === '.notdef'}>{w!.texts[i]}</span>→{#if g === '.notdef'}<span class="miss">not in font</span>{:else if app.svgs[g]}<b>{name(g)}</b>{:else}<span class="stray">{g}</span>{/if}{/each}
        {#if !w!.pieces.some((p) => p.layout)}<span class="muted"> · no word type matched</span>{/if}
      </span>
    </div>
  {/each}

  {#if full}
    <div class="sub">
      <h5>What changes {#if typingCheck.busy}<span class="muted">· checking…</span>{/if}</h5>
      {#if !app.typingDirty}<span class="muted small">No unsaved spelling changes.</span>
      {:else if typingCheck.changed.length === 0}<span class="muted small">No sample word types differently ({typingCheck.sampleWords.length} checked).</span>
      {:else}
        <span class="warn small">{typingCheck.changed.length} of {typingCheck.sampleWords.length} sample words type differently:</span>
        {#each typingCheck.changed.slice(0, 6) as c (c.word)}
          <div class="chg"><span class="mono small">{c.word}</span>{@render out(c.before, [])}<span>→</span>{@render out(c.after, c.after_texts)}</div>
        {/each}
        {#if typingCheck.changed.length > 6}<span class="muted small">… and {typingCheck.changed.length - 6} more</span>{/if}
      {/if}
    </div>
  {/if}
  {#if full || errors.length || warnings.length}
    <div class="sub">
      {#if full}<h5>Issues</h5>{/if}
      {#each errors as e}<div class="err small"><I.Problem size={12} /> {e.message}</div>{/each}
      {#each warnings as w}<div class="warn small"><I.Warn size={12} /> {w}</div>{/each}
      {#if full && !errors.length && !warnings.length}<span class="muted small">None.</span>{/if}
    </div>
  {/if}
</div>

<style>
  .try { display: flex; flex-direction: column; gap: var(--space-4); min-width: 0; }
  .checks { display: flex; flex-wrap: wrap; gap: var(--space-4); }
  .chk { display: flex; flex-direction: column; align-items: center; gap: 1px; padding: 3px 5px; border: 1px dashed var(--border); border-radius: 4px; background: var(--bg-field); min-width: 44px; }
  .chk.ok { border-style: solid; border-color: var(--status-saved); }
  .chk.bad { border-style: solid; border-color: var(--status-draft); background: color-mix(in srgb, var(--status-draft) 10%, var(--bg-field)); }
  .out { display: inline-flex; align-items: center; gap: 2px; min-height: 30px; }
  .miss { color: var(--status-danger); font-size: 20px; }
  .brk .miss { font-size: inherit; }
  .stray { font-family: var(--font-mono); color: var(--ink-muted); font-size: var(--t-small); }
  .sym { font-family: var(--font-mono); color: var(--ink-muted); }
  .free { font-family: var(--font-mono); width: 100%; }
  .word { display: flex; align-items: flex-end; gap: var(--space-4); }
  .brk { font-size: var(--t-caption); color: var(--ink-muted); }
  .brk b { color: var(--ink); font-weight: 400; font-size: var(--t-small); }
  .sub { display: flex; flex-direction: column; gap: 3px; border-top: 1px dashed var(--border); padding-top: var(--space-4); }
  h5 { margin: 0; font-size: var(--t-small); font-weight: 600; }
  .chg { display: flex; align-items: center; gap: var(--space-4); }
  .small { font-size: var(--t-caption); }
  .err { color: var(--status-danger); }
  .warn { color: var(--status-draft); }
</style>
