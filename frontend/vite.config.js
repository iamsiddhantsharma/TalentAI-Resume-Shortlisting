import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/upload': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/batches': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/job-description': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/ranking': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/status': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/results': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/demo': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
});
