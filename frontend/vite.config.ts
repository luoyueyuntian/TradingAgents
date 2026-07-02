import vue from '@vitejs/plugin-vue';
import { defineConfig, type ProxyOptions } from 'vite';

const DEFAULT_DEV_BACKEND_TARGET = 'http://127.0.0.1:8000';

type DevProxyEnv = Record<string, string | undefined>;

declare const process: {
  env: DevProxyEnv;
};

export function resolveDevBackendTarget(env: DevProxyEnv = process.env): string {
  return env.TRADINGAGENTS_WEB_DEV_PROXY_TARGET?.trim() || DEFAULT_DEV_BACKEND_TARGET;
}

export function createDevServerProxy(env: DevProxyEnv = process.env): Record<string, ProxyOptions> {
  const target = resolveDevBackendTarget(env);
  return {
    '/api': {
      target,
      changeOrigin: true,
    },
  };
}

export default defineConfig({
  base: '/static/spa/',
  plugins: [vue()],
  server: {
    proxy: createDevServerProxy(),
  },
  build: {
    outDir: '../web/static/spa',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/app.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name][extname]',
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
