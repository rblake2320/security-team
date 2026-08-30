import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const showcase = mode === 'showcase'
  const buildProfile = showcase ? 'showcase' : 'operator'
  return {
    plugins: [
      react(),
      {
        name: 'aegis-build-profile-receipt',
        generateBundle() {
          this.emitFile({ type: 'asset', fileName: 'aegis-build-profile.txt', source: `${buildProfile}\n` })
        },
      },
    ],
    resolve: {
      alias: showcase
        ? [{ find: /^\.\/api$/, replacement: fileURLToPath(new URL('./src/api.showcase.ts', import.meta.url)) }]
        : [],
    },
    server: {
      proxy: {
        '/api': 'http://127.0.0.1:8765',
      },
    },
    build: {
      sourcemap: false,
    },
  }
})
