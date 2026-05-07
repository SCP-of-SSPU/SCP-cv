import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig, loadEnv } from 'vite';

/**
 * Vite 构建配置。
 * 设计要点：
 * 1. envDir 固定指向 frontend 目录本身，使前端拥有独立的 `.env` 文件，避免与
 *    根目录 `.env`（其中包含 Django/MediaMTX 等后端机密）混用。
 * 2. dev 端口仍可通过 `VITE_FRONTEND_PORT` 显式覆盖，便于多实例并行。
 * 3. 别名 `@` 指向 `src`，与 tsconfig.json 的 paths 一致，让组件库与业务模块
 *    使用相同的导入语法。
 */
export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL('.', import.meta.url));
  const env = loadEnv(mode, envDir, '');
  const fallbackPort = 5173;
  const parsedPort = Number.parseInt(env.VITE_FRONTEND_PORT || '', 10);
  const frontendPort = Number.isFinite(parsedPort) && parsedPort > 0 ? parsedPort : fallbackPort;

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
      port: frontendPort,
    },
    preview: {
      host: '0.0.0.0',
      port: frontendPort,
    },
  };
});
