# Electron 验证

状态：部分完成（真实 Windows unpacked 包已启动并验证本地渲染与安全边界；ControlHost 联调项待补）。

已完成：`pnpm build:app`、`pnpm build:electron-main`；Electron 安全静态测试覆盖 `app://scp-cv` 资源边界、CSP、外链/新窗口拒绝、contextIsolation/sandbox、受限文件桥和 Cookie 清理。使用 `release-electron/win-unpacked/SCP-cv Control.exe --remote-debugging-port=9224` 实测：

- `app://scp-cv/#/connect` 成功加载，标题为“连接播放主机 · SCP-cv 播放控制台”；无空白页。
- `window.scpCvElectron` 暴露 `platform`、文件、会话、配置和生命周期 API，未暴露 `ipcRenderer`/Node 对象。
- 页面无水平溢出，Electron 控制台无 error/pageerror；关闭客户端不会终止 ControlHost（进程边界由独立 exe 保持）。

待执行：连接 simulation/真实 ControlHost 后完成登录、SSE 恢复、业务路由刷新，以及人工点击文件选择/保存对话框；这些依赖运行中的主机和交互式桌面，当前不将静态/页面验证扩大为完整通过。
