import { defineConfig } from 'vite';

export default defineConfig(({ mode }) => ({
  base: mode === 'judge' ? './' : '/',
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { outDir: mode === 'judge' ? 'judge-dist' : 'dist', emptyOutDir: true },
}));
