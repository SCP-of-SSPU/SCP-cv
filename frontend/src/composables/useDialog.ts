/*
 * 全局确认对话框 composable + store。
 * DESIGN.md §13.6 与设计稿 §5.8 / §6.5：
 *  - 危险操作必须 Confirm（Dialog）+ Danger 主按钮 + 写明对象/范围/后果；
 *  - 可恢复操作优先用 Toast 撤销，不要滥用确认对话框；
 *  - 焦点：打开时移入 Dialog 内，关闭后回到触发元素，由 FDialog 组件实现。
 *
 * 这里只负责语义数据：组件层订阅 store 渲染。
 */
import { defineStore } from 'pinia';

/** Dialog 主按钮风格；危险操作必须使用 danger。 */
export type DialogVariant = 'default' | 'danger';

export interface DialogConfig {
  /** 标题：写明任务或后果。 */
  title: string;
  /** 描述：用一段话讲清对象、范围与不可逆性。 */
  description?: string;
  /** 主按钮文案，默认「确定」。 */
  confirmLabel?: string;
  /** 次按钮文案，默认「取消」。 */
  cancelLabel?: string;
  /** 主按钮风格。 */
  variant?: DialogVariant;
  /** 触发该 Dialog 的元素（用于关闭后还原焦点）。 */
  triggerElement?: HTMLElement | null;
}

interface DialogState {
  open: boolean;
  config: DialogConfig | null;
  resolver: ((value: boolean) => void) | null;
  loading: boolean;
}

export const useDialogStore = defineStore('dialog', {
  state: (): DialogState => ({
    open: false,
    config: null,
    resolver: null,
    loading: false,
  }),
  actions: {
    /**
     * 弹出确认对话框。返回的 Promise 在用户确认/取消时 resolve。
     * @param config 对话框文案与样式
     * @return 用户确认 → true；取消 / Esc / 遮罩点击 → false
     */
    confirm(config: DialogConfig): Promise<boolean> {
      // 同一时间只允许存在一个 Dialog；如有未关闭的，按取消处理。
      if (this.resolver) this.resolver(false);
      this.config = config;
      this.open = true;
      this.loading = false;
      return new Promise<boolean>((resolve) => {
        this.resolver = resolve;
      });
    },
    /** 标记 Dialog 主按钮处于 loading 状态。 */
    setLoading(value: boolean): void {
      this.loading = value;
    },
    /** 用户点确认 / 主操作。 */
    accept(): void {
      const resolver = this.resolver;
      this.resolver = null;
      this.open = false;
      this.loading = false;
      const trigger = this.config?.triggerElement ?? null;
      this.config = null;
      resolver?.(true);
      // 焦点返还触发元素，符合 DESIGN.md §16.4 焦点管理要求。
      trigger?.focus?.();
    },
    /** 用户点取消 / Esc / 遮罩点击。 */
    cancel(): void {
      const resolver = this.resolver;
      this.resolver = null;
      this.open = false;
      this.loading = false;
      const trigger = this.config?.triggerElement ?? null;
      this.config = null;
      resolver?.(false);
      trigger?.focus?.();
    },
  },
});

export function useDialog() {
  const store = useDialogStore();
  return {
    confirm: store.confirm.bind(store),
    danger: (config: Omit<DialogConfig, 'variant'>) =>
      store.confirm({ ...config, variant: 'danger' }),
  };
}
