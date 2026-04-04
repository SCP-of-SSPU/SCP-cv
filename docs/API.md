# API 初稿

本文件记录阶段一已经预留的 HTTP 与 gRPC 接口边界，便于后续实现时保持解耦。

## HTTP

- `GET /`：播放控制台首页
- `GET /admin/`：Django admin 管理入口

## gRPC

阶段一的 gRPC 合同定义在 `protos/scp_cv/v1/control.proto`，当前预留的能力包括：

- 获取运行状态
- 获取显示器列表
- 打开资源
- PPT 翻页与跳页
- 控制当前页媒体
- 打开或停止 SRT 流
- 切换显示目标

## 关键数据对象

- `ResourceFile`：统一资源记录
- `PresentationDocument`：PPT 文档解析结果
- `PresentationPageMedia`：页内媒体对象
- `StreamSource`：SRT 流记录
- `PlaybackSession`：当前播放会话
