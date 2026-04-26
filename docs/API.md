# API 文档

## 通信架构

SCP-cv 已改为前后端分离架构：

| 通道 | 用途 | 默认地址 |
|------|------|----------|
| REST API | Vue 控制台主通信通道 | `http://127.0.0.1:8000/api/` |
| SSE | Vue 控制台播放状态实时同步 | `GET /api/events/` |
| gRPC | 外部中控、自动化脚本、兼容客户端 | `127.0.0.1:50051` |
| gRPC-Web | 兼容旧浏览器客户端，不作为 Vue 主通道 | `http://127.0.0.1:8081` |

Vue 前端位于 `frontend/`，开发期通过 Vite 运行在 `5173` 端口，并代理 `/api` 到 Django 后端。

## REST API

所有 REST 响应均为 JSON。成功响应包含 `success: true`，错误响应格式如下：

```json
{
  "detail": "错误说明",
  "code": "stable_error_code"
}
```

### 媒体源

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/sources/` | `source_type` 可选查询参数 | 获取媒体源列表 |
| `POST` | `/api/sources/upload/` | `multipart/form-data`: `file`, `name`, `source_type` | 上传文件并创建媒体源 |
| `POST` | `/api/sources/local/` | JSON: `path`, `name`, `source_type` | 通过本地路径创建媒体源 |
| `POST` | `/api/sources/web/` | JSON: `url`, `name` | 通过网页 URL 创建媒体源 |
| `DELETE` | `/api/sources/{source_id}/` | 无 | 删除媒体源 |

媒体源对象字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 媒体源主键 |
| `source_type` | string | `ppt` / `video` / `audio` / `image` / `web` / `srt_stream` 等 |
| `name` | string | 显示名称 |
| `uri` | string | 文件路径、URL 或流地址 |
| `is_available` | bool | 是否可用 |
| `stream_identifier` | string | 流标识符 |
| `created_at` | string | 创建时间 |

### 播放会话

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/sessions/` | 无 | 获取全部窗口快照 |
| `GET` | `/api/sessions/{window_id}/` | 无 | 获取单窗口快照 |

会话快照字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `window_id` | int | 窗口编号，范围 1-4 |
| `session_id` | int | 会话主键 |
| `source_name` | string | 当前源名称 |
| `source_type` | string | 当前源类型 |
| `source_type_label` | string | 当前源类型显示文本 |
| `source_uri` | string | 当前源地址 |
| `playback_state` | string | `idle` / `loading` / `playing` / `paused` / `stopped` / `error` |
| `playback_state_label` | string | 播放状态显示文本 |
| `display_mode` | string | `single` / `left_right_splice` |
| `target_display_label` | string | 目标显示器 |
| `is_spliced` | bool | 是否处于拼接模式 |
| `current_slide` | int | PPT 当前页 |
| `total_slides` | int | PPT 总页数 |
| `position_ms` | int | 视频/音频当前位置 |
| `duration_ms` | int | 视频/音频总时长 |
| `loop_enabled` | bool | 是否循环播放 |

### 播放控制

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `POST` | `/api/playback/{window_id}/open/` | JSON: `source_id`, `autoplay` | 打开源到窗口 |
| `POST` | `/api/playback/{window_id}/control/` | JSON: `action` | `play` / `pause` / `stop` |
| `POST` | `/api/playback/{window_id}/navigate/` | JSON: `action`, `target_index`, `position_ms` | `next` / `prev` / `goto` / `seek` |
| `POST` | `/api/playback/{window_id}/close/` | 无 | 关闭当前源 |
| `PATCH` | `/api/playback/{window_id}/loop/` | JSON: `enabled` | 设置循环播放 |
| `POST` | `/api/playback/splice/` | JSON: `enabled` | 设置窗口 1+2 拼接 |
| `POST` | `/api/playback/show-ids/` | 无 | 显示窗口 ID 覆盖层 |

播放控制接口成功后返回全量状态：

```json
{
  "success": true,
  "sessions": [],
  "splice_active": false
}
```

### 显示器

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/displays/` | 无 | 获取显示器和拼接标签 |
| `POST` | `/api/displays/select/` | JSON: `window_id`, `display_mode`, `target_label` | 切换窗口显示目标 |

### 预案

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/scenarios/` | 无 | 获取预案列表 |
| `POST` | `/api/scenarios/` | 预案 JSON | 创建预案 |
| `PATCH` | `/api/scenarios/{scenario_id}/` | 预案 JSON | 更新预案 |
| `DELETE` | `/api/scenarios/{scenario_id}/` | 无 | 删除预案 |
| `POST` | `/api/scenarios/{scenario_id}/activate/` | 无 | 激活预案 |
| `POST` | `/api/scenarios/capture/` | JSON: `name`, `description`, `scenario_id` | 从当前状态捕获预案 |

预案字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 预案主键 |
| `name` | string | 名称 |
| `description` | string | 描述 |
| `is_splice_mode` | bool | 是否拼接模式 |
| `window1_source_id` | int/null | 窗口 1 源 |
| `window1_autoplay` | bool | 窗口 1 自动播放 |
| `window1_resume` | bool | 窗口 1 保留进度 |
| `window2_source_id` | int/null | 窗口 2 源 |
| `window2_autoplay` | bool | 窗口 2 自动播放 |
| `window2_resume` | bool | 窗口 2 保留进度 |

### SSE

`GET /api/events/?last_id=0` 返回 `text/event-stream`。

事件类型：

| 事件 | 载荷 | 说明 |
|------|------|------|
| `playback_state` | `{sessions, splice_active}` | 播放状态变化 |
| `heartbeat` | 序列号 | 保活 |

## gRPC 接口

服务：`scp_cv.v1.PlaybackControlService`

合同定义：`protos/scp_cv/v1/control.proto`

默认端口：`50051`

Vue 前端不再依赖 gRPC；以下接口保留给外部中控、自动化脚本和兼容客户端：

| RPC | 请求 | 响应 | 说明 |
|-----|------|------|------|
| `OpenSource` | `OpenSourceRequest` | `OperationReply` | 打开媒体源 |
| `CloseSource` | `CloseSourceRequest` | `OperationReply` | 关闭媒体源 |
| `ControlPlayback` | `ControlPlaybackRequest` | `OperationReply` | 播放控制 |
| `NavigateContent` | `NavigateContentRequest` | `OperationReply` | 内容导航 |
| `GetRuntimeStatus` | `WindowRequest` | `RuntimeStatusReply` | 运行状态 |
| `GetPlaybackState` | `WindowRequest` | `PlaybackStateReply` | 播放状态 |
| `ListDisplayTargets` | `EmptyRequest` | `DisplayTargetsReply` | 显示器列表 |
| `SelectDisplayTarget` | `SelectDisplayTargetRequest` | `OperationReply` | 切换显示目标 |
| `WatchPlaybackState` | `EmptyRequest` | `stream PlaybackStateEvent` | 状态流 |
| `StopCurrentContent` | `EmptyRequest` | `OperationReply` | 兼容停止接口 |

以下 gRPC 方法第一阶段仍保留实现，但 Vue 前端不再调用，后续可在确认无外部依赖后移除：`ListSources`、`AddLocalPathSource`、`AddWebUrlSource`、`DeleteSource`、预案 CRUD 相关 RPC。

### Python 调用示例

```python
import grpc
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2, control_pb2_grpc

channel = grpc.insecure_channel("127.0.0.1:50051")
stub = control_pb2_grpc.PlaybackControlServiceStub(channel)

reply = stub.OpenSource(control_pb2.OpenSourceRequest(
    window_id=1,
    media_source_id=1,
    autoplay=True,
))
print(reply.success, reply.message)
```

## 端口汇总

| 服务 | 默认端口 | 说明 |
|------|----------|------|
| Vue 前端 | 5173 | `npm --prefix frontend run dev` |
| Django REST | 8000 | `/api/`、`/admin/`、媒体文件 |
| gRPC | 50051 | 外部控制接口 |
| gRPC-Web | 8081 | 兼容代理 |
| MediaMTX SRT | 8890 | 推流入口 |
| MediaMTX API | 9997 | 流管理 |

## 验证命令

```powershell
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
```
