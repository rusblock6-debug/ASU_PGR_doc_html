import path from 'path';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import svgr from 'vite-plugin-svgr';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // eslint-disable-next-line sonarjs/no-clear-text-protocols
  const apiGateway = env.VITE_API_GATEWAY_URL || 'http://10.100.109.14:8015';
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
        '/api': {
          target: apiGateway,
          changeOrigin: true,
        },
        '/ws/vehicle-tracking': {
          target: graphService,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  };
});
