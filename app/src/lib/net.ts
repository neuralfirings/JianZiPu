// Was a failed request the network (offline, server unreachable) or an answer that said no?
// Browsers word a failed fetch differently: Chrome "Failed to fetch", Firefox "NetworkError when
// attempting to fetch resource.", Safari "Load failed"; Node's fetch "fetch failed".

export function isNetworkError(e: unknown): boolean {
  if (typeof navigator !== 'undefined' && navigator.onLine === false) return true;
  const msg = e instanceof Error ? e.message : String(e ?? '');
  return /failed to fetch|networkerror|load failed|network request failed|fetch failed|network connection was lost/i.test(msg);
}
