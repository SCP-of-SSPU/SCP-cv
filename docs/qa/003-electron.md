# Electron 验证

状态：已完成（T113）。在真实 Windows unpacked 包上完成 HTTPS ControlHost 认证、SSE、路由恢复、文件上传/下载与客户端关闭验证。

已完成构建：`pnpm build:app`、`pnpm build:electron-main`；Electron 安全静态测试覆盖 `app://scp-cv` 资源边界、CSP、外链/新窗口拒绝、contextIsolation/sandbox、受限文件桥和 Cookie 清理。

## 2026-09-10 基线（提交 `91c6767`）

Electron 44.2.0 / Chromium 152、`agent-browser 0.19.0`，连接 `https://localhost:18443` 的独立 `SafetyMode=Simulation` ControlHost：

- `app://scp-cv/#/connect` 成功加载，标题为“连接播放主机 · SCP-cv 播放控制台”；无空白页。
- `window.scpCvElectron` 暴露 `platform`、文件、会话、配置和生命周期 API，未暴露 `ipcRenderer`/Node 对象；`window.require` 为 `undefined`。
- 从 `app://scp-cv` Origin 完成 csrf → login → me；服务端精确返回 `Access-Control-Allow-Origin: app://scp-cv` 与 credentials。
- SSE 返回 `text/event-stream`，首帧从 `id: 0` 开始；实际包显示“控制链路已连接”，同时保持“播放器离线”，没有把 SSE 在线误报为 Worker 在线。
- 进入 `app://scp-cv/#/sources` 后连续 10 次页面卸载/重新加载；每次均保持该 hash 路由、保持登录并重新显示“控制链路已连接”，没有回到登录页。
- 上述流程 console/pageerror 为 0。

## 2026-09-11 文件与关闭验证（提交 `22ed31f`）

真实 unpacked 包：`frontend/release-electron/win-unpacked/SCP-cv Control.exe`（`--remote-debugging-port=9224`），
连接 `https://localhost:18443` 的 `SafetyMode=Simulation` ControlHost，DataRoot `.validation\t128-live-20260911`。
用户已在本机信任 ControlHost 的 TLS 证书，未关闭证书校验、未改用明文。

上传（含缺陷修复）：

- 登录后上传 `.validation\t128-file.svg`（220 B），命名为 `Electron QA Upload`，服务端出现成功的 `POST /api/sources/upload/`，媒体源列表出现该条目。
- 该路径暴露并修复了一个真实缺陷：multipart 上传只读取 `document.cookie`，而 Electron 的安全 Cookie 无法经此路径读取，导致“缺少 CSRF token”。
  现已统一为 `resolveCsrfToken(csrfRequestToken, readCookie('csrftoken'))`（`frontend/src/platform/csrf.ts`）。

下载：

- 行末菜单“下载”触发 Electron 原生“另存为”对话框，默认文件名为 `t128-file.svg`；保存后客户端主进程 `writeFile` 落盘成功。
- 落盘文件与源文件 SHA-256 完全一致：`908B9893F19F81A2E726F2DA04534D2451CF3EDEAC5D0BB86242E94F47014127`。
- 验证副本已删除，未留在仓库根目录。

关闭：

- 关闭实际 Electron 进程组（4 个进程）后，独立 ControlHost 仍返回 `/health/ready` 200、`/api/auth/status/` 200，确认关闭客户端不停止播放主机。

## 已知边界

- 未在 Electron 上验证真实 Worker 在线（需要 `SafetyMode=Hardware`）；该部分由 `docs/qa/003-windows-runtime.md` 与 T116/T129 负责。
- 原生“另存为”对话框由 OS 渲染，自动化只能通过窗口自动化确认；本记录中的下载结论以文件落盘与哈希一致为准。
