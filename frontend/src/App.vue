<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { RouterLink, RouterView } from 'vue-router';
import { useRoute } from 'vue-router';

import { useAppStore } from '@/stores/app';

const appStore = useAppStore();
const route = useRoute();
const showChrome = computed(() => route.meta.focus !== true);

async function runAction(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '操作失败', true);
  }
}

onMounted(async () => {
  try {
    await appStore.bootstrap();
  } catch (error) {
    appStore.notify(error instanceof Error ? error.message : '初始化失败', true);
  }
});
</script>

<template>
  <header v-if="showChrome" class="topbar">
    <div class="brand">
      <span class="brand__mark">S</span>
      <div>
        <p>SCP-cv</p>
        <h1>现场指挥台</h1>
      </div>
    </div>
    <div class="topbar__meta">
      <span class="chip">REST API</span>
      <span class="chip chip--accent">{{ appStore.connectionStatus }}</span>
    </div>
  </header>

  <nav v-if="showChrome" class="toolbar" aria-label="控制台导航">
    <RouterLink to="/dashboard">总览</RouterLink>
    <RouterLink to="/display/big-left">大屏左</RouterLink>
    <RouterLink v-if="appStore.runtime?.big_screen_mode === 'double'" to="/display/big-right">大屏右</RouterLink>
    <RouterLink to="/display/tv-left">TV 左</RouterLink>
    <RouterLink to="/display/tv-right">TV 右</RouterLink>
    <RouterLink to="/sources">媒体源</RouterLink>
    <RouterLink to="/playback">播放控制</RouterLink>
    <RouterLink to="/settings">系统设置</RouterLink>
    <RouterLink to="/scenarios">预案管理</RouterLink>
    <RouterLink to="/about">关于</RouterLink>
    <button type="button" class="danger" @click="runAction(appStore.closeActive)">停止当前窗口</button>
  </nav>

  <main :class="showChrome ? 'content' : 'focus-content'">
    <p v-if="appStore.message" class="banner" :class="{ 'banner--error': appStore.isError }">
      {{ appStore.message }}
    </p>
    <RouterView />
  </main>
</template>
