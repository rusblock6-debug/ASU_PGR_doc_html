import path from 'path';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import svgr from 'vite-plugin-svgr';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // eslint-disable-next-line sonarjs/no-clear-text-protocols
  const authService = env.VITE_API_AUTH_SERVICE || 'http://10.100.109.14:8000';
  // eslint-disable-next-line sonarjs/no-clear-text-protocols
  const enterpriseService = env.VITE_API_ENTERPRISE_SERVICE || 'http://10.100.109.14:8002';
  // eslint-disable-next-line sonarjs/no-clear-text-protocols
  const tripService = env.VITE_API_TRIP_SERVICE || 'http://10.100.109.14:8003';
  // eslint-disable-next-line sonarjs/no-clear-text-protocols
  const graphService = env.VITE_API_GRAPH_SERVICE || 'http://10.100.109.14:8005';

  return {
    plugins: [
      react({
        babel: {
          plugins: [['babel-plugin-react-compiler']],
        },
      }),
      svgr(),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      assetsDir: 'assets',
      assetsInlineLimit: 0,
      outDir: 'dist',
      rollupOptions: {
        output: {
          manualChunks: {
            vendor: ['react', 'react-dom'],
            router: ['react-router-dom'],
            mantine: ['@mantine/core', '@mantine/hooks', '@mantine/dates', '@mantine/notifications'],
          },
        },
      },
    },
    server: {
      proxy: {
        '/api/v1/roles': {
          target: authService,
          changeOrigin: true,
        },
        '/api/v1/staff': {
          target: authService,
          changeOrigin: true,
        },
        '/api/vehicles/places': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/vehicles/popup': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/vehicles': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/vehicle-models': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/statuses': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/organization-categories': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/work-regimes': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/load_types': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/load_type_categories': {
          target: enterpriseService,
          changeOrigin: true,
        },
        '/api/trips': {
          target: tripService,
          changeOrigin: true,
        },
        '/api/events/stream/routes': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/events/stream': {
          target: tripService,
          changeOrigin: true,
        },
        '/api/event-log/state-history': {
          target: tripService,
          changeOrigin: true,
        },
        '/api/cycle-state-history': {
          target: tripService,
          changeOrigin: true,
        },
        '/api/shift-tasks': {
          target: tripService,
          changeOrigin: true,
        },
        '/api/tasks': {
          target: tripService,
          changeOrigin: true,
        },
        '/api/fleet-control': {
          target: tripService,
          changeOrigin: true,
        },
        '/ws/vehicle-tracking': {
          target: graphService,
          changeOrigin: true,
          ws: true,
        },
        '/api/levels': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/places': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/horizons': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/shafts': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/sections': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/tags': {
          target: graphService,
          changeOrigin: true,
        },
        '/api/substrates': {
          target: graphService,
          changeOrigin: true,
        },
      },
    },
  };
});
