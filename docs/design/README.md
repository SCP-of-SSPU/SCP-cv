# SCP-cv 设计文档索引

本文档集用于完整说明 SCP-cv 当前实现，并作为后续迁移合并到 Django + Fluent + Vue 项目的技术依据。

最后更新：2026-06-04。

## 阅读顺序

| 顺序 | 文档 | 适用读者 | 内容重点 |
| --- | --- | --- | --- |
| 1 | [系统架构](01-system-architecture.md) | 架构师、迁移负责人 | 系统边界、进程关系、核心控制流、运行约束 |
| 2 | [数据模型](02-data-model.md) | 后端、DB 迁移负责人 | Django 模型、状态枚举、关键字段、持久化约束 |
| 3 | [后端服务设计](03-backend-services.md) | Django 后端开发 | settings、URL、服务层、媒体/PPT/场景/设备/音量逻辑 |
| 4 | [接口与实时通信](04-api-realtime-grpc.md) | 前后端、自动化集成 | REST、SSE、gRPC、认证、错误格式、契约稳定点 |
| 5 | [前端 Fluent Vue 设计](05-frontend-fluent-vue.md) | Vue/Fluent 前端开发 | 路由、Pinia、API 客户端、Fluent token、页面模块 |
| 6 | [播放器与媒体运行时](06-player-media-runtime.md) | 桌面播放器、媒体开发 | PySide6、adapter、PPT 后端、预热、四屏窗口 |
| 7 | [部署运维与验收](07-deployment-operations-testing.md) | 运维、现场交付 | Windows 部署、runall、日志、备份、测试、故障定位 |
| 8 | [迁移合并指南](08-migration-guide.md) | 迁移实施团队 | 迁移策略、模块拆分、风险、验收清单 |

## 项目一句话定义

SCP-cv 是一个 Windows-first、单主机、多进程播放控制平台，用 Django REST/SSE/gRPC 管理媒体源和会话状态，用 Vue 控制台进行播控，用 PySide6/libVLC/Office/LibreOffice 播放器进程把内容输出到四个物理窗口。

## 当前系统边界

| 边界 | 当前实现 | 迁移时建议 |
| --- | --- | --- |
| Web 后端 | `scp_cv/` Django 项目，SQLite 本地状态库 | 可迁入目标 Django 项目，但保留服务层语义 |
| Web 前端 | `frontend/` Vue 3 + Vite + Pinia + Naive UI + Fluent tokens | 可迁入目标 Vue/Fluent 应用，优先复用 API 类型和 stores |
| 播放器 | `scp_cv/player/` PySide6 进程 | 不应嵌入 Django Worker，继续作为本机桌面进程 |
| 流媒体 | `tools/third_party/mediamtx/` + `scp_cv/services/mediamtx.py` | 作为独立本机服务保留，Django 只做状态同步 |
| PPT 后端 | PowerPoint COM、WPS COM、LibreOffice UNO/bridge | 按媒体源保留后端选择，不要简化成单后端 |
| 实时状态 | SQLite 状态表 + SSE 轮询/事件总线 | 可以升级消息队列，但要兼容现有状态快照 |

## 迁移目标说明

本文档中的“Django + Fluent + Vue”指目标项目可能已有：

- 一个新的 Django 后端或 Django monolith。
- 一个更标准的 Fluent 风格 Vue 控制台。
- 已有用户、权限、部署、日志、资产管理体系。

迁移的核心原则是：先迁移协议和服务语义，再迁移 UI；先保持播放器进程边界，再逐步优化命令总线。

## 权威源码入口

| 模块 | 主要路径 |
| --- | --- |
| Django 设置 | `scp_cv/settings.py` |
| REST 路由 | `scp_cv/apps/dashboard/api_urls.py` |
| REST 视图 | `scp_cv/apps/dashboard/api_views.py`, `scp_cv/apps/dashboard/api_playback_views.py` |
| 服务层 | `scp_cv/services/` |
| 播放模型 | `scp_cv/apps/playback/models/` |
| 流模型 | `scp_cv/apps/streams/models.py` |
| gRPC proto | `protos/scp_cv/v1/control.proto` |
| gRPC servicer | `scp_cv/grpc_servicers/` |
| 播放器 | `scp_cv/player/` |
| 前端 API | `frontend/src/services/api.ts` |
| 前端状态 | `frontend/src/stores/` |
| 前端页面 | `frontend/src/features/` |
| Fluent tokens | `frontend/src/styles/tokens.css`, `frontend/scripts/generate-fluent-tokens.mjs` |
| 运行编排 | `scp_cv/apps/dashboard/management/commands/runall.py` |

## 与现有文档的关系

| 文档 | 关系 |
| --- | --- |
| `README.md` | 面向用户和开发者的快速说明，包含启动和环境变量摘要 |
| `docs/使用文档.md` | 面向现场使用和部署 |
| `docs/维护文档.md` | 面向维护流程和故障定位 |
| `docs/openapi.yaml` | REST API 机器可读合同 |
| 根目录 `DESIGN.md` | Fluent 2 Vue 设计系统参考，不是 SCP-cv 系统架构文档 |
| 本目录 | 面向系统迁移和架构交接的完整设计说明 |

## 重要结论

- 播放器是独立桌面进程，必须运行在 Windows 活动用户桌面中。
- SQLite 表同时承担状态存储和轻量命令总线职责。
- 前端通过 REST 下发命令，通过 SSE 接收统一 `playback_state` 快照。
- 四窗口策略、背景音频、PPT 后端选择、MediaMTX 自动发现、设备 TCP 指令都是业务语义，不是 UI 细节。
- 当前前端已经采用 Fluent token 和 Fluent 图标，但组件库主体是 Naive UI；迁移到 Fluent Vue 时应先保留 tokens 和信息架构，再替换组件实现。
