# 播放器与媒体运行时设计

本文说明 PySide6 播放器、媒体 adapter、PowerPoint PPT、预热、状态回写和四窗口运行时。该部分是迁移中最不适合并入 Django Web Worker 的模块。

最后更新：2026-06-10。

## 运行时定位

播放器是独立 Windows 桌面进程，负责把后端会话表中的命令转成真实窗口、PowerPoint、QMediaPlayer、QWebEngine 和 libVLC 操作。

```text
Django 服务层
  -> PlaybackSession.pending_command / command_args
  -> PySide6 PlayerController 轮询
  -> Qt 主线程执行 adapter 命令
  -> AdapterState 写回 PlaybackSession
  -> SSE 轮询 DB 推送到 Vue
```

迁移时必须保持以下边界：

| 边界 | 原因 |
| --- | --- |
| 播放器独立进程 | Qt GUI、QWebEngine、libVLC HWND、Office COM 需要活动桌面 |
| 命令从 DB 或等价总线读取 | Django 和播放器是不同进程 |
| adapter 在 Qt 主线程执行 | Qt 对象、COM 和窗口句柄不能随意跨线程调用 |
| 状态由播放器写回 | 前端看到的播放状态应来自真实播放器，不是 REST 乐观值 |

## 启动入口

| 文件 | 责任 |
| --- | --- |
| `scp_cv/apps/dashboard/management/commands/run_player.py` | 播放器独立启动命令 |
| `scp_cv/apps/dashboard/management/commands/runall.py` | 全栈编排并启动播放器子进程 |
| `scp_cv/player/launcher_gui.py` | GUI 启动器，选择窗口和显示器 |
| `scp_cv/player/headless_launcher.py` | 无 GUI/headless 窗口映射 |
| `scp_cv/player/gpu.py` | GPU 选择辅助 |

`run_player` 的关键流程：

| 步骤 | 行为 |
| --- | --- |
| 1 | 创建 `QApplication` |
| 2 | GUI 模式打开 launcher，headless 模式从 `--window1` 到 `--window4` 构造映射 |
| 3 | 多窗口启动会拆成每窗口一个 `run_player --only-window` 子进程，隔离 PowerPoint COM 生命周期 |
| 4 | 单窗口进程创建 `PlayerController` |
| 5 | 为本窗口映射创建 `PlayerWindow` |
| 6 | 写入 `PlaybackSession.target_display_label` |
| 7 | `position_on_display()` 定位窗口 |
| 8 | `controller.apply_current_layout()` 应用布局 |
| 9 | `controller.preheat_sources()` 预热 |
| 10 | `controller.start_polling()` 开始轮询 |

通过 SSH、Windows 服务或非控制台会话启动时，播放器无法可靠访问物理显示器。此时应使用 `runall --headless --service`，让真实运行发生在当前登录用户的交互桌面中。

## PlayerController

主文件：`scp_cv/player/controller.py`。

| 成员 | 说明 |
| --- | --- |
| `_windows` | `window_id -> PlayerWindow` |
| `_adapters` | `window_id -> SourceAdapter` |
| `_adapter_source_ids` | 防止旧 adapter 状态覆盖新 source |
| `_preheat_pool` | 统一预热池 |
| `_background_audio_adapter` | 全局背景音频 adapter |
| `_last_reported_states` | 状态签名去重 |
| `sig_dispatch_command` | 后台轮询线程到 Qt 主线程的命令信号 |

轮询线程约 0.2 秒一轮，读取 `PlaybackSession.pending_command`。发现命令后会发射 Qt signal，并立即清空 pending command。执行失败不会恢复 pending command，而是通过 `playback_state=error` 和 `error_message` 写回。

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

打开新源时，播放器会尽量在新内容可见后再关闭旧 adapter，减少黑屏。若旧源是 PPT，控制器会先隐藏已嵌入的 PowerPoint 放映子窗口，让 PySide 容器立即接管；新源打开成功后再通过 Qt 下一轮事件循环关闭旧 PPT，打开失败时恢复旧 PPT 子窗口。

## PlayerWindow

文件：`scp_cv/player/window.py`。

`PlayerWindow` 是每个物理输出窗口的容器。正常模式下无边框并置顶，debug 模式下可移动和调整。

| 结构 | 用途 |
| --- | --- |
| 黑屏 label | 空闲、关闭、切换时的背景 |
| video viewport/container | 图片、本地视频、libVLC、PPT 嵌入容器 |
| web viewport/container | QWebEngineView 页面 |
| ID overlay | `show-id` 时显示窗口编号 |

`position_on_display()` 通过 Qt screen geometry 和 overlap 匹配屏幕。它能处理部分 DPI/坐标差异，但前提是 Windows 能正确枚举物理显示器。

已知限制：`PlayerController.sig_reposition` 存在但没有接线；REST 修改显示目标后不会让运行中的窗口立即移动。`left_right_splice` 在数据层存在，但播放器当前仍按单个显示器定位。

## Adapter 工厂

工厂位于 `scp_cv/player/adapters/__init__.py`。

| source_type | Adapter | 技术栈 |
| --- | --- | --- |
| `ppt` | `PptSourceAdapter` | PowerPoint COM |
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

## PowerPoint PPT

PPT 适配器文件：`scp_cv/player/adapters/ppt.py`。

| 能力 | 文件 |
| --- | --- |
| PowerPoint COM 放映 | `scp_cv/player/adapters/ppt.py` |
| 放映 HWND 查找、嵌入和尺寸同步 | `scp_cv/player/adapters/ppt_window.py` |
| PPT 切源容器准备和恢复 | `scp_cv/player/controller_window_helpers.py` |
| 当前页媒体控制 | `scp_cv/player/adapters/ppt_media.py` |

PowerPoint 播放只支持 COM 窗口化放映。适配器配置 `ppShowTypeWindow` 后调用 `SlideShowSettings.Run()`，读取 `SlideShowWindow.HWND`，再通过 Win32 `SetParent()` 嵌入目标 `PlayerWindow.video_window_handle`。嵌入时会移除顶层/弹出窗口样式，添加 `WS_CHILD | WS_VISIBLE`，清理 topmost/appwindow 扩展样式，并填满 PySide 视频容器。

| 后端 | 媒体控制 |
| --- | --- |
| PowerPoint | `scp_cv/player/adapters/ppt_media.py` 控制当前页 shape |

PPT 全局 volume/mute 大多不可控。窗口音量 UI 对 PPT 不应承诺等价于视频音量。

PowerPoint 启动、打开文档、运行放映、HWND 查找和嵌入都带确定性重试或明确失败路径；失败时保留 PySide 黑屏并回写明确错误，不回退到其它后端。播放器不再隐藏 PySide 窗口，不取消 PySide 置顶，也不最小化其它顶层窗口。

## PPT 资源、预览和播放缓存

PPT 后端不仅有播放 adapter，还有导入阶段的资源解析和缓存。

| 文件 | 责任 |
| --- | --- |
| `scp_cv/services/ppt_resources.py` | 解析 OOXML、生成 `PptResource`、提取媒体列表和 speaker notes |
| `scp_cv/services/ppt_preview.py` | 通过 worker 导出 slide PNG 预览 |
| `scp_cv/services/ppt_preview_worker.py` | 预览导出子进程入口 |
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
| PowerPoint | 预启动 COM 应用，必要时预打开文件 |

预热不是缓存业务状态，而是缓存播放器资源。迁移时不要把 `keep_alive` 简化为普通后端缓存字段。

## 背景音频

服务层：`scp_cv/services/background_audio.py`。

| 文件 | 责任 |
| --- | --- |
| `scp_cv/player/background_audio_handlers.py` | 读取并执行背景音频命令 |
| `scp_cv/player/adapters/background_audio.py` | `QMediaPlayer + QAudioOutput` 播放器 |

背景音频有独立的 `BackgroundAudioState` 和播放列表，不占用 `window_id` 1-4。音频源不能直接打开到显示窗口。

自然播放结束后，播放器通知服务层推进下一首。循环开启时会回到第一首。

## Reset 和 Show ID

| 功能 | 服务层 | 播放器侧 |
| --- | --- | --- |
| 全局 reset | `reset_all_sessions_to_idle()` | `_handle_reset_all_windows()` |
| PPT reset | `reset_ppt_playback()` | `_handle_reset_ppt()` |
| 显示窗口 ID | `show_window_ids_api()` | `_handle_show_id()` |

全局 reset 会向全部窗口写入带相同 `reset_token` 的 `CLOSE` + `{reset_all_windows: true}`。单窗口播放器各自消费自己的重置指令；旧的单进程调试路径会用 `reset_token` 去重，避免重复重建窗口和预热池。

## 迁移验收标准

| 项 | 标准 |
| --- | --- |
| 进程边界 | 播放器仍独立运行在活动 Windows 桌面 |
| 命令消费 | REST 写入命令后播放器能在 1 秒内消费 |
| 状态回写 | 前端看到的状态来自真实 adapter |
| 四窗口 | 1-4 语义保持不变 |
| PPT | PowerPoint-only，窗口化放映 HWND 嵌入 PySide 视频容器 |
| 直播 | MediaMTX 自动源和手动 SRT/RTSP 源均可播放 |
| 预热 | `keep_alive` 源能预热并可被前台认领 |
| 背景音频 | 播放列表、自然下一首、循环、音量、静音可用 |
| Reset | reset-all 后窗口重建且会话回 idle |
| 异常 | adapter 错误能写入 `error_message` 并经 SSE 展示 |
