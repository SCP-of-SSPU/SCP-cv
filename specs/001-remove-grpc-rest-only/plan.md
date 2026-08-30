# Implementation Plan: 仅保留 REST 接口

**Branch**: `001-remove-grpc-rest-only` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-remove-grpc-rest-only/spec.md`

## Summary

移除项目内全部 gRPC/gRPC-Web 服务、protobuf 合同和生成代码、专属依赖、启动参数、测试及
当前文档引用。现有 Django REST、SSE、Vue 控制台、播放器、MediaMTX 和设备控制行为保持不变。

## Technical Context

**Language/Version**: Python 3.12+、TypeScript 6.x、Vue 3

**Primary Dependencies**: Django 6、Django REST Framework、PySide6、Vue、Pinia

**Storage**: SQLite 与本地媒体文件；不变更数据模型

**Testing**: pytest、Django system check、Ruff、vue-tsc、Vite build、Redocly

**Target Platform**: Windows 10/11 现场主机；CI 可在通用环境验证静态与纯逻辑测试

**Project Type**: 单仓库 Web 控制台 + Django 后端 + Windows 播放器

**Performance Goals**: REST/SSE 控制延迟和播放切换行为不退化

**Constraints**: 不保留 gRPC 兼容层；不改变 REST URL、响应结构、认证或数据库模型

**Scale/Scope**: 删除约 3 组 gRPC 源码目录、1 份 proto 合同、启动编排分支、依赖和文档引用

## Constitution Check

- **现场安全优先**：通过 REST 全量回归、启动流程和资源清理测试保护现场行为。
- **规范驱动与可追溯**：`spec.md`、本计划与 `tasks.md` 记录删除范围和验收方式。
- **可验证交付**：运行后端全量测试、前端类型/构建、OpenAPI、Ruff 与静态引用扫描。
- **集成边界清晰**：只移除 gRPC 边界，保留 REST/SSE、播放器、MediaMTX 和设备合同。
- **简单、可观测、可维护**：删除不再使用的端口、进程、依赖和生成物，减少运行面。

所有治理门禁通过，无需复杂度例外。

## Project Structure

### Documentation (this feature)

```text
specs/001-remove-grpc-rest-only/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
scp_cv/
├── apps/dashboard/management/   # 删除 gRPC-Web 启动参数和进程分支
├── services/                    # 保持 REST/SSE 共用领域服务
├── player/                      # 保持播放器运行时
├── settings.py                  # 删除 gRPC 配置和应用注册
└── urls.py                      # 保持 REST/admin/media 路由

frontend/src/                    # 删除当前界面中的 gRPC 端口说明
tests/                           # 删除 gRPC 专属测试，更新 runall/REST 回归
docs/                            # 删除当前 gRPC 使用和部署说明
```

将整体删除：`protos/`、`scp_cv/grpc_generated/`、`scp_cv/grpc_servicers/`、
`scp_cv/grpc_auth.py`、`scp_cv/grpc_handlers.py`、`scp_cv/v1/`、
`tests/test_grpc_servicers.py` 和 `static/js/grpc-client.bundle.js.map`。

**Structure Decision**: 保持现有 REST 分层；删除 gRPC 边界，不引入替代抽象或数据迁移。

## Design Decisions

1. REST/SSE 为唯一控制接口，旧 gRPC 客户端直接停止支持，不增加适配层。
2. 用依赖管理器重新生成锁文件，避免手工编辑残留传递依赖。
3. runall 不再接受 gRPC-Web 参数，也不扫描或启动 gRPC 相关进程。
4. 历史 CHANGELOG 可以保留事实性描述；README、维护/使用文档和 UI 只描述当前能力。
5. OpenAPI 合同保持 REST 行为不变，并使用 Redocly 校验。

## Post-Design Constitution Check

设计未增加新服务、端口或兼容层，删除范围可由测试和静态扫描验证，仍满足全部宪章门禁。
