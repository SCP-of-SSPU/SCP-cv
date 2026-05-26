<script setup lang="ts">
/**
 * 设置中心显示器 Tab。
 * 负责选择物理显示器或左右拼接 label，并应用到指定播放窗口。
 */
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  NButton,
  NCard,
  NRadio,
  NRadioGroup,
} from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { useToast } from '@/composables/useToast';
import { useDisplayStore } from '@/stores/displays';
import type { DisplayTargetItem } from '@/services/api';

interface DisplaySelection {
  target: DisplayTargetItem | null;
  mode: 'single' | 'left_right_splice';
  label: string;
}

const { t } = useI18n();
const display = useDisplayStore();
const toast = useToast();

const targetWindowId = ref<number>(1);
const displaySelection = ref<DisplaySelection>({
  target: null,
  mode: 'single',
  label: '',
});

function pickDisplay(target: DisplayTargetItem): void {
  displaySelection.value = {
    target,
    mode: 'single',
    label: target.name,
  };
}

function pickSplice(): void {
  displaySelection.value = {
    target: null,
    mode: 'left_right_splice',
    label: display.spliceLabel,
  };
}

async function applyDisplay(): Promise<void> {
  const selection = displaySelection.value;
  if (!selection.label) {
    toast.warning(t('settings.pickDisplayFirst'));
    return;
  }
  try {
    await display.applyToWindow(targetWindowId.value, selection.mode, selection.label);
    toast.success(t('settings.appliedOk', { id: targetWindowId.value }));
  } catch (error) {
    toast.error(t('settings.applyFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}
</script>

<template>
  <section class="settings-view__display">
    <n-card :title="t('settings.windowSelect')">
      <n-radio-group v-model:value="targetWindowId">
        <n-radio :value="1">{{ t('settings.window', { id: 1 }) }}</n-radio>
        <n-radio :value="2">{{ t('settings.window', { id: 2 }) }}</n-radio>
        <n-radio :value="3">{{ t('settings.window', { id: 3 }) }}</n-radio>
        <n-radio :value="4">{{ t('settings.window', { id: 4 }) }}</n-radio>
      </n-radio-group>
    </n-card>

    <n-card :title="t('settings.availableDisplays')">
      <div class="settings-view__display-grid">
        <button v-for="target in display.targets" :key="target.index" type="button"
          class="settings-view__display-tile"
          :class="{ 'settings-view__display-tile--selected': displaySelection.label === target.name && displaySelection.mode === 'single' }"
          @click="pickDisplay(target)">
          <p class="settings-view__display-name">{{ t('settings.displayName', { n: target.index + 1 }) }}</p>
          <p class="settings-view__display-meta">{{ target.width }} × {{ target.height }}</p>
          <p class="settings-view__display-meta">({{ target.x }}, {{ target.y }})</p>
          <FIcon v-if="target.is_primary" class="settings-view__display-primary" name="star_24_filled" />
        </button>
        <button type="button" class="settings-view__display-tile settings-view__display-tile--splice"
          :class="{ 'settings-view__display-tile--selected': displaySelection.mode === 'left_right_splice' }"
          :disabled="!display.spliceLabel" @click="pickSplice">
          <p class="settings-view__display-name">{{ display.spliceLabel || t('settings.spliceUnset') }}</p>
          <p class="settings-view__display-meta">{{ t('settings.spliceMeta') }}</p>
        </button>
      </div>
    </n-card>

    <n-button type="primary" :disabled="!displaySelection.label" @click="applyDisplay">
      <template #icon><FIcon name="checkmark_24_regular" /></template>
      {{ t('settings.applyToWindow', { id: targetWindowId }) }}
    </n-button>
  </section>
</template>
