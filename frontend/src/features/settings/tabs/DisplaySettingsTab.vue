<script setup lang="ts">
/**
 * 设置中心显示器 Tab。
 * 负责选择物理显示器或左右拼接 label，并应用到指定播放窗口。
 */
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  FButton,
  FCard,
  FIcon,
  FSegmented,
} from '@/design-system';
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
    <FCard padding="cozy">
      <template #title>{{ t('settings.windowSelect') }}</template>
      <FSegmented v-model="targetWindowId" :options="[
        { label: t('settings.window', { id: 1 }), value: 1 },
        { label: t('settings.window', { id: 2 }), value: 2 },
        { label: t('settings.window', { id: 3 }), value: 3 },
        { label: t('settings.window', { id: 4 }), value: 4 },
      ]" full-width />
    </FCard>

    <FCard padding="cozy">
      <template #title>{{ t('settings.availableDisplays') }}</template>
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
    </FCard>

    <FButton appearance="primary" icon-start="checkmark_24_regular" :disabled="!displaySelection.label"
      @click="applyDisplay">
      {{ t('settings.applyToWindow', { id: targetWindowId }) }}
    </FButton>
  </section>
</template>
