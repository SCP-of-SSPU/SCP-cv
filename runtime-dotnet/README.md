# .NET 播控运行时

播放运行时仅支持 Windows x64 交互桌面。`ControlHost` 负责 REST/SSE、SQLite/EF Core 和持久命令队列；`Supervisor` 在同一交互会话启动四个 PlayerWorker、AudioWorker、PowerPointHost 与可选 MediaMTX。控制端（Web/Electron/Capacitor）不会直接访问 Named Pipe 或播放器对象。

开发构建：

```powershell
dotnet restore runtime-dotnet/ScpCv.sln
dotnet build runtime-dotnet/ScpCv.sln
dotnet test runtime-dotnet/ScpCv.sln
```

使用 `scripts/runtime.ps1 -Action status|start|stop|restart` 查看或请求运行时启停。停止流程只处理 Supervisor 登记且 PID/start-time/session 证据匹配的自有进程；Office 无法证明所有权时不强杀。开发数据库位于独立 DataRoot，Git 仅恢复代码与规范，不删除数据库、媒体和日志。
