# 迁移合并指南

本文给出把 SCP-cv 迁移合并到目标 Django + Fluent + Vue 项目的实施策略。它不是重写建议，而是在保留现场可用性的前提下拆分、搬迁、验证和逐步替换模块。

最后更新：2026-06-08。

## 迁移原则

| 原则 | 说明 |
| --- | --- |
| 先契约后界面 | 先保留 REST/SSE/gRPC 和数据模型语义，再替换前端组件 |
| 先旁路后切换 | 先让新项目旁路调用旧服务或复制服务层，再切换真实入口 |
| 保留播放器边界 | PySide6 播放器继续独立进程，不并入 Web Worker |
| 保留窗口语义 | `window_id` 1-4 和 single/double 模式不可随意重排 |
| 保持 PowerPoint-only | PPT 导入、预览、缓存、预热和放映只走 Microsoft PowerPoint |
| 保留状态回写 | 前端展示以播放器写回状态为准 |
| 小步验收 | 每迁一类源或一个页面都做对应回归 |

## 目标架构建议

```text
目标 Django 项目
  users / permissions / admin / deployment
  scp_cv domain app
    models / services / api / grpc
  media storage / logs

目标 Vue + Fluent 控制台
  shared design system
  scp_cv routes / stores / api client

本机运行时
  PySide6 Player process
  MediaMTX process
  PowerPoint / VLC
```

目标项目可以吸收 Django app、REST 视图、Pinia store 和页面，但播放器进程、MediaMTX 和 Windows runtime 仍应作为本机运行时组件管理。

## 模块分组

| 分组 | 当前路径 | 迁移策略 |
| --- | --- | --- |
| Django settings | `scp_cv/settings.py` | 拆出 SCP-cv 专属配置，接入目标项目 settings |
| Models | `scp_cv/apps/playback/models/`, `scp_cv/apps/streams/models.py` | 作为新 Django app 或并入现有 app，保留字段语义 |
| Services | `scp_cv/services/` | 优先整体迁移，避免把业务逻辑塞入 view |
| REST API | `scp_cv/apps/dashboard/api_*.py`, `api_urls.py` | 迁到目标 URL namespace，保留响应格式 |
| gRPC | `protos/`, `scp_cv/grpc_servicers/` | 如果仍有中控集成则保留，否则做兼容代理 |
| SSE | `scp_cv/services/sse.py` | 保留 `playback_state` 事件，内部可替换为 Redis/channel |
| Player | `scp_cv/player/` | 保持独立包和管理命令启动 |
| Runall | `scp_cv/apps/dashboard/management/commands/runall.py` | 可改造成目标平台进程编排器或 supervisor 配置 |
| Frontend API | `frontend/src/services/api.ts` | 先迁移类型和客户端，再迁页面 |
| Frontend stores | `frontend/src/stores/` | 作为领域状态层保留 |
| Frontend UI | `frontend/src/features/`, `layouts/`, `design-system/` | 可逐步替换为目标 Fluent 组件 |
| Runtime assets | `tools/third_party/` | 作为部署资产管理，不进入普通 Web 静态资源 |

## 迁移阶段

### 阶段 0：冻结契约

| 输出物 | 说明 |
| --- | --- |
| API 清单 | 以 `docs/openapi.yaml` 和 `docs/design/04-api-realtime-grpc.md` 为基础 |
| 模型清单 | 以 `docs/design/02-data-model.md` 为基础 |
| 播放器命令清单 | `PlaybackCommand`、`BackgroundAudioCommand`、`command_args` |
| 现场运行清单 | 显示器、IP、端口、PowerPoint/VLC/MediaMTX |

验收：旧项目所有测试通过，现场关键媒体能播放。

### 阶段 1：后端领域迁移

| 动作 | 注意事项 |
| --- | --- |
| 迁移 models | 保留 enum 字符串值和字段默认值 |
| 迁移 migrations | 不要压扁到丢失数据演进语义，除非明确做全量初始化 |
| 迁移 services | `playback.py`、`media.py`、`background_audio.py`、`mediamtx.py` 优先 |
| 迁移 API views | 保持 `success/detail/code` 响应风格 |
| 接入认证 | 可换目标认证，但保留 API 未授权 JSON 401 |
| 接入 media/static | 保证播放器进程可访问本地路径 |

验收：不用新前端，只用旧前端或 API 工具调用新后端，能创建源、打开源、收到 SSE 状态。

### 阶段 2：播放器接入新后端

| 动作 | 注意事项 |
| --- | --- |
| 保留 `run_player` 或等价入口 | 必须在活动 Windows 桌面启动 |
| 配置新 Django settings | Player 仍需能 import models/services |
| 验证 DB 连接 | Player 和 Web 后端访问同一状态库 |
| 验证 pending command | REST 写入后 Player 消费并清空 |
| 验证状态回写 | Player 写回后 SSE 能推给前端 |

验收：图片、视频、Web、PPT、直播、背景音频至少各跑通一个源。

### 阶段 3：前端状态层迁移

| 动作 | 注意事项 |
| --- | --- |
| 迁移 `api.ts` 类型 | 保持命名和 source/session 快照字段，不恢复 `ppt_backend` |
| 迁移 stores | 先不替换 UI，只让目标项目能读写状态 |
| 接入目标认证 | 替换 `auth` store 内部实现，保留外部动作 |
| 接入 SSE | 保留 `/api/events/` 或提供兼容路径 |
| 验证并发加载 | 保留 `Promise.allSettled()` 降级特性 |

验收：目标 Vue 项目中能显示四窗口状态和背景音乐状态，SSE 可更新。

### 阶段 4：Fluent UI 迁移

| 动作 | 注意事项 |
| --- | --- |
| 建立组件适配层 | 不要让业务页同时依赖多套 UI 组件 |
| 迁移 AppShell | 保留 compact/rail/drawer 响应式信息架构 |
| 迁移通用表单和按钮 | 先替换低风险控件 |
| 迁移媒体源页 | 保留上传进度，PPT 不提供后端选择 |
| 迁移显控页 | 最后迁移，逐源类型回归 |

验收：移动端、平板、桌面下都能完成显控操作。

### 阶段 5：运行编排迁移

| 动作 | 注意事项 |
| --- | --- |
| 决定保留 runall 或接入 supervisor | 必须能看护 MediaMTX、Django、Player、Frontend |
| 迁移日志路径 | 保留分进程日志 |
| 迁移 shutdown | 保留系统关机/退出触发机制 |
| 迁移备份策略 | DB 和 media 同周期备份 |
| 迁移物理烟测 | 保留 `/api/playback/physical-smoke/` 或等价工具 |

验收：一键启动、一键停止、日志查看、现场 reset 均可用。

## 数据迁移策略

### 必须保留的表语义

| 模型 | 保留点 |
| --- | --- |
| `MediaSource` | `source_type`、`uri`、`uploaded_file`、`stream_identifier`、`keep_alive`、`metadata`、临时源字段 |
| `PptResource` | `(source, page_index)` 唯一、`media_items` schema、speaker notes、slide image |
| `PlaybackSession` | `window_id` 唯一、pending command、command args、状态和错误写回 |
| `RuntimeState` | `pk=1` 单例、大屏模式、系统音量 |
| `Scenario` | tri-state `source_state/big_screen_mode_state/volume_state` |
| `BackgroundAudioState` | `pk=1` 单例、后台命令总线 |
| `BackgroundAudioPlaylistItem` | 播放列表顺序 |
| `StreamSource` | MediaMTX 自动发现和在线状态 |

### 文件迁移

| 文件类型 | 建议 |
| --- | --- |
| 上传媒体 | 必须迁移，并保持 DB 路径可解析 |
| 本地路径源 | 只迁 DB 不够，目标机器必须有相同本地路径或做路径重映射 |
| PPT 预览 | 可重建，但迁移可减少首次打开等待 |
| PPT 播放缓存 | 可重建，建议根据 metadata digest 校验 |
| 临时源 | 通常不迁移，迁移前可清理过期临时源 |

### 数据库选择

当前 SQLite 同时是状态库和轻量命令总线。迁移到 PostgreSQL/MySQL 时需关注：

| 问题 | 建议 |
| --- | --- |
| pending command 覆盖 | 考虑添加 command version 或队列表 |
| 高频状态写入 | 对 `last_updated_at` 和窗口 ID 做索引 |
| SSE 轮询成本 | 可引入 Redis/pubsub，但保留快照格式 |
| Player 和 Web DB 连接 | 确保播放器进程能访问目标 DB 和配置 |
| 事务边界 | 命令写入和会话状态更新要保持原子性 |

## API 迁移策略

| 主题 | 建议 |
| --- | --- |
| 路径 | 尽量保留 `/api/...`，或提供兼容 redirect/proxy |
| 响应 | 保留 `success`、`detail`、`code` 和统一快照结构 |
| 认证 | 可接目标 SSO，但前端仍需要 JSON 401，不要 redirect HTML |
| CSRF | 如果仍用 Cookie session，保留 `auth/csrf/` 或等价机制 |
| SSE | 保留 `playback_state` 事件名和 sessions/background_audio payload |
| gRPC | 如有中控设备，保持 proto 兼容；如无，至少保留 REST 等价能力 |
| OpenAPI | 更新 `docs/openapi.yaml` 并让前端类型同步 |

## 播放器迁移策略

播放器可以移动包路径，但不要改变这些行为：

| 行为 | 原因 |
| --- | --- |
| 轮询窗口 1-4 | 与 UI、场景、设备、音频策略绑定 |
| Qt 主线程执行命令 | Qt/COM/libVLC 安全边界 |
| `AdapterState` 写回 | 前端实时状态来源 |
| PPT 外部窗口定位 | PowerPoint 原生放映需要 |
| 直播流 5 秒错误宽限 | 避免握手期误报 error |
| 预热认领 | 现场切换性能关键 |
| 背景音频独立播放器 | 音频源不能占用显示窗口 |

如果目标项目希望替换 DB 轮询为队列，应保留一个兼容层，让旧服务层写入的 `PlaybackCommand` 能被播放器消费。

## 前端迁移策略

| 保留 | 可替换 |
| --- | --- |
| `api.ts` 领域类型 | 请求底层实现 |
| Pinia store 结构 | UI 组件库 |
| 路由信息架构 | 视觉细节 |
| SSE 合并逻辑 | Toast/Dialog 实现 |
| 源类型分支 | 组件样式 |
| PPT 专注模式预览刷新 | 组件样式 |
| 移动端显控流程 | 具体 breakpoint token |

前端迁移最容易出错的是把当前 Naive UI 组件替换为 Fluent 时顺手改业务状态。建议每个页面都先做“同 store、同 API、不同组件”的替换。

## 兼容性风险

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 目标项目认证返回 HTML 登录页 | API 客户端 JSON 解析失败 | API namespace 使用 JSON 401 |
| 目标项目统一静态存储不是本地路径 | 播放器打不开本地文件 | 为播放器提供本地缓存或路径映射 |
| 目标项目部署在非 Windows | 播放器和 Office 后端不可用 | Web 后端可跨平台，播放器节点仍需 Windows |
| 单字段命令总线未改进 | 高频操作覆盖 | 迁移时加版本号或队列，但保留兼容写法 |
| 组件替换改变移动端流程 | 现场操作效率下降 | 先做真实设备可用性测试 |
| 删除 gRPC | 中控系统或脚本失效 | 迁移前确认外部消费者 |
| 忽略 MediaMTX 自动发现 | 直播源不可见 | 保留 `sync_stream_states()` 和 `sync_streams_to_media_sources()` |
| 恢复 PPT 多后端 | 与 PowerPoint-only 合同冲突 | 不恢复源级或会话级 `ppt_backend` |
| 把 reset-all 当作普通 close | 窗口不重建，状态残留 | 保留 coordinator command 语义或提供等价重建命令 |

## 迁移验收矩阵

| 领域 | 验收项 |
| --- | --- |
| 认证 | 登录、登出、过期 401、CSRF unsafe method |
| 媒体源 | 上传、添加本机路径、添加网页、删除、临时源清理 |
| PPT 导入 | 资源解析、PowerPoint 预览、播放缓存 |
| 四窗口 | 1-4 打开/关闭/播放/暂停/停止 |
| 模式 | single/double 切换和静音策略 |
| PPT 播控 | 翻页、跳页、重置、当前页媒体控制、专注页预览刷新 |
| 视频 | seek、loop、volume、mute |
| 图片/Web | 打开、显示、关闭 |
| 直播 | MediaMTX 自动发现、RTSP read、手动 SRT/custom source |
| 背景音乐 | 播放列表、立即播放、下一首、循环、音量、静音 |
| 场景 | capture、activate、tri-state、pin、delete |
| 设备 | 拼接屏电源、TV toggle TCP 指令 |
| 系统音量 | Windows Core Audio 和 fallback |
| SSE | 播放器状态变化可实时到前端 |
| gRPC | 现有自动化脚本可继续调用 |
| runall | 启动、skip 参数、headless、service、shutdown |
| 物理烟测 | `/api/playback/physical-smoke/` 可完整跑通 |

## 切换计划建议

| 阶段 | 入口 | 回滚方式 |
| --- | --- | --- |
| 影子后端 | 旧前端仍连旧后端，新后端同步数据验证 | 停止新后端 |
| 后端切换 | 旧前端连新后端 | 改回 `VITE_BACKEND_TARGET` |
| 播放器切换 | 新后端控制播放器 | 停止新 player，恢复旧 runall |
| 前端切换 | 新 Vue/Fluent 控制台上线 | 切回旧 frontend 端口或静态入口 |
| 运维切换 | 新 supervisor/runall 替代旧 runall | 使用旧 `uv run python manage.py runall` |

每个阶段都应保留旧入口，直到现场完整验收通过。

## 完成定义

| 条件 | 标准 |
| --- | --- |
| 功能 | 迁移验收矩阵全部通过 |
| 数据 | 媒体源、场景、PPT 资源、背景音乐列表可用 |
| 运行 | 目标项目能一键启动或统一看护所有必需进程 |
| 文档 | 新项目 README、部署文档、API 文档和运维文档同步更新 |
| 回滚 | 保留旧项目或旧入口，直到现场连续稳定运行一个完整使用周期 |
| 责任 | 明确后端、前端、播放器、现场运维的维护边界 |

迁移完成后，建议保留本目录设计文档作为新项目的历史依据，并在新项目中维护对应的新版设计文档。
