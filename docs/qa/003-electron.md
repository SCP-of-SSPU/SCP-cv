# Electron 验证

状态：待执行真实打包程序验证。

已完成：`pnpm build:app`、`pnpm build:electron-main`；Electron 安全静态测试覆盖 `app://scp-cv` 资源边界、CSP、外链/新窗口拒绝、contextIsolation/sandbox、受限文件桥和 Cookie 清理。

待执行：在 Windows 打包目录启动程序，完成连接页、登录、SSE、路由刷新、文件选择/保存及关闭客户端不影响 ControlHost 的手工记录。
