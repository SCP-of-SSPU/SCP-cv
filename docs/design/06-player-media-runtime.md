# 播放器与媒体运行时设计

本文说明 PySide6 播放器、媒体 adapter、PowerPoint PPT、预热、状态回写和四窗口运行时。该部分是迁移中最不适合并入 Django Web Worker 的模块。

最后更新：2026-07-11。

## 运行时定位

播放器是独立 Windows 桌面进程，负责把持久化命令队列中的动作转成真实窗口、QMediaPlayer、QWebEngine 和 libVLC 操作。PowerPoint COM、Presentation、预热和放映 HWND 生命周期集中在唯一 Broker 中，播放器只持有普通数据客户端。

```text
Django 服务层
  -> ControlCommand 持久化有序队列
  -> PySide6 PlayerController 原子领取并携带 command_id 分派
  -> Qt 主线程执行普通 adapter / AF_PIPE 调用 PPT Broker
  -> succeeded / failed / cancelled 确认 + AdapterState 写回 PlaybackSession
  -> SSE 轮询 DB 推送到 Vue
```

迁移时必须保持以下边界：

| 边界 | 原因 |
| --- | --- |
| 播放器独立进程 | Qt GUI、QWebEngine、libVLC HWND、Office COM 需要活动桌面 |
| 命令从 `ControlCommand` 读取并显式确认 | Django 和播放器是不同进程；连续导航不能被单槽覆盖 |
| 普通 adapter 在 Qt 主线程执行 | Qt 对象和窗口句柄不能随意跨线程调用 |
| PowerPoint 只在 Broker STA 执行 | COM 对象不跨线程或进程；四个播放器共享一个 Application |
| 状态由播放器写回 | 前端看到的播放状态应来自真实播放器，不是 REST 乐观值 |

## 启动入口

| 文件 | 责任 |
| --- | --- |
| `scp_cv/apps/dashboard/management/commands/run_player.py` | 播放器独立启动命令 |
| `scp_cv/apps/dashboard/management/commands/run_ppt_broker.py` | 当前 Windows Session 唯一的 PowerPoint Broker |
| `scp_cv/apps/dashboard/management/commands/runall.py` | 全栈编排并启动播放器子进程 |
| `scp_cv/player/launcher_gui.py` | GUI 启动器，选择窗口和显示器 |
| `scp_cv/player/headless_launcher.py` | 无 GUI/headless 窗口映射 |
| `scp_cv/player/gpu.py` | GPU 选择辅助 |

`run_player` 的关键流程：

| 步骤 | 行为 |
| --- | --- |
| 1 | 创建 `QApplication` |
| 2 | GUI 模式打开 launcher，headless 模式从 `--window1` 到 `--window4` 构造映射 |
| 3 | 连接健康 Broker；普通独立启动在缺失时拉起自有 Broker，`--only-window` 只允许连接既有实例 |
| 4 | 多窗口启动会拆成每窗口一个 `run_player --only-window` 子进程，隔离 Qt 与渲染生命周期 |
| 5 | 单窗口进程创建注入 Broker 客户端的 `PlayerController` 与 `PlayerWindow` |
| 6 | 写入 `PlaybackSession.target_display_label` |
| 7 | `position_on_display()` 定位窗口 |
| 8 | `controller.apply_current_layout()` 应用布局 |
| 9 | `controller.preheat_sources()` 预热；PPT 请求转交 Broker |
| 10 | `controller.start_polling()` 开始领取队列 |

通过 SSH、Windows 服务或非控制台会话启动时，播放器无法可靠访问物理显示器。此时应使用 `runall --headless --service`，让真实运行发生在当前登录用户的交互桌面中。

## PlayerController

主文件：`scp_cv/player/controller.py`。

| 成员 | 说明 |
| --- | --- |
| `_windows` | `window_id -> PlayerWindow` |
| `_adapters` | `window_id -> SourceAdapter` |
| `_adapter_source_ids` | 防止旧 adapter 状态覆盖新 source |
| `_preheat_pool` | 普通媒体预热池与 PPT Broker 预热入口 |
| `_background_audio_adapter` | 全局背景音频 adapter |
| `_last_reported_states` | 状态签名去重 |
| `sig_dispatch_command` | 后台轮询线程到 Qt 主线程的命令信号 |

轮询线程约 0.2 秒一轮，通过条件更新原子领取本窗口最早的 `pending` `ControlCommand`，把 `command_id` 随 Qt signal 交给处理器。同步命令在 adapter 返回后确认；PPT 异步打开在 Broker 回调完成或取消清理完成后确认。异常进入 `failed` 并同步写入会话错误。

领取时会写入由随机 `consumer_id`、PID 和进程创建时间组成的消费者身份与心跳，播放器每 5 秒先续约自己的执行记录，再检查负责目标上的遗留记录。恢复只处理进程已消失、PID 创建时间不匹配或 30 秒租约已过期的其它消费者；仍存活且心跳新鲜的播放器保持所有权。被恢复的指令进入 `failed` 且不重放，正常退出则立即失败本进程尚未完成的记录。

`PlaybackSession.pending_command/command_args` 只镜像最早未完成指令，供一个稳定版本兼容读取；新代码不得从该字段领取、清空或推断执行完成。

状态回写由 `_report_all_adapter_states()` 统一执行。它会检查 adapter 是否仍对应当前 session 的 `media_source_id`，并只在状态签名变化时调用 `update_playback_progress()`。

## 指令处理

命令处理位于 `scp_cv/player/controller_handlers.py`。

| 命令 | 处理器 | 说明 |
| --- | --- | --- |
| `open` | `_handle_open` | 创建 adapter，打开媒体，设置音量/静音，必要时清理临时源 |
| `play` | `_handle_play` | 调用 adapter `play()` |
| `pause` | `_handle_pause` | 调用 adapter `pause()` |
| `stop` | `_handle_stop` | 调用 adapter `stop()` |
| `close` | `_handle_close` | 普通关闭或全局 reset |
| `next` | `_handle_next` | PPT 翻页或动画推进 |
| `prev` | `_handle_prev` | PPT 回退 |
| `goto` | `_handle_goto` | PPT 跳页 |
| `seek` | `_handle_seek` | 视频/音频 seek |
| `set_loop` | `_handle_set_loop` | 循环开关 |
| `set_volume` | `_handle_set_volume` | 窗口音量 |
| `set_mute` | `_handle_set_mute` | 窗口静音 |
| `ppt_media` | `_handle_ppt_media` | 当前 PPT 页媒体播放/暂停/停止 |
| `reset_ppt` | `_handle_reset_ppt` | 关闭并重开 PPT 会话 |
| `show_id` | `_handle_show_id` | 显示窗口 ID 覆盖层 |

`open` 的关键参数包括 `source_id`、`source_type`、`uri`、`autoplay`、`volume`、`muted`、`preheat_enabled`、`target_slide`。

打开新源时，播放器会尽量在目标容器激活后再关闭旧 adapter，减少黑屏。同一窗口切到新 PPT 时，Broker 在 STA 内隐藏旧会话，只有新放映启动和嵌入成功后才释放旧 Presentation，失败则恢复旧会话。播放器侧 PPT Adapter 的 detach/restore seam 不跨进程操作 HWND；切到其它媒体时由控制器激活目标容器，再通过 Qt 下一轮事件循环关闭旧 Broker 会话。

## PlayerWindow

文件：`scp_cv/player/window.py`。

`PlayerWindow` 是每个物理输出窗口的容器。正常模式下无边框并置顶，debug 模式下可移动和调整。

| 结构 | 用途 |
| --- | --- |
| 黑屏 label | 空闲、关闭、切换时的背景 |
| video viewport/container | 图片、本地视频、libVLC、PPT 嵌入容器 |
| web viewport/container | QWebEngineView 页面 |
| ID overlay | `show-id` 时显示窗口编号 |

`position_on_display()` 通过 Qt screen geometry 和 overlap 匹配屏幕。生产模式固定为目标显示器完整尺寸；debug 模式解除 fixed-size，创建不超过目标屏幕 80% 的 16:9 可缩放预览，并按窗口编号错位排列。它能处理部分 DPI/坐标差异，但前提是 Windows 能正确枚举物理显示器。

`resizeEvent()` 先更新 video/web 客户区，再以 50 ms 防抖发出 `render_viewport_resized(window_id, width, height)`。控制器将尺寸交给当前打开的 Adapter；PPT Adapter 不直接跨进程操作 HWND，而是发送 `PptCommand.RESIZE`，由 Broker 按 Player 容器实时客户区同步中间 host 与放映窗口。因此 debug 模式拖动缩放后，PPT 不再停留在首次打开时的尺寸。

已知限制：`PlayerController.sig_reposition` 存在但没有接线；REST 修改显示目标后不会让运行中的窗口立即移动。`left_right_splice` 在数据层存在，但播放器当前仍按单个显示器定位。

## Adapter 工厂

工厂位于 `scp_cv/player/adapters/__init__.py`。

| source_type | Adapter | 技术栈 |
| --- | --- | --- |
| `ppt` | `PptBrokerSourceAdapter` | Windows AF_PIPE；COM 只在 Broker STA |
| `video` | `VideoSourceAdapter` | Qt Multimedia `QMediaPlayer` |
| `audio` | `VideoSourceAdapter` | 兼容路径，业务上音频主要走背景音乐 |
| `image` | `ImageSourceAdapter` | `QPixmap` + `QLabel` |
| `web` | `WebSourceAdapter` | `QWebEngineView` |
| `srt_stream` | `SrtStreamAdapter` | libVLC |
| `rtsp_stream` | `SrtStreamAdapter` | libVLC |
| `custom_stream` | `SrtStreamAdapter` | libVLC |
| `webrtc_stream` | `SrtStreamAdapter` | 兼容遗留命名 |

基础接口在 `scp_cv/player/adapters/base.py`，包括 `SourceAdapter` 和 `AdapterState`。

## 本地视频和图片

| 文件 | 说明 |
| --- | --- |
| `scp_cv/player/adapters/video.py` | 本地视频使用 `QMediaPlayer + QVideoWidget`，支持 seek、loop、volume、mute |
| `scp_cv/player/adapters/image.py` | 图片使用 `QPixmap` 加载，按窗口大小保持比例显示 |

本地视频没有走 libVLC。迁移或调优时不要把直播流和本地视频的播放器实现混淆。

## 直播流

文件：`scp_cv/player/adapters/srt_stream.py`。

直播流使用 `python-vlc/libVLC`，在 Windows 下通过 `set_hwnd()` 嵌入 `PlayerWindow.video_window_handle`。

| 能力 | 说明 |
| --- | --- |
| VLC runtime 查找 | 项目内 `tools/third_party/vlc/runtime/` 优先，系统 VLC 兜底 |
| 低延迟参数 | 网络缓存、live 缓存、clock jitter、丢帧追实时 |
| RTSP 传输 | 根据配置转换为 `:rtsp-tcp` 或 `:rtsp-udp` |
| 瞬时错误宽限 | 首帧前 5 秒内不立即上报 error |
| 预热认领 | 可复用 `StreamPreheatHandle` 的 libVLC instance/player/media |

MediaMTX 地址由 `scp_cv/services/mediamtx.py` 生成。SRT publish URL 中 latency 是微秒，read URL 中 latency 是毫秒，迁移时不能互换单位。

## Web 页面

文件：`scp_cv/player/adapters/web.py`。

Web 播放使用 `QWebEngineView`，开启 JavaScript、本地存储、剪贴板和滚动。预热时可后台加载网页，打开时把已有 view 改父节点到当前窗口。

迁移时需要注意：Web 源不是在浏览器前端 iframe 中播放，而是在播放器进程的 Qt WebEngine 中播放到物理输出窗口。

## PowerPoint PPT 与 Broker

播放器侧适配器是 `scp_cv/player/adapters/ppt_broker.py`，深模块位于 `scp_cv/player/ppt_broker/`。播放器只传递 `PptOpenRequest`、`PptCommandRequest`、`PptSessionKey` 等普通数据，COM 对象永不跨进程。

| 能力 | 文件 |
| --- | --- |
| 播放器 `SourceAdapter` seam | `scp_cv/player/adapters/ppt_broker.py` |
| Broker 合同、单一 STA 与 AF_PIPE | `scp_cv/player/ppt_broker/contracts.py`、`engine.py`、`transport.py` |
| PowerPoint Application / Presentation 生命周期 | `scp_cv/player/ppt_broker/powerpoint.py`、`powerpoint_application.py`、`powerpoint_session.py` |
| 放映 HWND 查找、原生 host、嵌入和尺寸同步 | `scp_cv/player/ppt_broker/windows.py`、`window_handles.py`、`window_hosts.py`、`window_titles.py` |
| PPT 切源容器准备和恢复 | `scp_cv/player/controller_window_helpers.py` |
| 当前页媒体控制 | `scp_cv/player/adapters/ppt_media.py` |

Broker 懒加载一个 PowerPoint Application，窗口 1-4、预热、PNG 预览与 show-format 导出全部经同一 STA 高低优先级队列串行执行。每个活动会话以 `window_id + owner_token` 隔离；同一文件通过独立 untitled Presentation 副本打开，关闭单窗不得调用 `Application.Quit()`。播放器通过当前 Windows Session 专属的认证 `AF_PIPE` 只传输 JSON 普通数据；命名互斥量负责拒绝第二个 Broker 实例。

Application 创建前后都会快照 `POWERPNT.EXE` 的 PID 与创建时间。Broker 优先使用 Application HWND 对应 PID，HWND PID 不可读时只接受前后差集中的唯一新增 PID；多个候选直接失败。只有能定位到具体 Application 且其 PID 不在启动前快照中时，才修改该 Application 的 `DisplayAlerts` 或取得退出所有权。退出先确认没有外部 Presentation；若 `Quit()` 失败，强制终止还必须重新核对 PID、创建时间、进程名和不存在顶层窗口，任何条件无法确认都保留进程。

PowerPoint 播放只支持 COM 窗口化放映。Broker 配置 `ppShowTypeWindow` 并保持完整放映范围；`StartingSlide` 只作为兼容提示，`SlideShowSettings.Run()` 成功后对非首页目标显式调用 `GotoSlide()`，避免区间放映导致页码变成相对值。Broker 统一读取整数、可调用、包装型或 IDispatch `SlideShowWindow.HWND`；必要回退只接受本次新增、PID/class 正确且标题与当前独立 `Presentation.Name` 规范化匹配的唯一顶层窗口。真实 untitled 副本的标题可能是“演示文稿1/2/3/4”，不能用原始源文件名代替该身份。多候选明确失败，禁止“选择最大窗口”。

生产嵌入使用严格两级 Win32 父链：`SlideShowWindow → Broker 原生 host → PlayerWindow.video_window_handle`。Broker 先把自有 host 嵌入远端 Player 容器，再把 PowerPoint 放映窗口嵌入 host，并逐级验证父 HWND、子窗口样式和有效尺寸。关闭或 `View.Exit()` 前先隐藏放映与 host，把 host 从远端 Player 父链脱离到桌面；没有中间 host 的兼容路径则直接脱离放映窗口。Broker 此后只依据会话注册表操作 HWND，不重新枚举已嵌入窗口。

| 后端 | 媒体控制 |
| --- | --- |
| PowerPoint | `scp_cv/player/adapters/ppt_media.py` 控制当前页 shape |

PPT 全局 volume/mute 大多不可控。窗口音量 UI 对 PPT 不应承诺等价于视频音量。

创建、打开文档、运行放映、HWND 查找和嵌入都在 Broker 中执行。只有 `RPC_E_CALL_REJECTED`、`RPC_E_SERVERCALL_RETRYLATER` 做有限退避，确定性错误立即返回；打开、状态读取和 NEXT/PREV/GOTO 都使用同一策略。切源先隐藏旧会话，验证新放映成功后才释放旧 Presentation；失败时清理新对象并恢复旧画面，不回退到进程内 COM 或其它后端。

关闭任意会话时，Broker 都会先隐藏放映，脱离 host 与 Player 父链，把 SlideShowWindow 恢复为顶层 popup 并销毁 host，再幂等退出 View、释放放映 HWND 并关闭源 Presentation；最后一个公开会话同样完整释放，不保留内部隐藏放映。关闭最后一个源前，Broker 创建一个不带窗口、SlideShowWindow 或会话身份的空白 Application sentinel，使同一 Application 在 `SlideShowWindows.Count` 回到零后仍能继续 `Run()`；shutdown 时关闭 sentinel。物理冒烟在全部公开会话关闭后验证会话消失和旧 HWND 不再具有放映身份，再重新打开全部窗口。

## PPT 资源、预览和播放缓存

PPT 后端不仅有播放 adapter，还有导入阶段的资源解析和缓存。

| 文件 | 责任 |
| --- | --- |
| `scp_cv/services/ppt_resources.py` | 解析 OOXML、生成 `PptResource`、提取媒体列表和 speaker notes |
| `scp_cv/services/ppt_preview.py` | 通过 Broker 导出 slide PNG 预览 |
| `scp_cv/player/ppt_broker/powerpoint_exports.py` | 在共享 Application 中隔离导出任务 Presentation |
| `scp_cv/services/ppt_playback_cache.py` | 生成和解析 `.ppsx/.pps` 播放缓存 |
| `scp_cv/services/ppt_playback_export.py` | 用 PowerPoint 导出 show-format 文件 |

缓存规则：现代格式导出 `.ppsx`，旧格式导出 `.pps`。导出失败不阻断媒体源创建，播放时回退原始文件。

## 预热池

核心文件：`scp_cv/player/preheat_pool.py`。

预热触发来自 `PlayerController.preheat_sources()`，查询 `MediaSource.keep_alive=True`、`is_available=True`、`is_temporary=False` 的源。

| 类型 | 预热行为 |
| --- | --- |
| image | 预加载 `QPixmap` |
| video | 预建 `QMediaPlayer` 并设置 source |
| audio | 预建后台音频播放器资源 |
| stream | 隐藏 1x1 QWidget + libVLC 连接 |
| web | 隐藏 `QWebEngineView` |
| PowerPoint | 向 Broker 提交低优先级预热；按 `source_id + uri` 去重并可被前台认领 |

预热不是缓存业务状态，而是缓存播放器资源。迁移时不要把 `keep_alive` 简化为普通后端缓存字段。

## 背景音频

服务层：`scp_cv/services/background_audio.py`。

| 文件 | 责任 |
| --- | --- |
| `scp_cv/player/background_audio_handlers.py` | 读取并执行背景音频命令 |
| `scp_cv/player/adapters/background_audio.py` | `QMediaPlayer + QAudioOutput` 播放器 |

背景音频有独立的 `BackgroundAudioState`、播放列表与 `ControlCommand` 目标，不占用 `window_id` 1-4。音频源不能直接打开到显示窗口；控制指令与窗口通道一样需要领取和终态确认。

自然播放结束后，播放器通知服务层推进下一首。循环开启时会回到第一首。

## Reset 和 Show ID

| 功能 | 服务层 | 播放器侧 |
| --- | --- | --- |
| 全局 reset | `reset_all_sessions_to_idle()` | `_handle_reset_all_windows()` |
| PPT reset | `reset_ppt_playback()` | 按窗口消费有序 `CLOSE`、`OPEN(target_slide)` 批次 |
| 显示窗口 ID | `show_window_ids_api()` | `_handle_show_id()` |

全局 reset 会为全部窗口写入带相同 `reset_token` 的关闭批次。PPT reset 不再广播单槽 `RESET_PPT`，而是为每个当前 PPT 窗口按顺序追加 `CLOSE`、`OPEN(target_slide)`，恢复各自源与页码。单窗口播放器各自消费自己的批次；旧的单进程调试路径仍用 `reset_token` 去重，避免重复重建窗口和预热池。

## 迁移验收标准

| 项 | 标准 |
| --- | --- |
| 进程边界 | 播放器仍独立运行在活动 Windows 桌面 |
| 命令消费 | REST 写入后按目标有序领取；连续 NEXT 不丢失，终态可审计 |
| 状态回写 | 前端看到的状态来自真实 adapter |
| 四窗口 | 1-4 语义保持不变 |
| PPT | 唯一 Broker/Application；四个活动 HWND 唯一并嵌入各自 PySide 容器 |
| 直播 | MediaMTX 自动源和手动 SRT/RTSP 源均可播放 |
| 预热 | `keep_alive` 源能预热并可被前台认领 |
| 背景音频 | 播放列表、自然下一首、循环、音量、静音可用 |
| Reset | reset-all 后窗口重建；PPT reset 按窗口 CLOSE→OPEN 并恢复页码 |
| 异常 | adapter 错误能写入 `error_message` 并经 SSE 展示 |
