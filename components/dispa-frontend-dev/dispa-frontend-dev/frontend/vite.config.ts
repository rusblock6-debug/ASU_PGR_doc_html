import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/auth-api': {
        // Проксируем на сервис в той же docker-сети
        target: 'http://auth-service-backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/auth-api/, ''),
      },
      '/graph-api': {
        // Проксируем на graph-service-backend в docker-сети
        target: 'http://graph-service-backend:5000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/graph-api/, ''),
      },
    },
  },
})

