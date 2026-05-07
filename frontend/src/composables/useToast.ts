/*
 * Toast 全局通知 composable + Pinia store。
 * 设计稿 §5.11 / DESIGN.md §12.13：
 *  - 成功 Toast 自动消失（默认 3.2 s）；
 *  - 错误 Toast 不自动消失，必须可手动关闭并提供「重试」入口（可选）；
 *  - 同时最多展示 3 条；超出按 FIFO 替换最早一条；
 *  - 移动端由布局层将容器位置切到顶部居中；这里只产出语义数据。
 *
 * 不直接挂载 DOM；DOM 由 layouts 层的 ToastHost 渲染。
 */
import { defineStore } from 'pinia';

/** Toast 的语义级别。 */
export type ToastLevel = 'info' | 'success' | 'warning' | 'error';

/** Toast 携带的可选撤销/重试动作。 */
export interface ToastAction {
  label: string;
  /** 用户点击动作时回调；若返回 Promise 会等待完成再关闭 Toast。 */
  onTrigger: () => void | Promise<void>;
}

export interface ToastItem {
  id: number;
  level: ToastLevel;
  message: string;
  description?: string;
  action?: ToastAction;
  /** 自动关闭毫秒数；0 表示不自动关闭（错误默认 0）。 */
  duration: number;
}

interface ToastState {
  items: ToastItem[];
}

const MAX_VISIBLE_TOASTS = 3;
const SUCCESS_DURATION_MS = 3200;
const INFO_DURATION_MS = 3200;
const WARNING_DURATION_MS = 4800;

let nextToastId = 1;

/** 自动定时器表，避免 store 状态泄漏到 Pinia 序列化。 */
const dismissTimers = new Map<number, number>();

export const useToastStore = defineStore('toast', {
  state: (): ToastState => ({
    items: [],
  }),
  actions: {
    /**
     * 推送一条 Toast，超过上限时丢弃最早一条。
     * @param payload Toast 内容
     * @return 该 Toast 的 id，便于外部主动关闭
     */
    push(payload: Omit<ToastItem, 'id' | 'duration'> & { duration?: number }): number {
      const id = nextToastId++;
      const computedDuration = payload.duration
        ?? (payload.level === 'error' ? 0
          : payload.level === 'warning' ? WARNING_DURATION_MS
          : payload.level === 'success' ? SUCCESS_DURATION_MS : INFO_DURATION_MS);
      const item: ToastItem = {
        id,
        level: payload.level,
        message: payload.message,
        description: payload.description,
        action: payload.action,
        duration: computedDuration,
      };
      this.items.push(item);
      if (this.items.length > MAX_VISIBLE_TOASTS) {
        const dropped = this.items.shift();
        if (dropped) this._clearTimer(dropped.id);
      }
      if (computedDuration > 0) {
        const timerId = window.setTimeout(() => this.dismiss(id), computedDuration);
        dismissTimers.set(id, timerId);
      }
      return id;
    },
    /** 通用便捷方法：成功提示。 */
    success(message: string, description?: string): number {
      return this.push({ level: 'success', message, description });
    },
    info(message: string, description?: string): number {
      return this.push({ level: 'info', message, description });
    },
    warning(message: string, description?: string): number {
      return this.push({ level: 'warning', message, description });
    },
    /**
     * 错误 Toast；默认不自动消失，调用方应当通过 action 提供「重试」或显式关闭。
     */
    error(message: string, description?: string, action?: ToastAction): number {
      return this.push({ level: 'error', message, description, action });
    },
    /** 主动关闭某条 Toast。 */
    dismiss(id: number): void {
      this._clearTimer(id);
      const index = this.items.findIndex((item) => item.id === id);
      if (index >= 0) this.items.splice(index, 1);
    },
    /** 清空所有 Toast，常用于路由切换前。 */
    clear(): void {
      this.items.forEach((item) => this._clearTimer(item.id));
      this.items = [];
    },
    _clearTimer(id: number): void {
      const handle = dismissTimers.get(id);
      if (handle !== undefined) {
        window.clearTimeout(handle);
        dismissTimers.delete(id);
      }
    },
  },
});

/** 简化调用：业务代码大多只关心 success / error / info。 */
export function useToast() {
  const store = useToastStore();
  return {
    success: store.success.bind(store),
    info: store.info.bind(store),
    warning: store.warning.bind(store),
    error: store.error.bind(store),
    push: store.push.bind(store),
    dismiss: store.dismiss.bind(store),
  };
}
