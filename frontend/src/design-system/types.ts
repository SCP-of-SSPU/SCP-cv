/*
 * 设计系统通用类型导出。
 * 由于 `<script setup>` 内的 export 不会被外部访问到，
 * 这里集中暴露需要在业务侧引用的类型。
 */
import type { FluentIconName } from './icons';

export type ButtonAppearance = 'primary' | 'secondary' | 'subtle' | 'transparent' | 'danger' | 'ghost';
export type ButtonSize = 'small' | 'compact' | 'medium' | 'large';
export type TagTone = 'neutral' | 'info' | 'success' | 'warning' | 'error' | 'brand' | 'subtle';
export type MessageTone = 'info' | 'success' | 'warning' | 'error';

export interface FSegmentedOption<TValue extends string | number = string> {
  label: string;
  value: TValue;
  icon?: FluentIconName | string;
  disabled?: boolean;
  ariaLabel?: string;
}

export interface FTabsItem<TValue extends string | number = string> {
  label: string;
  value: TValue;
  icon?: FluentIconName | string;
  badge?: number | string;
  disabled?: boolean;
}

export interface FComboboxOption<TValue extends string | number = string> {
  label: string;
  value: TValue;
  group?: string;
  disabled?: boolean;
  hint?: string;
}

export interface FMenuItem {
  label: string;
  icon?: FluentIconName | string;
  onTrigger?: () => void | Promise<void>;
  disabled?: boolean;
  hint?: string;
  danger?: boolean;
}

export interface FMenuGroup {
  label?: string;
  items: FMenuItem[];
}
