import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html', strict: false }),
    // Content Security Policy, written into the page as a <meta> with the hash of SvelteKit's
    // inline start-up script. The web server adds the header-only parts (frame-ancestors etc.).
    // connect-src: the Python server, Supabase (hosted sign-in, drafts), Formspree (the forms).
    // wasm-unsafe-eval: the glyph editor's tracer (esm-potrace-wasm). Inline styles: Svelte style={}.
    csp: {
      mode: 'hash',
      directives: {
        'default-src': ['self'],
        'script-src': ['self', 'wasm-unsafe-eval'],
        'style-src': ['self', 'unsafe-inline'],
        'img-src': ['self', 'data:', 'blob:'],
        'font-src': ['self', 'data:', 'blob:'],
        'connect-src': ['self', 'https://*.supabase.co', 'https://formspree.io'],
        'worker-src': ['self', 'blob:'],
        'object-src': ['none'],
        'base-uri': ['self'],
        'form-action': ['self']
      }
    }
  }
};
export default config;
