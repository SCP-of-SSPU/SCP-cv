# API 文档

## HTTP 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 播放控制台首页 |
| POST | `/upload/` | 上传 PPT 文件 |
| POST | `/delete/` | 删除资源（参数 `resource_id`） |
| POST | `/open-resource/` | 打开 PPT 资源到播放区（参数 `resource_id`） |
| POST | `/ppt-navigate/` | PPT 翻页（参数 `direction`, `target_page`） |
| POST | `/stop/` | 停止当前播放内容 |
| POST | `/switch-display/` | 切换显示目标（参数 `mode`, `target_name`） |
| POST | `/open-stream/` | 打开 SRT 流（参数 `stream_id`） |
| GET | `/api/session/` | 获取当前会话状态快照（JSON） |
| GET | `/api/resources/` | 获取资源列表（JSON） |
| GET | `/api/page-media/` | 获取当前页媒体列表（JSON，参数 `resource_id`, `page`） |
| GET | `/api/streams/` | 同步 MediaMTX 并返回流列表（JSON，含自动注册） |
| GET | `/events/` | SSE 事件流（`playback_state`、`resource_updated`、`stream_updated`、`heartbeat`） |
| GET | `/admin/` | Django admin 管理入口 |

## gRPC 接口

服务：`scp_cv.v1.PlaybackControlService`（默认端口 50051）

合同定义：`protos/scp_cv/v1/control.proto`

| RPC | 请求 | 响应 | 说明 |
|-----|------|------|------|
| `GetRuntimeStatus` | `RuntimeStatusRequest` | `RuntimeStatusReply` | 获取运行时状态（内容类型、播放状态、显示模式、端点、调试模式） |
| `ListDisplayTargets` | `EmptyRequest` | `DisplayTargetsReply` | 列出可用显示器和拼接标签 |
| `OpenResource` | `OpenResourceRequest` | `OperationReply` | 按 resource_id 打开 PPT 资源 |
| `ControlPptPage` | `ControlPptPageRequest` | `OperationReply` | PPT 翻页（prev/next/goto） |
| `ControlCurrentMedia` | `ControlMediaRequest` | `OperationReply` | 控制页内媒体（play/pause/stop） |
| `OpenStream` | `OpenStreamRequest` | `OperationReply` | 按 stream_identifier 打开 SRT 流 |
| `StopCurrentContent` | `EmptyRequest` | `OperationReply` | 停止当前播放内容 |
| `SelectDisplayTarget` | `SelectDisplayTargetRequest` | `OperationReply` | 切换显示目标（single/left_right_splice） |

## 关键数据对象

- `ResourceFile`：统一资源记录
- `PresentationDocument`：PPT 文档解析结果
- `PresentationPageMedia`：页内媒体对象
- `StreamSource`：SRT 流记录
- `PlaybackSession`：当前播放会话
