# API 文档

## 通信架构

SCP-cv 已改为前后端分离架构：

| 通道 | 用途 | 默认地址 |
|------|------|----------|
| REST API | Vue 控制台主通信通道 | `http://127.0.0.1:8000/api/` |
| SSE | Vue 控制台播放状态实时同步 | `GET /api/events/` |
| gRPC | 外部中控、自动化脚本、兼容客户端 | `127.0.0.1:50051` |
| gRPC-Web | 兼容旧浏览器客户端，不作为 Vue 主通道，`runall` 默认不启动 | `http://127.0.0.1:8081` |

Vue 前端位于 `frontend/`，开发期通过 Vite 运行在 `5173` 端口，并使用 `frontend/.env` 中的 `VITE_BACKEND_TARGET` 直接访问 Django 后端。
当页面从局域网地址打开而 `VITE_BACKEND_TARGET` 仍指向 `127.0.0.1` 时，前端会自动改用当前页面主机名访问 Django，避免移动端请求自身 localhost。

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
| `GET` | `/api/folders/` | 无 | 获取媒体文件夹列表 |
| `POST` | `/api/folders/` | JSON: `name`, `parent_id` | 创建媒体文件夹 |
| `PATCH` | `/api/folders/{folder_id}/` | JSON: `name`, `parent_id` | 更新媒体文件夹 |
| `DELETE` | `/api/folders/{folder_id}/` | 无 | 删除媒体文件夹，源回到根目录 |
| `GET` | `/api/sources/` | `source_type`、`folder_id` 可选查询参数 | 获取媒体源列表 |
| `POST` | `/api/sources/upload/` | `multipart/form-data`: `file`, `name`, `source_type`, `folder_id`, `is_temporary` | 上传文件并创建媒体源 |
| `POST` | `/api/sources/local/` | JSON: `path`, `name`, `source_type`, `folder_id` | 通过本地路径创建媒体源 |
| `POST` | `/api/sources/web/` | JSON: `url`, `name`, `folder_id` | 通过网页 URL 创建媒体源 |
| `PATCH` | `/api/sources/{source_id}/move/` | JSON: `folder_id` | 移动媒体源到文件夹；空值表示根目录 |
| `GET` | `/api/sources/{source_id}/download/` | 无 | 下载文件型媒体源 |
| `GET` | `/api/sources/{source_id}/ppt-resources/` | 无 | 获取 PPT 页资源、预览、提词器和当前页媒体清单 |
| `PUT` | `/api/sources/{source_id}/ppt-resources/` | JSON: `resources` | 覆盖保存 PPT 页资源和媒体清单 |
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
| `folder_id` | int/null | 所属文件夹 |
| `original_filename` | string | 原始文件名 |
| `file_size` | int | 文件大小（字节） |
| `mime_type` | string | MIME 类型 |
| `is_temporary` | bool | 是否临时源 |
| `expires_at` | string/null | 临时源过期时间 |
| `metadata` | object | 扩展元数据 |
| `created_at` | string | 创建时间 |

离线超过 1 小时的直播源会在源列表同步时自动删除。`folder_id=-1` 查询根目录源。临时上传源会记录过期时间，并在播放器切换或关闭该源后由播放器进程清理。

PPT 资源对象字段：`id`、`source_id`、`page_index`、`slide_image`、`next_slide_image`、`speaker_notes`、`has_media`、`media_items`、`created_at`。`media_items` 是当前页音视频对象数组，字段包括 `id`、`media_index`、`media_type`、`name`、`target`、`shape_id`。上传或注册 `.pptx` / `.ppsx` 时会尝试自动解析页数、备注和媒体引用；`.ppt` / `.pps` 保留 PowerPoint COM 播放，但不自动解析资源。

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
| `volume` | int | 窗口音量，范围 0-100 |
| `is_muted` | bool | 窗口是否静音 |
| `loop_enabled` | bool | 是否循环播放 |

### 播放控制

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `POST` | `/api/playback/{window_id}/open/` | JSON: `source_id`, `autoplay` | 打开源到窗口 |
| `POST` | `/api/playback/{window_id}/control/` | JSON: `action` | `play` / `pause` / `stop` |
| `POST` | `/api/playback/{window_id}/navigate/` | JSON: `action`, `target_index`, `position_ms` | `next` / `prev` / `goto` / `seek` |
| `POST` | `/api/playback/{window_id}/ppt-media/` | JSON: `action`, `media_id`, `media_index` | 控制 PPT 当前页单个媒体，`action` 为 `play` / `pause` / `stop` |
| `POST` | `/api/playback/{window_id}/close/` | 无 | 关闭当前源 |
| `PATCH` | `/api/playback/{window_id}/loop/` | JSON: `enabled` | 设置循环播放 |
| `PATCH` | `/api/playback/{window_id}/volume/` | JSON: `volume` | 设置窗口音量 |
| `PATCH` | `/api/playback/{window_id}/mute/` | JSON: `muted` | 设置窗口静音 |
| `POST` | `/api/playback/show-ids/` | 无 | 显示窗口 ID 覆盖层 |

播放控制接口成功后返回全量状态：

```json
{
  "success": true,
  "sessions": []
}
```

### 显示器

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/displays/` | 无 | 获取显示器和拼接标签 |
| `POST` | `/api/displays/select/` | JSON: `window_id`, `display_mode`, `target_label` | 切换窗口显示目标 |

### 运行状态、音量与设备

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/runtime/` | 无 | 获取当前大屏模式和静音策略 |
| `PATCH` | `/api/runtime/` | JSON: `big_screen_mode` | 设置大屏模式，取值 `single` / `double` |
| `GET` | `/api/volume/` | 无 | 获取系统音量入口状态 |
| `PATCH` | `/api/volume/` | JSON: `level`, `muted` | 设置 Windows 系统音量和静音，失败时回退运行态 |
| `GET` | `/api/devices/` | 无 | 获取电源按钮配置，不包含设备状态 |
| `POST` | `/api/devices/{device_type}/toggle/` | 无 | 电视左/右发送开关机切换 TCP 指令 |
| `POST` | `/api/devices/{device_type}/power/{action}/` | 无 | 拼接屏发送开机或关机 TCP 指令，`action` 为 `on` / `off` |

设备类型：`splice_screen`、`tv_left`、`tv_right`。设备接口不保存开关机状态，也不读取硬件返回；发送失败时返回 `device_error`。拼接屏目标为 `192.168.5.10:8889`，开机发送 `FF06010A00010001FA`，等待 5 秒后发送 `FF06010A00010000FA`；关机发送 `FF06010A00020001FA`，等待 5 秒后发送 `FF06010A00020000FA`。电视左目标为 `192.168.5.161:8889`，电视右目标为 `192.168.5.162:8889`，切换时发送 `FF06010A00330001FA`，等待 0.1 秒后发送 `FF06010A00330000FA`。音量响应包含 `system_synced` 和 `backend`；Windows Core Audio 可用时为 `windows_core_audio`，否则回退 `runtime_state`。静音策略固定为：窗口 3/4 始终静音；`single` 模式下窗口 2 静音；`double` 模式下窗口 1/2 不静音。

### 预案

| 方法 | 路径 | 请求 | 说明 |
|------|------|------|------|
| `GET` | `/api/scenarios/` | 无 | 获取预案列表 |
| `POST` | `/api/scenarios/` | 预案 JSON | 创建预案 |
| `GET` | `/api/scenarios/{scenario_id}/` | 无 | 获取预案详情 |
| `PATCH` | `/api/scenarios/{scenario_id}/` | 预案 JSON | 更新预案 |
| `DELETE` | `/api/scenarios/{scenario_id}/` | 无 | 删除预案 |
| `POST` | `/api/scenarios/{scenario_id}/pin/` | 无 | 置顶预案 |
| `POST` | `/api/scenarios/{scenario_id}/activate/` | 无 | 激活预案 |
| `POST` | `/api/scenarios/capture/` | JSON: `name`, `description`, `scenario_id` | 从当前四窗口状态捕获预案 |

预案字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 预案主键 |
| `name` | string | 名称 |
| `description` | string | 描述 |
| `sort_order` | int | 排序权重，置顶时递增 |
| `big_screen_mode_state` | string | `unset` / `empty` / `set` |
| `big_screen_mode` | string | `single` / `double` |
| `volume_state` | string | `unset` / `empty` / `set` |
| `volume_level` | int | 系统音量，范围 0-100 |
| `targets` | array | 四窗口目标配置 |

`targets` 元素字段：`window_id`、`source_state`、`source_id`、`source_name`、`autoplay`、`resume`。`source_state=unset` 表示激活时保持窗口不变，`empty` 表示黑屏，`set` 表示打开绑定源。

### SSE

`GET /api/events/?last_id=0` 返回 `text/event-stream`。

事件类型：

| 事件 | 载荷 | 说明 |
|------|------|------|
| `playback_state` | `{sessions}` | 播放状态变化 |
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
| MediaMTX SRT | 8890 | 推流与读取入口 |
| MediaMTX API | 9997 | 流管理 |

## 验证命令

```powershell
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
```
