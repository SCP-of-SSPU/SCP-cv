# CHANGELOG

## 2026-04-10

### mpv 低延迟流播放

- 播放器从 QMediaPlayer（2-5s 延迟）切换到 mpv/libmpv 嵌入式低延迟播放（200-500ms）
- `window.py`：新增 mpv 容器层，延迟初始化 mpv 实例，配置 `low-latency` profile + `no-cache` + `untimed`
- `controller.py`：流播放 URL 从 RTSP 中转切换为 SRT 直连读取（`srt://...?streamid=read:<path>&latency=100000`）
- 新增依赖：`python-mpv==1.0.8`，`libmpv-2.dll` 置于 `tools/third_party/mpv/`
- QMediaPlayer 仍保留用于 PPT 内嵌本地媒体播放

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
