# 后端服务设计

本文说明 SCP-cv Django 后端的配置、路由、服务层和关键业务模块。迁移到目标 Django 项目时，应优先迁移服务层语义，再调整 URL、权限和项目结构。

## 后端模块结构

| 路径 | 职责 |
| --- | --- |
| `scp_cv/settings.py` | Django、REST、gRPC、MediaMTX、PPT、日志、静态媒体配置 |
| `scp_cv/urls.py` | root URL，挂载 admin、REST、dashboard、static/media |
| `scp_cv/apps/dashboard/api_urls.py` | REST API 路由表 |
| `scp_cv/apps/dashboard/api_views.py` | 媒体、设备、SSE 等普通 API |
| `scp_cv/apps/dashboard/api_playback_views.py` | 播放、显示、音量、reset、关机 API |
| `scp_cv/apps/dashboard/api_auth_views.py` | session 登录、退出、CSRF、当前用户 |
| `scp_cv/apps/dashboard/api_utils.py` | JSON、错误、请求解析、`mutate_playback()` |
| `scp_cv/services/` | 主要业务逻辑，迁移时应保留为后端核心层 |
| `scp_cv/grpc_servicers/` | gRPC 兼容接口，委托服务层 |

## settings 设计

`scp_cv/settings.py` 的关键点：

| 配置 | 当前值或行为 | 迁移注意 |
| --- | --- | --- |
| `INSTALLED_APPS` | Django built-ins、DRF、django-socio-grpc、dashboard、playback、streams | 目标项目要合并 app 或保留 namespace |
| `MIDDLEWARE` | CORS、Security、Session、Common、CSRF、Auth、`ApiAuthMiddleware` | API 401 行为依赖自定义中间件 |
| REST auth | SessionAuthentication + `IsAuthenticated` | 前端依赖 cookie session 和 CSRF |
| DB | SQLite `BASE_DIR / db.sqlite3` | 可换 DB，但播放器轮询语义要重新验证 |
| static/media | 本地目录，开发时直接 serve | 生产化时需明确媒体 URL 和本机播放器路径关系 |
| gRPC | django-socio-grpc async server，100 MiB 消息限制 | 外部中控依赖时保留 |
| MediaMTX | SRT/RTSP/API host/port、publish/read latency | 现场网络参数不要硬编码进 UI |
| VLC stream | libVLC caching、clock、drop/skip frame 参数 | 直播延迟和稳定性依赖这些参数 |
| LibreOffice | bin path、connect timeout、bridge timeout | 目标部署机需可找到 LibreOffice |
| PPT preview/export | worker/export timeout | 大 PPT 导入性能和失败降级依赖 |
| logging | `logs/app/scp-cv.log` rotating log | 迁移到统一日志系统时保留现场诊断字段 |

## URL 设计

`scp_cv/urls.py` 挂载：

| URL | 说明 |
| --- | --- |
| `/admin/` | Django admin |
| `/api/` | REST API，来自 `scp_cv.apps.dashboard.api_urls` |
| `/` | dashboard 页面路由，来自 `scp_cv.apps.dashboard.urls` |
| `/static/`, `/media/` | 本地静态和媒体文件 serve |

这体现单机桌面工具假设。迁移到目标生产项目时，可以改为由 Nginx 或对象存储服务媒体文件，但播放器仍需要本机可访问路径或新的媒体拉取机制。

## REST 路由分组

路由表：`scp_cv/apps/dashboard/api_urls.py`

| 分组 | 典型 endpoint | 服务层 |
| --- | --- | --- |
| Auth | `auth/csrf/`, `auth/login/`, `auth/logout/`, `auth/me/` | Django auth |
| Folders | `folders/`, `folders/<folder_id>/` | `services.media` |
| Sources | `sources/`, `sources/upload/`, `sources/local/`, `sources/web/`, `sources/<source_id>/...` | `services.media`, PPT services |
| Sessions | `sessions/`, `sessions/<window_id>/`, `runtime/` | `services.playback` |
| Playback | `playback/<window_id>/open/`, `control/`, `navigate/`, `ppt-media/`, `ppt-backend/`, `close/`, `loop/`, `volume/`, `mute/` | `services.playback`, `services.playback_window_controls` |
| Global playback | `playback/show-ids/`, `reset-all/`, `reset-ppt/`, `physical-smoke/` | `services.playback`, `services.physical_smoke` |
| Audio | `background-audio/...` | `services.background_audio` |
| Displays | `displays/`, `displays/select/` | `services.display`, `services.playback` |
| Devices | `devices/`, `devices/<device_type>/toggle/`, `devices/<device_type>/power/<action>/` | `services.device` |
| Scenarios | `scenarios/`, `capture/`, `<id>/activate/`, `<id>/pin/` | `services.scenario` |
| Realtime | `events/` | `services.sse` |
| System | `system/shutdown/`, `volume/` | `runall` shutdown file, `services.volume` |

## API helper 约定

`scp_cv/apps/dashboard/api_utils.py` 提供统一 REST 辅助：

| 函数 | 作用 |
| --- | --- |
| `success_response()` | 返回 `success=true` JSON |
| `error_response()` | 返回 `detail` 和 `code` |
| `parse_json_body()` | 解析 JSON 请求 |
| `parse_window_id()` | 校验窗口 ID |
| `mutate_playback(operation)` | 执行业务变更，刷新 sessions/background_audio，发布 SSE，并返回统一快照 |

迁移时应保留 `mutate_playback()` 的思想：所有会影响播放状态的 REST 变更，都应让响应包含最新状态快照，并触发实时通知。

## 认证服务

文件：`scp_cv/apps/dashboard/api_auth_views.py`

| endpoint | 行为 |
| --- | --- |
| `csrf_token_api()` | 设置 CSRF cookie，返回 token |
| `login_api()` | `csrf_exempt`，用户名密码认证，调用 Django `login()`，确保 CSRF cookie |
| `logout_api()` | 幂等退出，`csrf_exempt` |
| `me_api()` | 返回当前用户，未登录返回 401 |

`scp_cv/auth_middleware.py` 的 `ApiAuthMiddleware` 会保护 `/api/`、`/sources/`、`/playback/`、`/scenarios/`、`/events/` 等路径，未登录时返回 JSON 401，而不是重定向 HTML 登录页。

## 播放服务

文件：`scp_cv/services/playback.py`

核心职责：

| 函数 | 语义 |
| --- | --- |
| `get_or_create_session()` | 确保窗口会话存在 |
| `get_all_sessions_snapshot()` | 返回四窗口快照 |
| `get_runtime_snapshot()` | 返回大屏模式、音量、静音窗口 |
| `set_big_screen_mode()` | 校验并设置 single/double，调用视频墙模式服务并应用静音策略 |
| `apply_runtime_audio_policy()` | 强制窗口 3/4 静音，single 下窗口 2 静音 |
| `open_source()` | 校验源、拒绝 audio 四窗口播放、准备 PPT playback URI、写 `OPEN` 指令 |
| `switch_ppt_backend()` | 当前 PPT 重新打开为新后端，并回到当前页 |
| `reset_ppt_playback()` | 关闭所有 PPT adapter，再按原源和页码重开 |
| `control_playback()` | play/pause/stop |
| `navigate_content()` | PPT next/prev/goto，视频 seek |
| `control_ppt_media()` | 当前 PPT 页面嵌入媒体控制 |
| `close_source()` | 写关闭指令，UI 立即可见 idle，同时保留播放器清理参数 |
| `reset_all_sessions_to_idle()` | 重置会话并请求播放器窗口重建 |
| `update_playback_progress()` | 播放器进程回写状态 |
| `select_display_target()` | 选择目标显示器或拼接目标 |

关键业务规则：

- `VALID_WINDOW_IDS` 来自 `playback_sessions`，当前固定为 1-4。
- `SourceType.AUDIO` 不允许打开到四个显示窗口，只能走背景音乐。
- PPT 打开会解析 `ppt_backend`，并优先使用 `resolve_ppt_playback_uri()` 返回的 `.ppsx/.pps` 播放缓存。
- 关闭时如旧源是临时源，会通过 `cleanup_source_id` 触发清理。
- 运行态静音策略不是前端 UI 规则，而是后端写入每个 session 的业务规则。

## 媒体服务

文件：`scp_cv/services/media.py`

核心职责：

| 函数 | 语义 |
| --- | --- |
| `add_uploaded_file()` | 保存上传文件，识别类型，创建 `MediaSource`，准备 PPT 资源和缓存 |
| `add_local_path()` | 注册本机绝对路径，创建 `MediaSource` |
| `add_web_source()` | 创建网页源 |
| `update_media_source()` | 修改源信息、文件夹、PPT 后端、预热等 |
| `delete_media_source()` | 删除源并清理背景音频引用、PPT 缓存、上传文件、PPT 预览资源 |
| `delete_temporary_source_if_unused()` | 清理未被使用的临时源 |
| `cleanup_expired_temporary_sources()` | 扫描过期临时源 |
| `sync_streams_to_media_sources()` | 把 `StreamSource` 同步为流媒体 `MediaSource` |
| `list_ppt_resources()` | 读取或补齐 PPT 页资源 |
| `replace_ppt_resources()` | 覆盖保存 PPT 页资源 |

迁移注意：

- 上传文件保存到 `media/uploads/%Y%m%d/`。
- PPT 源创建后会调用 `prepare_ppt_source_resources()` 和 `prepare_ppt_playback_cache()`。
- 删除 PPT 源时必须清理 `media/ppt_previews/<source_id>/` 和 `media/ppt_playback/<source_id>/`。
- 流媒体源的可用性来自 MediaMTX 同步，不应由前端手动维护。

## PPT 资源和播放缓存

| 文件 | 职责 |
| --- | --- |
| `scp_cv/services/ppt_resources.py` | 从 PPTX zip 解析页数、备注、媒体关系；导出 PNG 预览；维护 `PptResource` |
| `scp_cv/services/ppt_preview.py` | 通过独立 worker 调用 PowerPoint/WPS/LibreOffice 导出 PNG 预览 |
| `scp_cv/services/ppt_preview_worker.py` | 隔离预览导出副作用 |
| `scp_cv/services/ppt_playback_cache.py` | 生成播放专用 `.ppsx/.pps` 缓存并写入 `MediaSource.metadata.ppt_playback` |
| `scp_cv/services/ppt_playback_export.py` | PowerPoint/WPS COM 和 LibreOffice headless 导出 show-format 文件 |
| `scp_cv/ppt_backend.py` | PPT 后端常量、默认值和规范化 |

PPT 资源处理是容错设计：zip 解析失败时仍会尝试导出预览；预览或播放缓存失败不会阻止媒体源创建，只会写 metadata 错误并在播放时回退原始文件。

## 背景音频服务

文件：`scp_cv/services/background_audio.py`

核心职责：

| 函数 | 语义 |
| --- | --- |
| `add_source_to_playlist()` | 校验 audio 源并加入播放列表，避免重复 |
| `play_source()` | 加入并立即播放音频源 |
| `play_playlist_item()` | 播放指定播放列表项 |
| `resume_background_audio()` | 恢复当前音频或播放列表首项 |
| `pause_background_audio()` | 写 `PAUSE` 命令 |
| `stop_background_audio()` | 停止，必要时清空当前源和清理临时源 |
| `seek_background_audio()` | 写 seek 命令 |
| `play_next_background_audio()` | 下一首 |
| `play_previous_background_audio()` | 上一首 |
| `set_background_audio_volume()` | 背景音量 |
| `set_background_audio_mute()` | 背景静音 |
| `set_background_audio_loop()` | 列表循环 |
| `advance_background_audio_on_finished()` | 自然结束后推进下一首，循环时回到首项 |
| `handle_media_source_deleted()` | 删除音频源前清理引用 |

背景音频与四窗口播放并列存在，前端和 SSE 快照都需要同时包含 `sessions` 与 `background_audio`。

## MediaMTX 与直播服务

文件：`scp_cv/services/mediamtx.py`

核心职责：

| 函数 | 语义 |
| --- | --- |
| `get_srt_publish_url()` | 给 OBS/外部设备展示 SRT 推流地址，latency 按微秒 |
| `get_srt_read_url()` | 给播放器展示 SRT 拉流地址，latency 按毫秒 |
| `get_rtsp_read_url()` | 生成 RTSP 拉流地址 |
| `start_mediamtx()` | 启动 `mediamtx.exe` 和同目录 `mediamtx.yml` |
| `stop_mediamtx()` | 停止本进程持有的 MediaMTX |
| `is_mediamtx_running()` | 优先检查进程，再检查 API |
| `query_stream_paths()` | 调用 `/v3/paths/list` |
| `sync_stream_states()` | 自动注册新路径，更新 online/offline 和 last_seen |

`scp_cv/apps/streams/models.py` 的 `StreamSource` 保存 MediaMTX path 状态。`list_sources_api()` 每次列源会先同步流状态，再同步为 `MediaSource`。

## 显示器服务

文件：`scp_cv/services/display.py`

主要功能：

- 使用 `screeninfo.get_monitors()` 枚举物理显示器。
- 构建 display label，供前端选择和 session 保存。
- 构建左右拼接目标标签。
- 提供 `list_display_targets()` 和 `find_display_target()`。

当前限制：显示器选择写入 DB 后，运行中的播放器不会自动 reposition。迁移时如果目标项目要求在线切屏，需要新增播放器命令或接通 `PlayerController.sig_reposition`。

## 设备控制服务

文件：`scp_cv/services/device.py`

当前是静态 TCP hex 帧控制，不保存设备状态，也不读取设备返回。

| 设备 | IP:Port | 行为 |
| --- | --- | --- |
| 拼接屏 | `192.168.5.10:8889` | 支持开机、关机 |
| 电视左 | `192.168.5.161:8889` | 支持 toggle |
| 电视右 | `192.168.5.162:8889` | 支持 toggle |

迁移时如果目标项目已有设备管理模块，可以把这些静态定义迁入配置表，但要保持原 API 返回中 `detail=电源指令已发送，未读取设备返回` 的语义，避免用户误以为 UI 展示的是真实设备状态。

## 系统音量服务

文件：`scp_cv/services/volume.py`

职责：

- 优先调用 Windows Core Audio 获取和设置系统主音量。
- 失败时回退 `RuntimeState.volume_level` 与 `volume_muted`。
- REST `/api/volume/` 给前端提供系统级音量控制。

系统音量和窗口音量不同：系统音量影响整机输出；窗口音量写 `PlaybackSession.volume` 并由 adapter 执行。

## 物理冒烟测试服务

文件：`scp_cv/services/physical_smoke.py`

`run_physical_smoke_test()` 会真实下发播放、关闭和 reset 指令，不是单元测试 mock。

测试顺序：

| 阶段 | 行为 |
| --- | --- |
| 解析窗口 | 默认 1-4，校验窗口合法 |
| 解析源 | 每种类型优先使用显式 source_id，否则选择最新可用源 |
| 四窗口播放 | 对 image/video/web/ppt/srt/custom/rtsp 逐窗口打开并等待 playing |
| 背景音频 | 打开 audio 源并等待背景音乐 playing |
| 重置 | 默认执行 reset-all 并停止背景音频 |

默认超时：普通源 30 秒，PPT 120 秒，流媒体 45 秒，总播放阶段 540 秒。迁移验收时，这是最接近现场真实播放链路的后端入口。

## runall 编排服务

文件：`scp_cv/apps/dashboard/management/commands/runall.py`

职责：

- 启动 MediaMTX、gRPC-Web、Django、Vite、PySide6 播放器。
- 创建每次运行日志目录。
- 等待端口就绪。
- 监控必需进程，异常退出时清理进程树。
- 启动前重置播放状态。
- 在 `--service` 模式下把真实 runall 拉起到当前登录用户交互桌面。

重要行为：

- `runall` 会移除父进程继承的 `VITE_*` 变量。
- 如果 `frontend/.env` 没有 `VITE_BACKEND_TARGET`，才按后端监听地址注入兜底值。
- `logs/runall.shutdown` 是系统关闭 API 和 runall 监控之间的文件信号。
- headless player 如果不在活动桌面会话中启动，会提示使用 `--headless --service`。

## 后端迁移建议

- 先迁移 `apps/playback/models` 和 `apps/streams/models`，保证数据契约存在。
- 再迁移 `services/`，避免把业务逻辑散落到新项目 views 中。
- REST URL 可以增加前缀，但应给前端集中配置，不要让页面组件硬编码路径。
- 若目标项目已有认证体系，保留 JSON 401 和 CSRF/session 兼容层，前端才能平滑迁移。
- 若目标项目使用 Celery 或消息队列，可以把耗时 PPT 预览/导出迁移为任务，但要保留失败不阻断媒体源创建的容错语义。
- 设备 IP、MediaMTX host、LibreOffice path、VLC runtime path 应配置化，不要继续散落硬编码。
- 所有写播放状态的 API 都应返回最新 `sessions` 和 `background_audio`，否则前端会出现本地状态与 SSE 状态抖动。
