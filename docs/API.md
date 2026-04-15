# API 文档

## HTTP 接口

所有 POST 接口需携带 CSRF Token（Cookie 中的 `csrftoken`）。

### 页面路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 播放控制台首页（三 Tab 布局：源列表、播放控制、设置） |
| GET | `/admin/` | Django admin 管理入口 |

### 源管理

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| POST | `/sources/upload/` | `file`（multipart 文件）, `name`（可选）, `source_type`（可选） | `{success, source: {id, name, source_type, uri}}` |
| POST | `/sources/add-local/` | `path`（文件绝对路径）, `name`（可选）, `source_type`（可选） | `{success, source: {id, name, source_type, uri}}` |
| POST | `/sources/remove/` | `source_id` | `{success}` |
| GET | `/api/sources/` | `source_type`（可选，过滤） | `{success, sources: [...], sync_result: {...}}` |

> 注：`/sources/add-local/` 同时支持 form-data 和 JSON body 两种提交方式。
> `source_type` 留空时系统根据文件扩展名自动检测，可选值：`PPT` / `VIDEO` / `AUDIO` / `IMAGE`。

### 播放控制

> 所有播放控制接口路径中包含 `<window_id>`（1-4），表示目标输出窗口编号。

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| POST | `/playback/<window_id>/open/` | `source_id`, `autoplay`（默认 `true`） | `{success, session: <快照>}` |
| POST | `/playback/<window_id>/control/` | `action`（`play` / `pause` / `stop`） | `{success, session: <快照>}` |
| POST | `/playback/<window_id>/navigate/` | `action`（`next` / `prev` / `goto` / `seek`）, `target_index`（goto 目标页，从 1 开始）, `position_ms`（seek 毫秒位置） | `{success, session: <快照>}` |
| POST | `/playback/<window_id>/close/` | — | `{success, session: <快照>}` |
| POST | `/playback/<window_id>/toggle-loop/` | — | `{success, session: <快照>}` |

### 拼接控制

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| POST | `/playback/splice/` | `enabled`（`true` / `false`） | `{success, splice_active: bool}` |

### 状态查询 & SSE

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/api/session/` | `window_id`（可选，1-4，缺省返回所有窗口） | `{success, session: <快照>}` 或 `{success, sessions: [<快照>, ...]}` |
| GET | `/events/` | `last_id`（可选，断线续传序列号） | SSE 事件流 |

### 会话快照字段

播放控制和状态查询接口返回的 `session` 对象包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `window_id` | int | 窗口编号（1-4） |
| `session_id` | int | 会话主键 |
| `source_name` | string | 当前源名称（无源时为空串） |
| `source_type` | string | 源类型代码（`PPT` / `VIDEO` / `RTSP_STREAM` 等） |
| `source_type_label` | string | 源类型显示标签 |
| `source_uri` | string | 源 URI（文件路径或 RTSP URL） |
| `playback_state` | string | 播放状态代码（`IDLE` / `PLAYING` / `PAUSED` / `STOPPED`） |
| `playback_state_label` | string | 播放状态显示标签 |
| `display_mode` | string | 显示模式代码（`single` / `left_right_splice`） |
| `display_mode_label` | string | 显示模式显示标签 |
| `target_display_label` | string | 目标显示器名称 |
| `spliced_display_label` | string | 拼接显示标签 |
| `is_spliced` | bool | 是否为拼接模式 |
| `current_slide` | int | PPT 当前页码（从 1 开始） |
| `total_slides` | int | PPT 总页数 |
| `position_ms` | int | 视频/音频当前播放位置（毫秒） |
| `duration_ms` | int | 视频/音频总时长（毫秒） |
| `pending_command` | string | 待执行的播放器命令（播放器轮询消费后清空） |
| `last_updated_at` | string | 最后更新时间（ISO 8601） |

### SSE 事件类型

| 事件名 | 载荷 | 说明 |
|--------|------|------|
| `playback_state` | 会话快照 JSON | 播放状态变更时推送 |
| `heartbeat` | 序列号 | 每 30 秒发送一次保活 |

---

## gRPC 接口

服务：`scp_cv.v1.PlaybackControlService`（默认端口 50051）

合同定义：`protos/scp_cv/v1/control.proto`

### RPC 方法列表

| RPC | 请求 | 响应 | 说明 |
|-----|------|------|------|
| `OpenSource` | `OpenSourceRequest` | `OperationReply` | 打开媒体源（按 MediaSource 主键） |
| `CloseSource` | `CloseSourceRequest` | `OperationReply` | 关闭当前播放的源 |
| `ControlPlayback` | `ControlPlaybackRequest` | `OperationReply` | 播放控制（play / pause / stop） |
| `NavigateContent` | `NavigateContentRequest` | `OperationReply` | 内容导航（翻页 / 跳转 / seek） |
| `GetRuntimeStatus` | `EmptyRequest` | `RuntimeStatusReply` | 获取运行时状态概览 |
| `GetPlaybackState` | `EmptyRequest` | `PlaybackStateReply` | 获取详细播放状态（含 PPT 页码、视频进度） |
| `ListDisplayTargets` | `EmptyRequest` | `DisplayTargetsReply` | 列出可用显示器和拼接标签 |
| `SelectDisplayTarget` | `SelectDisplayTargetRequest` | `OperationReply` | 切换显示目标（single / left_right_splice） |
| `StopCurrentContent` | `EmptyRequest` | `OperationReply` | 停止当前播放（兼容旧接口） |

### 枚举定义

**SourceType**：`SOURCE_UNKNOWN(0)` / `SOURCE_PPT(1)` / `SOURCE_VIDEO(2)` / `SOURCE_AUDIO(3)` / `SOURCE_IMAGE(4)` / `SOURCE_WEB(5)` / `SOURCE_CUSTOM_STREAM(6)` / `SOURCE_RTSP_STREAM(7)` / `SOURCE_SRT_STREAM(8)`

**PlaybackAction**：`ACTION_UNKNOWN(0)` / `ACTION_PLAY(1)` / `ACTION_PAUSE(2)` / `ACTION_STOP(3)`

**NavigateAction**：`NAV_UNKNOWN(0)` / `NAV_NEXT(1)` / `NAV_PREV(2)` / `NAV_GOTO(3)` / `NAV_SEEK(4)`

### 调用示例（Python）

```python
import grpc
from scp_cv.grpc_generated.scp_cv.v1 import control_pb2, control_pb2_grpc

# 建立连接
channel = grpc.insecure_channel("127.0.0.1:50051")
stub = control_pb2_grpc.PlaybackControlServiceStub(channel)

# 获取运行时状态
status = stub.GetRuntimeStatus(control_pb2.EmptyRequest())
print(status.source_type, status.playback_state)

# 打开媒体源（按 MediaSource ID）
reply = stub.OpenSource(control_pb2.OpenSourceRequest(
    media_source_id=1,
    autoplay=True,
))
print(reply.success, reply.message)

# 播放控制
reply = stub.ControlPlayback(control_pb2.ControlPlaybackRequest(
    action=control_pb2.ACTION_PLAY,
))

# PPT 翻下一页
reply = stub.NavigateContent(control_pb2.NavigateContentRequest(
    action=control_pb2.NAV_NEXT,
))

# 视频跳转到 10 秒
reply = stub.NavigateContent(control_pb2.NavigateContentRequest(
    action=control_pb2.NAV_SEEK,
    position_ms=10000,
))

# 切换显示器
reply = stub.SelectDisplayTarget(control_pb2.SelectDisplayTargetRequest(
    display_mode="single",
    target_label="HDMI-1",
))

# 关闭当前播放
reply = stub.CloseSource(control_pb2.CloseSourceRequest())
```

---

## 关键数据对象

- `MediaSource`：统一媒体源记录（PPT / 视频 / 音频 / WebRTC 流等）
- `PlaybackSession`：当前播放会话（关联 MediaSource、播放状态、显示配置）
- `StreamSource`：WebRTC 流记录（与 MediaMTX 同步）

---

## 端口汇总

| 服务 | 默认端口 | 配置方式 |
|------|----------|----------|
| Django Web 服务 | 8000 | `runserver` 命令参数 |
| gRPC 服务 | 50051 | `.env` 中 `GRPC_PORT` |
| MediaMTX WebRTC | 8889 | `mediamtx.yml` |
| MediaMTX API | 9997 | `mediamtx.yml` |
