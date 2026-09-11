# 003 运行时生命周期验证记录

状态：simulation 生命周期、PID/start-time 证据测试、开发构建整组故障退出，以及真实 Hardware 运行时 7 进程一次完整拉起均已通过；真实四屏、Office、音频与 MediaMTX 完整启停矩阵仍待工作站执行。

`ProcessRegistry` 只登记 Supervisor 自己启动的进程，并校验 PID、启动时间和会话号。`ShutdownCoordinator` 先请求协作退出并等待 5 秒，再对自有非 Office 进程执行最多 3 秒的受控终止；无法证明 Office 所有权时保留进程，不按名称误杀。客户端退出不会触发主机停止。

## 2026-09-09 开发构建整组故障退出

`runtime.ps1 start` 经 Supervisor 启动 4 个 PlayerWorker、1 个 AudioWorker、1 个 PowerPointHost 和项目自有 MediaMTX，共 7 个受管进程。当时 PowerPointHost 占位入口退出后，Supervisor 检测成员故障并触发整组停止；状态文件已删除，未发现残留 SCP-cv/MediaMTX 进程。该证据验证 T121 的编排和故障退出，不抵扣 T125 的真实 Office 宿主或 T116 的 60 分钟四屏测试。

## 2026-09-11 真实 Hardware 启动缺陷修复

首次执行 `POST /api/system/restart/`（`SafetyMode=Hardware`）无法启动运行时，用系统化调试在依赖图中定位到三个真实缺陷，均按“先加失败回归，再修根因”的顺序处理：

1. **Hardware ControlHost 启动死锁。**
   `RuntimePipeBroker` 构造依赖 `AudioFinishedEventProcessor → BackgroundAudioService → CommandCoordinator → ICommandWakeNotifier → RuntimePipeBroker`，
   两个线程互等同一个单例锁；进程完成数据库初始化后不再监听 HTTP。
   修复：新增 `RuntimeCommandWakeNotifier`（`IServiceProvider` 延迟解析 broker）切断构造环。
   回归：`HardwareControlHostStartupTests`，修复前稳定 10 秒超时，修复后约 1 秒返回 `/health/ready` 200。

2. **停止确认对已停止状态不幂等。**
   初始运行组已是 `Stopped`，`BeginDrainAsync` 会幂等返回该状态，但 `CompleteStopAsync` 只接受 `Draining`，使首次启动被 500 拦住。
   修复：同 `group_epoch` 的 `Stopped` 状态直接幂等返回。
   回归：`RuntimeLifecycleTests.CompleteStopIsIdempotentForTheCurrentStoppedEpoch`。

3. **子进程先连接、Supervisor 后登记的身份竞态。**
   Supervisor 先启动全部子进程，再统一向 ControlHost 登记；子进程立即连接 Named Pipe，被“客户端进程未由 Supervisor 登记”拒绝，
   PowerPointHost 随即以退出码 1 结束并触发整组停止。
   修复：新增启动门 `RuntimeStartGate`/`RuntimeStartGateHandle`。Supervisor 先创建命名 ManualReset 事件并传入 `--start-gate`，
   完成全部身份登记后才开门；PlayerWorker/AudioWorker/PowerPointHost 在开门前不连接管道。异常路径也会开门，避免子进程无界挂起。
   回归：`RuntimeStartGateTests`（未开门时 Worker 不继续；无门名称时立即继续）。

修复后的实测（`SafetyMode=Hardware`，`http://localhost:18444`，DataRoot `.validation\t129-live-20260911`）：

```
POST /api/system/restart/ -> 200
{"success":true,"group_epoch":3,"detail":"Supervisor restart 的全部 Worker 已就绪。"}
```

受管进程全部在线且 PID/start-time/session 证据写入状态文件：

| 角色 | 进程 |
| --- | --- |
| player-1..4 | ScpCv.PlayerWorker ×4 |
| audio | ScpCv.AudioWorker ×1 |
| office | ScpCv.PowerPointHost ×1 |
| mediamtx | mediamtx ×1 |

本次只证明“真实运行时可以被 Supervisor 一次拉起并全部就绪”，不证明四屏画面、Office COM、VLC 解码或音频输出效果；
这些仍由 T116/T129 在工作站记录。

## 2026-09-11 观察（不作为缺陷）

在开发桌面（单显示器）上，4 个 PlayerWorker 的无边框全屏窗口落在同一块屏幕上。试采集期间它们全部退出并触发整组协作停止，
ControlHost 进程本身仍存活。这与 FR-018「任一输出进程退出后整组协作停止」一致；规范也明确「独立自动拉起故障窗口」属于以后单独评审的行为变更。
因此本开发机不适合跑完整播放矩阵，正式 60 分钟测试必须放到工作站。

待执行实机矩阵：20 次正常 start/stop/restart、10 次故障退出、客户端关闭期间主机持续运行；记录每次残留 PID、停止闩锁、日志和恢复时间。
