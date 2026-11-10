import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8080',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  },
  '/ws': {
    target: 'ws://127.0.0.1:8080',
    ws: true,
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/ws/, '')
  }
}

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    proxy
  }
})
