# CHANGELOG

## 2026-04-30

### 现场控制补齐

- **播放内核替换**：SRT 播放器移除旧播放内核与旧 Python 绑定，改为 python-vlc + libVLC，第三方下载脚本同步切换到 VLC runtime
- **SRT 读端延迟修复**：播放器读取 URL 改为 `latency=50`，避免 libVLC 将旧值解释为 30 秒缓冲
- **启动显卡选择**：播放器启动器在多显卡主机上提供 SRT 渲染显卡选择，并过滤虚拟显示适配器
- **PPT 资源解析**：上传或注册 `.pptx` / `.ppsx` 时自动提取页数、备注文本和页面媒体引用，PPT 资源接口新增 `media_items` 字段
- **PPT 媒体控制**：新增 `/api/playback/{window_id}/ppt-media/`，支持对当前页单个媒体执行播放、暂停和停止
- **PPT 导航边界**：翻页到边界时保持当前页，跳页越界返回明确错误，PPT 不再接受无效 seek 指令
- **PPT 专注模式修复**：移除独立 `/playback` 页面，专注模式返回对应显示控制页，SSE 轮询播放器 DB 进度并联动当前页/下一页 PNG 预览
- **PowerPoint 弹窗修复**：PPT 适配器忽略最后一页后的继续下一页指令，关闭只读演示文稿前标记已保存并禁用 PowerPoint 保存提示
- **PPT 放映恢复**：PPT 停止后再次播放会尝试从上次页码重新进入放映
- **视频操作增强**：显示控制页补齐停止、前进 10 秒、后退 10 秒和窗口静音切换
- **系统音量同步**：系统音量优先调用 Windows Core Audio 同步主音量和静音状态，失败时回退运行态并返回同步标记
- **设备电源指令**：拼接屏和电视电源控制改为静态 TCP 指令下发，不再保存或展示设备开关机状态
- **文档与测试**：同步 REST API、使用文档和 README，补充 PPT 媒体、电源指令、系统音量和相关服务测试

## 2026-04-29

### 后端四窗口重构

- **媒体源管理**：新增媒体文件夹、源移动、文件下载、临时源标记和扩展元数据字段
- **直播源清理**：源同步时自动删除离线超过 1 小时的直播源
- **预案模型**：预案改为 `ScenarioTarget` 四窗口目标结构，支持 `unset` / `empty` / `set` 三态和置顶排序
- **运行状态**：新增 `single` / `double` 大屏模式运行态，窗口 3/4 始终静音，`single` 下窗口 2 静音
- **音量控制**：新增系统音量占位状态和窗口音量/静音 REST API，播放器消费 `set_volume` / `set_mute` 指令
- **设备占位**：新增拼接屏、电视左、电视右三类设备开关机状态接口
- **PPT 资源接口**：新增 PPT 页资源 REST API，用于保存当前页/下一页预览、提词器和页面媒体标记
- **临时源清理**：临时上传源在播放器切换或关闭后自动删除，避免临时文件长期残留
- **测试同步**：更新媒体源、播放会话、预案和 REST API 测试到新模型结构

### 前端控制台重写

- **总览首页**：新增现场指挥台总览，集中显示源数量、窗口态势、预案数量、设备状态和大屏模式
- **源管理页**：支持文件夹筛选、新建/删除文件夹、源移动、下载、临时上传和根目录视图
- **播放控制页**：补齐 `single` / `double` 大屏切换、窗口音量、静音状态和四窗口声音策略提示
- **设置页**：集中管理系统音量占位、设备开关机占位、显示器目标和窗口状态
- **预案页**：改为四窗口目标矩阵，支持 `unset` / `empty` / `set` 三态、置顶、音量策略和当前状态捕获
- **显示控制页**：新增大屏左、大屏右、TV 左、TV 右独立控制页，支持临时上传即开、保存上传、关闭显示和按源类型控制
- **PPT 专注页**：新增无导航专注模式，提供返回按钮、大号翻页、媒体播放、提词器、当前页/下一页预览和页码状态
- **关于页**：新增使用流程、关键入口、运行约束和验证命令说明
- **响应式设计**：重做深色控制室视觉，适配桌面端、手机竖屏和平板横屏

## 2026-04-28

### 控制台与播放稳定性

- **多屏定位**：播放器窗口改为使用 Qt 屏幕几何精确定位，避免 `showFullScreen()` 在多显示器环境中放大到其它屏幕
- **API 容错**：前端 REST 请求在解析前检查 JSON 响应，HTML 错误页会显示可读错误，不再抛出 `Unexpected token '<'`
- **局域网访问**：前端使用 `frontend/.env` 的 `VITE_BACKEND_TARGET` 直连 Django 后端，后端提供 CORS 响应头，降低 Vite 反向代理路径不一致风险
- **运行编排**：`runall` 默认监听局域网地址并跳过 gRPC-Web 代理，避免 `npx @grpc-web/proxy` 交互式安装提示阻塞启动
- **控制稳定性**：前端在局域网访问时自动把 `127.0.0.1` 后端地址替换为当前主机地址，避免手机/平板请求打到自身 localhost
- **MediaMTX 读取地址**：SRT/RTSP 读取地址支持配置局域网主机，SRT 端口文档统一为 `8890`
- **第三方二进制**：解除 `tools/third_party` 下 `.exe` / `.dll` 等可执行依赖的忽略规则，允许按需纳入 Git
- **窗口布局**：删除窗口 1 全屏填充窗口 2 的控制入口、REST 路由、服务逻辑、前端禁用规则和预案字段
- **日志落盘**：Django 与 `runall` 编排的子进程日志统一写入项目 `logs/` 目录，便于现场排障
- **局域网直播**：SRT 推流地址支持按局域网主机生成，播放器本机拉流继续使用本机地址
- **网页源**：未写协议的网页源默认使用 `http://`，并记录加载失败原因
- **上传体验**：前端文件上传增加进度条、上传中状态与重复操作保护
- **API 解耦**：将播放与预案 REST API 从超 500 行视图文件拆分到独立模块，保留核心路由行为

## 2026-04-27

## 2026-04-26

### 前后端分离与 REST 控制台迁移

- **拼接下线**：移除窗口 1+2 拼接控制入口、REST 路由、服务同步逻辑和预案拼接字段
- **Vue 前端**：新增 `frontend/`，使用 Vue 3、Vite、TypeScript、Pinia 与 Vue Router 重构控制台
- **REST API**：新增 `/api/` 控制台接口，覆盖媒体源、播放控制、窗口状态、显示器、预案和 SSE
- **gRPC 保留**：Vue 前端不再依赖 gRPC-Web，后端保留核心 gRPC 控制和状态接口供外部集成
- **运行编排**：`runall.py` 改为子进程 supervisor，同时启动 MediaMTX、Django、Vue、gRPC-Web 与 PySide 播放器
- **退出控制**：`run_player.py` 支持 SIGINT/SIGTERM，Ctrl+C 可触发 Qt 退出和轮询清理
- **测试覆盖**：新增 REST API 测试和真实 gRPC channel 集成测试，前端通过 TypeScript 检查与 Vite 构建

### Vue 控制台操作优化

- **手机 PPT 遥控增强**：移动端播放页新增当前页进度、PPT 源快速打开、首页 / 末页、±5 页快跳、页码步进和操作发送反馈
- **触控防误操作**：播放控制页对连续点击进行操作去重，翻页按钮按当前页边界禁用，遥控卡片支持左右滑动翻页
- **移动入口优化**：手机访问根路径时默认进入播放控制页，顶部导航和窗口选择器改为触控友好的横向 / 网格布局

### Web 控制台接管本地控制

- **控制窗口移除**：删除 PySide 本地控制面板，`run_player` 和 `runall` 启动后只保留启动器与播放窗口
- **Web 操作补齐**：播放控制页新增媒体源下拉打开入口，设置页窗口卡片新增 PPT/视频进度展示
- **手机 PPT 遥控**：手机端播放控制页新增 PPT 遥控器，支持大按钮翻页、左右滑动翻页和页码跳转
- **前端修复**：修复事件委托下按钮加载态绑定到 `document` 的问题，预案激活后立即应用返回的窗口快照
- **低延迟状态**：播放器默认轮询间隔降至 `0.2s`，gRPC 状态流增加事件唤醒与 DB 快照去重推送
- **文档同步**：使用文档和 API 文档更新为 Web 控制台统一控制流程

## 2026-04-24

### 预案系统增强

- **当前状态捕获**：新增 `CaptureScenario` gRPC 接口，支持从窗口 1/2 当前播放状态创建预案或覆盖已有预案
- **前端入口**：预案编辑器新增“保存当前状态”操作，编辑模式下覆盖前会二次确认
- **列表可读性**：gRPC 预案列表补充窗口源名称，前端摘要显示源名、自动播放和进度策略
- **客户端修复**：修复 gRPC-Web 一元调用和流式事件返回值与调用方 `toObject()` 使用不一致的问题
- **测试覆盖**：补充预案捕获、覆盖已有预案和源名称序列化测试

### Fluent 2 前端视觉与交互优化

- **设计令牌**：重整前端 CSS 令牌为中性背景、8px 圆角、轻量阴影、语义色和统一焦点描边
- **控制台布局**：优化顶栏、工具栏、Tab、面板、媒体源表单和窗口状态卡片的密度与响应式布局
- **状态表达**：运行状态、gRPC 连接、窗口会话和设置页状态统一使用语义色圆点与标签
- **预案列表安全**：预案名称与描述动态渲染时进行 HTML 转义，并移除内联样式以便统一维护
- **可访问性**：新增跳转主内容入口，保留键盘焦点可见性，降低移动端控件换行和重排风险

### 操作逻辑、状态推送与静态检查修复

- **启动器修复**：修复 `launcher_gui.py` 中 DEBUG 文案读取未定义变量导致启动器构建失败的问题
- **前端操作去重**：移除源列表刷新时重复注册的点击委托，避免刷新次数增加后一次点击触发多次打开或删除请求
- **状态推送解锁**：调整 SSE 与 gRPC 流式推送逻辑，避免在持有事件锁时向客户端 `yield`，降低慢客户端阻塞后续状态发布的风险
- **播放器轮询优化**：移除会吞掉连续相同指令的 hash 去重逻辑，并跳过无变化状态的重复 DB 上报
- **质量检查**：补充 SSE 锁释放与拼接同步回归测试，配置 Ruff 忽略生成代码并清理未使用导入

## 2026-04-21

### uv 依赖管理迁移与仓库清理

- **uv 项目入口**：新增 `pyproject.toml`、`.python-version` 与 `uv.lock`，将 `uv` 作为 Python 依赖与锁文件的主入口
- **依赖分组**：将 `pytest`、`pytest-django`、`ruff` 纳入 `dev` 依赖组，`uv sync` 默认同步开发依赖
- **运行工作流**：README 与 `docs/使用文档.md` 统一切换为 `uv python install`、`uv sync`、`uv run python manage.py ...` 与 `uv run pytest ...`
- **仓库清理**：更新 `.gitignore`，恢复误删的需求文档与第三方工具说明，继续忽略本地运行产物和第三方二进制文件


## 2026-04-20

### 前端 gRPC-Web 迁移

- **通信层**：前端从 HTTP 全面迁移至 gRPC-Web，文件上传保留 HTTP POST
- **Proto 扩展**：新增 10 个 RPC（源管理、循环、拼接、窗口 ID、全窗口快照、流式推送），所有请求消息添加 `window_id` 字段
- **gRPC 服务端**：实现所有新 RPC 的 Servicer 方法，新增 `WatchPlaybackState` 服务端流
- **gRPC-Web 基础设施**：生成 JS 桩代码（protoc-gen-js + protoc-gen-grpc-web），esbuild 打包为 ESM bundle，`@grpc-web/proxy` 集成到 `runall` 命令
- **HTML 重构**：移除所有内联 `onclick`/`onchange` 处理器（27 处），改用 `data-action` 声明式属性 + 事件委托；修复模板变量 Bug（`session.loop_enabled` 等未定义、硬编码窗口数）
- **JS 重构**：
  - `app.js`：移除 `window.*` 全局注册，改用 `ACTION_HANDLERS` 事件委托
  - `windows.js`：`fetchAllSessions()` / `showWindowIds()` 改用 gRPC 调用，字段名从 snake_case 迁移至 camelCase
  - `sources.js`：列表刷新、打开/删除源改用 gRPC，文件上传保留 HTTP，修复拖拽文件赋值兼容性
  - `playback.js`：全部控制操作改用 gRPC，状态更新依赖流式推送
  - `scenarios.js`：预案 CRUD 改用 gRPC（`listScenarios` / `createScenario` / `updateScenario` / `deleteScenario` / `activateScenario`）
  - `streaming.js`（新建）：替代 SSE 模块，使用 `WatchPlaybackState` gRPC 流式订阅 + 指数退避重连
  - `utils.js`：移除不再使用的 `postAction` HTTP 函数
  - `sse.js`：已删除（由 `streaming.js` 取代）
- **CSS 修复**：添加 Firefox `::-moz-range-thumb` 滑块样式
- **base.html**：加载 gRPC-Web bundle、更新连接状态标签和页脚文案

## 2026-04-19

### 预案系统

- **数据模型**：新增 `PlaybackScenario` 模型，包含窗口 1/2 源绑定、自动播放、保留进度等字段
- **服务层**：新增 `scp_cv.services.scenario` 模块，提供预案的 CRUD 和一键激活逻辑
- **HTTP 接口**：新增 5 个预案管理端点（列表 / 创建 / 更新 / 删除 / 激活）
- **gRPC 接口**：proto 新增 `ListScenarios` / `CreateScenario` / `UpdateScenario` / `DeleteScenario` / `ActivateScenario` 五个 RPC 方法及对应消息类型
- **gRPC-Web**：`grpc-client.js` 新增预案管理函数，bundle 已同步重建
- **前端 UI**：控制台新增「预案管理」Tab（第 4 个），包含预案列表、创建/编辑表单、一键激活功能
- **JS 模块**：新增 `static/js/scenarios.js` 模块（预案 CRUD、编辑器表单交互、列表动态刷新）
- **文档**：`docs/API.md` 同步补充预案相关 HTTP 及 gRPC 接口说明

## 2026-04-18

### DEBUG 模式显示器限制解除

- **启动器 GUI**：DEBUG 模式下不再要求显示器数量 ≥ 窗口数，始终开放全部 4 个窗口
- **屏幕复用**：DEBUG 模式下同一显示器可分配给多个窗口（已分配屏幕不再灰显禁用）
- 仅影响 `launcher_gui.py`，正常模式行为不变

### 前端 JS 模块化拆分 & 多窗口 UI

- **JS 模块化**：app.js 拆分为 7 个 ES 模块（utils / tabs / windows / sources / playback / sse / app），base.html 改为 `type="module"` 加载
- **多窗口 UI**：播放 Tab 新增窗口选择器导航（4 窗口按钮 + 显示 ID 按钮），设置 Tab 新增窗口状态网格卡片
- **CSS**：新增 `.window-selector` / `.window-status-grid` / `.window-status-card` / `.toolbar__active-window` 组件样式及响应式规则
- **多窗口播放 URL**：所有前端播放/源操作 URL 改为 `/playback/${windowId}/xxx/` 动态路径
- **SSE 适配**：事件处理兼容 `{sessions:[...]}` 多窗口快照格式

### SHOW_ID 指令

- **数据模型**：`PlaybackCommand` 枚举新增 `SHOW_ID`
- **HTTP 接口**：新增 `POST /playback/show-ids/`，触发所有窗口显示 5 秒 ID 覆盖层
- **播放器控制器**：`_handle_show_id` 调用 `window.show_id_overlay()`

### PySide GUI 控制面板（窗口 0）

- **新增 `control_panel.py`**：Fluent 2 风格控制面板，与 Web 前端功能对等
  - 4 窗口状态卡片（状态/源名/进度实时刷新）
  - 源选择下拉框 + 打开/关闭
  - 播放/暂停/停止/翻页/循环控制
  - 显示窗口 ID
  - QTimer 定时轮询 DB 状态更新 UI
- **run_player.py 集成**：启动器分配屏幕后自动在 GUI 屏幕居中显示控制面板

### 多窗口输出架构改造

- **数据模型**：`PlaybackSession` 新增 `window_id` 字段（PositiveSmallIntegerField, unique），标识所属输出窗口
- **服务层**：所有 playback 函数增加 `window_id` 参数，新增 `get_all_sessions()`、`get_all_sessions_snapshot()` 等多窗口相关函数
- **播放控制器**：改为多适配器架构（`_adapters: dict[int, SourceAdapter]`），按 window_id 分别创建、轮询、销毁适配器
- **播放窗口**：`window_id` 改为 int 类型，启动时 5 秒显示窗口编号 Overlay
- **启动器 GUI**：逐窗口弹出屏幕选择对话框，支持 4 个独立输出窗口分配到不同屏幕
- **HTTP 路由**：播放控制接口路径改为 `/playback/<window_id>/xxx/`，移除旧 `/display/switch/`
- **gRPC**：`_extract_window_id()` 从请求中提取 window_id，缺省回退到窗口 1 保持向后兼容
- **测试**：全部播放服务测试用例更新为传递 `window_id=1`
- **迁移**：`0007_add_window_id` 添加窗口编号字段

## 2026-04-17

### SRT 直接播放——旧低延迟引擎

- **架构切换**：RTSP 拉流链路替换为 SRT 直连，路径变为 OBS → SRT(30ms) → MediaMTX → SRT read → 播放内核 → PySide6 QWidget，延迟目标 < 200ms
- **新增 SrtStreamAdapter**：通过播放器内核嵌入 Qt 窗口，低延迟配置包括禁用缓存和追实时播放
- **新增下载脚本**：`tools/download_third_party.ps1` 自动准备 SRT 播放运行时
- **数据模型**：新增 `SourceType.SRT_STREAM`，保留 `RTSP_STREAM` 向后兼容
- **Proto 更新**：新增 `SOURCE_SRT_STREAM(8)`
- **服务层**：新增 `get_srt_read_url()`，`sync_streams_to_media_sources()` 改用 SRT URL
- **适配器工厂**：所有流类型映射到 `SrtStreamAdapter`，保留旧别名
- **依赖**：`requirements.txt` 添加 SRT 播放内核 Python 绑定
- **MediaMTX**：关闭 WebRTC 服务（`webrtc: false`）

### MediaMTX 低延迟参数优化

- **writeQueueSize**：512 → 8，大幅缩减内部缓冲队列深度，减少排队延迟
- **readTimeout**：10s → 3s，更快检测断流
- **writeTimeout**：10s → 3s，更快检测写超时

## 2026-04-16

### GStreamer 移除与 RTSP 播放重构

- **架构切换**：移除全部 GStreamer/PyGObject/WebRTC 依赖，改用 OBS → SRT(30ms) → MediaMTX → RTSP → QMediaPlayer(FFmpeg 后端) 链路
- **新增 RtspStreamAdapter**：基于 QMediaPlayer + QVideoWidget + QAudioOutput，支持硬件解码（DXVA2/D3D11VA）
- **删除文件**：`gst_pipeline.py`、`frame_sync.py`、`webrtc_stream.py`、`whep_client.py`、`install_pygobject.py`
- **MediaMTX 配置**：启用 SRT(8890) 和 RTSP(8554)，关闭 WebRTC
- **数据模型**：`SourceType.WEBRTC_STREAM` → `SourceType.RTSP_STREAM`
- **Proto 更新**：`SOURCE_WEBRTC_STREAM` → `SOURCE_RTSP_STREAM`
- **依赖精简**：从 `requirements.txt` 移除 `PyGObject>=3.50.0`

### PPT 放映窗口嵌入 PySide 播放器

- **窗口嵌入重构**：通过 `win32gui.SetParent()` 将 PowerPoint 放映窗口嵌入到 PySide `_video_container` 中，解决 PPT 独立窗口被播放器窗口過盖的问题
- **窗口样式处理**：移除 `WS_OVERLAPPEDWINDOW` 边框、添加 `WS_CHILD`、清除 `WS_EX_TOPMOST`
- **HWND 获取**：优先通过 COM `SlideShowWindow.HWND`，回退到枚举 `screenClass` 窗口
- **关闭安全**：关闭前先解除父窗口关系，避免影响 PySide 窗口
- **播放器日志**：`run_player` 命令添加 `logging.basicConfig()`，确保播放器模块日志输出到控制台

### 新增图片/网页适配器与视频循环播放

- **ImageSourceAdapter**：新增静态图片显示适配器，使用 `QLabel` + `QPixmap` 实现等比缩放显示
- **WebSourceAdapter**：新增网页显示适配器，使用 `QWebEngineView` 嵌入 Chromium 引擎渲染网页
- **视频循环播放**：
  - `PlaybackSession` 新增 `loop_enabled` 字段
  - `VideoSourceAdapter` 监听 `mediaStatusChanged` 信号，`EndOfMedia` 时自动重头播放
  - 前端新增循环播放切换按钮（`action-button--active` 样式）
- **Web URL 添加表单**：前端新增网页源 URL 输入表单与 `add_web_url` 服务
- **pywin32 依赖**：`requirements.txt` 添加 `pywin32>=310`，修复 PPT COM 自动化 `No module named 'pythoncom'` 错误
- **WebRTC 代码审查**：确认 GStreamer 管线、bus sync message、WHEP SDP 交换逻辑正确，显示问题为运行环境问题（MediaMTX 未启动或无源推流）

## 2026-04-15

### 播放器线程模型修复

- **ICE 候选收集超时修复**：新增 GLib 事件泵（QTimer 10ms），在 Qt 主线程迭代 `GLib.MainContext.default()`，驱动 GStreamer `webrtcbin` 信号分发
- **QObject 跨线程错误修复**：重构指令分发架构，轮询线程仅读取 DB 并发射 `sig_dispatch_command` Qt 信号，所有适配器操作（创建/控制 Qt widget、COM 对象、GStreamer 管线）在 Qt 主线程执行
- **GStreamer 管线非阻塞化**：`GstWebRTCPipeline` 拆分为 `build_pipeline()` + `start_playing()` + `on_ice_complete` 回调 + `set_remote_answer()`，ICE 完成后在工作线程异步执行 WHEP SDP 交换

### 前端页面全面改进

- **CSS 增强**：新增加载 spinner 动画、按钮禁用态样式、确认弹窗样式、`focus-visible` 焦点可见性、通知横幅动画、改进空状态视觉
- **JS 增强**：新增 `withLoading()` 防重复提交机制、`confirmAction()` 删除确认弹窗、改进通知系统（错误消息不自动隐藏）、Tab 键盘左右箭头导航
- **HTML 增强**：替换 emoji 图标为内联 SVG 图标、全面添加 ARIA 属性（`role`、`aria-label`、`aria-live`）、添加全局加载遮罩与确认弹窗容器

### 静态文件 404 修复

- 修复 `DEBUG=False` 时静态文件不可访问的问题：在 `urls.py` 中无条件注册 `/static/` 和 `/media/` 路由
- 修复 `STATIC_URL` 为绝对路径 `/static/` 以避免相对路径解析问题

## 2026-04-14

### GStreamer 运行时修复（集成测试通过）

- 修复 `Gst.init_check(None)` 在 PyGObject 3.50.x 下不接受 `None` 的 TypeError：改为传空列表 `[]`
- 修复 `check_gstreamer_available()` 在 Windows 上 `import gi` 前未配置 DLL 搜索路径导致 `_gi.pyd` 加载失败
- 集成测试验证：`manage.py runall` → MediaMTX + Django + GStreamer+PySide6 播放器正常启动

### PyGObject 安装脚本修复（实测通过）

- 修复 `install_pygobject.py` 中 Meson 找不到 `pkg-config.exe` 的问题：将 GStreamer `bin/` 目录注入构建环境 PATH
- 修复 PyGObject 版本兼容性：固定 `PyGObject>=3.50.0,<3.52`（3.52+ 要求 `girepository-2.0`，GStreamer MSVC 仅提供 `gobject-introspection-1.0`）
- 正确处理 Windows 环境变量大小写（`PATH` vs `Path`）
- 实测验证：PyGObject 3.50.2 + pycairo 1.29.0 在 MSVC 环境下编译安装成功

### GStreamer 多变体支持

- `player/__init__.py` 重构为多后端自动检测，按优先级：MSVC x86_64 → MinGW x86_64 → MSYS2 MinGW64 → 通用 x86_64
- `install_pygobject.py` 支持多编译器：优先 MSVC（通过 vcvarsall.bat 注入完整环境），回退到 GCC
- `install_pygobject.py` 支持多 GStreamer 变体的 pkgconfig 自动检测
- 所有错误提示从 MSVC 专用改为列出所有支持的变体
- 不再强制依赖 Visual Studio，可使用 GCC（Scoop / MSYS2）作为替代

### PyGObject Windows 安装修复

- 新增 `tools/install_pygobject.py` 辅助脚本，解决 Windows 上 Meson 找到 Git 的 `link.exe` 而非 MSVC `link.exe` 导致编译失败的问题
- GStreamer 安装要求从 Typical（Runtime Only）调整为 Complete（包含 gobject-introspection 开发文件）
- 更新所有 GStreamer 相关错误提示：https://gstreamer.freedesktop.org/download/ → Complete 选项 + install_pygobject.py
- 更新 README.md 环境要求：新增 Visual Studio 依赖说明、GStreamer Complete 选项
- 更新使用文档：重写 2.5 章节 GStreamer 安装步骤、新增 PyGObject 安装说明、新增 FAQ 条目

### README.md 重写

- 参考开源项目规范全面重写 README.md
- 新增：功能特性摘要、架构概览图、技术栈表格、快速开始指南、目录结构说明、端口汇总、测试命令
