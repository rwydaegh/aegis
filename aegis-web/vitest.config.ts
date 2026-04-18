import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      reportsDirectory: './coverage',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.spec.ts',
        'src/**/*.spec.tsx',
        'src/**/*.test.ts',
        'src/**/*.test.tsx',
        'src/**/__tests__/**',
        'src/vite-env.d.ts',
      ],
    },
  },
})
