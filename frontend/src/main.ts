/*
 * 前端应用入口：
 *   - 注册 Pinia 状态管理；
 *   - 安装 vue-i18n（DESIGN.md §8 工程约定中的 i18n 单源）；
 *   - 安装 Vue Router；
 *   - 注册 401 全局回调：服务端会话失效时清 auth store 并跳 /login；
 *   - 挂载根组件到 #app。
 */
import { createPinia } from 'pinia';
import { createApp } from 'vue';

import App from './App.vue';
import router from './router';
import { i18n } from './locales';
import { registerUnauthorizedHandler } from './services/api';
import { useAuthStore } from './stores/auth';
import { resolveNativePlatformAdapter } from './platform/native';
import { installClientLifecycle } from './platform/lifecycle';
import './styles/base.css';
import './styles/tailwind.css';

const pinia = createPinia();
const app = createApp(App).use(pinia).use(i18n).use(router);

// 全局 401：清本地 auth 状态并跳 /login，带 redirect 回当前路径。
registerUnauthorizedHandler(() => {
  const auth = useAuthStore(pinia);
  auth.clearLocal();
  const current = router.currentRoute.value;
  if (current.path === '/login') return;
  void router.push({
    path: '/login',
    query: current.fullPath && current.fullPath !== '/' ? { redirect: current.fullPath } : undefined,
  });
});

// 等待首个导航（包含异步鉴权守卫）完成后再挂载，避免直接访问 /login 或
// /connect 时 App.vue 读取到 START_LOCATION，短暂或永久渲染错误的外壳。
void router.isReady().then(() => {
  app.mount('#app');
  return resolveNativePlatformAdapter();
}).then((adapter) => {
  if (!adapter) return;
  const uninstall = installClientLifecycle(adapter, router);
  window.addEventListener('beforeunload', uninstall, { once: true });
});
