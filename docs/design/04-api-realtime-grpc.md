# 接口与实时通信

本文说明 SCP-cv 的 REST、SSE、gRPC 和认证契约。目标是让迁移团队知道哪些接口是前端和外部中控依赖的稳定边界。

## 接口分层

| 层 | 当前实现 | 主要调用方 |
| --- | --- | --- |
| REST | Django function views，路由在 `scp_cv/apps/dashboard/api_urls.py` | Vue 控制台、现场浏览器 |
| SSE | `/api/events/`，服务在 `scp_cv/services/sse.py` | Vue Pinia runtime store |
| gRPC | `protos/scp_cv/v1/control.proto`，servicer 在 `scp_cv/grpc_servicers/` | 外部中控、自动化脚本 |
| gRPC-Web | `runall.py` 启动代理 | 浏览器兼容场景 |
| Static/media | `scp_cv/urls.py` 直接 serve | PPT 预览、下载、上传媒体 |

REST 和 gRPC 都委托同一服务层。迁移时应避免为 REST 和 gRPC 复制两套业务逻辑。

## 认证契约

| 项 | 当前行为 |
| --- | --- |
| 登录状态 | Django session cookie |
| CSRF | `csrftoken` cookie，前端 unsafe method 发送 `X-CSRFToken` |
| 前端请求 | `credentials: include` 或 XHR with credentials |
| 未登录 REST | JSON 401，`detail=未登录或会话已过期`, `code=unauthorized` |
| 未登录 SSE | 同样由 `ApiAuthMiddleware` 拒绝 |
| gRPC auth | `GrpcAuthInterceptor` 从 metadata/cookie 恢复 session |

前端集中处理 401：`frontend/src/services/api.ts` 抛出 `UnauthorizedError`，`frontend/src/main.ts` 注册全局 handler，清理 auth store 并跳转 `/login?redirect=...`。

## 通用响应格式

成功响应通常包含：

```json
{
  "success": true,
  "...": "业务字段"
}
```

错误响应通常包含：

```json
{
  "detail": "错误说明",
  "code": "machine_readable_code"
}
```

状态变更类播放 API 通常通过 `mutate_playback()` 返回：

```json
{
  "success": true,
  "sessions": [],
  "background_audio": {}
}
```

迁移时应保留 `sessions` 与 `background_audio` 的同响应返回方式，否则前端在 REST 响应和 SSE 到达之间会出现状态空窗。

## REST 入口分组

### Auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/auth/csrf/` | 设置并返回 CSRF token |
| POST | `/api/auth/login/` | 用户名密码登录 |
| POST | `/api/auth/logout/` | 幂等退出 |
| GET | `/api/auth/me/` | 当前用户 |

### Media folders and sources

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/api/folders/` | 列出或创建文件夹 |
| PATCH/DELETE | `/api/folders/<folder_id>/` | 修改或删除文件夹 |
| GET | `/api/sources/` | 列出媒体源，内部会同步流状态 |
| POST | `/api/sources/upload/` | 上传媒体文件，可带临时源和 PPT 后端参数 |
| POST | `/api/sources/local/` | 注册本机路径 |
| POST | `/api/sources/web/` | 添加网页源 |
| POST | `/api/sources/<source_id>/move/` | 移动到文件夹 |
| GET | `/api/sources/<source_id>/download/` | 下载源文件 |
| GET | `/api/sources/<source_id>/preview/` | 预览信息 |
| GET/PUT | `/api/sources/<source_id>/ppt-resources/` | 获取或替换 PPT 页资源 |
| PATCH/DELETE | `/api/sources/<source_id>/` | 修改或删除媒体源 |

### Sessions and runtime

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/sessions/` | 四窗口会话快照 |
| GET | `/api/sessions/<window_id>/` | 单窗口会话快照 |
| GET/PATCH | `/api/runtime/` | 大屏模式等运行态 |
| GET/PATCH | `/api/volume/` | Windows 系统音量 |

### Playback

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/playback/<window_id>/open/` | 打开媒体源 |
| POST | `/api/playback/<window_id>/control/` | play/pause/stop |
| POST | `/api/playback/<window_id>/navigate/` | next/prev/goto/seek |
| POST | `/api/playback/<window_id>/ppt-media/` | 控制 PPT 页内媒体 |
| POST | `/api/playback/<window_id>/ppt-backend/` | 临时切换当前 PPT 后端 |
| POST | `/api/playback/<window_id>/close/` | 关闭窗口源 |
| POST | `/api/playback/<window_id>/loop/` | 设置循环 |
| POST | `/api/playback/<window_id>/volume/` | 窗口音量 |
| POST | `/api/playback/<window_id>/mute/` | 窗口静音 |
| POST | `/api/playback/show-ids/` | 显示窗口编号覆盖层 |
| POST | `/api/playback/reset-all/` | 全部窗口 reset |
| POST | `/api/playback/reset-ppt/` | 重置所有 PPT 放映 |
| POST | `/api/playback/physical-smoke/` | 真实播放冒烟测试 |

### Background audio

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/background-audio/` | 背景音频快照 |
| GET/POST/DELETE | `/api/background-audio/playlist/` | 列表查询、加入、清空 |
| POST | `/api/background-audio/playlist/<item_id>/play/` | 播放列表项 |
| DELETE | `/api/background-audio/playlist/<item_id>/` | 删除列表项 |
| POST | `/api/background-audio/control/` | play/pause/stop/next/prev/seek |
| POST | `/api/background-audio/play-source/` | 加入并播放音频源 |
| POST | `/api/background-audio/volume/` | 背景音量 |
| POST | `/api/background-audio/mute/` | 背景静音 |
| POST | `/api/background-audio/loop/` | 背景列表循环 |

### Displays, devices, scenarios, system

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/displays/` | 显示器目标列表 |
| POST | `/api/displays/select/` | 为窗口选择显示器或拼接目标 |
| GET | `/api/devices/` | 设备按钮配置 |
| POST | `/api/devices/<device_type>/toggle/` | 电视开关机切换 |
| POST | `/api/devices/<device_type>/power/<action>/` | 拼接屏开关机 |
| GET/POST | `/api/scenarios/` | 列表或创建预案 |
| POST | `/api/scenarios/create/` | 兼容创建入口 |
| POST | `/api/scenarios/capture/` | 从当前状态捕获预案 |
| PATCH/DELETE | `/api/scenarios/<scenario_id>/` | 修改或删除预案 |
| POST | `/api/scenarios/<scenario_id>/pin/` | 置顶预案 |
| POST | `/api/scenarios/<scenario_id>/activate/` | 激活预案 |
| GET | `/api/events/` | SSE 实时事件 |
| POST | `/api/system/shutdown/` | 写 shutdown 文件，让 runall 退出 |

完整机器可读契约见 `docs/openapi.yaml` 和 `docs/paths/`、`docs/components/`。

## 关键请求语义

### 打开媒体源

`POST /api/playback/<window_id>/open/`

典型请求：

```json
{
  "source_id": 12,
  "autoplay": true,
  "ppt_backend": "powerpoint",
  "target_slide": 1
}
```

后端行为：

- 校验 `window_id` 在 1-4。
- 校验源存在且可用。
- 拒绝把 audio 源打开到显示窗口。
- PPT 源解析后端并选择播放缓存 URI。
- 设置 session 为 `loading`。
- 写 `pending_command=open` 和完整 `command_args`。

### 导航

`POST /api/playback/<window_id>/navigate/`

动作语义：

| action | 适用类型 | 参数 |
| --- | --- | --- |
| `next` | PPT | 无 |
| `prev` | PPT | 无 |
| `goto` | PPT | `target_index` 或 page，1-based |
| `seek` | video/audio-like | `position_ms` |

服务层会阻止 PPT seek，也会阻止非 PPT next/prev/goto。

### PPT media

`POST /api/playback/<window_id>/ppt-media/`

典型请求：

```json
{
  "media_action": "play",
  "media_id": "page-3-media-1",
  "media_index": 1
}
```

后端只下发命令，实际 shape 查找和控制由播放器 PPT adapter 完成。

## SSE 设计

文件：`scp_cv/services/sse.py`

`/api/events/` 返回 `StreamingHttpResponse`，content type 是 `text/event-stream`。

事件格式：

```text
id: 123
event: playback_state
data: {"sessions": [...], "background_audio": {...}}

```

设计要点：

| 机制 | 说明 |
| --- | --- |
| 内存事件总线 | `publish_event(event_type, payload)` 递增全局 sequence，保存最新事件 |
| DB 轮询兜底 | 播放器独立进程只写 DB，SSE 每 0.2 秒读取 sessions/background_audio 并比较 JSON signature |
| 事件合并 | 如果没有新总线事件，但 DB 快照变化，会发送 `playback_state` |
| 心跳 | 每 30 秒发送 heartbeat，避免代理或浏览器断开 |
| Last-Event-ID | 支持 `last_sequence` 续传语义 |
| 响应头 | `Cache-Control: no-cache`, `X-Accel-Buffering: no` |

前端处理在 `frontend/src/stores/runtime.ts`：

- `connectEvents()` 建立 `EventSource(buildBackendUrl('/api/events/'), { withCredentials: true })`。
- 收到 `playback_state` 后调用 sessions store 和 background audio store。
- SSE 出错时切换到 reconnecting 状态，主动刷新 sessions/background audio，并 2 秒后重连。

迁移时如果改用 WebSocket，也建议保留同名 `playback_state` payload，减少前端改动。

## gRPC 设计

Proto：`protos/scp_cv/v1/control.proto`

注册入口：`scp_cv/grpc_handlers.py`

Servicer 组合：`scp_cv/grpc_servicers/servicer.py`

Mixin：

| Mixin | 职责 |
| --- | --- |
| `MediaSourceServicerMixin` | 媒体源 CRUD、列表、添加本机路径、添加网页 |
| `PlaybackControlMixin` | open/close/control/navigate/runtime/session |
| `DisplayMixin` | 显示器列表和选择 |
| `ScenarioMixin` | 预案 CRUD、激活、捕获 |
| `StreamingMixin` | `WatchPlaybackState` server-streaming |

主要 RPC 能力：

- `OpenSource`
- `CloseSource`
- `ControlPlayback`
- `NavigateContent`
- `GetPlaybackState`
- `GetRuntimeState`
- `SetBigScreenMode`
- `ListDisplayTargets`
- `SelectDisplayTarget`
- `ListSources`
- `AddLocalSource`
- `AddWebSource`
- `UpdateSource`
- `DeleteSource`
- `ToggleLoop`
- `ShowWindowIds`
- `GetAllSessions`
- `WatchPlaybackState`
- `ListScenarios`
- `CreateScenario`
- `UpdateScenario`
- `DeleteScenario`
- `ActivateScenario`
- `CaptureScenario`
- `StopCurrentContent`

gRPC 与 REST 的迁移原则：

- RPC 不应绕过服务层直接写模型。
- Proto 字段是外部中控合同，改名或删字段要比 REST 更谨慎。
- 如果目标项目不再需要 gRPC，也应保留 proto 和兼容说明，便于后续中控对接。
- `WatchPlaybackState` 应与 SSE 快照语义保持一致。

## 前端 API 客户端契约

文件：`frontend/src/services/api.ts`

关键行为：

| 行为 | 说明 |
| --- | --- |
| backend base | dev 使用相对路径，生产优先 `VITE_BACKEND_TARGET`，否则当前 host + 8000 |
| timeout | 默认 10 秒，上传使用 XHR |
| CSRF | unsafe method 自动从 `csrftoken` cookie 添加 header |
| credentials | fetch 和 XHR 都携带 cookie |
| JSON parsing | 只解析 JSON，401 转 `UnauthorizedError` |
| upload progress | `uploadFormData()` 支持进度回调 |

迁移到目标 Vue 应用时，建议先复制或适配 `api.ts` 的类型和请求层，再迁移页面组件。

## 兼容风险

| 风险 | 影响 | 建议 |
| --- | --- | --- |
| 改 REST 路径 | 前端 stores 和 OpenAPI 全部受影响 | 先做路径 alias 或集中 base path |
| 改错误格式 | 全局 401 和 toast 逻辑异常 | 保留 `detail` 和 `code` |
| 去掉 REST 响应快照 | UI 状态延迟或闪烁 | 保留 `sessions` 和 `background_audio` |
| SSE payload 改名 | Pinia 无法合并状态 | 保留 `playback_state` 事件名或做适配器 |
| CSRF/session 模型改变 | 登录和 unsafe request 失败 | 更新 `api.ts`，不要让页面直接处理认证细节 |
| gRPC 字段变更 | 外部中控脚本断裂 | 通过 proto versioning 迁移 |
