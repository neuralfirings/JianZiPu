import { beforeEach, describe, expect, it } from 'vitest';
import { dismissUpdate, pilot, updateDismissedFor } from './pilot.svelte';

describe('the new-release banner', () => {
  beforeEach(() => { localStorage.clear(); pilot.updateDismissed = false; });

  it('Not now lasts for that release, in this browser, for this tester', () => {
    dismissUpdate('u1', '3.300');
    expect(pilot.updateDismissed).toBe(true);
    expect(updateDismissedFor('u1', '3.300')).toBe(true);
    expect(updateDismissedFor('u1', '3.400')).toBe(false);   // a newer release shows again
    expect(updateDismissedFor('u2', '3.300')).toBe(false);
  });
});
