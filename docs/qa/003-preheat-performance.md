# 003 网页与流预热验证记录

状态：simulation/单元验证已通过；真实 WebView2 renderer、MediaMTX 和 10 分钟连续预热待 Windows 播放机执行。

## 软件证据

- `WebViewPlaybackAdapter` 按 `ResourceKey` 复用健康实例，同一资源重复 Prepare 不触发第二次导航。
- 达到每 Worker 预热预算时拒绝新资源；renderer ProcessFailed 后资源标记为不健康，下一代请求走冷重建。
- `VlcPlaybackAdapter` 对 file/http/https/rtsp/srt URI 做能力校验，并把 seek、音量、循环、结束事件限制在 Worker 内。
- `ResourceSwitchCoordinator` 仅在新资源 Ready 且 generation 仍当前时切换可见性，失败保留旧画面。
- `StreamDiscoveryService` 通过 HTTP HEAD 更新 MediaMTX/流源在线状态，不跨进程传递原生对象。

## 待执行实机记录

在目标 Windows x64 机器运行 50 次同一 Worker 网页切换，记录导航计数（目标为 0 次新增导航）、首帧延迟、内存和 renderer 重启；再对 MediaMTX 流预热 10 分钟，记录每分钟在线探测、认领结果和资源趋势。缺少实机时不得将软件测试结果表述为播放成功。
