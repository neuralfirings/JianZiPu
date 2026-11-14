import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html', strict: false }),
    // Content Security Policy, written into the page as a <meta> with the hash of SvelteKit's
    // inline start-up script. The web server adds the header-only parts (frame-ancestors etc.).
    // connect-src: the Python server, Supabase (hosted sign-in, drafts), Formspree (the forms), emfont
    // (lib/webfonts.ts reads its stylesheet to add size-adjust).
    // wasm-unsafe-eval: the glyph editor's tracer (esm-potrace-wasm). Inline styles: Svelte style={}.
    csp: {
      mode: 'hash',
      directives: {
        'default-src': ['self'],
        'script-src': ['self', 'wasm-unsafe-eval'],
        // font.emtech.cc + Google Fonts: the Chinese webfonts (lib/webfonts.ts)
        'style-src': ['self', 'unsafe-inline', 'https://font.emtech.cc', 'https://fonts.googleapis.com'],
        'img-src': ['self', 'data:', 'blob:'],
        'font-src': ['self', 'data:', 'blob:', 'https://font.emtech.cc', 'https://fonts.gstatic.com'],
        'connect-src': ['self', 'https://*.supabase.co', 'https://formspree.io', 'https://font.emtech.cc'],
        'worker-src': ['self', 'blob:'],
        'object-src': ['none'],
        'base-uri': ['self'],
        'form-action': ['self']
      }
    }
  }
};
export default config;
