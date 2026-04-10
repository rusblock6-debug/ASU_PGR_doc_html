import path from 'path';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import svgr from 'vite-plugin-svgr';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // eslint-disable-next-line sonarjs/no-clear-text-protocols -- dev proxy к внутреннему HTTP Trip Service
  const tripServiceTarget = env.VITE_TRIP_SERVICE_URL || 'http://10.100.109.13:8000';
  // eslint-disable-next-line sonarjs/no-clear-text-protocols -- dev proxy к внутреннему HTTP Graph Service
  const graphServiceTarget = env.VITE_GRAPH_SERVICE_URL || 'http://10.100.109.13:5001';
  // eslint-disable-next-line sonarjs/no-clear-text-protocols -- dev proxy к внутреннему HTTP Enterprise Service
  const enterpriseServiceTarget = env.VITE_ENTERPRISE_SERVICE_URL || 'http://10.100.109.13:8002';

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
          target: tripServiceTarget,
          changeOrigin: true,
        },
        '/graph-api': {
          target: graphServiceTarget,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/graph-api/, ''),
        },
        '/enterprise-api': {
          target: enterpriseServiceTarget,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(/^\/enterprise-api/, ''),
        },
      },
    },
  };
});
