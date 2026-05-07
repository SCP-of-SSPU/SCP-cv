<script setup lang="ts">
/**
 * Menu / Flyout：列表行末 ⋯ 菜单、应急 Flyout、设置选项菜单。
 * DESIGN.md §12.17 / 设计稿 §5.15：
 *   - 菜单项使用动词或明确名词；
 *   - 危险项分组并使用 status.error 文字色；
 *   - 禁用项必须配 Tooltip 说明不可用原因；
 *   - 键盘：方向键导航、Enter 触发、Esc 关闭。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

import FButton from './FButton.vue';
import FIcon from './FIcon.vue';
import type { FluentIconName } from './icons';
import type { ButtonAppearance, FMenuGroup, FMenuItem } from './types';

interface FMenuProps {
  /** 触发按钮的图标；不传时由调用方使用插槽自定义。 */
  triggerIcon?: FluentIconName | string;
  triggerLabel?: string;
  triggerAppearance?: ButtonAppearance;
  triggerSize?: 'compact' | 'medium' | 'large';
  /** 菜单分组数据。 */
  groups: FMenuGroup[];
  /** 触发按钮的可访问名称（icon-only 时必填）。 */
  ariaLabel?: string;
  disabled?: boolean;
  /** 浮层弹出位置：right（默认）/ left。 */
  placement?: 'right' | 'left';
}

const props = withDefaults(defineProps<FMenuProps>(), {
  triggerIcon: 'more_horizontal_20_regular',
  triggerLabel: undefined,
  triggerAppearance: 'transparent',
  triggerSize: 'medium',
  ariaLabel: '更多操作',
  disabled: false,
  placement: 'right',
});

const open = ref(false);
const root = ref<HTMLElement | null>(null);
const menuRef = ref<HTMLElement | null>(null);

const flatItems = computed(() => props.groups.flatMap((group) => group.items));

function toggle(): void {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) {
    nextTick(() => {
      const first = menuRef.value?.querySelector('button[role="menuitem"]:not([disabled])') as HTMLButtonElement | null;
      first?.focus();
    });
  }
}

async function trigger(item: FMenuItem): Promise<void> {
  if (item.disabled) return;
  open.value = false;
  if (item.onTrigger) await item.onTrigger();
}

function handleOutside(event: MouseEvent): void {
  if (!open.value) return;
  const target = event.target as Node;
  if (!root.value?.contains(target)) {
    open.value = false;
  }
}

function onKey(event: KeyboardEvent): void {
  if (!open.value) return;
  const items = Array.from(
    menuRef.value?.querySelectorAll<HTMLButtonElement>('button[role="menuitem"]:not([disabled])') ?? [],
  );
  if (items.length === 0) return;
  const current = items.indexOf(document.activeElement as HTMLButtonElement);
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    items[(current + 1 + items.length) % items.length].focus();
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    items[(current - 1 + items.length) % items.length].focus();
  } else if (event.key === 'Escape') {
    event.preventDefault();
    open.value = false;
  } else if (event.key === 'Home') {
    event.preventDefault();
    items[0].focus();
  } else if (event.key === 'End') {
    event.preventDefault();
    items[items.length - 1].focus();
  }
}

watch(open, (val) => {
  if (val) {
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', onKey);
  } else {
    document.removeEventListener('mousedown', handleOutside);
    document.removeEventListener('keydown', onKey);
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleOutside);
  document.removeEventListener('keydown', onKey);
});

void flatItems; // 显式标记，避免 lint 抱怨
</script>

<template>
  <div ref="root" class="f-menu">
    <FButton v-if="!$slots.trigger" :appearance="triggerAppearance" :size="triggerSize" :icon-only="!triggerLabel"
      :icon-start="triggerIcon" :aria-label="ariaLabel" :disabled="disabled" @click="toggle">
      {{ triggerLabel }}
    </FButton>
    <span v-else class="f-menu__custom-trigger" @click="toggle">
      <slot name="trigger" :open="open" />
    </span>

    <Transition name="f-menu">
      <div v-if="open" ref="menuRef" class="f-menu__list" :class="`f-menu__list--${placement}`" role="menu">
        <template v-for="(group, gIndex) in groups" :key="gIndex">
          <p v-if="group.label" class="f-menu__group">{{ group.label }}</p>
          <button v-for="(item, idx) in group.items" :key="`${gIndex}-${idx}`" type="button" role="menuitem"
            class="f-menu__item"
            :class="{ 'f-menu__item--danger': item.danger, 'f-menu__item--disabled': item.disabled }"
            :disabled="item.disabled" :title="item.hint" @click="trigger(item)">
            <FIcon v-if="item.icon" class="f-menu__icon" :name="item.icon" />
            <span class="f-menu__label">{{ item.label }}</span>
            <span v-if="item.hint && !item.disabled" class="f-menu__hint">{{ item.hint }}</span>
          </button>
          <hr v-if="gIndex < groups.length - 1" class="f-menu__divider" />
        </template>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.f-menu {
  position: relative;
  display: inline-flex;
}

.f-menu__custom-trigger {
  display: inline-flex;
}

.f-menu__list {
  position: absolute;
  z-index: var(--z-popover);
  top: calc(100% + var(--spacing-xs));
  min-width: 200px;
  max-width: 320px;
  background: var(--color-background-raised);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-large);
  box-shadow: var(--shadow-8);
  padding: var(--spacing-xs);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxs);
}

.f-menu__list--right {
  right: 0;
}

.f-menu__list--left {
  left: 0;
}

.f-menu__group {
  margin: var(--spacing-xs) var(--spacing-s) var(--spacing-xxs);
  font-size: var(--type-caption1-size);
  font-weight: 600;
  color: var(--color-text-tertiary);
}

.f-menu__item {
  display: flex;
  align-items: center;
  gap: var(--spacing-s);
  width: 100%;
  padding: var(--spacing-s) var(--spacing-m);
  border: none;
  background: transparent;
  color: var(--color-text-primary);
  font: inherit;
  cursor: pointer;
  border-radius: var(--radius-medium);
  text-align: left;
  /* hover 时背景过渡走 medium(160ms)，比原来的瞬切更自然。 */
  transition: background var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-menu__item:hover:not(:disabled) {
  background: var(--color-background-subtle);
}

.f-menu__item--danger {
  color: var(--color-status-error-foreground);
}

.f-menu__item--danger:hover:not(:disabled) {
  background: var(--color-status-error-background);
}

.f-menu__item--disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-menu__icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.f-menu__label {
  flex: 1 1 auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.f-menu__hint {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.f-menu__divider {
  border: none;
  border-top: 1px solid var(--color-border-subtle);
  margin: var(--spacing-xs) 0;
}

/*
 * 浮层进入：medium(160ms) decelerate；离场用 fast(100ms) accelerate 收尾。
 * 进入位移加大到 -8 px，让"从触发器掉下来"的方向感更明显。
 */
.f-menu-enter-active {
  transition: opacity var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-decelerate);
}

.f-menu-leave-active {
  transition: opacity var(--motion-duration-fast) var(--motion-curve-ease),
    transform var(--motion-duration-fast) var(--motion-curve-accelerate);
}

.f-menu-enter-from,
.f-menu-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 767px) {
  .f-menu__item {
    min-height: var(--touch-target-min);
  }
}
</style>
