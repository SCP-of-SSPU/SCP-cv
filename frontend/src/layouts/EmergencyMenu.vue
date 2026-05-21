<script setup lang="ts">
/**
 * 应急 Flyout：顶栏右侧入口。
 * 设计稿 §3.1 + §13.6：把不常用但关键的全局动作收纳到这里。
 *  - 重置全部窗口（无确认，因为本身就是兜底操作）
 *  - 显示窗口 ID（调试用，仅触发一次）
 *  - 系统关机（带 Dialog 二次确认 + Danger 主按钮）
 */
import { useI18n } from 'vue-i18n';

import { FMenu } from '@/design-system';
import type { FMenuGroup } from '@/design-system';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';

const { t } = useI18n();
const session = useSessionStore();
const dialog = useDialog();
const toast = useToast();

async function onResetAll(): Promise<void> {
  try {
    await session.resetAll();
    toast.success(t('emergency.resetAllOk'));
  } catch (error) {
    toast.error(t('emergency.resetAllFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function onShowWindowIds(): Promise<void> {
  try {
    await session.showWindowIds();
    toast.info(t('emergency.showIdsOk'));
  } catch (error) {
    toast.error(t('emergency.showIdsFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

async function onShutdown(): Promise<void> {
  const confirmed = await dialog.danger({
    title: t('emergency.shutdownTitle'),
    description: t('emergency.shutdownDesc'),
    confirmLabel: t('emergency.shutdownConfirm'),
    cancelLabel: t('common.cancel'),
  });
  if (!confirmed) return;
  try {
    const result = await session.shutdownSystem();
    toast.warning(t('emergency.shutdownOk'), result.detail ?? t('emergency.shutdownSent'));
  } catch (error) {
    toast.error(t('emergency.shutdownFail'), error instanceof Error ? error.message : t('common.retry'));
  }
}

const groups: FMenuGroup[] = [
  {
    label: t('emergency.groupLabel'),
    items: [
      { label: t('emergency.resetAll'), icon: 'arrow_reset_24_regular', onTrigger: onResetAll },
      { label: t('emergency.showIds'), icon: 'eye_24_regular', onTrigger: onShowWindowIds },
    ],
  },
  {
    items: [
      { label: t('emergency.shutdown'), icon: 'plug_disconnected_24_regular', danger: true, onTrigger: onShutdown },
    ],
  },
];
</script>

<template>
  <FMenu
    :groups="groups"
    trigger-icon="alert_urgent_24_regular"
    trigger-appearance="transparent"
    :aria-label="t('emergency.triggerAria')"
  />
</template>
