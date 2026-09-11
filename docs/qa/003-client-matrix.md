# 003 客户端矩阵

| 客户端 | 页面/构建 | 会话与 SSE | 文件与关闭 | 结论 |
| --- | --- | --- | --- | --- |
| Web（Chrome 1440/900、768/1024、390/844） | 已检查登录/控制台、响应式无横向溢出；真实浏览器 10 次 reload 均保持登录并恢复控制链路 | 依赖 ControlHost 合同测试；`client-connection.test.mjs` 覆盖断线重连代次 | 受保护下载在浏览器会话内取得 200 + `attachment` + 220 B + SHA-256 一致的 Blob；浏览器落盘由 `download` 属性交给浏览器 | 实包通过 |
| Electron Windows | `build:app`、`build:electron-main`、安全静态测试通过；unpacked 包成功加载连接页和媒体源路由；10 次 reload 保持登录与单一控制链路 | HTTPS ControlHost 的 csrf/login/me/SSE 实测通过 | 上传（含 CSRF 缺陷修复）与原生“另存为”下载落盘 SHA-256 一致；关闭进程组后主机仍 200 | 实包通过（T113） |
| Android Capacitor | `build:app`、debug APK 安装并启动；Medium_Tablet / Android 16 API 36 / WebView 134.0.6998.135（>=111） | HTTPS ControlHost 登录、REST、SSE 及 10 次 HOME/恢复通过；SSE 无订阅倍增 | 原生选择/上传、受保护保存、外链转系统 Chrome、三段返回键及退出后主机存活均通过 | 实包通过（T114） |

三端共享用例与结果已按登录 → 控制台 → 媒体源 → 文件 → 关闭的顺序记录，详见 `003-browser-ui.md`、`003-electron.md`、`003-android.md`。

说明：

- Web 的“文件”一项验证到“受保护下载请求返回正确字节”为止；浏览器把 Blob 落盘的最终一步由浏览器自身完成，未在自动化中抓取到落盘文件，故按证据强度如实记录。
- 三端均未验证真实 Worker 在线状态；Client 侧只证明控制链路与客户端行为，播放侧由 `003-windows-runtime.md` 与 T116/T129 负责。
