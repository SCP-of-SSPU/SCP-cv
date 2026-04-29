import { createRouter, createWebHistory } from 'vue-router';

import DashboardView from '@/views/DashboardView.vue';
import PlaybackView from '@/views/PlaybackView.vue';
import ScenariosView from '@/views/ScenariosView.vue';
import SettingsView from '@/views/SettingsView.vue';
import SourcesView from '@/views/SourcesView.vue';

function getDefaultRoute(): string {
  if (window.matchMedia('(max-width: 760px)').matches) return '/playback';
  return '/dashboard';
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: getDefaultRoute },
    { path: '/dashboard', component: DashboardView },
    { path: '/sources', component: SourcesView },
    { path: '/playback', component: PlaybackView },
    { path: '/settings', component: SettingsView },
    { path: '/scenarios', component: ScenariosView },
  ],
});

export default router;
