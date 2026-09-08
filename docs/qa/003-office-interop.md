# 003 Office/窗口互操作验证记录

状态：软件探针已实现；真实 Office、四显示器和混合 DPI 验证待开发 Windows 播放机执行。

## 已覆盖的软件边界

- `PowerPointOwnershipGuard` 以主机唯一命名 Mutex 和 PID/start-time 证据持有 Office 所有权；释放顺序已覆盖正常和异常路径。
- `OfficeStaDispatcher` 使用独立 STA 与 WPF 消息泵，operation ID 在完成后保留结果，重复请求不会再次触发 COM。
- `PowerPointComAdapter` 只关闭由当前实例打开并登记的 Presentation；无法证明所有权时不退出用户 Office。
- `SlideShowWindowAttacher` 在嵌入前校验 HWND、PID、进程启动时间和 DPI，并在附着/调整失败时返回明确错误。

## 开发机探针（待执行）

在安装 PowerPoint 的交互桌面运行：

```powershell
dotnet test runtime-dotnet/tests/ScpCv.Integration.Tests --filter FullyQualifiedName~OfficeOperation
dotnet run --project runtime-dotnet/tools/ScpCv.InteropProbe -- --office-hwnd <放映窗口HWND>
```

需要记录：PowerPoint 版本、Office 是否已有用户文档、放映窗口 HWND/PID/start-time、每台显示器设备路径与 DPI、模态对话框行为、长导出耗时及超时后的 Office 状态。当前环境未宣称已完成上述实机验证，也不因缺少 Office 而放宽所有权或强杀策略。
