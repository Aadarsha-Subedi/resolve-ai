import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

// The backend serves everything under /api (session cookie auth), so the dev
// server proxies it to keep cookies same-site. The browser always calls the dev
// server's own origin (http://localhost:3000/api/...); the proxy forwards it to
// VITE_API_PROXY_TARGET. Vite does not copy .env values into process.env for this
// file, so they are read with loadEnv (a variable set in the shell still wins).
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, import.meta.dirname, ''), ...process.env }
  return {
    plugins: [tanstackRouter({ target: 'react', autoCodeSplitting: true }), react(), tailwindcss()],
    resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
    server: {
      // 3000 is what the backend's FRONTEND_URL, CORS and CSRF origins expect.
      port: Number(env.VITE_DEV_PORT ?? 3000),
      strictPort: true,
      // Listen on all interfaces so a container's published port reaches the server.
      host: true,
      // Bind mounts from Docker Desktop do not deliver file events; set VITE_USE_POLLING=true there.
      // Generated folders stay out of the watcher: polling a pnpm store or router cache inside the project slows every reload.
      watch: {
        ignored: ['**/.pnpm-store/**', '**/.tanstack/**', '**/dist/**'],
        ...(env.VITE_USE_POLLING === 'true' ? { usePolling: true, interval: 300 } : {}),
      },
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
          // Keep the browser's Host so the backend builds redirect and CSRF origins for localhost:3000.
          changeOrigin: false,
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  }
})
