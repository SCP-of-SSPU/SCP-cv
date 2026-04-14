# CHANGELOG

## 2026-04-14

### 一键启动命令 `runall`

- 新增 `manage.py runall` 管理命令，单个终端同时启动 MediaMTX、Django 开发服务器和 PySide6 播放器
- MediaMTX 和 Django 以子进程运行，PySide6 Qt 事件循环占据主线程
- 关闭播放窗口时通过 atexit/signal 自动终止所有子进程
- 支持 `--host`、`--port`、`--skip-mediamtx`、`--poll-interval` 参数
- 播放器全屏行为由 `.env` 中 `DJANGO_DEBUG` 控制，单屏/双屏由启动器 GUI 选择
- 更新使用文档：新增一键启动说明，原分进程启动方式移至「调试用」章节
- 修复使用文档 FAQ 中 GStreamer MSVC 残留引用

### GStreamer 从 MSVC 迁移至 MinGW x86_64

- 环境变量优先检测从 `GSTREAMER_1_0_ROOT_MSVC_X86_64` 改为 `GSTREAMER_1_0_ROOT_MINGW_X86_64`
- 默认安装路径从 `C:\gstreamer\1.0\msvc_x86_64` 改为 `C:\Program Files\gstreamer\1.0\mingw_x86_64`
- 安装方式简化：使用默认安装选项即可（无需选择 Complete）
- 更新 `player/__init__.py`、`run_player.py`、文档安装说明

### 统一媒体源架构与 PPT 控制支持

- **数据模型**：新建 `MediaSource` 统一媒体源模型（PPT / VIDEO / AUDIO / IMAGE / WEBRTC_STREAM），`PlaybackSession` 关联 `MediaSource` 并新增 PPT 页码、视频进度等字段
- **Proto 更新**：`control.proto` 新增 `OpenSource`、`CloseSource`、`ControlPlayback`、`NavigateContent`、`GetPlaybackState` RPC 方法，增加 `SourceType`、`PlaybackAction`、`NavigateAction` 枚举
- **服务层**：新建 `services/media.py` 媒体源管理服务（上传、本地路径、流同步、删除、类型自动检测）；重构 `services/playback.py`（统一播放控制、导航、显示切换、快照）
- **适配器层**：新建 `player/adapters/` 统一媒体源适配器架构（`SourceAdapter` ABC + 工厂函数），实现 `PptSourceAdapter`（PowerPoint COM 放映）、`VideoSourceAdapter`（QMediaPlayer）、`WebRTCStreamAdapter`（GStreamer WHEP）
- **控制器重构**：`controller.py` 采用适配器模式，统一 `pending_command` 分发逻辑，移除旧硬编码信号
- **HTTP API**：新增 `/sources/upload/`、`/sources/add-local/`、`/sources/remove/`、`/api/sources/`、`/playback/open/`、`/playback/control/`、`/playback/navigate/`、`/playback/close/`、`/display/switch/`；移除旧接口 `/stop/`、`/open-stream/`、`/api/streams/`
- **前端重做**：`home.html` 重写为三 Tab 布局（源列表 / 播放控制 / 设置）；`app.css` 新增 PPT 翻页、视频进度条、上传区域等组件样式；`app.js` 完全重写（Tab 切换、源 CRUD、播放控制、导航/Seek、SSE 状态同步、拖拽上传）
- **测试套件**：新增 65 个单元测试，覆盖媒体源管理服务（17 项）和播放会话服务（48 项），配置 pytest + pytest-django
- **死代码清理**：移除 `views.py` 无用导入（`get_or_create_session`、`stop_current_content`）
- **文档更新**：重写 `docs/API.md` 与新 HTTP / gRPC 接口对齐；更新 `docs/使用文档.md` 的 Web 控制台、HTTP API、端口等章节

### Fluent 2 启动器 GUI：屏幕选择界面

- 新增 `player/launcher_gui.py`：Fluent 2 风格两步启动器（模式选择 → 屏幕分配）
- 单屏模式：从检测到的显示器列表点选目标
- 双屏拼接模式：为每台显示器手动指定左/右角色，同角色互斥自动清除
- `run_player` 命令：先运行启动器 GUI 后创建播放窗口，`--debug-window` 改为 `--dev`
- `--dev` 模式启动器和播放窗口均显示标题栏；非 `--dev` 启动器无边框+播放窗口全屏置顶
- GUI 关闭后自动写入会话的 display_mode / target_display_label / spliced_display_label

### 全协议迁移至 WebRTC + GStreamer 播放引擎

- **协议层**：全部流传输协议从 SRT/RTSP 迁移至 WebRTC（WHIP 推流 / WHEP 拉流）
- **播放引擎**：从 mpv/libmpv 切换为 GStreamer + webrtcbin，支持 WebRTC 原生接收和硬件加速渲染
- **多窗口架构**：每个物理屏幕对应独立 PlayerWindow + GStreamer 管线实例
- **帧同步**：新增 `FrameSyncCoordinator`，通过 GstClock 共享 + 漂移监控实现多屏帧级同步（33ms 阈值）
- **WHEP 客户端**：新增 `WhepClient`，实现 RFC 9002 WHEP 信令协商（SDP Offer/Answer + ICE）
- **MediaMTX 配置**：关闭 RTSP/RTMP/HLS/SRT 协议，仅保留 WebRTC（端口 8889）
- **依赖变更**：移除 `python-mpv`，新增 `PyGObject>=3.50.0`、`requests==2.32.3`；需安装 GStreamer MSVC Runtime
- **数据模型**：`PlaybackContentKind.STREAM` 标签从 "SRT 流" 更新为 "WebRTC 流"
- **服务层**：`get_srt_publish_url()` → `get_whip_publish_url()`，`get_rtsp_read_url()` → `get_whep_read_url()`
- 全部代码注释和文档中的 SRT 引用已更新为 WebRTC

## 2026-04-11

### 移除全部 PPT 相关代码

- 删除 `scp_cv/services/ppt_processor.py`、`scp_cv/services/resource_manager.py`
- 删除 `scp_cv/apps/resources/` 整个 Django app（models、admin、migrations）
- 删除 `tools/testdata/` 测试数据目录
- `PlaybackSession` 模型移除 `content_resource` FK、`current_page_number`、`total_pages` 字段
- `PlaybackContentKind` 移除 `PPT` 枚举值
- `settings.py` 移除 `resources` app 注册和 `LIBREOFFICE_BIN_PATH` 配置
- `grpc_servicers.py` 移除 `OpenResource`、`ControlPptPage`、`ControlCurrentMedia` 三个 RPC
- `controller.py` 移除 `sig_show_page`、`sig_play_media`、`sig_pause_media` 信号和 `_apply_ppt_state()` 方法
- `window.py` 移除 QMediaPlayer 媒体叠加层、PPT 页面图片渲染、`show_page_image()`、`play_media()` 等方法
- 前端移除文件上传面板、PPT 控件卡片、资源表格及相关 JS/CSS
- `requirements.txt` 移除 `python-pptx`、`PyMuPDF`、`Pillow`
- `download_third_party.ps1` 移除 LibreOffice 安装段落
- 数据库已重新迁移（SQLite 数据库已重建）

## 2026-04-10

### mpv 低延迟流播放

- 播放器从 QMediaPlayer（2-5s 延迟）切换到 mpv/libmpv 嵌入式低延迟播放（200-500ms）
- `window.py`：新增 mpv 容器层，延迟初始化 mpv 实例，配置 `low-latency` profile + `no-cache` + `untimed`
- `controller.py`：流播放 URL 从 RTSP 中转切换为 SRT 直连读取（`srt://...?streamid=read:<path>&latency=100000`）
- 新增依赖：`python-mpv==1.0.8`，`libmpv-2.dll` 置于 `tools/third_party/mpv/`
- ~~QMediaPlayer 仍保留用于 PPT 内嵌本地媒体播放~~ （已在 2026-04-11 移除）

### 前端流面板稳定性修复

- 移除 SSE `stream_updated` 事件监听，消除无限刷新循环
- 新增指纹变更检测 + 防抖锁，避免 DOM 无效重建
- 轮询间隔从 5s 调整到 10s

### SRT 流自动发现与注册

- 增强 `sync_stream_states()` 自动注册 MediaMTX 新发现的流路径为 `StreamSource` 记录
- 新增 `GET /api/streams/` 端点，触发同步并返回最新流列表
- 前端 5 秒轮询自动刷新流面板，新增手动刷新按钮
- SSE `stream_updated` 事件跨客户端同步流列表
- 修复 SRT 推流 URL 格式（MediaMTX v1.17+ 路径不含前导斜杠）

### 需求I 全模块实现

- **Module F（服务层）**：新建 `playback.py`、`resource_manager.py`、`ppt_processor.py`、`sse.py`，实现播放会话管理、资源上传解析、PPT 转换渲染、SSE 实时推送
- **Module A（PPT 处理）**：`ppt_processor.py` 中实现 python-pptx 解析 → LibreOffice PDF 转换 → PyMuPDF 逐页 PNG 渲染管线
- **Module D（HTTP API + 页面）**：重写 `dashboard/views.py`（13 个视图）、`urls.py`（12 条路由）、`home.html`（完整控制台 UI）、`app.js`（AJAX + SSE 客户端）、`app.css`（Fluent 2 组件样式）
- **Module C（PySide6 播放窗口）**：新建 `player/window.py`（全屏/无边框/置顶/跨屏）、`controller.py`（Django → Qt 信号桥接 + 轮询线程）、`run_player` 管理命令
- **Module B（SRT/MediaMTX）**：新建 `services/mediamtx.py`，实现 MediaMTX 进程管理、流状态同步、SRT/RTSP URL 构造
- **Module E（gRPC 服务）**：新建 `grpc_servicers.py`，实现 `PlaybackControlServicer` 全部 8 个 RPC 方法，更新 `grpc_handlers.py` 注册入口

## 2026-04-04

### 初始化

- 创建 Django 6 项目骨架和服务端渲染首页
- 接入 Fluent 2 风格的基础布局与样式
- 补齐统一播放会话、资源、流记录的数据模型
- 预留 gRPC 配置、proto 合同和第三方可执行文件下载脚本
- 增加 `.env`、依赖清单和初始项目说明
