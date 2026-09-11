# Windows 播放运行

状态：T126 软件接线与本机只读探针通过；真实运行时可在 Hardware 模式一次拉起全部 7 个受管进程并到达就绪；待执行 T116 的 60 分钟四屏/媒体/音频混合测试。

## 本机只读探针（2026-09-10）

在当前 Windows 交互桌面执行只读探针：Hardware provider 通过 Per-Monitor-V2 上下文识别 1 台 `2560×1600` 主显示器，
默认 Core Audio 渲染端点可读取；未修改系统音量，也未移动播放窗口。`HostHardwareIntegrationTests` 覆盖负坐标、无效目标、
硬件观测值持久化和端点 unavailable 时的 fail-closed 行为。

## 真实运行时启动（2026-09-11）

`SafetyMode=Hardware` + Supervisor 控制通道，`POST /api/system/restart/` 返回：

```
{"success":true,"group_epoch":3,"detail":"Supervisor restart 的全部 Worker 已就绪。"}
```

4 个 PlayerWorker、AudioWorker、PowerPointHost、MediaMTX 全部在线，PID/start-time/session 证据写入 `runtime-processes.json`。
本次启动过程中修复的三个真实缺陷见 `003-runtime-lifecycle.md`。

## 仍待工作站验证

- 四屏真实显示拓扑与跨屏 DPI（当前开发机只有 1 台显示器）。
- Office COM/HWND 附着与实际放映效果（本机未安装可用 Office 素材流程）。
- VLC 视频、SRT/RTSP 流与 MediaMTX 转发。
- 真实音频输出（本机只做了端点只读探针，未播放）。
- 连续 60 分钟混合播放的稳定性、内存与残留进程。

在这些条件满足前，不得据本页结论宣称四屏或混合播放通过；T118 的旧实现删除仍被 T107–T116 门禁阻塞。

## 工作站 `d2` 硬件探针（2026-09-11）

在交互会话内以无头方式（计划任务 + 隐藏窗口）启动 `SafetyMode=Hardware` 的 ControlHost 后：

- `/api/displays/`：4 块真实显示器，均为 `3840×2160`，坐标 `x=0 / 3840 / 7680 / 11520`，`DISPLAY1` 为主屏；
  即工作站已具备 T116 所需的四屏拓扑。
- `/api/volume/`：`level=51, muted=false, system_synced=true, backend=windows_core_audio`，Core Audio 可用。

这一条与开发机的“1 台 2560×1600 主显示器”形成对照：SSH 会话（session 0）看不到真实显示拓扑，
硬件结论必须取自交互会话内运行的 ControlHost。

部署方式与命令见 `003-workstation-runbook.md`；上述探针只证明硬件可见，不代表四屏播放已通过。
