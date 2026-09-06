import type { Directive } from 'vue';

/**
 * Naive UI 的 Slider 把未知 aria-label 留在根节点，而实际可聚焦的
 * role="slider" handle 不会继承。该指令把可读名称同步到真正的焦点节点。
 */
function applySliderAriaLabel(root: HTMLElement, label: string): void {
  root.querySelectorAll<HTMLElement>('[role="slider"]').forEach((handle) => {
    handle.setAttribute('aria-label', label);
  });
}

export const sliderAriaLabel: Directive<HTMLElement, string> = {
  mounted(element, binding): void {
    applySliderAriaLabel(element, binding.value);
  },
  updated(element, binding): void {
    applySliderAriaLabel(element, binding.value);
  },
};
