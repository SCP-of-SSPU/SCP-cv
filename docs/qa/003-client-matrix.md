# 003 客户端矩阵

| 客户端 | 页面/构建 | 会话与 SSE | 文件与关闭 | 结论 |
| --- | --- | --- | --- | --- |
| Web（Chrome 1440/900、768/1024、390/844） | 已检查登录/控制台、响应式无横向溢出 | 依赖 ControlHost 合同测试 | 浏览器 Blob 路径由前端测试覆盖 | 软件通过 |
| Electron Windows | `build:app`、`build:electron-main`、安全静态测试通过；unpacked 包成功加载连接页和媒体源路由 | HTTPS ControlHost 的 csrf/login/me/SSE 实测通过；媒体源路由连续 10 次 reload 均保持登录并恢复单一控制链路 | 原生桥边界已测；交互式文件对话框待验证 | 部分通过 |
| Android Capacitor | `build:app`、debug APK 安装并启动；Medium_Tablet WebView 134.0.6998.135（>=111） | 前后台重启实测；已尝试用户 CA + HTTPS ControlHost，但 WebView 仍返回 `CERT_AUTHORITY_INVALID (-202)`，认证/SSE 未通过 | Manifest/本地资源安全边界实测；文件/外链待验证 | 部分通过（TLS 信任阻断） |

当前没有把 Electron/Android 的静态构建结果宣称为真实封装客户端通过；T114 仍待解决测试设备信任链后补录。
