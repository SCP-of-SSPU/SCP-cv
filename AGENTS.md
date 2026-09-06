# 项目级 Agent 指引

## Spec Kit 优先规则

本项目使用 GitHub Spec Kit 管理需求、设计和实现。Agent 处理用户需求时，必须先判断需求
是否属于规范驱动开发（SDD）范围；只要需求涉及新功能、功能变更、需求澄清、技术方案、
任务拆分、实现计划、规范一致性分析、项目原则或将任务转换为 issue，就优先匹配并使用
对应的 `speckit-*` skill，再进行后续工作。

不要绕过 Spec Kit 直接开始较大范围的功能实现。若用户明确要求跳过某个阶段，应记录跳过
原因、提示由此产生的返工风险，并继续使用仍然适用的后续 skill。

### Skill 匹配

| 用户意图 | 优先使用的 skill |
| --- | --- |
| 从自然语言需求建立或更新功能规范 | `speckit-specify` |
| 找出规范中的关键歧义并补充答案 | `speckit-clarify` |
| 从规范制定技术方案和设计产物 | `speckit-plan` |
| 生成依赖有序、可执行的任务清单 | `speckit-tasks` |
| 按任务清单实现功能 | `speckit-implement` |
| 检查 `spec.md`、`plan.md`、`tasks.md` 的一致性 | `speckit-analyze` |
| 评估实现与规范的差距并追加未完成任务 | `speckit-converge` |
| 创建或修订项目原则与治理规则 | `speckit-constitution` |
| 为当前功能生成质量检查清单 | `speckit-checklist` |
| 将任务转换为 GitHub issue | `speckit-taskstoissues` |

当一个请求跨越多个阶段时，按最小必要集合依次使用 skill，通常遵循：

```text
specify → clarify → plan → tasks → implement → analyze/review
```

### 规范与产物约定

- 功能规范位于 `specs/<编号>-<短名称>/`，至少包含 `spec.md`。
- 进入实现阶段后，应具备 `plan.md` 和 `tasks.md`；调研、数据模型、合同和检查清单按需添加。
- 执行 skill 前先读取其 `SKILL.md`，并遵循其中的前置检查、验证和完成报告要求。
- 功能阶段应读取 `.specify/memory/constitution.md`，将其作为项目治理约束。
- `.specify/feature.json` 是当前功能的本地指针，由 `.specify/.gitignore` 忽略，不提交到仓库。
- 规范产物应提交到 Git，以便 GitHub PR 审查和后续维护。

GitHub Issue 表单、PR 模板和自动校验位于 `.github/`；规范相关变更会触发
`.github/workflows/spec-kit.yml`。校验失败时，先修复规范产物，再进入实现或合并流程。

## 普通开发约定

- 默认使用简体中文与用户沟通，项目文档和注释也使用简体中文。
- 遵循 `CONTRIBUTING.md`、`STYLE.md` 和项目宪章中的验证、文档、提交与安全约定。
- 变更前检查工作区状态，保留用户已有改动；交付前运行与变更相关的验证并报告未执行项目。
