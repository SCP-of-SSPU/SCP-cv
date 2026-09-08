/*
 * 路由表：
 *   - /login → LoginView（无需登录）；
 *   - / → /dashboard 重定向；
 *   - /display/:target → DisplayControlView；
 *   - /ppt-focus/:windowId → PptFocusView，meta.focus 让 App.vue 替换 Shell；
 *   - /background-audio → 背景音乐；
 *   - /sources / /scenarios / /settings；
 *   - /about → /settings 重定向；
 *   - 全局守卫：除 meta.public=true 外，未登录一律跳 /login？redirect=...。
 */
import { createRouter, type RouteRecordRaw, type Router } from 'vue-router';

import { t } from '@/locales';

import DashboardView from '@/features/dashboard/DashboardView.vue';
import BackgroundAudioView from '@/features/backgroundAudio/BackgroundAudioView.vue';
import DisplayControlView from '@/features/display/DisplayControlView.vue';
import LoginView from '@/features/auth/LoginView.vue';
import ServerConnectionView from '@/features/settings/ServerConnectionView.vue';
import PptFocusView from '@/features/pptFocus/PptFocusView.vue';
import ScenariosView from '@/features/scenarios/ScenariosView.vue';
import SettingsView from '@/features/settings/SettingsView.vue';
import SourcesView from '@/features/sources/SourcesView.vue';
import { useAuthStore } from '@/stores/auth';
import { createClientHistory, getClientBuildTarget, resolveInitialRoute } from '@/platform';
import { loadStoredServerProfile } from '@/platform/connection';

const routes: RouteRecordRaw[] = [
  {
    path: '/connect',
    component: ServerConnectionView,
    meta: { titleKey: 'serverConnection.routeTitle', public: true, focus: true },
  },
  {
    path: '/login',
    component: LoginView,
    meta: { titleKey: 'auth.routeTitle', public: true, focus: true },
  },
  {
    path: '/',
    redirect: () => resolveInitialRoute(getClientBuildTarget(), Boolean(loadStoredServerProfile())),
  },
  { path: '/dashboard', component: DashboardView, meta: { titleKey: 'nav.dashboard' } },
  {
    path: '/display/:target',
    component: DisplayControlView,
    meta: { titleKey: 'display.routeTitle' },
  },
  {
    path: '/ppt-focus/:windowId',
    component: PptFocusView,
    meta: { focus: true, titleKey: 'pptFocus.routeTitle' },
  },
  { path: '/sources', component: SourcesView, meta: { titleKey: 'nav.sources' } },
  { path: '/background-audio', component: BackgroundAudioView, meta: { titleKey: 'backgroundAudio.routeTitle' } },
  { path: '/scenarios', component: ScenariosView, meta: { titleKey: 'nav.scenarios' } },
  { path: '/settings', component: SettingsView, meta: { titleKey: 'nav.settings' } },
  // 兼容旧链接：原 about 内容已并入 settings。
  { path: '/about', redirect: '/settings' },
  // 兜底：未知路径回首页。
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
];

export function createAppRouter(): Router {
  const router = createRouter({
    history: createClientHistory(),
    routes,
    scrollBehavior() {
      return { top: 0 };
    },
  });

  // 路由守卫：保证 auth store 完成首屏 me 探活；未登录访问非公开页统一跳 /login。
  router.beforeEach(async (to) => {
    const auth = useAuthStore();
    if (!auth.initialized) {
      await auth.ensureInitialized();
    }
    const isPublic = Boolean(to.meta?.public);
    if (!isPublic && !auth.isAuthenticated) {
      return {
        path: '/login',
        query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : undefined,
      };
    }
    // 已登录用户进 /login，直接放回首页。
    if (auth.isAuthenticated && to.path === '/login') {
      return { path: '/dashboard' };
    }
    return true;
  });

  router.afterEach((to) => {
    if (typeof document !== 'undefined') {
      const baseTitle = t('app.baseTitle');
      const titleKey = to.meta?.titleKey as string | undefined;
      document.title = titleKey
        ? t('app.titleWithPage', { page: t(titleKey), base: baseTitle })
        : baseTitle;
    }
  });

  return router;
}

const router = createAppRouter();

export default router;
