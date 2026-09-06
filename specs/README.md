# 功能规范

每个功能使用一个目录保存 Spec Kit 产物：

```text
specs/001-example-feature/
├── spec.md          # 用户价值、场景、需求和成功标准
├── plan.md          # 技术方案与结构决策
├── tasks.md         # 可执行任务清单
├── research.md      # 方案调研（可选）
├── data-model.md    # 数据模型（需要时）
├── contracts/       # API/事件合同（需要时）
└── checklists/      # 质量检查清单（需要时）
```

推荐从 `/speckit-specify` 开始，完成 `/speckit-clarify` 后再进入计划和实现阶段。
规范文件应提交到 Git，以便 PR 审查和后续维护；生成的目录编号遵循 `.specify/init-options.json`
中的 `feature_numbering` 设置。
