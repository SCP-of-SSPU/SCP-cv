<script setup lang="ts">
/**
 * Combobox（下拉选择器）。
 * 设计稿 §5.3：
 *   - 选项 < 5 且短，应改用 Radio / SegmentedControl，不强用 Combobox；
 *   - 选项 ≥ 10 时支持搜索（这里通过外部传 searchable=true 启用）；
 *   - 不在下拉里嵌入复杂表单。
 *
 * 实现要点：
 *   - 通过 details/summary 风格的非原生下拉，统一桌面/移动视觉；
 *   - 键盘：Enter/Space 打开，方向键浏览，Esc 关闭；
 *   - 匹配 Fluent 焦点环风格。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';

import FIcon from './FIcon.vue';
import type { FComboboxOption } from './types';

interface FComboboxProps {
  modelValue: string | number | null;
  options: ReadonlyArray<FComboboxOption<string | number>>;
  placeholder?: string;
  disabled?: boolean;
  /** 是否启用顶部搜索框。 */
  searchable?: boolean;
  /** 显式 id，便于外部 label/aria 关联。 */
  id?: string;
  ariaLabel?: string;
  /** 是否清除当前选择（在右侧显示 ✕）。 */
  clearable?: boolean;
  /** 不变长输入字段时的尺寸控制；默认 medium。 */
  size?: 'compact' | 'medium' | 'large';
}

const props = withDefaults(defineProps<FComboboxProps>(), {
  placeholder: '请选择',
  disabled: false,
  searchable: false,
  id: undefined,
  ariaLabel: undefined,
  clearable: false,
  size: 'medium',
});

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number | null): void;
}>();

const open = ref(false);
const triggerEl = ref<HTMLButtonElement | null>(null);
const listRef = ref<HTMLElement | null>(null);
const searchText = ref('');

const groupedOptions = computed(() => {
  if (!searchText.value.trim()) return props.options;
  const query = searchText.value.trim().toLowerCase();
  return props.options.filter((opt) =>
    opt.label.toLowerCase().includes(query) || String(opt.value).toLowerCase().includes(query),
  );
});

const selectedLabel = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined) return '';
  const found = props.options.find((opt) => opt.value === props.modelValue);
  return found?.label ?? '';
});

function toggle(): void {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) {
    nextTick(() => {
      // 聚焦到列表/搜索框
      const focusTarget = (listRef.value?.querySelector('input,button[role="option"]:not([disabled])') as HTMLElement)
        ?? listRef.value;
      focusTarget?.focus();
    });
  }
}

function pick(option: FComboboxOption<string | number>): void {
  if (option.disabled) return;
  emit('update:modelValue', option.value);
  open.value = false;
  searchText.value = '';
  triggerEl.value?.focus();
}

function clear(event: MouseEvent): void {
  event.stopPropagation();
  emit('update:modelValue', null);
}

function onTriggerKey(event: KeyboardEvent): void {
  if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    if (!open.value) toggle();
  } else if (event.key === 'Escape' && open.value) {
    event.preventDefault();
    open.value = false;
  }
}

function handleOutside(event: MouseEvent): void {
  if (!open.value) return;
  const target = event.target as Node;
  if (!triggerEl.value?.contains(target) && !listRef.value?.contains(target)) {
    open.value = false;
  }
}

watch(open, (val) => {
  if (val) {
    document.addEventListener('mousedown', handleOutside);
  } else {
    document.removeEventListener('mousedown', handleOutside);
    searchText.value = '';
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleOutside);
});
</script>

<template>
  <div class="f-combobox" :class="[`f-combobox--${size}`, disabled && 'f-combobox--disabled']">
    <button ref="triggerEl" :id="id" type="button" class="f-combobox__trigger"
      :class="{ 'f-combobox__trigger--open': open }" :disabled="disabled" :aria-label="ariaLabel" :aria-expanded="open"
      aria-haspopup="listbox" @click="toggle" @keydown="onTriggerKey">
      <span class="f-combobox__value">
        <slot v-if="$slots.value && modelValue !== null" name="value" :label="selectedLabel" />
        <template v-else-if="selectedLabel">{{ selectedLabel }}</template>
        <template v-else>
          <span class="f-combobox__placeholder">{{ placeholder }}</span>
        </template>
      </span>
      <span class="f-combobox__chevrons">
        <button v-if="clearable && modelValue !== null && modelValue !== undefined" type="button"
          class="f-combobox__clear" aria-label="清除选择" @click="clear">
          <FIcon name="dismiss_16_regular" />
        </button>
        <FIcon class="f-combobox__chevron" :name="open ? 'chevron_up_20_regular' : 'chevron_down_20_regular'" />
      </span>
    </button>

    <Transition name="f-combobox-list">
      <div v-if="open" ref="listRef" class="f-combobox__list" role="listbox">
        <div v-if="searchable" class="f-combobox__search">
          <FIcon name="search_20_regular" />
          <input v-model="searchText" type="search" class="f-combobox__search-input" placeholder="搜索…" aria-label="搜索选项"
            autocomplete="off" />
        </div>
        <div class="f-combobox__items">
          <template v-for="(option, index) in groupedOptions" :key="String(option.value) + '-' + index">
            <p v-if="option.group" class="f-combobox__group">{{ option.group }}</p>
            <button v-else type="button" role="option" class="f-combobox__option" :class="{
              'f-combobox__option--selected': option.value === modelValue,
              'f-combobox__option--disabled': option.disabled,
            }" :aria-selected="option.value === modelValue" :disabled="option.disabled" @click="pick(option)">
              <span class="f-combobox__option-label">{{ option.label }}</span>
              <span v-if="option.hint" class="f-combobox__option-hint">{{ option.hint }}</span>
              <FIcon v-if="option.value === modelValue" class="f-combobox__option-check" name="checkmark_20_regular" />
            </button>
          </template>
          <p v-if="groupedOptions.length === 0" class="f-combobox__empty">无匹配项</p>
        </div>
        <slot name="footer" />
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.f-combobox {
  position: relative;
  display: inline-flex;
  width: 100%;
}

.f-combobox--disabled {
  pointer-events: none;
  opacity: 0.55;
}

.f-combobox__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-s);
  width: 100%;
  min-height: 32px;
  padding: 0 var(--spacing-m);
  border-radius: var(--radius-medium);
  border: 1px solid var(--color-border-default);
  background: var(--color-background-card);
  color: var(--color-text-primary);
  font-family: inherit;
  font-size: var(--type-body1-size);
  cursor: pointer;
  box-shadow: var(--shadow-control);
  transition:
    border-color var(--motion-duration-medium) var(--motion-curve-ease),
    box-shadow var(--motion-duration-medium) var(--motion-curve-ease),
    background-color var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-combobox--compact .f-combobox__trigger {
  min-height: 28px;
}

.f-combobox--large .f-combobox__trigger {
  min-height: 40px;
}

.f-combobox__trigger:hover:not(:disabled) {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-2);
}

.f-combobox__trigger--open,
.f-combobox__trigger:focus-visible {
  border-color: var(--color-border-focus);
  box-shadow: var(--shadow-focus), var(--shadow-2);
  outline: none;
}

.f-combobox__value {
  flex: 1 1 auto;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.f-combobox__placeholder {
  color: var(--color-text-tertiary);
}

.f-combobox__chevrons {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.f-combobox__clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-circular);
}

.f-combobox__clear:hover {
  background: var(--color-background-subtle);
  color: var(--color-text-primary);
}

.f-combobox__chevron {
  width: 16px;
  height: 16px;
}

.f-combobox__list {
  position: absolute;
  z-index: var(--z-dropdown);
  top: calc(100% + var(--spacing-xxs));
  left: 0;
  width: 100%;
  max-height: 320px;
  /*
   * Acrylic 浮层：与 FMenu / FTooltip / FToast 同款，避免不同浮层视觉风格分裂。
   * @supports not (backdrop-filter) 回退到原 raised 实色，老浏览器仍可用。
   */
  background: var(--color-background-glass-strong);
  border-radius: var(--radius-large);
  border: var(--stroke-width-thin) solid color-mix(in srgb, var(--color-border-subtle) 70%, transparent);
  box-shadow: var(--shadow-flyout);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  -webkit-backdrop-filter: blur(20px) saturate(1.15);
  backdrop-filter: blur(20px) saturate(1.15);
}

@supports not (backdrop-filter: blur(20px)) {
  .f-combobox__list {
    background: var(--color-background-raised);
  }
}

.f-combobox__search {
  display: flex;
  align-items: center;
  gap: var(--spacing-s);
  padding: var(--spacing-s) var(--spacing-m);
  border-bottom: 1px solid var(--color-border-subtle);
  color: var(--color-text-tertiary);
}

.f-combobox__search-input {
  flex: 1 1 auto;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-text-primary);
  font: inherit;
}

.f-combobox__items {
  flex: 1 1 auto;
  overflow: auto;
  padding: var(--spacing-xs);
}

.f-combobox__group {
  margin: var(--spacing-s) var(--spacing-s) var(--spacing-xs);
  font-size: var(--type-caption1-size);
  font-weight: 600;
  color: var(--color-text-tertiary);
}

.f-combobox__option {
  display: flex;
  align-items: center;
  gap: var(--spacing-s);
  width: 100%;
  padding: var(--spacing-s) var(--spacing-m);
  border: none;
  background: transparent;
  color: var(--color-text-primary);
  text-align: left;
  border-radius: var(--radius-medium);
  cursor: pointer;
  font-family: inherit;
  font-size: var(--type-body1-size);
  transition:
    background-color var(--motion-duration-medium) var(--motion-curve-ease),
    color var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-ease);
}

.f-combobox__option:hover:not(:disabled) {
  background: var(--color-background-subtle);
  transform: translateX(2px);
}

.f-combobox__option--selected {
  background: var(--color-background-brand-selected);
  color: var(--color-text-brand);
  font-weight: 600;
}

.f-combobox__option--disabled {
  cursor: not-allowed;
  color: var(--color-text-disabled);
}

.f-combobox__option-label {
  flex: 1 1 auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.f-combobox__option-hint {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.f-combobox__option-check {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.f-combobox__empty {
  margin: 0;
  padding: var(--spacing-l);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--type-caption1-size);
}

.f-combobox-list-enter-active,
.f-combobox-list-leave-active {
  transition: opacity var(--motion-duration-medium) var(--motion-curve-ease),
    transform var(--motion-duration-medium) var(--motion-curve-decelerate);
}

.f-combobox-list-enter-from,
.f-combobox-list-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 767px) {
  .f-combobox__trigger {
    min-height: var(--touch-target-min);
  }

  .f-combobox__option {
    min-height: var(--touch-target-min);
  }
}
</style>
