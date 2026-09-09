# 003 运行时生命周期验证记录

状态：simulation 生命周期、PID/start-time 证据测试及一次开发构建整组故障退出已通过；真实四屏、Office、音频与 MediaMTX 完整启停矩阵仍待开发 Windows 交互桌面执行。

`ProcessRegistry` 只登记 Supervisor 自己启动的进程，并校验 PID、启动时间和会话号。`ShutdownCoordinator` 先请求协作退出并等待 5 秒，再对自有非 Office 进程执行最多 3 秒的受控终止；无法证明 Office 所有权时保留进程，不按名称误杀。客户端退出不会触发主机停止。

2026-09-09 开发构建实测：`runtime.ps1 start` 经 Supervisor 启动 4 个 PlayerWorker、1 个 AudioWorker、1 个 PowerPointHost 和项目自有 MediaMTX，共 7 个受管进程。当前 PowerPointHost 占位入口退出后，Supervisor 检测成员故障并触发整组停止；状态文件已删除，未发现残留 SCP-cv/MediaMTX 进程。该证据验证 T121 的编排和故障退出，不抵扣 T125 的真实 Office 宿主或 T116 的 60 分钟四屏测试。

待执行实机矩阵：20 次正常 start/stop/restart、10 次故障退出、客户端关闭期间主机持续运行；记录每次残留 PID、停止闩锁、日志和恢复时间。
