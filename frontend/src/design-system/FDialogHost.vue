<script setup lang="ts">
/**
 * 全局 Dialog 宿主：监听 useDialog/useDialogStore 的状态，渲染唯一一个 FDialog。
 * 在 layouts 顶层挂载一次即可，让任意业务通过 useDialog().confirm() 弹出确认。
 */
import { computed } from 'vue';

import FDialog from './FDialog.vue';
import { useDialogStore } from '@/composables/useDialog';

const store = useDialogStore();
const config = computed(() => store.config);
const variant = computed(() => store.config?.variant ?? 'default');
// 危险确认默认禁止 Esc / 遮罩点击关闭，迫使用户做明确选择。
const cancellable = computed(() => variant.value !== 'danger');

function onConfirm(): void {
  store.accept();
}

function onCancel(): void {
  store.cancel();
}
</script>

<template>
  <FDialog
    :open="store.open"
    :title="config?.title ?? ''"
    :description="config?.description"
    :confirm-label="config?.confirmLabel ?? '确定'"
    :cancel-label="config?.cancelLabel ?? '取消'"
    :variant="variant"
    :cancellable="cancellable"
    :loading="store.loading"
    @update:open="(value) => !value && store.cancel()"
    @confirm="onConfirm"
    @cancel="onCancel"
  />
</template>
