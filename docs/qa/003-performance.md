# 性能基准

状态：方法与脚本已就绪；普通命令 1000 样本与健康热切换 100 样本仍待在工作站硬件上执行。

目标（SC-006）：普通控制 1000 样本 p95 开始执行 ≤ 1 秒；健康热切换 100 样本 p95 可见 ≤ 300 毫秒。
执行时必须记录 CPU、内存、网络、媒体类型、ControlHost/Worker 版本和原始样本，不以单元测试代替该基准。

## 采集方法

普通命令使用 [`runtime-dotnet/scripts/benchmark-commands.ps1`](../../runtime-dotnet/scripts/benchmark-commands.ps1)：

- 通过真实 ControlHost 提交 1000 条 `PATCH /api/playback/{1..4}/volume/`，在 4 个窗口之间轮询并默认间隔 50 ms。
- 延迟取自命令表 `CreatedAt → StartedAt`，即“入队时刻到 Worker 真正开始执行”，HTTP 往返只作为旁证。
- 脚本显式拒绝在 simulation 上给出结论，并在折叠比例超过 20% 时判定“测量无效”，避免把被覆盖的命令算成通过。

健康热切换需要在工作站上用两个已预热的网页源来回切换，记录从发起到画面可见的时间；当前开发机没有可用的 WebView2 预热素材与多屏拓扑，未执行。

## 前置条件

必须连接 `SafetyMode=Hardware` 且 Supervisor 已拉起 4 个 PlayerWorker、AudioWorker、PowerPointHost 与 MediaMTX 的主机；
simulation 没有 Worker 认领命令，不能用于本基准。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File runtime-dotnet/scripts/benchmark-commands.ps1 `
  -BaseUrl http://localhost:18444 `
  -DatabasePath .validation\t129-live-20260911\control.db `
  -Password '<开发账号口令>' `
  -Samples 1000 -Targets 1,2,3,4 -DelayMilliseconds 50 `
  -HardwareNote '四屏/媒体/网络条件' `
  -OutputPath docs/qa/003-performance-commands.md
```

## 2026-09-11 试采集（判定：测量无效，不作为结论）

在开发桌面 1 台 `2560×1600` 显示器上启动真实运行时后试采集 1000 条窗口音量命令，结果：

| 指标 | 值 |
| --- | --- |
| 入队命令数 | 1003 |
| 真正开始执行 | 3 |
| 被后续意图折叠 | 1007（Superseded） |
| HTTP 提交平均 / p95 | 5.7 ms / 10.5 ms |
| 排空后仍未完成 | 1 |

两点结论：

1. **同目标命令会被新意图折叠**是设计行为（`superseded_by_newer_intent`），因此“连打同一窗口 1000 次”不能作为性能样本；
   正式采集必须跨 4 个窗口轮询并留出提交间隔。脚本已按此修正。
2. 试采集期间 4 个 PlayerWorker 窗口位于同一块屏幕上（无边框全屏），随后全部退出并触发整组协作停止，
   与 FR-018“任一输出进程退出后整组停止”一致；这次运行不能用于判定性能，也不能代表工作站四屏条件。

因此 T115/T129 仍未完成，必须在工作站执行并按上面的脚本产出原始样本。
