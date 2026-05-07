/*
 * 路由表：
 *   - / → /dashboard 重定向；
 *   - /display/:target → DisplayControlView，target 取 big-left/big-right/tv-left/tv-right；
 *   - /ppt-focus/:windowId → PptFocusView，meta.focus 让 App.vue 替换 Shell；
 *   - /sources / /scenarios / /settings；
 *   - /about → /settings 重定向，避免外部书签失效（设计稿 §4.6）。
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

import DashboardView from '@/features/dashboard/DashboardView.vue';
import DisplayControlView from '@/features/display/DisplayControlView.vue';
import PptFocusView from '@/features/pptFocus/PptFocusView.vue';
import ScenariosView from '@/features/scenarios/ScenariosView.vue';
import SettingsView from '@/features/settings/SettingsView.vue';
import SourcesView from '@/features/sources/SourcesView.vue';

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: DashboardView, meta: { title: '仪表盘' } },
  {
    path: '/display/:target',
    component: DisplayControlView,
    meta: { title: '显示控制' },
  },
  {
    path: '/ppt-focus/:windowId',
    component: PptFocusView,
    meta: { focus: true, title: 'PPT 专注模式' },
  },
  { path: '/sources', component: SourcesView, meta: { title: '媒体源' } },
  { path: '/scenarios', component: ScenariosView, meta: { title: '预案' } },
  { path: '/settings', component: SettingsView, meta: { title: '设置' } },
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
    const baseTitle = 'SCP-cv 播放控制台';
    const pageTitle = to.meta?.title ? `${to.meta.title} · ${baseTitle}` : baseTitle;
    document.title = pageTitle;
  }
});

export default router;
