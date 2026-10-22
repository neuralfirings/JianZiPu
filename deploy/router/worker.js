// The router at builder.jianzipufont.com (docs/maintainers/setup.md "The router"): a Cloudflare
// Worker that passes every request to the host serving the Builder now, Railway or its Cloud Run
// backup, so switching hosts changes nothing testers see: same address, same sign-in, same drafts.
// The switch is the variable ACTIVE ("railway", the default, or "cloudrun"), set in the Cloudflare
// dashboard; the hosts' own addresses are in wrangler.toml.

export default {
  async fetch(request, env) {
    const name = env.ACTIVE === 'cloudrun' ? 'cloudrun' : 'railway';
    const upstream = new URL(name === 'cloudrun' ? env.CLOUDRUN_ORIGIN : env.RAILWAY_ORIGIN);
    const url = new URL(request.url);
    const headers = new Headers(request.headers);
    // the server refuses a write whose Origin isn't the host it was asked on (webserver.py
    // request_problem); a request from this address is the host's own, any other stays refused
    if (headers.get('Origin') === url.origin) headers.set('Origin', upstream.origin);
    headers.delete('X-Forwarded-Host');        // nothing may build links from a host a client names
    const resp = await fetch(new URL(url.pathname + url.search, upstream), {
      method: request.method, headers, body: request.body, redirect: 'manual',
      cache: 'no-store'                        // never Cloudflare's cache: builds are per tester
    });
    const out = new Response(resp.body, resp);
    const loc = out.headers.get('Location');
    if (loc?.startsWith(upstream.origin)) out.headers.set('Location', url.origin + loc.slice(upstream.origin.length));
    out.headers.set('X-JZP-Host', name);       // which host answered: curl -sI https://builder.jianzipufont.com
    return out;
  }
};
