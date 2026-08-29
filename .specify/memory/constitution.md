<!--
Sync Impact Report
- Version change: template → 1.0.0
- Modified principles: template placeholders → project-specific safety, testability,
  traceability, integration, and operational reliability principles
- Added sections: Project Constraints; Development Workflow
- Removed sections: none
- Follow-up TODOs: none
-->

# SCP-cv Constitution

## Core Principles

### I. 现场安全优先

涉及现场播放、设备控制、端口、权限或第三方运行时的变更 MUST 保持可回滚、可诊断，
并明确说明失败时的安全行为。任何可能影响实际显示设备的操作 MUST 有测试或实机验证边界，
不得以默认成功或静默降级掩盖故障。

### II. 规范驱动与可追溯

新功能 MUST 先在 `specs/` 下形成可审查的 `spec.md`，再生成 `plan.md` 与 `tasks.md`；
需求、设计、任务、实现和验证 MUST 能相互追溯。范围、非目标、成功标准或兼容性发生变化时，
必须同步更新对应规范并在 PR 中说明影响。

### III. 可验证交付

每项行为变更 MUST 至少有一项自动化测试、合同测试或明确的人工/实机验证记录；
修复缺陷时 MUST 先覆盖回归场景。交付前 MUST 运行与变更相关的后端检查、测试和前端校验，
无法运行的检查必须在 PR 中写明原因、剩余风险和后续动作。

### IV. 集成边界清晰

REST、SSE、gRPC、播放器、MediaMTX、PowerPoint COM 和前端之间的合同变更 MUST 同步更新
相关文档与测试。模块 MUST 通过已有服务边界协作，不得绕过权限、生命周期或资源清理约束。

### V. 简单、可观测、可维护

实现 MUST 复用现有分层和运行时约定，避免无需求依据的抽象。关键流程 MUST 记录足以定位
问题的结构化日志或状态；资源、进程、窗口和临时文件 MUST 在成功与失败路径均可清理。
单文件超过 500 行时，后续变更 MUST 优先拆分模块。

## Project Constraints

项目面向 Windows 10/11 现场主机，后端使用 Python/Django，前端使用 Vue/TypeScript，
并依赖 PowerPoint、VLC/libVLC 和 MediaMTX。变更 MUST 保持既有端口、配置来源和第三方运行时
约定的兼容性；敏感配置 MUST 通过环境变量或本地配置提供，不得提交密钥、媒体、日志或缓存。

## Development Workflow

工作按 `specify → clarify → plan → tasks → implement → analyze/review` 推进。PR MUST 关联
对应的规范目录，说明验证命令及结果，并通过 GitHub Actions 的 Spec Kit 文档校验。
涉及现场行为的 PR 还 MUST 提供回滚步骤和实机验证计划。

## Governance

本宪章优先于一般开发约定。修改原则或治理规则 MUST 在 PR 中说明动机、影响、迁移安排和
版本变更，并由维护者审查；每次发布前应检查规范、实现与验证记录是否一致。版本遵循语义化
版本：新增或实质扩展原则递增 MINOR，破坏既有治理契约递增 MAJOR，文字澄清递增 PATCH。

**Version**: 1.0.0 | **Ratified**: 2026-08-30 | **Last Amended**: 2026-08-30
