# 系统架构

本文说明 SCP-cv 的系统级边界、进程拓扑、核心控制流和迁移时不能破坏的架构约束。

## 设计目标

SCP-cv 面向上海第二工业大学 28#108 多媒体显示系统，目标是在一台 Windows 主机上统一控制大屏和电视窗口。

核心能力包括：

- 管理 PPT、视频、图片、网页、音频、SRT/RTSP/custom 直播流等媒体源。
- 控制四个输出窗口：大屏左、大屏右、TV 左、TV 右。
- 支持 single/double 大屏模式和固定静音策略。
- 支持背景音乐独立通道。
- 支持 Microsoft PowerPoint 作为唯一 PPT 播放、预览和导出组件。
- 支持 OBS/外部设备通过 MediaMTX SRT 推流，播放器通过 SRT/RTSP/libVLC 读取。
- 通过 Vue 控制台提供现场播控，通过 gRPC 保留外部自动化兼容能力。

## 进程拓扑

```text
Vue/Vite 控制台
  | REST / SSE / cookie session / CSRF
  v
Django Web 进程
  | 服务层写 ControlCommand / PlaybackSession / BackgroundAudioState / RuntimeState
  v
SQLite 本地数据库
  ^                                |
  | 状态和命令终态回写               | 原子领取 ControlCommand
  |                                v
PySide6 播放器进程组 ------------> 四个物理播放窗口
  |                                |
  | libVLC / Qt Multimedia          | AF_PIPE 请求
  |                                v
  |                         唯一 PowerPoint Broker / STA
  |                                |
  |                                | PowerPoint 窗口化放映 HWND 嵌入 PySide
  v                                v
MediaMTX / 本机文件 / Web / PowerPoint / 系统音频 / 物理显示器

gRPC 服务与 REST 共用同一 Django 服务层。`runall --headless` 默认按窗口启动 4 个独立 PySide 播放器进程，以隔离 Qt 和非 PPT adapter 生命周期；所有 PPT COM、Presentation、SlideShowWindow、预热和 PowerPoint 进程所有权统一收敛到一个 Broker STA。直接 `run_player --headless` 也会在多窗口参数下拆分子进程并连接或拉起 Broker，`--only-window` 只连接健康的已有 Broker。
```

## 主要进程

| 进程 | 启动入口 | 职责 | 迁移约束 |
| --- | --- | --- | --- |
| Django REST/gRPC | `manage.py runserver`, `runall.py` | API、认证、服务层、数据库状态、SSE | 可迁移到目标 Django，但服务层语义要保留 |
| Vue/Vite | `npm --prefix frontend run dev`, `runall.py` | 控制台 UI | 可迁移到目标 Vue/Fluent 应用 |
| PySide6 player | `manage.py run_player` | 读取 DB 指令、播放媒体、回写状态 | 必须继续作为桌面进程，不要放进 Web Worker |
| PowerPoint Broker | `manage.py run_ppt_broker` | 唯一 STA、共享 PowerPoint Application、四窗 PPT 会话和预热 | 必须在活动 Windows 会话中保持单实例，COM 对象不得跨进程 |
| MediaMTX | `tools/third_party/mediamtx/mediamtx.exe` | SRT 发布/读取、RTSP 暴露、路径 API | 可作为外部服务保留 |
| gRPC-Web proxy | `runall.py` | 浏览器兼容 gRPC-Web | 如目标项目不需要可停用，但 proto 契约需保留迁移说明 |

## 关键源码入口

| 领域 | 路径 |
| --- | --- |
| Django settings | `scp_cv/settings.py` |
| Django root URL | `scp_cv/urls.py` |
| REST API route table | `scp_cv/apps/dashboard/api_urls.py` |
| 播放服务 | `scp_cv/services/playback.py` |
| 持久化命令队列 | `scp_cv/services/command_queue.py`, `scp_cv/apps/playback/models/control_command.py` |
| SSE 服务 | `scp_cv/services/sse.py` |
| 媒体服务 | `scp_cv/services/media.py` |
| MediaMTX 服务 | `scp_cv/services/mediamtx.py` |
| 播放器控制器 | `scp_cv/player/controller.py`, `scp_cv/player/controller_handlers.py` |
| 播放窗口 | `scp_cv/player/window.py` |
| 播放 adapter | `scp_cv/player/adapters/` |
| PowerPoint Broker | `scp_cv/player/ppt_broker/`, `scp_cv/player/adapters/ppt_broker.py` |
| runall 编排 | `scp_cv/apps/dashboard/management/commands/runall.py` |
| run_player | `scp_cv/apps/dashboard/management/commands/run_player.py` |

## 核心控制流

```text
用户点击 Vue 控制台按钮
  -> frontend/src/services/api.ts 发 REST 请求
  -> Django api_*_views 解析请求
  -> scp_cv/services/* 校验业务规则
  -> 向目标通道追加 ControlCommand
  -> REST 返回 sessions/runtime/background_audio 快照和已接受命令 ID
  -> PlayerController 通过条件 UPDATE 原子领取最早的 pending 命令
  -> Qt 主线程执行 adapter 操作
  -> adapter 读取本机文件、网页、MediaMTX 流；PPT 请求转交唯一 Broker
  -> PlayerController 回写 playback_state/position/duration/slide/error
  -> PlayerController 把命令确认成 succeeded/failed/cancelled
  -> SSE event_stream 发现 DB 快照或命令状态变化
  -> Pinia stores 合并远端状态、命令终态并刷新 UI
```

## 状态与命令边界

| 边界 | 说明 |
| --- | --- |
| REST/gRPC 写命令 | 后端服务层把命令追加到窗口 1-4 或背景音频的 `ControlCommand` 通道，并返回命令 ID 与受理状态 |
| 播放器读命令 | `PlayerController._poll_loop()` 按目标原子领取最早的 `pending` 命令，领取后进入 `executing` |
| 播放器确认命令 | 同步 adapter 返回后确认；PPT 异步打开由回调确认，异常和取消分别写 `failed`/`cancelled` |
| 播放器写状态 | `update_playback_progress()` 和 `update_background_audio_progress()` 写 DB |
| 前端读状态 | REST 响应返回快照和本次受理命令，SSE 持续推送会话、背景音频以及未完成和近期终态命令 |

`PlaybackSession.pending_command/command_args` 与背景音频同名字段只镜像目标通道中最早的未完成命令，供一个稳定版本兼容读取；新代码不得从这些字段领取、清空或判断完成。导航命令严格追加，音量、静音和循环只合并尚未领取的同类设置，终止批次可取消未执行旧命令并给在途命令设置取消标记。

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
| PPT | `PptBrokerSourceAdapter` 经 AF_PIPE 请求唯一 Broker | Broker 的 STA 独占 COM，并把窗口化放映 HWND 嵌入对应 PySide 视频容器 |
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
- PowerPoint COM 放映、PySide6 窗口、QWebEngine、libVLC HWND 都依赖当前 Windows 用户桌面。
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
| PPT Broker | 启动唯一 Broker，等待命名管道健康检查后再启动播放器 |
| Player | 启动 PySide6 播放器，GUI 或 headless 选择显示器 |
| 监控 | 监控子进程、关闭文件、端口和异常退出 |

退出时按相反顺序停止：播放器先释放客户端会话，Broker 最后关闭自有 Presentation 和可确认归属的 PowerPoint Application。Broker 是关键进程；其异常退出会使活动 PPT 会话进入 error，并由 runall 终止整套运行时。

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
| PowerPoint COM | 不应服务端远程化 | 必须在目标播放主机的交互桌面运行 |
| MediaMTX | 独立进程 | 由 runall 或目标运维系统托管 |

## 当前已知架构限制

| 限制 | 影响 | 迁移建议 |
| --- | --- | --- |
| SQLite 队列依赖本机共享数据库 | 不适合多主机消费者 | 迁移到外部数据库时保留目标内顺序、原子领取、取消和确认语义 |
| 播放器只消费已注册窗口 | 未创建窗口的命令会保持 pending | 迁移时显式区分物理窗口和逻辑窗口，并监控目标积压 |
| 显示器选择不是实时 reposition | 修改显示目标后需 reset/restart 才稳定生效 | 接通已有 `sig_reposition` 或新增播放器命令 |
| 左右拼接主要是数据字段 | 播放窗口实际仍按单显示器定位 | 若需要真实拼接，补充窗口 geometry 计算 |
| SQLite 轻量共享 | 多主机、多并发能力有限 | 目标系统可换 PostgreSQL，但要处理轮询性能和事务语义 |
| 本地媒体路径入库 | 远端浏览器无法直接访问本机文件 | 迁移时区分媒体源注册路径和浏览器下载/预览 URL |

## 迁移时的架构验收标准

- Vue 控制台可以登录、拉取 CSRF、访问 REST、连接 SSE。
- 打开任意媒体源后，目标窗口的 `PlaybackSession` 先进入 loading，再由播放器回写 playing/error。
- 关闭媒体源后，UI 可观察到 `media_source=null`、`playback_state=idle`。
- PPT 仅使用 PowerPoint；四个播放器共用唯一 Broker/Application，每个活动会话拥有唯一放映 HWND，且父 HWND 与对应 PySide 容器一致。
- 背景音频可以加入播放列表、播放、暂停、停止、调音量、循环。
- MediaMTX 在线路径可以同步为 `StreamSource` 和 `MediaSource`。
- reset-all 可以关闭 adapter、重建窗口、清空会话状态。
- gRPC 客户端如仍需兼容，可以使用同一服务层完成 open/control/navigate/watch。
