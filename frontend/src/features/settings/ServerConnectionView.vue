<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import {
  NAlert,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NSwitch,
  NTag,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useAuthStore } from '@/stores/auth';
import { useRuntimeStore } from '@/stores/runtime';
import { useSessionStore } from '@/stores/sessions';
import { deriveConnectionLayerSummary } from './serverConnectionState';

type ProbeState = 'idle' | 'checking' | 'reachable' | 'failed';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();
const runtime = useRuntimeStore();
const sessions = useSessionStore();

const origin = ref(runtime.serverProfile?.origin ?? '');
const displayName = ref(runtime.serverProfile?.displayName ?? '');
const allowInsecureDevelopment = ref(Boolean(runtime.serverProfile?.allowInsecureDevelopment));
const probeState = ref<ProbeState>('idle');
const errorMessage = ref('');

const layerSummary = computed(() => deriveConnectionLayerSummary(runtime.sseStatus, sessions.sessions));
const currentProfileLabel = computed(() => runtime.serverProfile?.displayName || t('serverConnection.notConfigured'));

const controlLabel = computed(() => {
  if (probeState.value === 'checking') return t('serverConnection.controlChecking');
  if (probeState.value === 'failed') return t('serverConnection.controlOffline');
  switch (layerSummary.value.control) {
    case 'connected': return t('serverConnection.controlConnected');
    case 'connecting': return t('serverConnection.controlConnecting');
    case 'reconnecting': return t('serverConnection.controlReconnecting');
    default: return probeState.value === 'reachable'
      ? t('serverConnection.controlReachable')
      : t('serverConnection.controlNotChecked');
  }
});

const controlTagType = computed<'success' | 'warning' | 'error' | 'default'>(() => {
  if (layerSummary.value.control === 'connected') return 'success';
  if (probeState.value === 'failed') return 'error';
  if (probeState.value === 'checking' || layerSummary.value.control !== 'offline') return 'warning';
  return probeState.value === 'reachable' ? 'success' : 'default';
});

const playerLabel = computed(() => layerSummary.value.player === 'online'
  ? t('serverConnection.playerOnline', { count: layerSummary.value.onlinePlayerCount })
  : t('serverConnection.playerOffline'));

async function connect(): Promise<void> {
  if (probeState.value === 'checking') return;
  errorMessage.value = '';
  probeState.value = 'checking';
  try {
    await runtime.switchServer({
      origin: origin.value,
      displayName: displayName.value,
      allowInsecureDevelopment: allowInsecureDevelopment.value,
    });
    origin.value = runtime.serverProfile?.origin ?? origin.value;
    displayName.value = runtime.serverProfile?.displayName ?? displayName.value;
    allowInsecureDevelopment.value = Boolean(runtime.serverProfile?.allowInsecureDevelopment);
    const authenticated = await auth.probeCurrentServer();
    probeState.value = 'reachable';
    if (authenticated) {
      await router.replace('/dashboard');
    }
  } catch (error) {
    probeState.value = 'failed';
    errorMessage.value = error instanceof Error ? error.message : t('serverConnection.connectFailed');
  }
}

function openLogin(): void {
  void router.push('/login');
}
</script>

<template>
  <main class="min-h-dvh bg-canvas px-4 py-8 text-foreground sm:px-6 lg:px-8">
    <div class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header class="flex items-center gap-4">
        <span class="grid size-12 shrink-0 place-items-center rounded-xl bg-brand text-white shadow-panel" aria-hidden="true">
          <FIcon name="desktop_24_regular" :size="26" />
        </span>
        <div>
          <p class="m-0 text-sm text-foreground-muted">SCP-cv</p>
          <h1 class="m-0 text-2xl font-semibold">{{ t('serverConnection.title') }}</h1>
          <p class="mt-1 text-sm text-foreground-muted">{{ t('serverConnection.subtitle') }}</p>
        </div>
      </header>

      <section class="grid gap-3 sm:grid-cols-2" :aria-label="t('serverConnection.layerStatus')">
        <n-card size="small" :title="t('serverConnection.controlLayer')">
          <n-tag :type="controlTagType" round>{{ controlLabel }}</n-tag>
          <p class="mb-0 mt-3 text-sm text-foreground-muted">{{ t('serverConnection.controlHint') }}</p>
        </n-card>
        <n-card size="small" :title="t('serverConnection.playerLayer')">
          <n-tag :type="layerSummary.player === 'online' ? 'success' : 'error'" round>{{ playerLabel }}</n-tag>
          <p class="mb-0 mt-3 text-sm text-foreground-muted">{{ t('serverConnection.playerHint') }}</p>
        </n-card>
      </section>

      <n-card :title="t('serverConnection.formTitle')">
        <p class="mt-0 text-sm text-foreground-muted">
          {{ t('serverConnection.currentProfile', { profile: currentProfileLabel }) }}
        </p>
        <n-form @submit.prevent="connect">
          <n-form-item :label="t('serverConnection.origin')" required>
            <n-input
              v-model:value="origin"
              inputmode="url"
              autocomplete="url"
              :disabled="probeState === 'checking'"
              :placeholder="t('serverConnection.originPlaceholder')"
            />
          </n-form-item>
          <n-form-item :label="t('serverConnection.displayName')">
            <n-input
              v-model:value="displayName"
              :disabled="probeState === 'checking'"
              :placeholder="t('serverConnection.displayNamePlaceholder')"
            />
          </n-form-item>
          <div class="mb-4 flex min-h-11 items-center justify-between gap-4 rounded-lg border border-stroke px-3 py-2">
            <div>
              <p class="m-0 font-medium">{{ t('serverConnection.insecureDevelopment') }}</p>
              <p class="m-0 text-sm text-foreground-muted">{{ t('serverConnection.insecureDevelopmentHint') }}</p>
            </div>
            <n-switch v-model:value="allowInsecureDevelopment" :disabled="probeState === 'checking'" />
          </div>
          <n-alert v-if="errorMessage" type="error" :title="t('serverConnection.connectFailed')">
            {{ errorMessage }}
          </n-alert>
          <n-alert v-else-if="probeState === 'reachable' && !auth.isAuthenticated" type="success" :title="t('serverConnection.hostReachable')">
            {{ t('serverConnection.loginRequired') }}
          </n-alert>
          <div class="mt-5 flex flex-col gap-3 sm:flex-row">
            <n-button type="primary" attr-type="submit" :loading="probeState === 'checking'">
              {{ t('serverConnection.connect') }}
            </n-button>
            <n-button v-if="probeState === 'reachable' && !auth.isAuthenticated" @click="openLogin">
              {{ t('serverConnection.openLogin') }}
            </n-button>
            <n-button v-if="auth.isAuthenticated" tertiary @click="router.push('/dashboard')">
              {{ t('serverConnection.backToConsole') }}
            </n-button>
          </div>
        </n-form>
      </n-card>

      <n-alert type="info" :title="t('serverConnection.securityTitle')">
        {{ t('serverConnection.securityHint') }}
      </n-alert>
    </div>
  </main>
</template>
