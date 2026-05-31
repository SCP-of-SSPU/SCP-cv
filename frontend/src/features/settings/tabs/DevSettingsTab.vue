<script setup lang="ts">
/**
 * 设置中心开发诊断 Tab。
 * 展示前后端端口、API 端点、日志路径与环境变量来源。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NAlert, NButton, NCard, NTag } from 'naive-ui';

import { api, PHYSICAL_SMOKE_TOTAL_TIMEOUT_SECONDS, type PhysicalSmokeResult } from '@/services/api';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';

const { t } = useI18n();
const dialog = useDialog();
const toast = useToast();
const sessionStore = useSessionStore();

const backendTarget = computed(() => String(import.meta.env.VITE_BACKEND_TARGET || ''));
const portsCaption = computed(() =>
  t('settings.ports', { port: import.meta.env.VITE_FRONTEND_PORT || '5173' }),
);
const smokeRunning = ref(false);
const smokeResult = ref<PhysicalSmokeResult | null>(null);
const failedSmokeResults = computed(() => smokeResult.value?.results.filter((item) => item.status !== 'ok') ?? []);
const latestSmokeRows = computed(() => smokeResult.value?.results.slice(-8) ?? []);

function smokeStatusType(status: string): 'success' | 'error' | 'warning' | 'default' {
  if (status === 'ok') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'skipped') return 'warning';
  return 'default';
}

async function runPhysicalSmoke(): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('settings.physicalSmokeConfirmTitle'),
    description: t('settings.physicalSmokeConfirmDesc'),
    confirmLabel: t('settings.physicalSmokeConfirm'),
  });
  if (!confirmed) return;
  smokeRunning.value = true;
  smokeResult.value = null;
  try {
    const result = await api.runPhysicalSmoke({
      reset_after: true,
      total_timeout_seconds: PHYSICAL_SMOKE_TOTAL_TIMEOUT_SECONDS,
    });
    smokeResult.value = result;
    sessionStore.applyRemoteSessions(result.sessions);
    if (result.success) {
      toast.success(t('settings.physicalSmokeOk'), t('settings.physicalSmokeOkDetail', result.summary));
    } else {
      toast.warning(t('settings.physicalSmokePartial'), t('settings.physicalSmokeFailDetail', result.summary));
    }
  } catch (error) {
    toast.error(t('settings.physicalSmokeFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    smokeRunning.value = false;
  }
}
</script>

<template>
  <section class="settings-view__grid">
    <n-card :title="t('settings.apiEndpoints')">
      <ul class="settings-view__api-list">
        <li><code>{{ backendTarget }}/api/sources/</code></li>
        <li><code>{{ backendTarget }}/api/scenarios/</code></li>
        <li><code>{{ backendTarget }}/api/sessions/</code></li>
        <li><code>{{ backendTarget }}/api/runtime/</code></li>
        <li><code>{{ backendTarget }}/api/playback/physical-smoke/</code></li>
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

    <n-card class="settings-view__smoke-card" :title="t('settings.physicalSmokeTitle')">
      <n-alert type="warning" :show-icon="true">
        {{ t('settings.physicalSmokeHint') }}
      </n-alert>
      <div class="settings-view__row settings-view__smoke-actions">
        <n-button type="error" :loading="smokeRunning" @click="runPhysicalSmoke">
          {{ smokeRunning ? t('settings.physicalSmokeRunning') : t('settings.physicalSmokeStart') }}
        </n-button>
        <span class="settings-view__hint">{{ t('settings.physicalSmokeTimeoutHint') }}</span>
      </div>

      <div v-if="smokeResult" class="settings-view__smoke-result">
        <div class="settings-view__smoke-summary">
          <div>
            <span class="settings-view__smoke-label">{{ t('settings.physicalSmokeTotal') }}</span>
            <strong>{{ smokeResult.summary.total }}</strong>
          </div>
          <div>
            <span class="settings-view__smoke-label">{{ t('settings.physicalSmokePassed') }}</span>
            <strong>{{ smokeResult.summary.passed }}</strong>
          </div>
          <div>
            <span class="settings-view__smoke-label">{{ t('settings.physicalSmokeFailed') }}</span>
            <strong>{{ smokeResult.summary.failed }}</strong>
          </div>
          <div>
            <span class="settings-view__smoke-label">{{ t('settings.physicalSmokeElapsed') }}</span>
            <strong>{{ smokeResult.elapsed_seconds.toFixed(1) }}s</strong>
          </div>
        </div>

        <p class="settings-view__hint">
          {{ t('settings.physicalSmokeResetStatus') }}
          <n-tag :type="smokeStatusType(smokeResult.reset.status)" size="small" round>
            {{ smokeResult.reset.status }}
          </n-tag>
        </p>

        <div v-if="failedSmokeResults.length" class="settings-view__smoke-failures">
          <h4>{{ t('settings.physicalSmokeFailures') }}</h4>
          <p v-for="item in failedSmokeResults" :key="`${item.window_id}-${item.source_type}`" class="settings-view__hint">
            {{ t('settings.physicalSmokeFailureLine', { window: item.window_id, type: item.source_type, error: item.error_message || '-' }) }}
          </p>
        </div>

        <table class="settings-view__smoke-table">
          <thead>
            <tr>
              <th>{{ t('settings.physicalSmokeWindow') }}</th>
              <th>{{ t('settings.physicalSmokeType') }}</th>
              <th>{{ t('settings.physicalSmokeOpen') }}</th>
              <th>{{ t('settings.physicalSmokeClose') }}</th>
              <th>{{ t('settings.physicalSmokeStatus') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in latestSmokeRows" :key="`${item.window_id}-${item.source_type}-${item.source_id}`">
              <td>{{ item.window_id }}</td>
              <td>{{ item.source_type }}</td>
              <td>{{ item.open_elapsed.toFixed(2) }}s</td>
              <td>{{ item.close_elapsed.toFixed(2) }}s</td>
              <td>
                <n-tag :type="smokeStatusType(item.status)" size="small" round>{{ item.status }}</n-tag>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </n-card>
  </section>
</template>
