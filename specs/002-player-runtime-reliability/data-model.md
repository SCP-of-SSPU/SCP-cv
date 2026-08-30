# Data Model: 播放器 Runtime 可靠性与热切换

## PlaybackCommandRecord

现有窗口播放指令记录保留 `session`、`command`、`command_args`、`created_at`，新增：

| 字段 | 类型 | 约束/语义 |
| --- | --- | --- |
| `status` | 短字符串 | `pending` 或 `processing`；默认 `pending` |
| `claimed_by` | 短字符串 | 播放器进程 UUID；未领取为空 |
| `claimed_at` | 时间 | 领取时间；未领取为空 |
| `attempt_count` | 非负整数 | 每次重新领取递增 |
| `last_error` | 文本 | 领取/执行失败的诊断说明，可为空 |

索引：`(session, id)` 保持顺序；`(session, status, id)` 加速领取。最早的 `processing` 且未过期记录会阻止同窗口后续记录被领取。确认必须匹配记录 ID 和 `claimed_by`；释放租约只清除指定消费者的 processing 状态。

## BackgroundAudioCommandRecord

新增背景音频独立队列，关联 `BackgroundAudioState` 单例，字段与 `PlaybackCommandRecord` 的租约字段相同，并包含 `command`、`command_args`、`created_at`。`BackgroundAudioState.pending_command/command_args` 仅为最早记录的兼容投影，不再作为真实队列。

合并规则：只有 `pending` 状态的 SEEK、SET_LOOP、SET_VOLUME、SET_MUTE 可按同类命令合并；OPEN、PLAY、PAUSE、STOP 保留有序记录；终止命令不得删除 processing 记录。

## PowerPointRuntimeLease

不新增数据库实体。主机级命名互斥体仍是唯一事实来源，适配器记录以下运行时内存字段：

- `slot_name`: 固定命名空间名称
- `owner_process_id`: 当前 PowerPoint 进程 ID（仅由播放器启动的实例记录）
- `acquired_at`: 槽位取得时间
- `adapter_kind`: `powerpoint` 或 `pdf`

Windows 内核在播放器崩溃时自动释放命名互斥体；释放或超时日志不得杀死未由本系统启动的 PowerPoint。

## SlidePlaybackSelection

沿用 `MediaSource.metadata` 中的 `slides_pdf` 摘要：`status`、`source_digest`、`path/relative_path`、`generated_at`、`original_extension`。运行时 OPEN 参数携带实际 `adapter_kind` 和 `uri`。当 `adapter_kind=pdf` 时，`uri` 必须存在且摘要与当前源匹配；不可用直接进入 error/安全画面。

## PreheatedResource

预热池各类型记录必须至少能验证：`source_id`、规范化 `uri`、源版本/摘要（若源支持）、资源状态、归属容器、创建/最近续热时间。网页资源保留同一个 `QWebEngineView` 实例，切换只改变父容器和可见性；直播句柄在 TTL 前续热或重建，不得在认领时无条件冷启动。

## MediaCapabilities

能力是适配器类的只读集合，至少包含：`play`、`pause`、`stop`、`seek`、`next`、`prev`、`goto`、`control_media`、`set_loop`、`set_volume`、`set_mute`。服务层以源类型能力校验请求；不支持操作返回业务错误且不修改播放状态。

## Migration

新增一次 Django migration：

1. 为两个命令记录表增加租约与状态字段及索引。
2. 新建 `BackgroundAudioCommandRecord` 表。
3. 将所有 `PlaybackSession` 的 `display_mode` 归一为 `single`，清空 `is_spliced` 和 `spliced_display_label`；随后删除这些废弃字段及 `PlaybackMode.LEFT_RIGHT_SPLICE` 的新合同引用。历史 migration 文件保持不可变。
4. 旧 `pending_command` 字段继续保留为兼容投影，既有记录按 pending 状态初始化。
