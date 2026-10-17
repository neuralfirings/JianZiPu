import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// The Python dev server (python3 -m jzpbuild.devserver) owns /api and the
// built font; in `npm run dev` the Vite server proxies to it.
export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5713',
      '/JianZiPu.ttf': 'http://127.0.0.1:5713',
      '/inputs': 'http://127.0.0.1:5713'
    }
  }
});
