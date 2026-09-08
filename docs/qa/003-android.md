# Android Capacitor 验证

状态：部分完成（真实 Android AVD/APK 与 WebView 版本已验证基础启动和生命周期；ControlHost 联调项待补）。

已完成：`pnpm build:app` 与前端 Capacitor/Android Manifest 安全测试；静态检查确认不默认启用明文、远程 `server.url` 或任意外链权限。Pixel_9_Pro（API 37，Android WebView `145.0.7632.218`）实测：

- `app-debug.apk` 安装成功，`MainActivity` 启动并渲染“连接播放主机”页面。
- HOME → 再启动可恢复页面；返回键在连接页不导致崩溃；强制停止后重新启动成功。
- `usesCleartextTraffic=false`、应用私有 FileProvider 与 Capacitor 本地 `https://localhost` 资源加载均已从 Manifest/logcat 核对。

待执行：连接 simulation/真实 ControlHost 后完成 APK 登录/SSE 恢复、文件上传下载、外链拒绝和完整返回键导航记录；当前 WebView 日志中的安全区注入警告需在可交互页面复核，不据此宣称完整通过。
