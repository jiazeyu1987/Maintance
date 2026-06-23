import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import packageJson from './package.json'

const appVersion = packageJson.version

if (!appVersion) {
  throw new Error('frontend package version is required')
}

export default defineConfig({
  plugins: [vue()],
  define: {
    __APP_VERSION__: JSON.stringify(appVersion)
  },
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
