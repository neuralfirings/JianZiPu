import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// The Python web server (python3 -m jzpbuild.webserver) owns /api and the
// built font; in `npm run dev` the Vite server proxies to it.
export default defineConfig({
  plugins: [sveltekit()],
  // under Vitest, resolve Svelte's browser build so component tests can mount() (it is the client app anyway)
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
  test: {
    // unit tests next to the code: src/**/*.test.ts (npm test). jsdom + node-canvas let Paper.js run.
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['src/test-setup.ts']
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5713',
      '/JianZiPu.ttf': 'http://127.0.0.1:5713',
      '/inputs': 'http://127.0.0.1:5713'
    }
  }
});
