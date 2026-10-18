import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// The Python dev server (python3 -m jzpbuild.devserver) owns /api and the
// built font; in `npm run dev` the Vite server proxies to it.
export default defineConfig({
  plugins: [sveltekit()],
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
