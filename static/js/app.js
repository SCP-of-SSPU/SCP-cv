document.addEventListener("DOMContentLoaded", () => {
  const bannerElement = document.querySelector("[data-banner]");
  const clockElement = document.querySelector("[data-clock]");
  const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "medium",
  });

  const refreshClock = () => {
    if (clockElement) {
      clockElement.textContent = timeFormatter.format(new Date());
    }
  };

  refreshClock();
  window.setInterval(refreshClock, 1000);

  document.querySelectorAll("[data-command]").forEach((commandButton) => {
    commandButton.addEventListener("click", () => {
      if (!bannerElement) {
        return;
      }

      const commandLabel = commandButton.textContent?.trim() || "操作";
      bannerElement.textContent = `${commandLabel} 已挂接到初始化骨架，后续会对接真实控制逻辑。`;
    });
  });
});
