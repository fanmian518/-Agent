import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Vite 配置：Vue3 + TS + 路径别名 @ -> /src
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
    // —— 后端联调时解开下面的注释（把 /api 转发到后端，解决浏览器跨域）——
    // 同时需把 src/api/config.ts 的 USE_BACKEND 改为 true、API_BASE_URL 改为 ''
    // proxy: {
    //   '/api': {
    //     target: 'http://localhost:8000', // 你的后端服务地址
    //     changeOrigin: true
    //     // rewrite: path => path.replace(/^\/api/, '') // 后端路由不带 /api 前缀时启用
    //   }
    // }
  }
})
