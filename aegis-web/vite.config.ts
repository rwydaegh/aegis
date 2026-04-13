import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import path from 'path'

export default defineConfig({
  build: {
    sourcemap: 'hidden',
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/three/') || id.includes('@react-three/')) {
            return 'three'
          }
          if (id.includes('@deck.gl/')) {
            return 'deckgl'
          }
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/') ||
              id.includes('node_modules/zustand/') || id.includes('node_modules/recharts/')) {
            return 'vendor'
          }
        },
      },
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    // Upload source maps to Sentry during production builds (requires SENTRY_AUTH_TOKEN env var)
    sentryVitePlugin({
      org: process.env.SENTRY_ORG,
      project: process.env.SENTRY_PROJECT,
      authToken: process.env.SENTRY_AUTH_TOKEN,
      disable: !process.env.SENTRY_AUTH_TOKEN,
      errorHandler: (err) => {
        console.warn('[sentry-vite-plugin] Source map upload failed (non-fatal):', err.message)
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        timeout: 120000,
      },
    },
  },
})
