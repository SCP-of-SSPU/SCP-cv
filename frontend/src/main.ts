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
import './styles/base.css';

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

app.mount('#app');
