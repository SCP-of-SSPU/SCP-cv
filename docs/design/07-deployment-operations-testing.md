# 部署运维与验收设计

本文说明 SCP-cv 的 Windows 部署、运行编排、日志、备份、测试和现场故障定位。它面向后续把本项目迁移合并到目标 Django + Fluent + Vue 项目时的交付和运维团队。

最后更新：2026-06-04。

## 部署目标

SCP-cv 当前部署模型是 Windows-first、single-host、多进程。目标机器同时承担控制台后端、前端开发服务或静态服务、MediaMTX、PySide6 播放器和四个物理输出窗口。

```text
Windows 主机
  Django REST / gRPC / SSE
  Vue Vite dev server 或构建产物
  MediaMTX
  PySide6 Player
  SQLite / media / logs
  Office / WPS / LibreOffice / VLC runtime
```

迁移后如果目标系统有统一部署平台，也应把播放器和 MediaMTX 作为本机运行组件管理，而不是作为普通 Web Worker 管理。

## 环境要求

| 项 | 要求 |
| --- | --- |
| OS | Windows 10/11 |
| Python | 3.12+，由 `uv` 管理 |
| Node.js | 20+ |
| DB | 当前为本机 SQLite |
| Office | Microsoft PowerPoint 默认 PPT 后端 |
| WPS | 可选 PPT 后端，需要 COM 注册 |
| LibreOffice | 推荐安装，用于 PPT 播放、预览和导出后端 |
| VLC | SRT/RTSP/custom stream 播放必需 |
| MediaMTX | SRT 接收和 RTSP 读取 |
| 显示器 | 现场四窗口输出需要 Windows 能枚举物理屏幕 |

第三方 runtime 约定：

| 资产 | 路径 |
| --- | --- |
| MediaMTX | `tools/third_party/mediamtx/mediamtx.exe` |
| MediaMTX config | `tools/third_party/mediamtx/mediamtx.yml` |
| 项目内 VLC | `tools/third_party/vlc/runtime/` |
| 系统 VLC 兜底 | `C:/Program Files/VideoLAN/VLC` |

## 配置来源

| 文件 | 内容 |
| --- | --- |
| `.env` | Django、gRPC、MediaMTX、日志、PPT、直播低延迟、LibreOffice 配置 |
| `frontend/.env` | Vite 前端端口和 `VITE_BACKEND_TARGET` |
| `config.toml` | 固定启动数据，当前主要是默认管理员 |
| `tools/third_party/mediamtx/mediamtx.yml` | MediaMTX 自身配置 |

`runall` 启动 Vite 前会清理父进程继承的 `VITE_*` 变量，使 `frontend/.env` 成为前端实际配置来源。只有当前端 env 文件未设置 `VITE_BACKEND_TARGET` 时，`runall` 才注入后端兜底地址。

## 启动命令

推荐全栈启动：

```powershell
uv run python manage.py runall
```

常用模式：

| 命令 | 用途 |
| --- | --- |
| `uv run python manage.py runall --backend-host 0.0.0.0 --frontend-host 0.0.0.0` | 局域网访问 |
| `uv run python manage.py runall --skip-mediamtx` | 已手动启动 MediaMTX |
| `uv run python manage.py runall --skip-player` | 调试后端/前端，不启动播放器 |
| `uv run python manage.py runall --skip-frontend` | 只启动后端、流服务和播放器 |
| `uv run python manage.py runall --headless` | 无 launcher，按默认显示器映射创建窗口 |
| `uv run python manage.py runall --headless --service` | 从非交互终端拉起活动桌面运行 |
| `uv run python manage.py runall --headless --window1 1 --window2 2 --window3 3 --window4 4 --gpu 0` | 显式窗口和 GPU 映射 |

分进程调试：

```powershell
uv run python manage.py runserver
npm --prefix frontend run dev
uv run python manage.py run_player
./tools/third_party/mediamtx/mediamtx.exe ./tools/third_party/mediamtx/mediamtx.yml
```

## runall 编排

主文件：`scp_cv/apps/dashboard/management/commands/runall.py`。

| 步骤 | 行为 |
| --- | --- |
| 1 | 创建 `logs/runall/<timestamp>/` |
| 2 | 启动 MediaMTX，除非 `--skip-mediamtx` |
| 3 | 启动 gRPC-Web proxy |
| 4 | 启动 Django |
| 5 | 等待端口就绪 |
| 6 | 重置所有 playback sessions 到 idle |
| 7 | 启动 Vite，除非 `--skip-frontend` |
| 8 | 启动 PySide player，除非 `--skip-player` |
| 9 | 监控子进程和 `logs/runall.shutdown` |
| 10 | 退出时清理进程树 |

`/api/system/shutdown/` 会请求关闭全部窗口并写入 `logs/runall.shutdown`，runall 监控到后退出整个栈。

## 端口

| 端口 | 服务 |
| --- | --- |
| 5173 | Vue 控制台 |
| 8000 | Django REST / admin / media |
| 50051 | gRPC |
| 8890 | MediaMTX SRT publish/read |
| 9997 | MediaMTX API |

gRPC-Web proxy 端口由 runall 参数和配置决定，迁移时需同时检查前端或自动化系统是否依赖 gRPC-Web。

## 运行数据

| 路径 | 内容 | 迁移处理 |
| --- | --- | --- |
| `db.sqlite3` | 当前状态库和命令总线 | 迁移前备份，迁移时保留状态语义 |
| `media/uploads/` | 上传文件 | 需要随数据库迁移 |
| `media/ppt_previews/` | PPT slide 预览 | 可重建，但迁移可保留减少首次加载 |
| `media/ppt_playback/` | `.ppsx/.pps` 播放缓存 | 可重建，建议按源 digest 校验 |
| `logs/` | app/runall/调试日志 | 不迁移为业务数据 |
| `staticfiles/` | collectstatic 输出 | 可重建 |

清空运行数据：

```powershell
uv run manage.py clearall
```

该命令会删除 SQLite、media 和 logs 后重新迁移，只保留 `config.toml` 固定数据。它不暴露 REST API。

## 日志

| 日志 | 说明 |
| --- | --- |
| `logs/app/scp-cv.log` | Django 应用日志，RotatingFileHandler |
| `logs/runall/<timestamp>/django.log` | runall 启动的 Django 子进程输出 |
| `logs/runall/<timestamp>/frontend.log` | Vite 输出 |
| `logs/runall/<timestamp>/player.log` | PySide 播放器输出 |
| `logs/runall/<timestamp>/mediamtx.log` | MediaMTX 输出 |
| `logs/runall/service/` | `--service` 后台启动日志 |
| `logs/runall.shutdown` | 系统关机哨兵文件 |

迁移到目标运维平台时，应保留按子进程拆分日志的能力。播放器日志和 Django 日志必须分开，否则 Qt/COM/libVLC 的现场错误很难定位。

## 备份与恢复

最小备份集：

| 数据 | 原因 |
| --- | --- |
| `db.sqlite3` | 媒体源、会话、场景、背景音乐、流状态 |
| `media/uploads/` | 上传媒体文件 |
| `media/ppt_previews/` | 可选，PPT 预览缓存 |
| `media/ppt_playback/` | 可选，PPT 播放缓存 |
| `.env` 和 `frontend/.env` | 本机端口、PPT、MediaMTX、局域网访问配置 |
| `config.toml` | 固定管理员等启动数据 |

恢复顺序：

| 步骤 | 行为 |
| --- | --- |
| 1 | 停止 runall、Django、播放器、MediaMTX |
| 2 | 恢复 `.env`、`frontend/.env`、`config.toml` |
| 3 | 恢复 SQLite 和 media |
| 4 | 运行 `uv run python manage.py migrate` |
| 5 | 运行 `uv run python manage.py check` |
| 6 | 启动 `runall` 验证现场输出 |

## 测试命令

完整验证：

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

重点测试：

| 命令 | 覆盖 |
| --- | --- |
| `uv run pytest tests/test_runall_command.py -v` | runall 编排 |
| `uv run pytest tests/test_playback_service.py -v` | 播放服务 |
| `uv run pytest tests/test_rest_api.py -v` | REST API |
| `uv run pytest tests/test_grpc_servicers.py -v` | gRPC |
| `uv run pytest tests/test_player_controller.py -v` | 播放器控制器 |
| `uv run pytest tests/test_mediamtx_service.py -v` | MediaMTX |
| `uv run pytest tests/test_ppt_adapter.py -v` | PPT adapter |
| `uv run pytest tests/test_ppt_router.py tests/test_ppt_libreoffice_adapter.py tests/test_ppt_libreoffice_window.py tests/test_ppt_preview.py -v` | PPT 路由、LibreOffice、预览 |
| `uv run pytest tests/test_srt_stream_adapter.py -v` | SRT/libVLC adapter |
| `uv run pytest tests/test_volume_service.py -v` | 系统音量 |
| `uv run pytest tests/test_device_service.py -v` | 设备 TCP 指令 |

文档-only 修改通常不需要运行完整测试，但发布前应至少确认链接和 Markdown 格式，且不要引入与代码不一致的命令。

## 物理烟测

服务：`scp_cv/services/physical_smoke.py`。

接口：`POST /api/playback/physical-smoke/`。

| 步骤 | 行为 |
| --- | --- |
| 1 | 选取每类最新可用源，或使用请求中的 source_ids |
| 2 | 依次在选定窗口测试 image、video、web、ppt、srt/custom/rtsp |
| 3 | 等待 session 到达 `PLAYING` 且 source 匹配 |
| 4 | PPT 额外等待页码或总页数有效 |
| 5 | 测试背景音频 |
| 6 | 关闭源并等待 idle |
| 7 | 默认 reset-all 和停止背景音频 |

默认超时包括普通源 30 秒、PPT 120 秒、流 45 秒、总超时 540 秒。该接口是真实物理播放测试，不是单元测试；现场执行前应确认窗口和音频输出不会影响正在使用的系统。

## 故障定位

| 现象 | 优先检查 |
| --- | --- |
| 控制台 401 | 登录态、CSRF、`ApiAuthMiddleware`、cookie SameSite |
| SSE 不更新 | `/api/events/`、浏览器 EventSource、Django 日志、DB 是否被播放器写回 |
| 播放器不启动 | 是否活动桌面、PySide6、GPU 参数、`player.log` |
| 只启动后无窗口 | headless 显示器 ID 是否存在，launcher 是否选择窗口 |
| REST 发命令无反应 | `PlaybackSession.pending_command` 是否写入，播放器是否注册该窗口 |
| PPT 无法打开 | `ppt_backend`、Office/WPS COM 注册、LibreOffice 路径、bridge 日志 |
| PPT 卡在加载 | PPT 导出超时、LibreOffice bridge 超时、外部窗口 HWND 查找 |
| 直播黑屏 | MediaMTX path、RTSP/SRT read URL、VLC runtime、网络缓存、OBS 推流状态 |
| Web 页面空白 | QWebEngine、目标 URL、证书/登录状态、web 预热复用 |
| 显示器不对 | `screeninfo` 枚举、Windows 显示器编号、DPI、`target_display_label` |
| 设备无反应 | 现场 IP、端口 8889、TCP 指令、设备电源和网络 |
| 系统音量失败 | Windows Core Audio 权限，`RuntimeState` fallback |

## 发布前检查

| 类别 | 检查项 |
| --- | --- |
| 依赖 | `uv.lock`、`frontend/package-lock.json` 与源码一致 |
| 迁移 | `makemigrations --check --dry-run` 无新迁移 |
| 构建 | 前端 typecheck/build 通过 |
| 运行 | runall 能启动和关闭所有子进程 |
| 媒体 | 图片、视频、Web、PPT、直播、背景音频均可播放 |
| PPT | 三个后端按现场安装情况验证 |
| 流 | MediaMTX 自动发现和 RTSP read 验证 |
| 设备 | 拼接屏和 TV TCP 指令现场验证 |
| 文档 | README、使用文档、维护文档和设计文档同步 |

## 运维迁移建议

| 主题 | 建议 |
| --- | --- |
| 进程管理 | 目标平台应能分别启动、停止、看护 Django、MediaMTX、Player、Frontend |
| 日志 | 保留子进程日志拆分，并把 runall 日志纳入统一采集 |
| 备份 | DB 和 media 必须同周期备份，避免源记录和文件脱节 |
| 配置 | 后端 `.env` 与前端 `frontend/.env` 分开管理 |
| 权限 | 运行用户必须能访问显示器、音频设备、Office COM 和本地文件 |
| 监控 | 至少监控端口、播放器进程、MediaMTX API、SSE 新鲜度 |
| 灰度 | 先在单窗口和 skip-mediamtx 模式验证，再接入全四屏和真实设备 |
