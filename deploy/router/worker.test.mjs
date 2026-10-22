// node --test deploy/router
import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker from './worker.js';

const env = { RAILWAY_ORIGIN: 'https://jzp.up.railway.app', CLOUDRUN_ORIGIN: 'https://jzp-builder-abc.a.run.app' };

async function route(request, vars = env, reply = new Response('ok')) {
  let sent;
  globalThis.fetch = async (url, init) => { sent = { url: String(url), init }; return reply; };
  const resp = await worker.fetch(request, vars);
  return { sent, resp };
}

test('Railway unless ACTIVE says cloudrun', async () => {
  let { sent, resp } = await route(new Request('https://builder.jianzipufont.com/glyphs?x=1'));
  assert.equal(sent.url, 'https://jzp.up.railway.app/glyphs?x=1');
  assert.equal(resp.headers.get('X-JZP-Host'), 'railway');
  ({ sent, resp } = await route(new Request('https://builder.jianzipufont.com/api/config'), { ...env, ACTIVE: 'cloudrun' }));
  assert.equal(sent.url, 'https://jzp-builder-abc.a.run.app/api/config');
  assert.equal(resp.headers.get('X-JZP-Host'), 'cloudrun');
  assert.equal(sent.init.cache, 'no-store');
});

test('a write from the Builder passes the server\'s Origin check; another site\'s does not', async () => {
  const post = (origin) => new Request('https://builder.jianzipufont.com/api/build', {
    method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json', Authorization: 'Bearer t' }, body: '{}'
  });
  let { sent } = await route(post('https://builder.jianzipufont.com'));
  assert.equal(sent.init.headers.get('Origin'), 'https://jzp.up.railway.app');
  assert.equal(sent.init.headers.get('Authorization'), 'Bearer t');
  assert.equal(sent.init.headers.get('X-Forwarded-Host'), 'builder.jianzipufont.com');
  assert.equal(sent.init.method, 'POST');
  ({ sent } = await route(post('https://evil.example')));
  assert.equal(sent.init.headers.get('Origin'), 'https://evil.example');
});

test('redirects to the host come back to the public address', async () => {
  const reply = new Response(null, { status: 301, headers: { Location: 'https://jzp.up.railway.app/help/' } });
  const { resp } = await route(new Request('https://builder.jianzipufont.com/help'), env, reply);
  assert.equal(resp.status, 301);
  assert.equal(resp.headers.get('Location'), 'https://builder.jianzipufont.com/help/');
});
