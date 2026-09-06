# Implementation Plan: 播放器 Runtime 可靠性与热切换

**Branch**: `main` | **Date**: 2026-08-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-player-runtime-reliability/spec.md`

**Note**: This template is filled in by the `$speckit-plan` command; its definition describes the execution workflow.

## Summary

本计划修复播放器 Runtime 审查中的全部 P1/P2/P3：播放和背景音频命令改为带租约的持久队列，只有 Qt 主线程完成真实操作后才确认；多窗口进程使用协作式退出；PowerPoint 使用主机级唯一 COM 槽位，槽位被占用时自动选择已生成且校验匹配的 PDF；网页及其它可预热资源采用前后台容器切换并保留实例状态；左右拼接功能从新合同、模型和界面中移除；最后拆分超大文件并更新 Runtime 文档。

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.14、Vue 3/TypeScript

**Primary Dependencies**: Django、PySide6/Qt Multimedia/Qt WebEngine/QtPdf、python-vlc/libVLC、pywin32 PowerPoint COM、pytest-django、Vite

**Storage**: Django ORM 数据库（开发 SQLite，部署按现有配置）及 MEDIA_ROOT 文件缓存

**Testing**: pytest/pytest-django、Ruff、TypeScript typecheck/build、Redocly CLI

**Target Platform**: Windows 10/11 交互桌面；无 GUI 环境仅允许明确失败

**Project Type**: Django Web 控制台 + 独立 PySide6 桌面播放器

**Performance Goals**: 指令正常情况下 1 秒内开始消费；已预热网页切换不触发导航；轮询和状态上报不阻塞 Qt 主线程

**Constraints**: 单主机最多一个 PowerPoint COM 放映；失败路径必须可诊断、可回滚、可清理；新功能不得恢复左右拼接；第三方对象不得跨线程使用

**Scale/Scope**: 4 个播放器窗口、1 个背景音频实例、每类媒体至少一个可复用预热资源

## Constitution Check

*GATE: Phase 0 research and Phase 1 design pass.*

- 现场安全优先：命令租约、协作式退出、单 COM 槽位和安全 PDF 回退均保留失败证据，不静默成功。
- 规范驱动与可追溯：所有实现任务映射到 `spec.md` 的 FR/SC，合同和迁移同步更新。
- 可验证交付：先增加回归测试，再实现；无法在当前主机运行的 PowerPoint/VLC/多屏场景记录实机验证步骤。
- 集成边界清晰：REST/SSE、Django 服务、播放器和第三方运行时通过现有服务层协作。
- 简单、可观测、可维护：独立资源清理、结构化日志、超大文件拆分和文档同步列为交付项。

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
scp_cv/
├── apps/playback/models/                 # 队列、会话和单屏显示模型
├── services/                             # 命令、背景音频、PPT/PDF 和 REST 投影
├── player/                               # Controller、窗口、适配器、预热和 COM 槽
└── apps/dashboard/management/commands/   # 父子播放器进程编排
frontend/src/                             # 显示设置、会话合同和能力呈现
docs/                                      # OpenAPI 与 Runtime 设计
tests/                                     # 服务、控制器、适配器和第三方边界测试
```

**Structure Decision**: 在现有 Django 服务、PySide6 播放器和 Vue 控制台分层内增量修改；新增队列/槽位状态模型及迁移，适配器按职责拆分到 `scp_cv/player/` 现有子模块，不引入新的运行时进程或消息基础设施。

## Complexity Tracking

本计划没有需要豁免的宪章违反。增加背景音频队列表和命令租约是为了跨进程崩溃恢复，不能用单槽字段或内存队列替代。
