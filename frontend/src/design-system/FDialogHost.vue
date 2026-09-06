<script setup lang="ts">
/**
 * 全局 Dialog 宿主：监听 useDialogStore 的状态，用 Naive UI 的 NModal 渲染单实例
 * 确认对话框。业务侧仍调用 useDialog().confirm(...) / danger(...)，保持原有 Promise
 * API 不变；本组件是 Pinia store → NUI 之间的桥接层。
 *
 * 危险确认默认禁止 Esc / 遮罩点击关闭，但必须保留显式“取消”，让用户能
 * 在不误触危险动作的前提下安全退出。
 */
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NModal } from 'naive-ui';

import { useDialogStore } from '@/composables/useDialog';

const { t } = useI18n();
const store = useDialogStore();

const open = computed({
  get: () => store.open,
  set: (value: boolean) => {
    if (!value && store.open) store.cancel();
  },
});

const variant = computed(() => store.config?.variant ?? 'default');
const dismissible = computed(() => variant.value !== 'danger');
const confirmText = computed(() => store.config?.confirmLabel ?? t('ds.dialogConfirm'));
const cancelText = computed(() => store.config?.cancelLabel ?? t('ds.dialogCancel'));
const isDanger = computed(() => variant.value === 'danger');
</script>

<template>
  <n-modal
    v-model:show="open"
    preset="card"
    :title="store.config?.title ?? ''"
    :mask-closable="dismissible"
    :close-on-esc="dismissible"
    :closable="dismissible"
    :auto-focus="true"
    :trap-focus="true"
    :block-scroll="true"
    style="max-width: 480px"
    @close="store.cancel"
  >
    <p v-if="store.config?.description" class="f-dialog-host__body">
      {{ store.config.description }}
    </p>
    <template #footer>
      <div class="f-dialog-host__actions">
        <n-button :disabled="store.loading" @click="store.cancel">
          {{ cancelText }}
        </n-button>
        <n-button
          :type="isDanger ? 'error' : 'primary'"
          :loading="store.loading"
          @click="store.accept"
        >
          {{ confirmText }}
        </n-button>
      </div>
    </template>
  </n-modal>
</template>

<style scoped>
.f-dialog-host__body {
  margin: 0;
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase300);
  line-height: var(--lineHeightBase300);
}

.f-dialog-host__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacingHorizontalS);
  justify-content: flex-end;
  width: 100%;
}
</style>
