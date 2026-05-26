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
 * 4. dev server 把 `/api`、`/events`、`/media`、`/static`、`/admin` 反向代理到
 *    Django：让前端与后端共享同一个 origin（http://<host>:5173），从根本上
 *    避免跨 origin + SameSite cookie 导致 csrftoken 不随登录请求发送的问题。
 */
export default defineConfig(({ mode }) => {
  const envDir = fileURLToPath(new URL('.', import.meta.url));
  const env = loadEnv(mode, envDir, '');
  const fallbackPort = 5173;
  const parsedPort = Number.parseInt(env.VITE_FRONTEND_PORT || '', 10);
  const frontendPort = Number.isFinite(parsedPort) && parsedPort > 0 ? parsedPort : fallbackPort;
  const backendTarget = (env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000').replace(/\/+$/, '');

  // 共用代理规则。
  //   - changeOrigin=false：保留浏览器原始 Host 头，让 Django 的 CSRF Origin 校验
  //     拿到与 Origin 头一致的 host（同 origin 验证天然通过），否则 Host 被改为
  //     backend host 后 Django 计算的 good_origin 与浏览器 Origin 不匹配 → 403。
  //   - secure=false：本地 dev 后端通常用 http；忽略证书校验。
  const proxyRule = {
    target: backendTarget,
    changeOrigin: false,
    secure: false,
  } as const;

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
      proxy: {
        '/api': proxyRule,
        // events 是历史 dashboard SSE 路径，与 /api/events/ 共存；统一代理。
        '/events': proxyRule,
        '/media': proxyRule,
        '/static': proxyRule,
        '/admin': proxyRule,
      },
    },
    preview: {
      host: '0.0.0.0',
      port: frontendPort,
      proxy: {
        '/api': proxyRule,
        '/events': proxyRule,
        '/media': proxyRule,
        '/static': proxyRule,
        '/admin': proxyRule,
      },
    },
  };
});
