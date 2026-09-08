# 003 客户端矩阵

| 客户端 | 页面/构建 | 会话与 SSE | 文件与关闭 | 结论 |
| --- | --- | --- | --- | --- |
| Web（Chrome 1440/900、768/1024、390/844） | 已检查登录/控制台、响应式无横向溢出 | 依赖 ControlHost 合同测试 | 浏览器 Blob 路径由前端测试覆盖 | 软件通过 |
| Electron Windows | `build:app`、`build:electron-main`、安全静态测试通过 | 打包进程实测待有可执行包后执行 | 原生桥边界已测，完整包待验证 | 待实机 |
| Android Capacitor | `build:app`、平台静态测试通过 | WebView>=111 设备待验证 | APK 文件选择/返回键待验证 | 待实机 |

当前没有把 Electron/Android 的静态构建结果宣称为真实封装客户端通过；需要设备时按 T113/T114 补录。
