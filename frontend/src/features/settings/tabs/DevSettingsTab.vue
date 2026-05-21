<script setup lang="ts">
/**
 * 设置中心开发诊断 Tab。
 * 展示前后端端口、API 端点、日志路径与环境变量来源。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import { FCard } from '@/design-system';

const { t } = useI18n();

const backendTarget = computed(() => String(import.meta.env.VITE_BACKEND_TARGET || ''));
const portsCaption = computed(() =>
  t('settings.ports', { port: import.meta.env.VITE_FRONTEND_PORT || '5173' }),
);
</script>

<template>
  <section class="settings-view__grid">
    <FCard padding="cozy">
      <template #title>{{ t('settings.apiEndpoints') }}</template>
      <ul class="settings-view__api-list">
        <li><code>{{ backendTarget }}/api/sources/</code></li>
        <li><code>{{ backendTarget }}/api/scenarios/</code></li>
        <li><code>{{ backendTarget }}/api/sessions/</code></li>
        <li><code>{{ backendTarget }}/api/runtime/</code></li>
        <li><code>{{ backendTarget }}/api/events/</code></li>
      </ul>
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.portsSummary') }}</template>
      <p class="settings-view__hint">{{ portsCaption }}</p>
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.logPath') }}</template>
      <p class="settings-view__hint">
        {{ t('settings.logPathHint') }}
      </p>
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.envVars') }}</template>
      <p class="settings-view__hint">
        {{ t('settings.envVarsHint') }}
      </p>
    </FCard>
  </section>
</template>
