# Windows 播放运行

状态：T126 软件接线与本机只读探针通过；待执行 T116。

2026-09-10 在当前 Windows 交互桌面执行只读探针：Hardware provider 通过
Per-Monitor-V2 上下文识别 1 台 `2560×1600` 主显示器，默认 Core Audio 渲染端点可读取；
未修改系统音量，也未移动播放窗口。`HostHardwareIntegrationTests` 覆盖负坐标、无效目标、
硬件观测值持久化和端点 unavailable 时的 fail-closed 行为。

当前已通过 Windows x64 编译、PDF/WebView2/VLC/进程生命周期和音频自动化边界测试；尚未在四屏、Office、VLC、MediaMTX 和真实音频设备上完成 60 分钟混合播放。未完成项不作通过结论。
