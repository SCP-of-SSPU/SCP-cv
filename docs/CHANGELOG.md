# CHANGELOG

## 2026-04-14

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
