# 003 运行时生命周期验证记录

状态：simulation 生命周期和 PID/start-time 证据测试已通过；真实四屏、Office、音频与 MediaMTX 启停待开发 Windows 交互桌面执行。

`ProcessRegistry` 只登记 Supervisor 自己启动的进程，并校验 PID、启动时间和会话号。`ShutdownCoordinator` 先请求协作退出并等待 5 秒，再对自有非 Office 进程执行最多 3 秒的受控终止；无法证明 Office 所有权时保留进程，不按名称误杀。客户端退出不会触发主机停止。

待执行实机矩阵：20 次正常 start/stop/restart、10 次故障退出、客户端关闭期间主机持续运行；记录每次残留 PID、停止闩锁、日志和恢复时间。
