# 数据模型

本文说明 SCP-cv 的持久化模型、状态枚举和迁移时必须保持的字段语义。当前数据库默认是 `db.sqlite3`，模型定义集中在 `scp_cv/apps/playback/models/` 和 `scp_cv/apps/streams/models.py`。

## 模型总览

| 模型 | 路径 | 职责 |
| --- | --- | --- |
| `MediaFolder` | `scp_cv/apps/playback/models/media.py` | 媒体文件夹树，当前 UI 已弱化但 API 仍支持 |
| `MediaSource` | `scp_cv/apps/playback/models/media.py` | 所有可播放媒体源的统一注册表 |
| `PptResource` | `scp_cv/apps/playback/models/media.py` | PPT 页资源、预览图、备注、嵌入媒体清单 |
| `PlaybackSession` | `scp_cv/apps/playback/models/session.py` | 四个播放窗口的命令和状态表 |
| `RuntimeState` | `scp_cv/apps/playback/models/runtime.py` | 全局大屏模式和系统音量状态 |
| `Scenario` | `scp_cv/apps/playback/models/scenario_models.py` | 预案和四窗口快照 |
| `BackgroundAudioState` | `scp_cv/apps/playback/models/background_audio.py` | 背景音频命令和状态单例 |
| `BackgroundAudioPlaylistItem` | `scp_cv/apps/playback/models/background_audio.py` | 背景音频播放列表 |
| `StreamSource` | `scp_cv/apps/streams/models.py` | MediaMTX 自动发现的外部推流记录 |
| `DeviceEndpoint` | `scp_cv/apps/playback/models/device.py` | 已废弃 unmanaged 占位，保留给历史迁移兼容 |

## 枚举

路径：`scp_cv/apps/playback/models/enums.py`

| 枚举 | 值 | 语义 |
| --- | --- | --- |
| `SourceType` | `ppt`, `video`, `audio`, `image`, `web`, `custom_stream`, `rtsp_stream`, `srt_stream` | 媒体源类型，前端筛选、服务校验和 adapter 工厂都依赖这些值 |
| `PlaybackMode` | `single`, `left_right_splice` | 会话显示模式，拼接字段当前偏数据语义 |
| `BigScreenMode` | `single`, `double` | 大屏单/双画面运行模式 |
| `PlaybackState` | `idle`, `loading`, `playing`, `paused`, `stopped`, `error` | 前端、服务层、播放器共同使用的播放状态 |
| `PlaybackCommand` | `open`, `play`, `pause`, `stop`, `close`, `seek`, `next`, `prev`, `goto`, `set_loop`, `set_volume`, `set_mute`, `ppt_media`, `reset_ppt`, `show_id` | 四窗口命令 |
| `BackgroundAudioCommand` | `open`, `play`, `pause`, `stop`, `seek`, `next`, `prev`, `set_loop`, `set_volume`, `set_mute` | 背景音频命令 |
| `SourceState` | `unset`, `empty`, `set` | 预案 tri-state，区分不修改、清空、设置 |
| `DeviceType` | `splice_screen`, `tv_left`, `tv_right` | 物理电源控制设备类型 |

迁移时不要随意改枚举字符串。前端 API 类型、OpenAPI、gRPC 兼容层、历史数据和场景 JSON 都依赖字符串值。

## `MediaFolder`

`MediaFolder` 是自引用目录树，用于老版本媒体分类。

关键字段：

| 字段 | 语义 |
| --- | --- |
| `name` | 文件夹名 |
| `parent` | 上级文件夹，可空 |
| `created_at`, `updated_at` | 审计时间 |

当前 `frontend/src/stores/sources.ts` 注释说明：文件夹概念已不再暴露在主要 UI 中，但 REST API 仍保留 `folders/`、`sources/<source_id>/move/` 等能力。迁移时如目标项目没有文件夹 UI，可以保留模型和 API 兼容，暂不把它作为核心信息架构。

## `MediaSource`

`MediaSource` 是最重要的数据模型，代表所有可播放内容。

关键字段：

| 字段 | 语义 | 迁移注意 |
| --- | --- | --- |
| `source_type` | 媒体类型 | 必须匹配 `SourceType` |
| `name` | UI 显示名 | 前端按中文 collator 排序 |
| `uri` | 播放 URI 或本机路径 | 播放器进程必须可访问 |
| `uploaded_file` | Django 上传文件 | 删除源时要清理文件 |
| `stream_identifier` | MediaMTX path 名 | 用于流同步和在线状态映射 |
| `is_available` | 是否可用 | 流离线时会置 false |
| `folder` | 所属文件夹 | 当前 UI 可忽略但数据保留 |
| `original_filename` | 原始文件名 | 下载和展示使用 |
| `file_size` | 文件大小 | 上传源统计 |
| `mime_type` | MIME | UI 和下载辅助 |
| `is_temporary` | 临时源 | 关闭/过期后会自动清理 |
| `expires_at` | 临时源过期时间 | `cleanup_expired_temporary_sources()` 使用 |
| `metadata` | JSON 扩展信息 | PPT 解析、播放缓存、流信息都写入此字段 |
| `keep_alive` | 是否预热 | 播放器启动后预热池读取 |
| `created_at` | 创建时间 | 前端最新源、冒烟测试默认源选择依赖 |

`MediaSource.uri` 当前可能是：

| 类型 | URI 形态 |
| --- | --- |
| 上传文件 | `MEDIA_ROOT` 下文件的绝对路径 |
| 本机路径 | 用户注册的 Windows 绝对路径 |
| Web | `http://` 或 `https://` URL |
| SRT | `srt://host:port?streamid=...` |
| RTSP | `rtsp://host:8554/<stream_identifier>` |
| custom stream | libVLC 可读取的自定义 URL |
| PPT | 原始 PPT 路径，播放时可由 `resolve_ppt_playback_uri()` 替换为 `.ppsx/.pps` 缓存 |

迁移到多主机或容器后，必须重新设计 `uri` 的可访问性。当前系统假设 Django、播放器和媒体文件在同一 Windows 主机上。

## `PptResource`

`PptResource` 存储 PPT 页面级资源。

关键字段：

| 字段 | 语义 |
| --- | --- |
| `source` | 所属 PPT 媒体源 |
| `page_index` | 1-based 页码 |
| `slide_image` | PNG 预览图 URL 或路径 |
| `speaker_notes` | 备注文本 |
| `media_items` | 页面内音视频对象 JSON |
| `created_at` | 创建时间 |

约束和派生属性：

| 项 | 说明 |
| --- | --- |
| 唯一约束 | `(source, page_index)` 唯一 |
| `has_media` | `media_items` 非空 |
| `next_slide_image` | 当前源下一页预览图，前端 PPT focus/控制使用 |

`media_items` 的规范化字段来自 `scp_cv/services/ppt_resources.py`：

| 字段 | 语义 |
| --- | --- |
| `id` | 前端和控制命令引用 ID，例如 `page-1-media-1` |
| `media_index` | 页面内媒体顺序，从 1 开始 |
| `media_type` | `audio`、`video` 或 `unknown` |
| `name` | 文件名或显示名 |
| `target` | PPT 内部关系目标 |
| `shape_id` | 可手工修正的 shape id，0 表示未知 |

## `PlaybackSession`

`PlaybackSession` 是四窗口命令总线和状态表。

关键字段：

| 字段 | 语义 | 写入方 |
| --- | --- | --- |
| `window_id` | 逻辑窗口 ID，唯一 | 初始化和服务层 |
| `media_source` | 当前媒体源 | 后端服务层和关闭逻辑 |
| `playback_state` | UI 可见状态 | 服务层初始化，播放器回写 |
| `error_message` | 错误说明 | 播放器回写，服务层清空 |
| `display_mode` | 单窗口或左右拼接 | 显示选择服务 |
| `target_display_label` | 目标显示器标签 | run_player 和显示选择服务 |
| `spliced_display_label` | 拼接目标标签 | 显示选择服务 |
| `is_spliced` | 是否拼接 | 显示选择服务 |
| `current_slide` | PPT 当前页，1-based | 播放器回写 |
| `total_slides` | PPT 总页数 | 播放器回写 |
| `position_ms` | 视频/音频/流进度 | 播放器回写 |
| `duration_ms` | 视频/音频总时长 | 播放器回写 |
| `volume` | 窗口音量 0-100 | REST 窗口控制 |
| `is_muted` | 窗口静音 | 运行策略和窗口控制 |
| `loop_enabled` | 循环播放 | REST 窗口控制 |
| `pending_command` | 待执行命令 | 后端服务层 |
| `command_args` | 命令 JSON 参数 | 后端服务层 |
| `last_updated_at` | 更新时间 | Django auto_now |

命令写入示例：

| 命令 | 关键 `command_args` |
| --- | --- |
| `open` | `source_id`, `source_type`, `uri`, `autoplay`, `volume`, `muted`, `preheat_enabled`, `target_slide`, `cleanup_source_id` |
| `seek` | `position_ms` |
| `goto` | `target_index` |
| `set_loop` | `enabled` |
| `set_volume` | `volume` |
| `set_mute` | `muted` |
| `ppt_media` | `media_action`, `media_id`, `media_index` |
| `reset_ppt` | `restart_sessions` |
| `close` | `reset_all_windows`, `cleanup_source_id` |

迁移注意：

- `pending_command` 不是队列，迁移时不要误以为可以保留多个未执行动作。
- 播放器消费命令后会立即清空 pending，再执行实际 adapter 操作。
- `last_updated_at` 被前端 `sessions.ts` 用来避免旧 SSE/REST 帧覆盖较新的本地状态。
- `window_id` 的 1-4 语义是业务契约，不只是数据库编号。

## `RuntimeState`

`RuntimeState` 是逻辑单例，`get_instance()` 使用 `pk=1`。

关键字段：

| 字段 | 语义 |
| --- | --- |
| `big_screen_mode` | `single` 或 `double` |
| `volume_level` | 系统主音量快照 |
| `volume_muted` | 系统静音快照 |
| `updated_at` | 更新时间 |

迁移时如果切换数据库，建议显式保留单例约束或使用配置表形式，避免出现多行运行态。

## `Scenario`

`Scenario` 存储预案，使用 JSON 保存窗口目标。

关键字段：

| 字段 | 语义 |
| --- | --- |
| `name` | 预案名 |
| `description` | 描述 |
| `sort_order` | 排序，置顶逻辑依赖 |
| `big_screen_mode_state` | `unset`、`empty`、`set` |
| `big_screen_mode` | 当 state 为 `set` 时应用 |
| `volume_state` | `unset`、`empty`、`set` |
| `volume_level`, `volume_muted` | 当 volume state 为 `set` 时应用 |
| `targets` | 窗口动作 JSON 列表 |

`targets` 中每个窗口项通常包含：

| 字段 | 语义 |
| --- | --- |
| `window_id` | 目标窗口 |
| `source_state` | `unset` 不修改，`empty` 清空，`set` 打开源 |
| `source_id` | 要打开的媒体源 |
| `autoplay` | 是否自动播放 |
| `resume` | 是否恢复历史状态，当前以数据保留为主 |

tri-state 设计的价值是避免预案激活时无意清空未配置窗口。迁移时不要把空值简单等同于清空。

## `BackgroundAudioState`

背景音频是独立全局播放器，不占四个 display window。

关键字段：

| 字段 | 语义 |
| --- | --- |
| `current_source` | 当前音频 `MediaSource` |
| `playback_state` | 背景音频状态 |
| `error_message` | 错误信息 |
| `position_ms`, `duration_ms` | 进度和时长 |
| `volume` | 背景音乐音量 |
| `is_muted` | 是否静音 |
| `loop_enabled` | 播放列表循环 |
| `pending_command` | 背景音频待执行命令 |
| `command_args` | 背景音频命令参数 |
| `updated_at` | 更新时间 |

`BackgroundAudioState` 同样是逻辑单例，服务层通过 `get_instance()` 获取。

## `BackgroundAudioPlaylistItem`

播放列表项字段：

| 字段 | 语义 |
| --- | --- |
| `source` | 必须是 `SourceType.AUDIO` |
| `sort_order` | 排序，新增项按当前最大值 + 10 |
| `created_at` | 加入时间 |

服务层 `add_source_to_playlist()` 会避免同一音频源重复加入。删除当前播放项时会自动停止背景音频。

## `StreamSource`

路径：`scp_cv/apps/streams/models.py`

`StreamSource` 由 MediaMTX API 自动发现并同步。

关键字段：

| 字段 | 语义 |
| --- | --- |
| `name` | 显示名，新发现流默认 `[自动] <identifier>` |
| `stream_identifier` | MediaMTX path 名，唯一 |
| `stream_url` | 默认 SRT read URL |
| `is_active` | 是否启用 |
| `is_online` | 是否在线 |
| `current_state` | `offline`, `connecting`, `online`, `disconnected`, `error` |
| `last_connected_at` | 最近上线时间 |
| `last_seen_at` | 最近被 MediaMTX API 看到时间 |
| `last_error_message` | 错误说明 |

`sync_stream_states()` 更新 `StreamSource` 后，`sync_streams_to_media_sources()` 会把在线流同步为 `MediaSource`，当前 README 描述为默认 RTSP 拉流源。

## 重要 migration 脉络

| migration | 影响 |
| --- | --- |
| `0007_add_window_id.py` | 引入 `PlaybackSession.window_id` 唯一逻辑 |
| `0012_expand_models_for_full_rewrite.py` | 扩展媒体源、会话、运行态和预案模型 |
| `0013_ppt_media_items_and_command.py` | 引入 PPT 媒体项和 `ppt_media` 命令 |
| `0014_runtime_volume_muted.py` | 引入系统静音运行态 |
| `0017_add_media_source_keep_alive.py` | 引入预热字段 `keep_alive` |
| `0018_playbacksession_error_message.py` | 引入播放错误详情 |
| `0020_ppt_backend_selection.py` | 引入 PPT 后端选择 |
| `0021_add_wps_ppt_backend.py` | 支持 WPS 演示 |
| `0023_background_audio.py` | 引入背景音频状态和播放列表 |
| `0024_default_powerpoint_ppt_backend.py` | 默认 PPT 后端改为 PowerPoint |
| `0025_remove_ppt_backend_fields.py` | 删除媒体源和会话 PPT 后端字段，统一 PowerPoint-only |

## 数据迁移原则

- 先迁移枚举字符串和模型字段，再迁移 UI。
- 保留 `PlaybackSession.window_id` 1-4 的固定语义。
- 保留 `MediaSource.metadata` 中的 PPT 解析和播放缓存信息，除非重新生成缓存。
- 保留临时源字段和清理语义，避免迁移后上传临时音频或临时媒体残留。
- 保留 `PptResource` 的 1-based 页码，前端和播放器都按 1-based 显示和跳转。
- 如果改用 PostgreSQL，可以用事务和行锁优化命令消费，但 REST/SSE 快照格式应保持兼容。
- 如果引入消息队列，仍建议把 `PlaybackSession` 保留为最终可观察状态表。
