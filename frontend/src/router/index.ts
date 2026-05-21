/*
 * 路由表：
 *   - / → /dashboard 重定向；
 *   - /display/:target → DisplayControlView，target 取 big-left/big-right/tv-left/tv-right；
 *   - /ppt-focus/:windowId → PptFocusView，meta.focus 让 App.vue 替换 Shell；
 *   - /sources / /scenarios / /settings；
 *   - /about → /settings 重定向，避免外部书签失效（设计稿 §4.6）。
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import { t } from '@/locales';

import DashboardView from '@/features/dashboard/DashboardView.vue';
import DisplayControlView from '@/features/display/DisplayControlView.vue';
import PptFocusView from '@/features/pptFocus/PptFocusView.vue';
import ScenariosView from '@/features/scenarios/ScenariosView.vue';
import SettingsView from '@/features/settings/SettingsView.vue';
import SourcesView from '@/features/sources/SourcesView.vue';

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
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
  { path: '/scenarios', component: ScenariosView, meta: { titleKey: 'nav.scenarios' } },
  { path: '/settings', component: SettingsView, meta: { titleKey: 'nav.settings' } },
  // 兼容旧链接：原 about 内容已并入 settings。
  { path: '/about', redirect: '/settings' },
  // 兜底：未知路径回首页。
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  },
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

export default router;
