import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL('..', import.meta.url));
  const env = loadEnv(mode, envDir, '');
  const frontendPort = Number.parseInt(env.VITE_FRONTEND_PORT || '5173', 10);

  return {
    envDir,
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: Number.isFinite(frontendPort) ? frontendPort : 5173,
    },
  };
});
