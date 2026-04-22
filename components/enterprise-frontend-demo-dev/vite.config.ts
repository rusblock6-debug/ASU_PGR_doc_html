import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Dev режим: enterprise-service, trip-service (shift-tasks, route-tasks, event-log)
  // VITE_TRIP_SERVICE_URL: в Docker (docker-compose.server) — http://trip-service-server:8000
  //                       trip-service на хосте — http://host.docker.internal:8003
  //                       локальный dev (без Docker) — http://127.0.0.1:8003
  const apiTarget = 'http://enterprise-service:8001';
  const tripServiceTarget = process.env.VITE_TRIP_SERVICE_URL || 'http://trip-service-server:8000';
  const graphApiTarget = 'http://graph-service-backend:5000';

  console.log('='.repeat(50));
  console.log('Vite Dev Configuration:');
  console.log(`  Mode: ${mode}`);
  console.log(`  API (enterprise): ${apiTarget}`);
  console.log(`  Trip Service: ${tripServiceTarget}`);
  console.log(`  Graph API: ${graphApiTarget}`);
  console.log('='.repeat(50));

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0', // Required for Docker
      port: 3000,
      watch: {
        usePolling: true, // Required for Docker on Windows/Mac
      },
      // HMR для Docker
      hmr: {
        clientPort: 3002,
      },
      proxy: {
        // /trip-api/* -> trip-service /api/* (сменные задания и др. в trip-service)
        '/trip-api': {
          target: tripServiceTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/trip-api/, '/api'),
        },
        '/api/shift-tasks': {
          target: tripServiceTarget,
          changeOrigin: true,
        },
        '/api/route-tasks': {
          target: tripServiceTarget,
          changeOrigin: true,
        },
        '/api/route-summary': {
          target: tripServiceTarget,
          changeOrigin: true,
        },
        '/api/cycle-state-history': {
          target: tripServiceTarget,
          changeOrigin: true,
        },
        '/api/event-log': {
          target: tripServiceTarget,
          changeOrigin: true,
        },
        '/api/events': {
          target: tripServiceTarget,
          changeOrigin: true,
          ws: true, // Включаем WebSocket поддержку для SSE
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log(`[SSE Proxy ERROR] ${err.message}`);
              console.log(`  Target: ${tripServiceTarget}`);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log(`[SSE Proxy] ${req.method} ${req.url} -> ${tripServiceTarget}`);
              // SSE требует особых headers
              proxyReq.setHeader('Accept', 'text/event-stream');
              proxyReq.setHeader('Cache-Control', 'no-cache');
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.log(`[SSE Proxy] ${proxyRes.statusCode} ${req.url}`);
              // Добавляем headers для SSE
              proxyRes.headers['content-type'] = 'text/event-stream';
              proxyRes.headers['cache-control'] = 'no-cache';
              proxyRes.headers['connection'] = 'keep-alive';
            });
          },
        },
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          // Не удаляем /api, если backend использует этот префикс
          // rewrite: (path) => path.replace(/^\/api/, ''),
          secure: false,
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log(`[API Proxy ERROR] ${err.message}`);
              console.log(`  Target: ${apiTarget}`);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log(`[API Proxy] ${req.method} ${req.url} -> ${apiTarget}`);
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.log(`[API Proxy] ${proxyRes.statusCode} ${req.url}`);
            });
          },
        },
        '/graph-api': {
          target: graphApiTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/graph-api/, '/api'),
          secure: false,
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log(`[Graph API Proxy ERROR] ${err.message}`);
              console.log(`  Target: ${graphApiTarget}`);
            });
            proxy.on('proxyReq', (proxyReq, req, _res) => {
              console.log(`[Graph API Proxy] ${req.method} ${req.url} -> ${graphApiTarget}`);
            });
            proxy.on('proxyRes', (proxyRes, req, _res) => {
              console.log(`[Graph API Proxy] ${proxyRes.statusCode} ${req.url}`);
            });
          },
        },
      },
    },
  };
});

