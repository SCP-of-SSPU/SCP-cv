# 测试分层

- `ScpCv.Domain.Tests`：纯业务规则，不访问文件、网络、数据库或 Windows API。
- `ScpCv.Contracts.Tests`：HTTP/SSE 与 IPC 序列化、OpenAPI 外观。
- `ScpCv.Infrastructure.Tests`：SQLite、文件边界和基础设施适配。
- `ScpCv.ControlHost.Tests`：ASP.NET Core 端点、认证与授权。
- `ScpCv.Integration.Tests`：simulation 模式下的跨层故障与恢复。
- `ScpCv.Windows.Tests`：需要 Windows API 的可自动化测试；真实 Office、显示器和播放器测试
  仍须在验证记录中单独标明。

默认测试不得启动真实播放器、Office、MediaMTX 或设备控制。需要物理副作用的测试使用
`Physical` trait，常规命令通过 `--filter "Category!=Physical"` 排除。
