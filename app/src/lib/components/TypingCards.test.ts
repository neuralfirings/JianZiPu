// The phone's Typing cards show the same fields as the table, and a tap opens the glyph.
import { describe, it, expect, vi, afterEach } from 'vitest';
import { flushSync, mount, unmount } from 'svelte';
import TypingCards from './TypingCards.svelte';
import { app } from '$lib/state.svelte';
import * as T from '$lib/typing';

afterEach(() => { document.body.innerHTML = ''; app.typing = {}; });

describe('TypingCards', () => {
  it('lists every filled spelling with the table labels, and a tap selects the glyph', () => {
    app.typing = { lg_gou: { ...T.empty(), latin: 'k', simplified: '勾', pinyin: 'gōu' }, md_1: T.empty() };
    const onselect = vi.fn();
    const c = mount(TypingCards, { target: document.body, props: { sections: [{ key: 'right', title: 'Right hand', glyphs: ['lg_gou', 'md_1'] }], selected: null, onselect } });
    flushSync();
    const [gou, one] = [...document.querySelectorAll<HTMLButtonElement>('button.card')];
    const shown = [...gou.querySelectorAll('.sp')].map((e) => e.textContent!.trim());
    expect(shown).toEqual([`${T.LABEL.latin} k`, `${T.LABEL.simplified} 勾`, `${T.LABEL.pinyin} gōu`]);
    expect(T.FIELDS.filter((f) => ['latin', 'simplified', 'pinyin'].includes(f))).toEqual(['latin', 'simplified', 'pinyin']);   // the table's order
    expect(one.textContent).toContain('no spellings yet');
    gou.click();
    expect(onselect).toHaveBeenCalledWith('lg_gou');
    unmount(c);
  });
});
