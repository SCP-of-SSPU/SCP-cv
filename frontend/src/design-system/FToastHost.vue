<script setup lang="ts">
/**
 * 全局 Toast 宿主：把 useToastStore 的 items 桥接到 Naive UI 的 useNotification。
 * 业务侧 useToast().success/error/... API 保持不变；本组件负责把 store 数据流
 * 渲染为 NUI 通知（title + content + action 三段，与原数据结构一一对应）。
 *
 * 错误通知不自动消失（duration=0），与 DESIGN.md §7 / 设计稿 §5.11 一致。
 */
import { watch } from 'vue';
import { useNotification, type NotificationType } from 'naive-ui';

import { useToastStore, type ToastItem, type ToastLevel } from '@/composables/useToast';

const store = useToastStore();
const notification = useNotification();

const activeHandles = new Map<number, ReturnType<typeof notification.create>>();

function mapLevel(level: ToastLevel): NotificationType {
  switch (level) {
    case 'success':
      return 'success';
    case 'warning':
      return 'warning';
    case 'error':
      return 'error';
    default:
      return 'info';
  }
}

function open(item: ToastItem): void {
  if (activeHandles.has(item.id)) return;
  const handle = notification.create({
    type: mapLevel(item.level),
    title: item.message,
    content: item.description,
    duration: item.duration > 0 ? item.duration : undefined,
    closable: true,
    meta: item.action?.label,
    onAfterLeave: () => {
      activeHandles.delete(item.id);
      store.dismiss(item.id);
    },
    action: item.action
      ? () => {
          const label = item.action!.label;
          const handler = item.action!.onTrigger;
          return h('button', {
            class: 'f-toast-host__action',
            type: 'button',
            onClick: async () => {
              try {
                await handler();
              } finally {
                handle.destroy();
              }
            },
          }, label);
        }
      : undefined,
  });
  activeHandles.set(item.id, handle);
}

function close(id: number): void {
  const handle = activeHandles.get(id);
  if (handle) {
    handle.destroy();
    activeHandles.delete(id);
  }
}

// 跟随 store.items 增量同步：新增项目→打开；删除项目→关闭。
watch(
  () => store.items.map((item) => item.id),
  (currentIds, previousIds) => {
    const prev = new Set(previousIds ?? []);
    const next = new Set(currentIds);
    for (const id of currentIds) {
      if (!prev.has(id)) {
        const item = store.items.find((i) => i.id === id);
        if (item) open(item);
      }
    }
    for (const id of prev) {
      if (!next.has(id)) close(id);
    }
  },
  { immediate: true },
);
</script>

<script lang="ts">
import { h } from 'vue';
</script>

<template>
  <span aria-hidden="true" style="display: none" />
</template>

<style>
.f-toast-host__action {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--colorBrandForeground1);
  font: inherit;
  font-weight: var(--fontWeightSemibold);
  cursor: pointer;
  padding: var(--spacingVerticalXS) var(--spacingHorizontalS);
  border-radius: var(--borderRadiusMedium);
}
.f-toast-host__action:hover {
  background: var(--colorSubtleBackgroundHover);
}
.f-toast-host__action:focus-visible {
  outline: var(--strokeWidthThick) solid var(--colorBrandStroke1);
  outline-offset: 1px;
}
</style>
