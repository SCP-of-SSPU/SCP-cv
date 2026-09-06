# Data Model: 仅保留 REST 接口

本功能不新增、删除或修改数据库实体、字段、关系和状态迁移。

现有 `MediaSource`、`PlaybackSession`、`PlaybackCommand`、`Scenario`、背景音频、设备与运行时
模型继续由 REST/SSE 和播放器服务使用。删除的 protobuf message 只是传输 DTO，不是持久化实体。
