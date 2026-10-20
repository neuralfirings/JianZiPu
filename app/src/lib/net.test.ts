import { describe, it, expect } from 'vitest';
import { isNetworkError } from './net';

describe('isNetworkError', () => {
  it('knows each browser’s words for a fetch that never got an answer', () => {
    for (const m of ['Failed to fetch', 'NetworkError when attempting to fetch resource.', 'Load failed', 'fetch failed', 'TypeError: Network request failed'])
      expect(isNetworkError(new Error(m)), m).toBe(true);
  });
  it('treats an answer that said no as not the network', () => {
    for (const m of ['new row violates row-level security policy', 'The object exceeded the maximum allowed size', 'Bucket not found', 'jwt expired'])
      expect(isNetworkError(new Error(m)), m).toBe(false);
  });
});
