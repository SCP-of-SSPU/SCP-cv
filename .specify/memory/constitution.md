<!--
Sync Impact Report
- Version change: 1.0.0 → 2.0.0
- Modified principles:
  - I. 现场安全优先 → I. 运行安全优先
  - III. 可验证交付 → III. 分层验证交付
  - IV. 集成边界清晰 → IV. 合同与进程边界清晰
  - V. 简单、可观测、可维护 → V. 快速迭代与最小复杂度
- Added sections: none
- Removed sections: none
- Follow-up TODOs: none
-->

# SCP-cv Constitution

## Core Principles

### I. 运行安全优先

涉及播放、设备、进程、窗口、端口、权限或第三方运行时的变更 MUST 明确失败时的安全行为，
不得假报成功、静默丢弃有效命令或在授权不确定时盲目重放外部副作用。资源和子进程 MUST 在
成功与失败路径均可追踪、诊断和清理；无法通过自动化覆盖的 Windows、Office、显示器或音频
行为 MUST 明确标注开发测试机验证边界。

### II. 规范驱动与可追溯

新功能和较大重构 MUST 先在 `specs/` 下形成可审查的 `spec.md`，再生成 `plan.md` 与
`tasks.md`；需求、设计、任务、实现和验证 MUST 相互追溯。范围、非目标、成功标准、平台支持
或合同发生变化时，MUST 同步更新对应规范并在 PR 中说明影响。

### III. 分层验证交付

每项行为变更 MUST 至少有一项自动化测试、合同测试或明确的人工验证记录；缺陷修复 MUST
覆盖回归场景。REST/SSE、进程间通信、持久化队列和客户端生命周期需要对应层级的测试；前端
用户可见变更除构建与类型检查外，还 MUST 验证真实浏览器或封装客户端中的关键布局、状态和
控制台错误。无法运行的检查 MUST 在交付说明中列出原因、剩余风险和后续动作。

### IV. 合同与进程边界清晰

控制客户端只能通过已定义的 REST/SSE 合同访问播放主机，不得直接访问本机 Named Pipe、
业务数据库或原生播放对象。ControlHost 是运行时业务数据库的唯一写入者；Supervisor、
PlayerWorker、AudioWorker 和 PowerPointHost MUST 通过带身份、代次和完成证据的本机合同协作。
PowerPoint COM MUST 由独立 STA 进程拥有，VLC、WebView2、PDF、WPF 和 COM 对象不得跨工作进程
传递。合同变更 MUST 同步更新文档与合同测试。

### V. 快速迭代与最小复杂度

实现 MUST 复用既有业务语义、设计令牌和服务边界，避免没有当前需求依据的抽象、长期双栈、
生产切换编排或复杂回滚设施。开发期代码、规范和锁文件通过 Git 分支与小提交恢复；数据库、
媒体、日志和其他忽略文件不属于 Git 恢复范围，任何操作不得据此删除或覆盖用户数据。关键流程
MUST 提供足够的结构化日志和状态；单文件超过 500 行时，后续变更 MUST 优先拆分模块。

## Project Constraints

共享控制台使用 Vue 3、TypeScript、Tailwind CSS 4、Vue Router、Pinia 和 Vite；网页直接使用
Vue 应用，Windows 客户端使用 Electron，Android 客户端使用 Capacitor。Linux/macOS 原生
客户端、iOS、商店发布和客户端内播放执行不在当前范围。三种控制端 MUST 共享页面、路由、
store、API 类型和业务规则，只允许保留必要的薄平台适配层。

播放主机面向受支持的 Windows x64 交互桌面，使用 ASP.NET Core ControlHost、SQLite/EF Core、
持久化命令队列和 Named Pipe；Supervisor 管理四个 PlayerWorker、一个 AudioWorker、独立
PowerPointHost 和 MediaMTX。四窗、独立音频、场景三态、单 PowerPoint COM 与 PDF 回退等
现有核心语义 MUST 保持。敏感配置 MUST 通过环境变量或本地配置提供，不得提交密钥、媒体、
数据库、日志或缓存。

## Development Workflow

工作按 `specify → clarify → plan → tasks → implement → analyze/review` 推进。进入实现前 MUST
完成当前功能的 requirements checklist，并让 `tasks.md` 提供依赖有序、带明确文件路径和独立
验收方式的任务。封装客户端的认证/SSE、Windows COM/STA、混合 DPI/窗口嵌入和播放器预热等
高风险假设 MUST 尽早通过可丢弃实验或集成测试验证。

当前项目处于快速迭代期，除非具体规范明确加入部署范围，否则不要求旧数据库迁移、逆迁移、
长期双栈、生产切换窗口、现场回退演练或自动更新系统。新 EF Core 数据库 MUST 使用独立目录
初始化，不得覆盖原 `db.sqlite3`。每个独立可审查块 MUST 使用符合项目格式的小提交；PR MUST
关联规范目录、列出验证命令及结果，并通过 Spec Kit 校验。

## Governance

本宪章优先于一般开发约定。修改原则或治理规则 MUST 在 PR 中说明动机、影响和版本变更，并由
维护者审查；功能 PR 和代码审查 MUST 检查规范、实现、任务勾选与验证证据的一致性。复杂度只有
在对应需求、风险或实测证据支持时才能引入。

版本遵循语义化版本：移除或重新定义现有治理契约递增 MAJOR；新增原则或实质扩展规则递增
MINOR；不改变含义的澄清与文字修订递增 PATCH。快速开发范围不免除运行时安全、数据保护、
合同兼容和如实报告未验证边界的义务。

**Version**: 2.0.0 | **Ratified**: 2026-08-30 | **Last Amended**: 2026-09-08
