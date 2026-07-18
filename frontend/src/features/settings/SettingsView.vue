<script setup lang="ts">
/**
 * 设置中心容器：品牌头 + 设置分组 Tab。
 * 各设置分组拆入 tabs/ 子组件，避免单文件继续堆积运行态、显示器、设备电源与开发诊断逻辑。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NTabPane, NTabs } from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { getConnectionPorts } from '@/services/api';
import { useToast } from '@/composables/useToast';
import RuntimeSettingsTab from './tabs/RuntimeSettingsTab.vue';
import DisplaySettingsTab from './tabs/DisplaySettingsTab.vue';
import DevicePowerSettingsTab from './tabs/DevicePowerSettingsTab.vue';
import DevSettingsTab from './tabs/DevSettingsTab.vue';
import AccountSettingsTab from './tabs/AccountSettingsTab.vue';

type SettingsTab = 'runtime' | 'display' | 'devices' | 'account' | 'dev';

const { t } = useI18n();
const toast = useToast();

const activeTab = ref<SettingsTab>('runtime');
const version = '1.0.0';
const connectionPorts = getConnectionPorts();
const portsCaption = computed(() =>
  t('settings.ports', connectionPorts),
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
        <n-button disabled :aria-label="t('settings.openLogsAria')">
          <template #icon><FIcon name="open_24_regular" /></template>
          {{ t('settings.openLogs') }}
        </n-button>
        <n-button tertiary
          @click="() => toast.info(t('settings.reportToast'), t('settings.reportToastDetail'))">
          <template #icon><FIcon name="info_24_regular" /></template>
          {{ t('settings.report') }}
        </n-button>
      </div>
    </header>

    <n-tabs v-model:value="activeTab" type="line" :aria-label="t('settings.tabsAria')">
      <n-tab-pane name="runtime" :tab="t('settings.tabRuntime')">
        <RuntimeSettingsTab />
      </n-tab-pane>
      <n-tab-pane name="display" :tab="t('settings.tabDisplay')">
        <DisplaySettingsTab />
      </n-tab-pane>
      <n-tab-pane name="devices" :tab="t('settings.tabDevices')">
        <DevicePowerSettingsTab />
      </n-tab-pane>
      <n-tab-pane name="account" :tab="t('settings.tabAccount')">
        <AccountSettingsTab />
      </n-tab-pane>
      <n-tab-pane name="dev" :tab="t('settings.tabDev')">
        <DevSettingsTab />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<style src="./SettingsView.css"></style>
