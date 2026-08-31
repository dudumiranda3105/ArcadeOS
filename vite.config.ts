import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8000' },
    watch: { ignored: ['**/.tools/**', '**/.runtime/**', '**/.venv/**', '**/.pnpm-store/**'] },
    fs: { deny: ['.env', '.env.*', '*.{crt,pem}', '**/.git/**', '**/.runtime/**', '**/.tools/**', '**/.venv/**', '**/backend/**'] },
  },
})
