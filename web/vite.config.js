import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import UnoCSS from 'unocss/vite'

// 本地联调时可用 API_TARGET 覆盖后端地址，例如：
//   API_TARGET=http://localhost:8081 npm run dev
const apiTarget = process.env.API_TARGET || 'http://localhost:8080'

export default defineConfig({
  plugins: [UnoCSS(), vue()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': apiTarget,
      '/health': apiTarget,
    },
  },
})
