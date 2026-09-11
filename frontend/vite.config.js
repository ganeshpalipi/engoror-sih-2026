import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// RootVerse frontend config.
// In dev, /health and /api/* are proxied to the FastAPI backend so the UI
// works without CORS friction. In production builds, set VITE_API_BASE_URL
// in frontend/.env to point at the backend origin.
export default defineConfig({
  plugins: [react()],
  // RootVerse uses plain CSS (no PostCSS plugins). Pinning an empty inline
  // config stops Vite from searching parent folders for a postcss.config
  // file and accidentally inheriting someone else's setup.
  css: {
    postcss: {},
  },
  server: {
    port: 5173,
    proxy: {
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
