/*
 * 焦点陷阱 composable。
 * 用于 Dialog / Drawer / Sheet：键盘 Tab 序列循环在容器内，Esc 由调用方监听。
 * 受 DESIGN.md §16.4 焦点管理要求驱动。
 */
import { onBeforeUnmount, watch, type Ref } from 'vue';

/**
 * 可聚焦元素的 CSS 选择器，覆盖按钮/链接/原生表单/含 tabindex 元素。
 */
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

interface UseFocusTrapOptions {
  /** 容器引用；为空时不启用陷阱。 */
  container: Ref<HTMLElement | null>;
  /** 是否激活；通常绑定到浮层的 v-model:open。 */
  active: Ref<boolean>;
  /** 关闭后焦点应回到的触发元素，由调用方传入。 */
  returnFocusTo?: Ref<HTMLElement | null>;
}

/**
 * 在 active=true 期间，把 Tab 焦点循环锁定在 container 内部。
 * 自动记录上一次焦点元素并在关闭时还原。
 * @param options 容器、激活信号、还原焦点目标
 * @return None
 */
export function useFocusTrap(options: UseFocusTrapOptions): void {
  let previousActiveElement: HTMLElement | null = null;

  function getFocusable(el: HTMLElement): HTMLElement[] {
    return Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
      (node) => !node.hasAttribute('inert') && node.offsetParent !== null,
    );
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Tab') return;
    const container = options.container.value;
    if (!container) return;
    const focusables = getFocusable(container);
    if (focusables.length === 0) {
      event.preventDefault();
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement | null;
    if (event.shiftKey) {
      if (active === first || !container.contains(active)) {
        event.preventDefault();
        last.focus();
      }
    } else if (active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function activate(): void {
    const container = options.container.value;
    if (!container) return;
    previousActiveElement = (document.activeElement as HTMLElement) || null;
    document.addEventListener('keydown', handleKeydown);
    // 入场后选第一个可聚焦元素，符合 ARIA 浮层最佳实践。
    const focusables = getFocusable(container);
    const initial = focusables[0] ?? container;
    initial.focus();
  }

  function deactivate(): void {
    document.removeEventListener('keydown', handleKeydown);
    const target = options.returnFocusTo?.value ?? previousActiveElement;
    previousActiveElement = null;
    target?.focus?.();
  }

  watch(
    () => options.active.value,
    (active) => {
      if (active) {
        // 等待 DOM 渲染完毕后再陷阱，避免拿不到容器引用。
        requestAnimationFrame(activate);
      } else {
        deactivate();
      }
    },
    { immediate: false },
  );

  onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown);
  });
}
