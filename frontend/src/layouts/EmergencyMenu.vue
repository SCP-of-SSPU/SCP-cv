<script setup lang="ts">
/**
 * 应急 Flyout：顶栏右侧入口。
 * 设计稿 §3.1 + §13.6：把不常用但关键的全局动作收纳到这里。
 *  - 重置全部窗口（无确认，因为本身就是兜底操作）
 *  - 显示窗口 ID（调试用，仅触发一次）
 *  - 系统关机（带 Dialog 二次确认 + Danger 主按钮）
 */
import { FMenu } from '@/design-system';
import type { FMenuGroup } from '@/design-system';
import { useDialog } from '@/composables/useDialog';
import { useToast } from '@/composables/useToast';
import { useSessionStore } from '@/stores/sessions';

const session = useSessionStore();
const dialog = useDialog();
const toast = useToast();

async function onResetAll(): Promise<void> {
  try {
    await session.resetAll();
    toast.success('已将所有窗口重置为待机');
  } catch (error) {
    toast.error('重置失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function onShowWindowIds(): Promise<void> {
  try {
    await session.showWindowIds();
    toast.info('已触发窗口 ID 显示');
  } catch (error) {
    toast.error('指令发送失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

async function onShutdown(): Promise<void> {
  const confirmed = await dialog.danger({
    title: '关闭播放器服务？',
    description: '关闭后所有窗口立即停止播放，整个播放控制台进入离线状态。继续前请确认现场无正在使用的演讲。',
    confirmLabel: '确认关闭',
    cancelLabel: '取消',
  });
  if (!confirmed) return;
  try {
    const result = await session.shutdownSystem();
    toast.warning('系统关闭中', result.detail ?? '已发送关闭指令');
  } catch (error) {
    toast.error('关闭失败', error instanceof Error ? error.message : '请稍后重试');
  }
}

const groups: FMenuGroup[] = [
  {
    label: '应急控制',
    items: [
      { label: '重置全部窗口', icon: 'arrow_reset_24_regular', onTrigger: onResetAll },
      { label: '显示窗口 ID', icon: 'eye_24_regular', onTrigger: onShowWindowIds },
    ],
  },
  {
    items: [
      { label: '关闭播放器服务', icon: 'plug_disconnected_24_regular', danger: true, onTrigger: onShutdown },
    ],
  },
];
</script>

<template>
  <FMenu
    :groups="groups"
    trigger-icon="alert_urgent_24_regular"
    trigger-appearance="transparent"
    aria-label="应急控制"
  />
</template>
