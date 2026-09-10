# Electron 验证

状态：部分完成（真实 Windows unpacked 包已完成 HTTPS ControlHost 认证、SSE 与路由恢复联调；原生文件对话框待补）。

已完成：`pnpm build:app`、`pnpm build:electron-main`；Electron 安全静态测试覆盖 `app://scp-cv` 资源边界、CSP、外链/新窗口拒绝、contextIsolation/sandbox、受限文件桥和 Cookie 清理。使用 `release-electron/win-unpacked/SCP-cv Control.exe --remote-debugging-port=9224` 实测：

- `app://scp-cv/#/connect` 成功加载，标题为“连接播放主机 · SCP-cv 播放控制台”；无空白页。
- `window.scpCvElectron` 暴露 `platform`、文件、会话、配置和生命周期 API，未暴露 `ipcRenderer`/Node 对象。
- 页面无水平溢出，Electron 控制台无 error/pageerror；关闭客户端不会终止 ControlHost（进程边界由独立 exe 保持）。

2026-09-10 在提交 `91c6767` 上使用 Electron 44.2.0 / Chromium 152、`agent-browser 0.19.0`
连接 `https://localhost:18443` 的独立 `SafetyMode=Simulation` ControlHost：

- 从 `app://scp-cv` Origin 完成 csrf → login → me；服务端精确返回
  `Access-Control-Allow-Origin: app://scp-cv` 与 credentials，渲染器取得 `csrftoken`/`sessionid` 后进入仪表盘。
- SSE 返回 `text/event-stream`，首帧从 `id: 0` 开始；实际包显示“控制链路已连接”，同时保持“播放器离线”，没有把 SSE 在线误报为 Worker 在线。
- 进入 `app://scp-cv/#/sources` 后连续执行 10 次页面卸载/重新加载；每次均保持该 hash 路由、保持登录并重新显示“控制链路已连接”，没有回到登录页。
- 复核渲染器仅暴露受限 `window.scpCvElectron` API，`window.require` 为 `undefined`；上述流程 console/pageerror 为 0。
- 关闭实际 Electron 进程组后，独立 ControlHost 的 `/health/ready` 与服务根仍返回 200，确认关闭客户端不停止播放主机。

待执行：人工完成文件选择/上传与受保护下载保存对话框。原生文件项完成前不将 T113/T128 标为完整通过。
