<script setup lang="ts">
/**
 * 设置中心容器：品牌头 + 设置分组 Tab。
 * 各设置分组拆入 tabs/ 子组件，避免单文件继续堆积运行态、显示器、设备电源与开发诊断逻辑。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  FButton,
  FTabs,
} from '@/design-system';
import type { FTabsItem } from '@/design-system';
import { useToast } from '@/composables/useToast';
import RuntimeSettingsTab from './tabs/RuntimeSettingsTab.vue';
import DisplaySettingsTab from './tabs/DisplaySettingsTab.vue';
import DevicePowerSettingsTab from './tabs/DevicePowerSettingsTab.vue';
import DevSettingsTab from './tabs/DevSettingsTab.vue';

type SettingsTab = 'runtime' | 'display' | 'devices' | 'dev';

const { t } = useI18n();
const toast = useToast();

const tabs = computed<FTabsItem<SettingsTab>[]>(() => [
  { label: t('settings.tabRuntime'), value: 'runtime' },
  { label: t('settings.tabDisplay'), value: 'display' },
  { label: t('settings.tabDevices'), value: 'devices' },
  { label: t('settings.tabDev'), value: 'dev' },
]);

const activeTab = ref<SettingsTab>('runtime');
const version = '1.0.0';
const portsCaption = computed(() =>
  t('settings.ports', { port: import.meta.env.VITE_FRONTEND_PORT || '5173' }),
);
</script>

<template>
  <div class="settings-view">
    <header class="settings-view__app-header">
      <div class="settings-view__brand">
        <span class="settings-view__brand-mark">S</span>
        <div>
          <p class="settings-view__brand-eyebrow">{{ t('settings.brandEyebrow') }}</p>
          <h2 class="settings-view__brand-title">{{ t('settings.brandTitle', { version }) }}</h2>
          <p class="settings-view__brand-caption">{{ portsCaption }}</p>
        </div>
      </div>
      <div class="settings-view__app-actions">
        <FButton appearance="secondary" icon-start="open_24_regular" :disabled="true" :aria-label="t('settings.openLogsAria')">
          {{ t('settings.openLogs') }}
        </FButton>
        <FButton appearance="subtle" icon-start="info_24_regular"
          @click="() => toast.info(t('settings.reportToast'), t('settings.reportToastDetail'))">
          {{ t('settings.report') }}
        </FButton>
      </div>
    </header>

    <FTabs v-model="activeTab" :items="tabs" appearance="line" full-width :aria-label="t('settings.tabsAria')" />

    <RuntimeSettingsTab v-if="activeTab === 'runtime'" />
    <DisplaySettingsTab v-else-if="activeTab === 'display'" />
    <DevicePowerSettingsTab v-else-if="activeTab === 'devices'" />
    <DevSettingsTab v-else />
  </div>
</template>

<style src="./SettingsView.css"></style>
