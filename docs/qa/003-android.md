# Android Capacitor 验证

状态：通过（真实 Android AVD/debug APK，2026-09-11）。

## 环境

- 设备：Medium_Tablet AVD，Android 16 / API 36，serial `emulator-5556`。
- WebView：`134.0.6998.135`，满足最低版本 `>=111`。
- 应用：`cn.edu.sspu.scpcv.control`，由 `pnpm --dir frontend run cap:sync` 与 `frontend/android/gradlew.bat assembleDebug --no-daemon` 构建。
- 主机：`https://localhost:18443`，SafetyMode=`Simulation`，ADB reverse `tcp:18443 -> tcp:18443`。
- TLS：隔离测试 CA/localhost 证书位于未提交的 `.validation/android-tls`；AVD 用户凭据已安装该 CA。APK 中 `network_security_config.xml` 的 debug trust anchor 经构建产物核对存在，未使用 `ignore-https-errors`、明文 HTTP 或匿名 SSE。

## 实包结果

- `app-debug.apk` 安装、`MainActivity` 启动和 Capacitor 本地 `https://localhost` 资源加载通过。
- `qa-admin` 登录成功；认证后的 REST 全量状态请求均成功，`/api/events/` EventSource 建立成功。
- 连续 10 次 HOME → 前台恢复后仍位于 dashboard；网络记录仅出现预期的两次 SSE 重建，没有订阅倍增。
- 原生文件选择器选择 `/sdcard/Download/scp-cv-qa-upload.png` 后上传成功，生成媒体源 `Android QA Upload`。
- 受保护下载成功保存为 `/storage/emulated/0/Documents/SCP-cv/scp-cv-qa-upload.png`。
- `window.open("https://example.com")` 交由系统 Chrome；应用 WebView 保持在 `https://localhost/#/sources`，未允许任意远程页面进入受信 WebView。
- 返回键顺序通过：添加媒体源抽屉打开时第一次 Back 仅关闭抽屉并保持 `/sources`；第二次 Back 回到 `/dashboard`；根页面第三次 Back 退出客户端 Activity。
- 客户端退出后 ControlHost 的 `/api/auth/status/` 仍返回 HTTP 200，确认客户端生命周期不控制主机进程。
- Manifest 仍保持 `usesCleartextTraffic=false`，FileProvider 只暴露应用私有范围。

## 返回键缺陷与修复证据

初次实测发现 `plugins.App.disableBackButtonHandler=true` 会禁用 Capacitor AppPlugin 的原生回调。改为 `false` 后，logcat 已确认 `backButton` 事件进入 WebView；随后又发现旧实现派发的合成 Escape 事件不能关闭 Naive UI 抽屉，而真实 Escape 可以。

最终实现通过 `frontend/src/platform/lifecycleBack.ts` 显式调用最上层浮层自身的关闭控件，不改变页面路由和业务状态。`frontend/scripts/platform-adapters.test.mjs` 覆盖关闭行为，`frontend/scripts/capacitor-platform.test.mjs` 覆盖原生回调配置；专项测试、typecheck、Capacitor sync、Gradle 构建和上述 APK 返回键序列均通过。

## 结论边界

本记录完成 T114 的 Android APK 门禁。它不代表 Windows 四屏、Office、VLC、MediaMTX 或音频硬件通过；这些仍由 T116/T129 单独验证。
