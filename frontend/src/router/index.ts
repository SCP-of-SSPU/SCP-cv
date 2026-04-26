import { createRouter, createWebHistory } from 'vue-router';

import PlaybackView from '@/views/PlaybackView.vue';
import ScenariosView from '@/views/ScenariosView.vue';
import SettingsView from '@/views/SettingsView.vue';
import SourcesView from '@/views/SourcesView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/sources' },
    { path: '/sources', component: SourcesView },
    { path: '/playback', component: PlaybackView },
    { path: '/settings', component: SettingsView },
    { path: '/scenarios', component: ScenariosView },
  ],
});

export default router;
