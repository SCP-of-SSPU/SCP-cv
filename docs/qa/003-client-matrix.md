# 003 客户端矩阵

| 客户端 | 页面/构建 | 会话与 SSE | 文件与关闭 | 结论 |
| --- | --- | --- | --- | --- |
| Web（Chrome 1440/900、768/1024、390/844） | 已检查登录/控制台、响应式无横向溢出 | 依赖 ControlHost 合同测试 | 浏览器 Blob 路径由前端测试覆盖 | 软件通过 |
| Electron Windows | `build:app`、`build:electron-main`、安全静态测试通过；unpacked 包成功加载连接页和媒体源路由 | HTTPS ControlHost 的 csrf/login/me/SSE 实测通过；媒体源路由连续 10 次 reload 均保持登录并恢复单一控制链路 | 原生桥边界已测；交互式文件对话框待验证 | 部分通过 |
| Android Capacitor | `build:app`、debug APK 安装并启动；Medium_Tablet / Android 16 API 36 / WebView 134.0.6998.135（>=111） | HTTPS ControlHost 登录、REST、SSE 及 10 次 HOME/恢复通过；SSE 无订阅倍增 | 原生选择/上传、受保护保存、外链转系统 Chrome、三段返回键及退出后主机存活均通过 | 实包通过（T114） |

Android 已完成真实 APK 门禁；Electron 的交互式文件选择/保存和关闭行为仍待补，因此 T050/T113/T128 尚未整体完成。
