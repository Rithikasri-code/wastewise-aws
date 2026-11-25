import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-only backend origin. Override with VITE_BACKEND_ORIGIN; the fallback is
// local config, not a production URL baked into the app.
const backend = process.env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // The frontend calls relative /api paths; Vite proxies to FastAPI.
      '/api': { target: backend, changeOrigin: true },
    },
  },
})
