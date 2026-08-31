import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const showcase = mode === 'showcase'
  const buildProfile = showcase ? 'showcase' : 'operator'
  const canonicalUrl = showcase ? 'https://showcase.aihangout.ai/' : 'https://mission.aihangout.ai/'
  const pageTitle = showcase ? 'AEGIS Public Showcase // Interactive Mission' : 'AEGIS // Mission Control'
  const pageDescription = showcase
    ? 'Run a safe, browser-contained AEGIS security mission with synthetic inputs, seven-team processing, comparison and demo evidence exports.'
    : 'Private AEGIS Security Program Mission Control for governed security operations.'
  return {
    plugins: [
      react(),
      {
        name: 'aegis-build-profile-receipt',
        generateBundle() {
          this.emitFile({ type: 'asset', fileName: 'aegis-build-profile.txt', source: `${buildProfile}\n` })
        },
      },
      {
        name: 'aegis-profile-metadata',
        transformIndexHtml(html) {
          return html
            .replaceAll('__AEGIS_CANONICAL_URL__', canonicalUrl)
            .replaceAll('__AEGIS_TITLE__', pageTitle)
            .replaceAll('__AEGIS_DESCRIPTION__', pageDescription)
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
