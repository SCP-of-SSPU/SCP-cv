# Spec Kit 工作区

本目录保存 GitHub Spec Kit 的项目级配置、模板、脚本和 Codex 集成元数据。

## 命令顺序

```text
/speckit-specify  →  /speckit-clarify  →  /speckit-plan
                 →  /speckit-tasks    →  /speckit-implement
                 →  /speckit-analyze
```

每个功能的产物位于 `specs/<编号>-<短名称>/`。`.specify/feature.json` 仅是当前
功能指针，不应提交；模板、宪章和脚本属于项目资产，应随仓库版本控制。

GitHub PR 会由 `.github/workflows/spec-kit.yml` 校验规范目录结构和未完成占位符。
