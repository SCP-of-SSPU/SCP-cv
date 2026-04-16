/**
 * SCP-cv Tab 导航模块
 * 职责：Tab 切换逻辑与键盘导航支持
 */

/**
 * 激活指定的 Tab 按钮并切换面板
 * @param {HTMLElement} targetTab - 要激活的 Tab 按钮
 * @param {NodeList} allTabs - 所有 Tab 按钮集合
 */
function activateTab(targetTab, allTabs) {
  const targetTabId = targetTab.dataset.tab;

  allTabs.forEach((otherButton) => {
    const isActive = otherButton === targetTab;
    otherButton.classList.toggle("tab-bar__item--active", isActive);
    otherButton.setAttribute("aria-selected", String(isActive));
    /* 非激活 Tab 排除 Tab 序列以符合 WAI-ARIA Tab 模式 */
    otherButton.setAttribute("tabindex", isActive ? "0" : "-1");
  });

  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const isPanelActive = panel.id === `tab-${targetTabId}`;
    panel.classList.toggle("tab-panel--active", isPanelActive);
    panel.hidden = !isPanelActive;
  });
}

/**
 * 初始化 Tab 导航的点击事件与键盘左右箭头导航
 */
export function initTabNavigation() {
  const tabButtons = document.querySelectorAll(".tab-bar__item[data-tab]");

  tabButtons.forEach((tabButton) => {
    tabButton.addEventListener("click", () => {
      activateTab(tabButton, tabButtons);
    });
  });

  /* 键盘导航：左右方向键在 Tab 之间移动焦点 */
  const tabBar = document.querySelector(".tab-bar");
  if (tabBar) {
    tabBar.addEventListener("keydown", (keyEvent) => {
      const tabArray = Array.from(tabButtons);
      const currentIndex = tabArray.indexOf(document.activeElement);
      if (currentIndex < 0) return;

      let nextIndex = -1;
      if (keyEvent.key === "ArrowRight" || keyEvent.key === "ArrowDown") {
        nextIndex = (currentIndex + 1) % tabArray.length;
      } else if (keyEvent.key === "ArrowLeft" || keyEvent.key === "ArrowUp") {
        nextIndex = (currentIndex - 1 + tabArray.length) % tabArray.length;
      }

      if (nextIndex >= 0) {
        keyEvent.preventDefault();
        tabArray[nextIndex].focus();
        activateTab(tabArray[nextIndex], tabButtons);
      }
    });
  }
}
