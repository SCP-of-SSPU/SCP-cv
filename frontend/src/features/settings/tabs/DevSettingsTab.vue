<script setup lang="ts">
/**
 * 设置中心开发诊断 Tab。
 * 展示前后端端口、API 端点、日志路径与环境变量来源。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { NCard } from 'naive-ui';

const { t } = useI18n();

const backendTarget = computed(() => String(import.meta.env.VITE_BACKEND_TARGET || ''));
const portsCaption = computed(() =>
  t('settings.ports', { port: import.meta.env.VITE_FRONTEND_PORT || '5173' }),
);
</script>

<template>
  <section class="settings-view__grid">
    <n-card :title="t('settings.apiEndpoints')">
      <ul class="settings-view__api-list">
        <li><code>{{ backendTarget }}/api/sources/</code></li>
        <li><code>{{ backendTarget }}/api/scenarios/</code></li>
        <li><code>{{ backendTarget }}/api/sessions/</code></li>
        <li><code>{{ backendTarget }}/api/runtime/</code></li>
        <li><code>{{ backendTarget }}/api/events/</code></li>
      </ul>
    </n-card>

    <n-card :title="t('settings.portsSummary')">
      <p class="settings-view__hint">{{ portsCaption }}</p>
    </n-card>

    <n-card :title="t('settings.logPath')">
      <p class="settings-view__hint">{{ t('settings.logPathHint') }}</p>
    </n-card>

    <n-card :title="t('settings.envVars')">
      <p class="settings-view__hint">{{ t('settings.envVarsHint') }}</p>
    </n-card>
  </section>
</template>
