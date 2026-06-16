import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 48182,
    proxy: {
      '/admin-api': 'http://127.0.0.1:48181',
      '/actuator': 'http://127.0.0.1:48181'
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false
  }
})
