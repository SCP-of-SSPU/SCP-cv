# 系统架构

本文说明 SCP-cv 的系统级边界、进程拓扑、核心控制流和迁移时不能破坏的架构约束。

## 设计目标

SCP-cv 面向上海第二工业大学 28#108 多媒体显示系统，目标是在一台 Windows 主机上统一控制大屏和电视窗口。

核心能力包括：

- 管理 PPT、视频、图片、网页、音频、SRT/RTSP/custom 直播流等媒体源。
- 控制四个输出窗口：大屏左、大屏右、TV 左、TV 右。
- 支持 single/double 大屏模式和固定静音策略。
- 支持背景音乐独立通道。
- 支持 PowerPoint、LibreOffice、WPS 三种 PPT 播放后端。
- 支持 OBS/外部设备通过 MediaMTX SRT 推流，播放器通过 SRT/RTSP/libVLC 读取。
- 通过 Vue 控制台提供现场播控，通过 gRPC 保留外部自动化兼容能力。

## 进程拓扑

```text
Vue/Vite 控制台
  | REST / SSE / cookie session / CSRF
  v
Django Web 进程
  | 服务层写 PlaybackSession / BackgroundAudioState / RuntimeState
  v
SQLite 本地数据库
  ^                                |
  | 状态回写                        | 轮询 pending_command
  |                                v
PySide6 播放器进程 --------------> 四个物理播放窗口
  |                                |
  | libVLC / Qt Multimedia          | Office/LibreOffice/WPS 外部放映窗口
  v                                v
MediaMTX / 本机文件 / Web / PPT 后端 / 系统音频 / 物理显示器

gRPC 服务与 REST 共用同一 Django 服务层。
```

## 主要进程

| 进程 | 启动入口 | 职责 | 迁移约束 |
| --- | --- | --- | --- |
| Django REST/gRPC | `manage.py runserver`, `runall.py` | API、认证、服务层、数据库状态、SSE | 可迁移到目标 Django，但服务层语义要保留 |
| Vue/Vite | `npm --prefix frontend run dev`, `runall.py` | 控制台 UI | 可迁移到目标 Vue/Fluent 应用 |
| PySide6 player | `manage.py run_player` | 读取 DB 指令、播放媒体、回写状态 | 必须继续作为桌面进程，不要放进 Web Worker |
| MediaMTX | `tools/third_party/mediamtx/mediamtx.exe` | SRT 发布/读取、RTSP 暴露、路径 API | 可作为外部服务保留 |
| gRPC-Web proxy | `runall.py` | 浏览器兼容 gRPC-Web | 如目标项目不需要可停用，但 proto 契约需保留迁移说明 |

## 关键源码入口

| 领域 | 路径 |
| --- | --- |
| Django settings | `scp_cv/settings.py` |
| Django root URL | `scp_cv/urls.py` |
| REST API route table | `scp_cv/apps/dashboard/api_urls.py` |
| 播放服务 | `scp_cv/services/playback.py` |
| SSE 服务 | `scp_cv/services/sse.py` |
| 媒体服务 | `scp_cv/services/media.py` |
| MediaMTX 服务 | `scp_cv/services/mediamtx.py` |
| 播放器控制器 | `scp_cv/player/controller.py`, `scp_cv/player/controller_handlers.py` |
| 播放窗口 | `scp_cv/player/window.py` |
| 播放 adapter | `scp_cv/player/adapters/` |
| runall 编排 | `scp_cv/apps/dashboard/management/commands/runall.py` |
| run_player | `scp_cv/apps/dashboard/management/commands/run_player.py` |

## 核心控制流

```text
用户点击 Vue 控制台按钮
  -> frontend/src/services/api.ts 发 REST 请求
  -> Django api_*_views 解析请求
  -> scp_cv/services/* 校验业务规则
  -> 写 PlaybackSession.pending_command 和 command_args
  -> REST 返回 sessions/runtime/background_audio 快照
  -> PlayerController 轮询 DB 发现 pending_command
  -> Qt 主线程执行 adapter 操作
  -> adapter 读取本机文件、网页、MediaMTX 流、PPT 后端
  -> PlayerController 回写 playback_state/position/duration/slide/error
  -> SSE event_stream 发现 DB 快照变化
  -> Pinia stores 合并远端状态并刷新 UI
```

## 状态与命令边界

| 边界 | 说明 |
| --- | --- |
| REST 写命令 | 后端服务层把命令写入 `PlaybackSession.pending_command` 或 `BackgroundAudioState.pending_command` |
| 播放器读命令 | `PlayerController._poll_loop()` 读取已注册窗口的 pending command |
| 播放器清命令 | 播放器发出 Qt 信号后立即清空 pending command，失败通过状态回写表达 |
| 播放器写状态 | `update_playback_progress()` 和 `update_background_audio_progress()` 写 DB |
| 前端读状态 | REST 响应直接返回快照，SSE 持续推送 `playback_state` 事件 |

当前命令总线是单字段覆盖模型，不是队列。如果同一窗口短时间内连续写入多个命令，后写命令可能覆盖前写命令。迁移时如果改为队列，需要保留现有 REST 响应和 SSE 快照语义。

## 四窗口模型

| window_id | 业务含义 | 模式关系 |
| --- | --- | --- |
| 1 | 大屏左 | single/double 均可用 |
| 2 | 大屏右 | double 可用，single 下通常被静音或隐藏在导航中 |
| 3 | TV 左 | 始终独立窗口，固定静音 |
| 4 | TV 右 | 始终独立窗口，固定静音 |

`RuntimeState.big_screen_mode` 控制大屏 single/double 模式。`apply_runtime_audio_policy()` 会强制窗口 3/4 静音，single 模式下窗口 2 也静音。

## 媒体类型边界

| 类型 | 当前播放路径 | 备注 |
| --- | --- | --- |
| PPT | `PptSourceAdapter` 路由到 PowerPoint/WPS/LibreOffice | 外部原生放映窗口铺满目标显示器 |
| video | `VideoSourceAdapter` | 本地视频使用 Qt Multimedia，不是 libVLC |
| audio | 背景音频服务和 `BackgroundAudioAdapter` | 不允许作为四窗口显示源打开 |
| image | `ImageSourceAdapter` | QPixmap 渲染到 QLabel |
| web | `WebSourceAdapter` | QWebEngineView 嵌入窗口 |
| srt_stream | `SrtStreamAdapter` | libVLC 直接 SRT 拉流 |
| rtsp_stream | `SrtStreamAdapter` | 工厂当前映射到同一 libVLC adapter |
| custom_stream | `SrtStreamAdapter` | 兼容自定义直播 URL |

## 单主机假设

SCP-cv 当前不是分布式平台，很多设计依赖单 Windows 主机：

- SQLite 文件由 Django 和播放器进程共同访问。
- `MediaSource.uri` 可以保存本机绝对路径，播放器必须能访问同一路径。
- PPT COM、WPS COM、LibreOffice 放映、PySide6 窗口、QWebEngine、libVLC HWND 都依赖当前 Windows 用户桌面。
- MediaMTX 默认同机启动，播放器默认从 `127.0.0.1` 读取 SRT/RTSP。
- 静态文件和上传媒体由 Django 本地直接 serve，未按云对象存储设计。

## 启动顺序

`runall.py` 是推荐启动入口，实际顺序是：

| 阶段 | 行为 |
| --- | --- |
| 准备 | 解析 `.env`、建立 `logs/runall/<timestamp>/`、清理继承的 `VITE_*` |
| MediaMTX | 启动 `mediamtx.exe` 并等待端口/API |
| Django | 启动后端并等待 REST 端口 |
| gRPC-Web | 按配置启动代理 |
| 状态重置 | 调用 `reset_all_sessions_to_idle()`，保证 UI 和播放器从空闲态开始 |
| Vue | 启动 Vite，必要时注入后端 target |
| Player | 启动 PySide6 播放器，GUI 或 headless 选择显示器 |
| 监控 | 监控子进程、关闭文件、端口和异常退出 |

## 认证与访问边界

| 机制 | 当前实现 |
| --- | --- |
| Web 会话 | Django session cookie |
| CSRF | `csrftoken` cookie + `X-CSRFToken` header |
| REST 全局权限 | DRF session auth + `IsAuthenticated` |
| API 中间件 | `ApiAuthMiddleware` 对 `/api/` 等路径返回 JSON 401 |
| SSE | 复用 session cookie，未登录时由中间件拒绝 |
| gRPC | `GrpcAuthInterceptor` 从 metadata/cookie 恢复 Django session |

## 可迁移模块与不可合并模块

| 模块 | 可否直接并入目标 Django | 建议 |
| --- | --- | --- |
| Django models | 可以 | 保留 migration 历史或编写数据迁移脚本 |
| Django services | 可以 | 优先原样迁移，再按目标项目分层改造 |
| REST views/routes | 可以 | 路径可加前缀，但前端 API 类型要同步 |
| SSE | 可以 | 如目标已有实时通道，可封装为兼容 `playback_state` 事件 |
| gRPC servicers | 视需求 | 外部中控依赖时必须保留 |
| PySide6 player | 不应并入 Web Worker | 继续作为独立桌面进程，最多抽象启动/监控接口 |
| Office/WPS COM | 不应服务端远程化 | 必须在目标播放主机的交互桌面运行 |
| MediaMTX | 独立进程 | 由 runall 或目标运维系统托管 |

## 当前已知架构限制

| 限制 | 影响 | 迁移建议 |
| --- | --- | --- |
| `pending_command` 是单字段 | 连续命令可能覆盖 | 队列化或增加 command version |
| 播放器只轮询已注册窗口 | 未创建窗口的命令会残留 | 迁移时显式区分物理窗口和逻辑窗口 |
| 显示器选择不是实时 reposition | 修改显示目标后需 reset/restart 才稳定生效 | 接通已有 `sig_reposition` 或新增播放器命令 |
| 左右拼接主要是数据字段 | 播放窗口实际仍按单显示器定位 | 若需要真实拼接，补充窗口 geometry 计算 |
| SQLite 轻量共享 | 多主机、多并发能力有限 | 目标系统可换 PostgreSQL，但要处理轮询性能和事务语义 |
| 本地媒体路径入库 | 远端浏览器无法直接访问本机文件 | 迁移时区分媒体源注册路径和浏览器下载/预览 URL |

## 迁移时的架构验收标准

- Vue 控制台可以登录、拉取 CSRF、访问 REST、连接 SSE。
- 打开任意媒体源后，目标窗口的 `PlaybackSession` 先进入 loading，再由播放器回写 playing/error。
- 关闭媒体源后，UI 可观察到 `media_source=null`、`playback_state=idle`。
- PPT 后端选择可以保存在媒体源，也可以在当前播放时临时切换并回到原页。
- 背景音频可以加入播放列表、播放、暂停、停止、调音量、循环。
- MediaMTX 在线路径可以同步为 `StreamSource` 和 `MediaSource`。
- reset-all 可以关闭 adapter、重建窗口、清空会话状态。
- gRPC 客户端如仍需兼容，可以使用同一服务层完成 open/control/navigate/watch。
