# 浏览器 UI 验证

日期：2026-09-08。使用本地 Vite preview、simulation ControlHost 和系统 Chrome（Playwright headless）检查 1440×900、768×1024、390×844 三种视口。

- 登录页/已登录控制台均能渲染，页面无水平溢出。
- 桌面、平板、手机导航分别显示完整侧栏或移动底栏。
- 捕获截图：`003-browser-desktop.png`、`003-browser-tablet.png`、`003-browser-mobile.png`。
- 浏览器 console error 与 pageerror：0（ControlHost simulation 同时运行，未产生连接拒绝噪声）。

真实设备触控与 GPU 播放仍需现场 Windows/Android 复核。

## 2026-09-11 真实 HTTPS 会话补充

使用 Vite dev（`http://localhost:5173`，`/api` 反代到 `https://localhost:18443`）与 `SafetyMode=Simulation` ControlHost，
在系统 Chrome 中由 `agent-browser` 驱动：

- `qa-admin` 登录成功，控制台显示“控制链路已连接”且同时保持“播放器离线”，未把 SSE 在线误报为 Worker 在线。
- 连续 10 次 `reload` 后仍停留在 `/dashboard`、保持登录、恢复控制链路；页面无水平溢出，console/pageerror 为空。
- 媒体源页展示上传条目；行末菜单“下载”触发的受保护请求返回 `200`、`Content-Type: image/svg+xml`、
  `Content-Disposition: attachment; filename=t128-file.svg`，`blob` 大小 220 B，
  SHA-256 `908b9893f19f81a2e726f2da04534d2451cf3edeac5d0bb86242e94f47014127`，与源文件一致。

浏览器把该 Blob 落盘的最终一步由浏览器自身完成，自动化未抓取到落盘文件；结论以“请求成功且字节一致”为准，
已在 `003-client-matrix.md` 如实标注。
