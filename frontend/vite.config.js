// vite.config.js
// Vite build configuration for the Helix dashboard.
// Enables React fast refresh and proxies API calls to the FastAPI backend.

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy REST API calls to FastAPI backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      // WebSocket proxy
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
