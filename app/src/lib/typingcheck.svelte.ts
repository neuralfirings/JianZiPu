// The server's view of the current (unsaved) spellings: every spelling typed alone
// must give its own glyph (the round trip), which sample words change against the saved
// spellings, and what the last build can't show yet. Reruns shortly after each edit.
import { api, type RoundTrip, type TypingPreview } from './api';
import { app } from './state.svelte';
import * as T from './typing';
import { SAMPLE_SETS } from './words';

class TypingCheck {
  roundtrip = $state<RoundTrip[]>([]);
  changed = $state<NonNullable<TypingPreview['changed']>>([]);
  notBuilt = $state<string[]>([]);
  missing = $state<Record<string, string[]>>({});
  /** The server has the base font, so a missing character is one the base font lacks too. */
  baseFont = $state(false);
  error = $state<string | null>(null);
  busy = $state(false);
  ran = $state(false);
  private timer: ReturnType<typeof setTimeout> | null = null;
  private seq = 0;

  /** Sample words for "What changes": the built-in sets plus the design's own test sets. */
  get sampleWords(): string[] {
    const sets = [...Object.values(SAMPLE_SETS), ...Object.values(app.design?.test_sets ?? {})];
    return [...new Set(sets.flat().flatMap((w) => w.split(/\s+/)).filter(Boolean))];
  }

  schedule(delay = 350) {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => this.run(), delay);
  }

  async run() {
    if (!app.design) return;
    const id = ++this.seq;
    this.busy = true;
    try {
      const dirty = app.typingDirty;
      const r = await api.typingPreview({
        design: app.design, rows: T.toRecords(app.typing), roundtrip: true, svg_names: app.extraGlyphs, svgs: app.extraSvgs,
        base_rows: dirty ? T.toRecords(app.savedTyping) : undefined,
        compare_words: dirty ? this.sampleWords : []
      });
      if (id !== this.seq) return;
      if (!r.ok) { this.error = r.error ?? 'preview failed'; return; }
      this.error = null;
      this.roundtrip = r.roundtrip ?? [];
      this.changed = r.changed ?? [];
      this.notBuilt = r.not_built ?? [];
      this.missing = r.missing_chars ?? {};
      this.baseFont = !!r.base_font;
      this.ran = true;
    } catch (e) {
      if (id === this.seq) this.error = (e as Error).message;
    } finally {
      if (id === this.seq) this.busy = false;
    }
  }

  /** Warnings for one glyph (Save still works). */
  warningsFor(g: string): string[] {
    const out = this.roundtrip.filter((r) => r.glyph === g).map((r) => r.message);
    for (const v of new Set(this.missing[g] ?? []))      // 简体 and 繁體 alike: once
      out.push(this.baseFont ? `${v}: the base font (TW-Kai) doesn't have this character, so the font can't type it.`
        : `${v}: not in the font yet. It arrives with the next Build.`);
    if (this.notBuilt.includes(g)) out.push(`${g} has no drawing yet, so it can't be previewed. Draw it in the glyph editor.`);
    return out;
  }
  /** Everything wrong with one glyph's spellings, errors (Save waits) first. */
  issuesFor(g: string): string[] {
    return [...app.typingErrors.filter((e) => (e.kind === 'clash' ? e.glyphs.includes(g) : e.glyph === g)).map((e) => e.message), ...this.warningsFor(g)];
  }
  /** 'err' when Save waits on this glyph, 'warn' when it only has warnings. */
  statusOf(g: string): 'err' | 'warn' | '' {
    if (app.typingErrors.some((e) => (e.kind === 'clash' ? e.glyphs.includes(g) : e.glyph === g))) return 'err';
    return this.warningsFor(g).length ? 'warn' : '';
  }
}

export const typingCheck = new TypingCheck();
