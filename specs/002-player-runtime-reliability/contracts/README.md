# Runtime Contracts

本目录记录本功能对现有 REST/SSE 合同的约束：

- 显示目标接口只接受单屏显示器名称；左右拼接模式、`is_spliced` 和 `spliced_display_label` 不再属于新合同。
- 播放控制接口在能力不支持时返回现有错误响应结构，且不得修改会话的乐观播放状态。
- 播放会话快照中的播放状态必须来自真实适配器；新增/变更的命令租约字段仅供播放器内部使用，不直接暴露给前端。
- PPT 源快照可报告实际 `playback_mode`（`powerpoint` 或 `pdf`）及 PDF 回退错误原因。
- SSE 继续推送播放状态、错误和实际播放模式；播放器离线与 SSE 连接状态分开表达。

具体路径和 schema 变更在实现阶段同步到 `docs/openapi.yaml`、`docs/paths/` 和 `docs/components/schemas/`，并通过 Redocly 校验。
