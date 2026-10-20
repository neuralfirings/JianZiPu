import { describe, it, expect } from 'vitest';
import { createHash } from 'node:crypto';
import { sha256, sha256Hex } from './sha256';

describe('sha256Hex (for http pages without crypto.subtle)', () => {
  it('matches the standard vectors and node, across block boundaries and non-ASCII text', () => {
    expect(sha256Hex('')).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
    expect(sha256Hex('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
    for (const t of ['a'.repeat(55), 'a'.repeat(56), 'a'.repeat(64), '勾 <svg viewBox="0 0 350 350"/>\n'.repeat(500)])
      expect(sha256Hex(t)).toBe(createHash('sha256').update(t, 'utf8').digest('hex'));
  });
  it('sha256 gives the same answer with or without the browser one', async () => {
    const t = '<svg><path d="M0 0L10 10"/></svg>';
    expect(await sha256(t)).toBe(sha256Hex(t));
  });
});
