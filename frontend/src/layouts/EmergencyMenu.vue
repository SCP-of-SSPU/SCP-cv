<script setup lang="ts">
/**
 * 应急 Flyout：顶栏右侧入口。
 * 把不常用但关键的全局动作收纳到这里。
 *  - 重置全部窗口（无确认，因为本身就是兜底操作）
 *  - 显示窗口 ID（调试用，仅触发一次）
 *  - 系统关机（带 Dialog 二次确认 + Danger 主按钮）
 */
import { h } from 'vue';
import { useI18n } from 'vue-i18n';
import { NButton, NDropdown, type DropdownOption } from 'naive-ui';

import FIcon from '@/design-system/FIcon.vue';
import type { FluentIconName } from '@/design-system';
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

function renderIcon(name: FluentIconName) {
  return () => h(FIcon, { name, size: 18 });
}

const options: DropdownOption[] = [
  {
    type: 'group',
    label: t('emergency.groupLabel'),
    key: 'group-main',
    children: [
      { label: t('emergency.resetAll'), key: 'reset', icon: renderIcon('arrow_reset_24_regular'), props: { onClick: onResetAll } },
      { label: t('emergency.showIds'), key: 'show-ids', icon: renderIcon('eye_24_regular'), props: { onClick: onShowWindowIds } },
    ],
  },
  { type: 'divider', key: 'divider-1' },
  {
    label: t('emergency.shutdown'),
    key: 'shutdown',
    icon: renderIcon('plug_disconnected_24_regular'),
    props: { onClick: onShutdown, style: 'color: var(--colorStatusDangerForeground1);' },
  },
];

function handleSelect(_key: string, option: DropdownOption): void {
  const handler = (option.props as { onClick?: () => void } | undefined)?.onClick;
  handler?.();
}
</script>

<template>
  <n-dropdown
    trigger="click"
    placement="bottom-end"
    :options="options"
    @select="handleSelect"
  >
    <n-button
      quaternary
      circle
      :aria-label="t('emergency.triggerAria')"
    >
      <template #icon>
        <FIcon name="alert_urgent_24_regular" />
      </template>
    </n-button>
  </n-dropdown>
</template>
