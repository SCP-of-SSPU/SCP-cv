# Android Capacitor 验证

状态：部分完成（真实 Android AVD/APK 与 WebView 版本已验证基础启动；HTTPS ControlHost 联调被测试证书信任阻断，未放宽 TLS）。

已完成：`pnpm build:app` 与前端 Capacitor/Android Manifest 安全测试；静态检查确认不默认启用明文、远程 `server.url` 或任意外链权限。Medium_Tablet（Android 16/API 36，Android WebView `134.0.6998.135`，满足 >=111）实测：

- `app-debug.apk` 安装成功，`MainActivity` 启动并渲染“连接播放主机”页面。
- HOME → 再启动可恢复页面；返回键在连接页不导致崩溃；强制停止后重新启动成功。
- `usesCleartextTraffic=false`、应用私有 FileProvider 与 Capacitor 本地 `https://localhost` 资源加载均已从 Manifest/logcat 核对。
- `app-debug.apk` 安装成功，应用包为 `cn.edu.sspu.scpcv.control`；ADB reverse `18443` 与 WebView CDP 均可用。
- 为验证 HTTPS，使用隔离 `.validation/android-tls` 生成测试 CA/localhost 证书，并在 AVD 的“用户凭据 → CA 证书”中确认 `SCP-cv Android QA CA` 已安装；ControlHost 侧用同一 CA 校验通过。
- APK 页面仍收到 `CERT_AUTHORITY_INVALID (-202)`，随后认证/SSE 请求失败。该结果记录为测试设备/应用信任链未完成，未使用 `ignore-https-errors`、明文 HTTP 或匿名 SSE 绕过。

待执行：在设备接受受信测试 CA 后完成 APK 登录/SSE 恢复、文件上传下载、外链拒绝和完整返回键导航记录；当前 WebView 日志中的安全区注入警告需在可交互页面复核，不据此宣称完整通过。
