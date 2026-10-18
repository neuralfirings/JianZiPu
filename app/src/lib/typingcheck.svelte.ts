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
        design: app.design, rows: T.toRecords(app.typing), roundtrip: true,
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
    for (const v of this.missing[g] ?? []) out.push(`${v}: not in the font yet. It arrives with the next Build.`);
    if (this.notBuilt.includes(g)) out.push(`${g} isn't in the last build yet. Build to preview it.`);
    return out;
  }
}

export const typingCheck = new TypingCheck();
