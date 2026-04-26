# API 文档

## HTTP 接口

所有 POST 接口需携带 CSRF Token（Cookie 中的 `csrftoken`）。

> **前端通信变更**：Web 控制台已迁移至 gRPC-Web 通信。HTTP 接口仅保留：页面渲染（`GET /`）、文件上传（`POST /sources/upload/`）、静态/媒体文件。其余前端操作均通过 gRPC-Web 代理（端口 8081）访问 gRPC 服务。

### 页面路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 播放控制台首页（四 Tab 布局：源列表、播放控制、设置、预案管理） |
| GET | `/admin/` | Django admin 管理入口 |

### 源管理

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| POST | `/sources/upload/` | `file`（multipart 文件）, `name`（可选）, `source_type`（可选） | `{success, source: {id, name, source_type, uri}}` |
| POST | `/sources/add-local/` | `path`（文件绝对路径）, `name`（可选）, `source_type`（可选） | `{success, source: {id, name, source_type, uri}}` |
| POST | `/sources/add-web/` | `url`（网页地址）, `name`（可选） | `{success, source: {id, name, source_type, uri}}` |
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
| POST | `/playback/<window_id>/toggle-loop/` | `enabled`（`true` / `false`，默认 `false`） | `{success, session: <快照>}` |

### 拼接控制

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| POST | `/playback/splice/` | `enabled`（`true` / `false`） | `{success, splice_active: bool, sessions: [<快照>, ...]}` |

### 窗口 ID 叠加显示

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| POST | `/playback/show-ids/` | — | `{success: true}` |

> 触发所有输出窗口（1-4）显示半透明窗口 ID 叠加层，5 秒后自动消失。

### 状态查询

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/api/session/` | `window_id`（可选，1-4，缺省返回所有窗口） | 单窗口：`{success, session: <快照>}`；全部窗口：`{success, sessions: [<快照>, ...], splice_active: bool}` |
| GET | `/events/` | `last_id`（可选，断线续传序列号） | SSE 事件流 |

### 预案管理

| 方法 | 路径 | 参数 | 响应 |
|------|------|------|------|
| GET | `/api/scenarios/` | — | `{success, scenarios: [<预案>, ...]}` |
| POST | `/scenarios/create/` | `name`（必填）, `description`, `is_splice_mode`, `window1_source_id`, `window1_autoplay`, `window1_resume`, `window2_source_id`, `window2_autoplay`, `window2_resume` | `{success, scenario: <预案>}` |
| POST | `/scenarios/<id>/update/` | 同上（仅传需修改的字段） | `{success, scenario: <预案>}` |
| POST | `/scenarios/<id>/delete/` | — | `{success}` |
| POST | `/scenarios/<id>/activate/` | — | `{success, sessions: [<快照>, ...], splice_active: bool}` |

> 支持 JSON body 和 form-data 两种提交方式。
> `window*_source_id` 设为 `0` 或不传表示该窗口不绑定源。

#### 预案对象字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 预案主键 |
| `name` | string | 预案名称 |
| `description` | string | 描述 |
| `is_splice_mode` | bool | 是否拼接模式 |
| `window1_source_id` | int/null | 窗口 1 绑定的媒体源 ID |
| `window1_source_name` | string | 窗口 1 媒体源名称 |
| `window1_autoplay` | bool | 窗口 1 是否自动播放 |
| `window1_resume` | bool | 窗口 1 是否保留播放进度 |
| `window2_source_id` | int/null | 窗口 2 绑定的媒体源 ID |
| `window2_source_name` | string | 窗口 2 媒体源名称 |
| `window2_autoplay` | bool | 窗口 2 是否自动播放 |
| `window2_resume` | bool | 窗口 2 是否保留播放进度 |
| `created_at` | string | 创建时间（ISO 8601） |
| `updated_at` | string | 最后更新时间（ISO 8601） |

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
| `loop_enabled` | bool | 是否启用循环播放 |
| `last_updated_at` | string | 最后更新时间（ISO 8601） |

### SSE 事件类型（已废弃）

> ⚠️ Web 前端已迁移至 gRPC 流式订阅（`WatchPlaybackState`），SSE 端点 `/events/` 仍保留供第三方集成使用。

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
| `GetRuntimeStatus` | `WindowRequest` | `RuntimeStatusReply` | 获取运行时状态概览 |
| `GetPlaybackState` | `WindowRequest` | `PlaybackStateReply` | 获取详细播放状态（含 PPT 页码、视频进度） |
| `ListDisplayTargets` | `EmptyRequest` | `DisplayTargetsReply` | 列出可用显示器和拼接标签 |
| `SelectDisplayTarget` | `SelectDisplayTargetRequest` | `OperationReply` | 切换显示目标（single / left_right_splice） |
| `ListSources` | `ListSourcesRequest` | `ListSourcesReply` | 列出所有可用媒体源（可按类型过滤） |
| `AddLocalPathSource` | `AddLocalPathSourceRequest` | `SourceReply` | 通过本地路径注册媒体源 |
| `AddWebUrlSource` | `AddWebUrlSourceRequest` | `SourceReply` | 通过 URL 添加网页媒体源 |
| `DeleteSource` | `DeleteSourceRequest` | `OperationReply` | 删除指定媒体源 |
| `ToggleLoop` | `ToggleLoopRequest` | `OperationReply` | 切换循环播放模式 |
| `SetSpliceMode` | `SetSpliceModeRequest` | `SpliceModeReply` | 设置窗口 1+2 拼接模式 |
| `ShowWindowIds` | `EmptyRequest` | `OperationReply` | 触发窗口 ID 叠加显示（5s） |
| `GetAllSessionSnapshots` | `EmptyRequest` | `AllSessionSnapshotsReply` | 获取所有窗口播放会话快照 |
| `WatchPlaybackState` | `EmptyRequest` | `stream PlaybackStateEvent` | 服务端流式推送播放状态变更 |
| `StopCurrentContent` | `EmptyRequest` | `OperationReply` | 停止当前播放（兼容旧接口） |
| `ListScenarios` | `EmptyRequest` | `ListScenariosReply` | 获取所有预案列表 |
| `CreateScenario` | `ScenarioDetail` | `ScenarioReply` | 创建新预案 |
| `UpdateScenario` | `UpdateScenarioRequest` | `ScenarioReply` | 更新预案 |
| `DeleteScenario` | `DeleteScenarioRequest` | `OperationReply` | 删除预案 |
| `ActivateScenario` | `ActivateScenarioRequest` | `ActivateScenarioReply` | 激活预案（一键应用窗口配置） |
| `CaptureScenario` | `CaptureScenarioRequest` | `ScenarioReply` | 从当前窗口 1/2 状态创建或覆盖预案 |

### 枚举定义

**SourceType**：`SOURCE_UNKNOWN(0)` / `SOURCE_PPT(1)` / `SOURCE_VIDEO(2)` / `SOURCE_AUDIO(3)` / `SOURCE_IMAGE(4)` / `SOURCE_WEB(5)` / `SOURCE_CUSTOM_STREAM(6)` / `SOURCE_RTSP_STREAM(7)` / `SOURCE_SRT_STREAM(8)`

**PlaybackAction**：`ACTION_UNKNOWN(0)` / `ACTION_PLAY(1)` / `ACTION_PAUSE(2)` / `ACTION_STOP(3)`

**NavigateAction**：`NAV_UNKNOWN(0)` / `NAV_NEXT(1)` / `NAV_PREV(2)` / `NAV_GOTO(3)` / `NAV_SEEK(4)`

### gRPC-Web 浏览器客户端

前端通过 gRPC-Web 代理（端口 8081）访问 gRPC 服务。

Web 控制台通过 `WatchPlaybackState` 订阅全量窗口快照。控制类 RPC 成功下发命令后会发布 `playback_state` 事件；播放器独立进程回写数据库时，服务端流还会以 0.2 秒间隔进行快照签名对比，只在状态变化时推送，避免依赖手动刷新。

| 组件 | 路径/位置 | 说明 |
|------|-----------|------|
| 代理 | `npx @grpc-web/proxy --backend http://localhost:50051 --port 8081` | 将 gRPC-Web 请求转为原生 gRPC |
| JS 桩代码 | `static/js/grpc-generated/scp_cv/v1/` | protoc + grpc-web 生成 |
| 客户端封装 | `static/js/grpc-client.js` → `grpc-client.bundle.js` | Promise 风格 API，18 个 RPC + 6 个预案 + 1 个流式订阅 |
| 启动方式 | `uv run python manage.py runall`（自动启动代理） | 可通过 `--skip-grpcweb` 跳过 |

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

- `MediaSource`：统一媒体源记录（PPT / 视频 / 音频 / SRT 流等）
- `PlaybackSession`：当前播放会话（关联 MediaSource、播放状态、显示配置）
- `StreamSource`：外部推流（SRT/RTSP）接入记录（与 MediaMTX 同步）
- `PlaybackScenario`：预案配置记录（窗口 1/2 源绑定、拼接模式、自动播放等）

---

## 端口汇总

| 服务 | 默认端口 | 配置方式 |
|------|----------|----------|
| Django Web 服务 | 8000 | `runserver` 命令参数 |
| gRPC 服务 | 50051 | `.env` 中 `GRPC_PORT` |
| MediaMTX SRT | 8890 | `mediamtx.yml` |
| MediaMTX API | 9997 | `mediamtx.yml` |
