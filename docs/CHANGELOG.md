# CHANGELOG

## 2026-04-19

### 预案系统

- **数据模型**：新增 `PlaybackScenario` 模型，包含窗口 1/2 源绑定、拼接模式、自动播放、保留进度等字段
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
- **多窗口 UI**：播放 Tab 新增窗口选择器导航（4 窗口按钮 + 拼接开关 + 显示 ID 按钮），设置 Tab 新增窗口状态网格卡片
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
  - 拼接模式切换 + 显示窗口 ID
  - QTimer 定时轮询 DB 状态更新 UI
- **run_player.py 集成**：启动器分配屏幕后自动在 GUI 屏幕居中显示控制面板

### 多窗口输出架构改造

- **数据模型**：`PlaybackSession` 新增 `window_id` 字段（PositiveSmallIntegerField, unique），标识所属输出窗口
- **服务层**：所有 playback 函数增加 `window_id` 参数，新增 `get_all_sessions()`、`get_all_sessions_snapshot()`、`set_splice_mode()`、`is_splice_mode_active()`、`sync_splice_command()` 等多窗口/拼接相关函数
- **播放控制器**：改为多适配器架构（`_adapters: dict[int, SourceAdapter]`），按 window_id 分别创建、轮询、销毁适配器
- **播放窗口**：`window_id` 改为 int 类型，启动时 5 秒显示窗口编号 Overlay
- **启动器 GUI**：逐窗口弹出屏幕选择对话框，支持 4 个独立输出窗口分配到不同屏幕
- **HTTP 路由**：播放控制接口路径改为 `/playback/<window_id>/xxx/`，新增 `/playback/splice/` 拼接控制端点，移除旧 `/display/switch/`
- **gRPC**：`_extract_window_id()` 从请求中提取 window_id，缺省回退到窗口 1 保持向后兼容
- **测试**：全部播放服务测试用例更新为传递 `window_id=1`
- **迁移**：`0007_add_window_id` 添加窗口编号字段

## 2026-04-17

### SRT 直接播放——mpv/libmpv 低延迟引擎

- **架构切换**：RTSP 拉流链路替换为 SRT 直连，路径变为 OBS → SRT(30ms) → MediaMTX → SRT read → mpv/libmpv → PySide6 QWidget，延迟目标 < 200ms
- **新增 SrtStreamAdapter**：基于 python-mpv + libmpv，通过 `wid` 参数嵌入 Qt 窗口，低延迟配置（`profile=low-latency, cache=no, untimed=True`）
- **新增下载脚本**：`tools/download_third_party.ps1` 自动从 GitHub Releases 下载 libmpv-2.dll
- **数据模型**：新增 `SourceType.SRT_STREAM`，保留 `RTSP_STREAM` 向后兼容
- **Proto 更新**：新增 `SOURCE_SRT_STREAM(8)`
- **服务层**：新增 `get_srt_read_url()`，`sync_streams_to_media_sources()` 改用 SRT URL
- **适配器工厂**：所有流类型映射到 `SrtStreamAdapter`，保留旧别名
- **依赖**：`requirements.txt` 添加 `python-mpv>=1.0.7`
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
