<script setup lang="ts">
/**
 * 设置中心设备电源 Tab。
 * 复用设备 store 发送拼接屏开关机与电视切换 TCP 指令。
 */
import { useI18n } from 'vue-i18n';
import { NAlert, NButton, NCard } from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useDeviceStore } from '@/stores/devices';

const { t } = useI18n();
const device = useDeviceStore();
const toast = useToast();
const dialog = useDialog();

async function powerOnSplice(): Promise<void> {
  try {
    await device.power('splice_screen', 'on');
    toast.success(t('settings.spliceOnOk'));
  } catch (error) {
    toast.error(t('settings.spliceOnFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function powerOffSplice(): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('settings.spliceOffTitle'),
    description: t('settings.spliceOffDesc'),
    confirmLabel: t('settings.spliceOffConfirm'),
  });
  if (!confirmed) return;
  try {
    await device.power('splice_screen', 'off');
    toast.warning(t('settings.spliceOffOk'), t('settings.spliceOffOkDetail'));
  } catch (error) {
    toast.error(t('settings.spliceOffFail'), error instanceof Error ? error.message : t('settings.spliceOffFailDetail'));
  }
}

async function toggleTv(deviceType: 'tv_left' | 'tv_right', label: string): Promise<void> {
  try {
    await device.toggle(deviceType);
    toast.success(t('settings.tvToggleOk', { label }));
  } catch (error) {
    toast.error(t('settings.tvToggleFail', { label }), error instanceof Error ? error.message : t('common.retry'));
  }
}

function lastActionLabel(deviceType: string): string {
  const at = device.lastActionAt[deviceType];
  if (!at) return t('settings.notOperated');
  const date = new Date(at);
  const detail = device.lastActionDetail[deviceType] ?? '';
  return `${date.toLocaleTimeString()} · ${detail}`;
}
</script>

<template>
  <section class="settings-view__grid">
    <n-card :title="t('settings.splice')">
      <p class="settings-view__hint">{{ t('settings.spliceHint') }}</p>
      <div class="settings-view__row">
        <n-button type="primary" @click="powerOnSplice">
          <template #icon><FIcon name="power_24_regular" /></template>
          {{ t('settings.powerOn') }}
        </n-button>
        <n-button type="error" @click="powerOffSplice">
          <template #icon><FIcon name="plug_disconnected_24_regular" /></template>
          {{ t('settings.powerOff') }}
        </n-button>
      </div>
      <p class="settings-view__hint">{{ t('settings.lastAction', { detail: lastActionLabel('splice_screen') }) }}</p>
      <n-alert v-if="device.lastActionResult.splice_screen === 'error'" type="error" :title="t('settings.spliceTcpFail')">
        {{ device.lastActionDetail.splice_screen }}
      </n-alert>
    </n-card>

    <n-card :title="t('settings.tv')">
      <p class="settings-view__hint">{{ t('settings.tvHint') }}</p>
      <div class="settings-view__row">
        <n-button @click="toggleTv('tv_left', t('settings.devLeft'))">
          <template #icon><FIcon name="arrow_swap_24_regular" /></template>
          {{ t('settings.tvLeftToggle') }}
        </n-button>
        <n-button @click="toggleTv('tv_right', t('settings.devRight'))">
          <template #icon><FIcon name="arrow_swap_24_regular" /></template>
          {{ t('settings.tvRightToggle') }}
        </n-button>
      </div>
      <p class="settings-view__hint">
        {{ t('settings.tvLeftLast', { detail: lastActionLabel('tv_left') }) }}<br />
        {{ t('settings.tvRightLast', { detail: lastActionLabel('tv_right') }) }}
      </p>
    </n-card>
  </section>
</template>
