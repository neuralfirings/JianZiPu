<script lang="ts">
  // One spelling field of one glyph, edited in place. Checked as you type in a line under the
  // field; Enter (or leaving the field) saves it as one undo step; Esc puts the old value back.
  // A vertical form shows its partner's spelling greyed out as the placeholder.
  import * as I from '$lib/icons';
  import { app } from '$lib/state.svelte';
  import * as T from '$lib/typing';
  let {
    glyph, field, cell = false, onenter, onpastegrid
  }: {
    glyph: string; field: T.SpellField; cell?: boolean;
    onenter?: (dir: 1 | -1) => void;
    onpastegrid?: (grid: string[][]) => void;
  } = $props();

  let own = $derived(T.get(app.typing, glyph)[field]);
  let inherited = $derived(T.shown(app.typing, glyph, field).inherited);
  // a Latin Entry suggestion from the PinYin, only when the glyph has no Latin or number spelling yet, and only if free
  let suggestion = $derived.by(() => {
    const sp = T.get(app.typing, glyph);
    if (field !== 'latin' || own || inherited || sp.latin_alt || sp.common || T.partners(app.typing)[glyph]) return '';
    const c = T.pinyinToLatin(T.get(app.typing, glyph).pinyin);
    return c && T.cellNote(app.typing, glyph, 'latin', c)?.level === 'free' ? c : '';
  });
  let placeholder = $derived(inherited ? T.shown(app.typing, glyph, field).value : suggestion);
  let draft = $state<string | null>(null);
  let focused = $state(false);
  let note = $derived(focused && draft !== null ? T.cellNote(app.typing, glyph, field, draft, app.known, (g) => app.charOf(g), app.glossarySections.map((s) => s.id)) : null);
  let bad = $derived(app.typingErrors.some((e) => (e.kind === 'clash' ? e.fields.some((f) => f.glyph === glyph && f.field === field) : e.glyph === glyph && e.field === field)));
  let changed = $derived(T.get(app.savedTyping, glyph)[field] !== own);
  let zh = $derived(field === 'simplified' || field === 'traditional');
  /** In a sent Change Request: shown, not editable. */
  let locked = $derived(!!app.lockOf(`spelling:${glyph}`));
  let input = $state<HTMLInputElement>() as HTMLInputElement;

  function commit() {
    if (draft === null) return;
    const v = draft;
    draft = null;
    app.setSpelling(glyph, field, v);
  }
  function onkeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); draft = input.value; commit(); onenter?.(e.shiftKey ? -1 : 1); }
    else if (e.key === 'Escape') { e.preventDefault(); draft = null; input.value = own; input.blur(); }
    else if (e.key === 'Tab' && !e.shiftKey && !input.value && suggestion) { e.preventDefault(); input.value = suggestion; draft = suggestion; }
  }
  function onpaste(e: ClipboardEvent) {
    const text = e.clipboardData?.getData('text/plain') ?? '';
    if (onpastegrid && /[\t\n]/.test(text.replace(/\n$/, ''))) { e.preventDefault(); onpastegrid(T.parseGrid(text)); }
  }
</script>

<span class="si" class:cell>
  {#if field === 'common'}
    <span class="ro" title={T.HELP.common}>{own}</span>
  {:else}
    <input bind:this={input} type="text" value={own} {placeholder} class:zh class:bad class:changed class:inh={!!inherited && !own}
      readonly={locked} data-tip={locked ? app.lockMessage(`spelling:${glyph}`) : undefined}
      list={field === 'vert_variant' ? 'jzp-glyph-names' : field === 'glossary' ? 'jzp-glossary-sections' : undefined}
      title={inherited && !own ? `${T.LABEL[field]} of ${inherited}, its partner: typed after a colon` : T.HELP[field]}
      onfocus={() => { focused = true; draft = own; }}
      onblur={() => { focused = false; if (!locked) commit(); }}
      oninput={(e) => (draft = (e.target as HTMLInputElement).value)}
      {onkeydown} {onpaste} spellcheck="false" autocomplete="off" />
    {#if note && (note.level !== 'free' || (draft !== own && draft))}
      <span class="note {note?.level}" role="status">{#if note?.level === 'error'}<I.Problem size={12} /> {:else if note?.level === 'shared'}<I.Pair size={12} /> {:else if note?.level === 'free'}<I.Check size={12} /> {:else if note?.level === 'warn'}<I.Warn size={12} /> {/if}{note?.text}{#if note?.level === 'error'}<span class="muted"> · Enter keeps it; Save waits until it's fixed</span>{/if}</span>
    {/if}
  {/if}
</span>

<style>
  .si { position: relative; display: inline-block; width: 100%; }
  input { width: 100%; min-width: 0; height: 26px; font-family: var(--font-mono); font-size: var(--t-small); }
  input.zh { font-family: var(--font-serif); font-size: 15px; }
  .cell input { border-color: transparent; background: transparent; border-radius: 3px; }
  .cell input:hover { border-color: var(--border); }
  .cell input:focus { border-color: var(--link); background: var(--bg-field); }
  input.changed { background: color-mix(in srgb, var(--status-draft) 14%, transparent); }
  input.bad { border-color: var(--status-danger) !important; color: var(--status-danger); }
  input.inh::placeholder { color: var(--ink-muted); font-style: italic; }
  .ro { display: inline-block; padding: 0 6px; font-family: var(--font-mono); font-size: var(--t-small); color: var(--ink-muted); border-bottom: 1px dotted var(--border); }
  .note { position: absolute; left: 0; top: 100%; z-index: 20; margin-top: 2px; white-space: nowrap; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 4px; padding: 2px 8px; font-size: var(--t-caption); box-shadow: 0 4px 12px rgba(0,0,0,.12); }
  .note.error { border-color: var(--status-danger); color: var(--status-danger); }
  .note.shared { color: var(--link); }
  .note.free { color: var(--status-saved); }
  .note.warn { border-color: var(--status-draft); }
  .note.warn :global(svg) { color: var(--status-draft); }
</style>
