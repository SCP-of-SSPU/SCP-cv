<script setup lang="ts">
/**
 * 大屏模式动作按钮组：当前模式高亮，但点击当前模式仍会重新下发控制命令。
 */
import { computed } from 'vue';
import { NButton } from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import { t } from '@/locales';

type BigScreenMode = 'single' | 'double';

const props = withDefaults(defineProps<{
  currentMode: BigScreenMode;
  pendingMode?: BigScreenMode | null;
  disabled?: boolean;
  block?: boolean;
}>(), {
  pendingMode: null,
  disabled: false,
  block: false,
});

const emit = defineEmits<{
  (event: 'select', mode: BigScreenMode): void;
}>();

const isBusy = computed(() => props.pendingMode !== null);

/**
 * 判断指定按钮是否处于不可点击状态。
 * :param mode: 按钮对应的大屏模式
 * :return: True 表示当前不应重复触发
 */
function isButtonDisabled(mode: BigScreenMode): boolean {
  return props.disabled || (isBusy.value && props.pendingMode !== mode);
}

/**
 * 点击模式按钮后始终向父组件发出命令，不因当前模式相同而短路。
 * :param mode: 目标大屏模式
 * :return: None
 */
function selectMode(mode: BigScreenMode): void {
  if (isButtonDisabled(mode)) return;
  emit('select', mode);
}
</script>

<template>
  <div
    class="big-screen-mode-buttons"
    :class="{ 'big-screen-mode-buttons--block': block }"
    role="group"
    :aria-label="t('dashboard.screenSelectAria')"
  >
    <n-button
      :type="currentMode === 'single' ? 'primary' : 'default'"
      :secondary="currentMode === 'single'"
      :loading="pendingMode === 'single'"
      :disabled="isButtonDisabled('single')"
      :aria-pressed="currentMode === 'single'"
      @click="selectMode('single')"
    >
      <template #icon><FIcon name="tv_24_filled" /></template>
      {{ t('screen.single') }}
    </n-button>
    <n-button
      :type="currentMode === 'double' ? 'primary' : 'default'"
      :secondary="currentMode === 'double'"
      :loading="pendingMode === 'double'"
      :disabled="isButtonDisabled('double')"
      :aria-pressed="currentMode === 'double'"
      @click="selectMode('double')"
    >
      <template #icon><FIcon name="layer_24_regular" /></template>
      {{ t('screen.double') }}
    </n-button>
  </div>
</template>

<style scoped>
.big-screen-mode-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacingHorizontalS);
}

.big-screen-mode-buttons--block :deep(.n-button) {
  flex: 1 1 140px;
}

@media (max-width: 480px) {
  .big-screen-mode-buttons :deep(.n-button) {
    flex: 1 1 100%;
  }
}
</style>
