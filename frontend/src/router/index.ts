import { createRouter, createWebHistory } from 'vue-router';

import AboutView from '@/views/AboutView.vue';
import DashboardView from '@/views/DashboardView.vue';
import DisplayControlView from '@/views/DisplayControlView.vue';
import PlaybackView from '@/views/PlaybackView.vue';
import PptFocusView from '@/views/PptFocusView.vue';
import ScenariosView from '@/views/ScenariosView.vue';
import SettingsView from '@/views/SettingsView.vue';
import SourcesView from '@/views/SourcesView.vue';

function getDefaultRoute(): string {
  return '/dashboard';
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: getDefaultRoute },
    { path: '/dashboard', component: DashboardView },
    { path: '/display/:target', component: DisplayControlView },
    { path: '/ppt-focus/:windowId', component: PptFocusView, meta: { focus: true } },
    { path: '/sources', component: SourcesView },
    { path: '/playback', component: PlaybackView },
    { path: '/settings', component: SettingsView },
    { path: '/scenarios', component: ScenariosView },
    { path: '/about', component: AboutView },
  ],
});

export default router;
