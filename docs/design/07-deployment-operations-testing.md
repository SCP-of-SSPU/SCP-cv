# 部署运维与验收设计

本文说明 SCP-cv 的 Windows 部署、运行编排、日志、备份、测试和现场故障定位。它面向后续把本项目迁移合并到目标 Django + Fluent + Vue 项目时的交付和运维团队。

最后更新：2026-07-11。

## 部署目标

SCP-cv 当前部署模型是 Windows-first、single-host、多进程。目标机器同时承担控制台后端、前端开发服务或静态服务、MediaMTX、当前 Windows Session 唯一的 PowerPoint Broker、PySide6 播放器和四个物理输出窗口。

```text
Windows 主机
  Django REST / gRPC / SSE
  Vue Vite dev server 或构建产物
  MediaMTX
  PowerPoint Broker（AF_PIPE + 单一 COM STA / Application）
  PySide6 Player
  SQLite / media / logs
  PowerPoint / VLC runtime
```

迁移后如果目标系统有统一部署平台，也应把 Broker、播放器和 MediaMTX 作为本机运行组件管理，而不是作为普通 Web Worker 管理。Broker 与播放器必须处于当前登录用户的同一活动桌面 Session。

## 环境要求

| 项 | 要求 |
| --- | --- |
| OS | Windows 10/11 |
| Python | 3.12+，由 `uv` 管理 |
| Node.js | 20+ |
| DB | 当前为本机 SQLite |
| PowerPoint | 唯一支持的 PPT 播放、预览和导出组件 |
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
| `.env` | Django、gRPC、MediaMTX、日志、PPT 和直播低延迟配置 |
| `frontend/.env` | Vite 前端端口和 `VITE_BACKEND_TARGET` |
| `config.toml` | 固定启动数据，当前主要是默认管理员 |
| `tools/third_party/mediamtx/mediamtx.yml` | MediaMTX 自身配置 |
| `%LOCALAPPDATA%/SCP-cv/runtime/` | Broker 管道诊断元数据和本机认证密钥；不得提交或跨主机复制 |

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
uv run python manage.py run_ppt_broker
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
| 8 | 若当前 Session 有健康 Broker 则记录 PID+generation 并复用；否则启动 required 自有 Broker 并等待 AF_PIPE readiness |
| 9 | 启动 PySide player，除非 `--skip-player` |
| 10 | 监控子进程、Broker 身份和 `logs/runall.shutdown` |
| 11 | 反序退出：先播放器；自有 Broker 先发 `shutdown` 并等待，复用 Broker 不取得关闭所有权 |

`/api/system/shutdown/` 会请求关闭全部窗口并写入 `logs/runall.shutdown`，runall 监控到后退出整个栈。运行中 Broker health 的 PID 或 generation 变化会按关键依赖断开处理。Broker 绝不走递归 PowerPoint 进程树终止；优雅退出超时只能处理精确的 Broker 自有进程，不能误杀其子级或用户已有 `POWERPNT.EXE`。

Broker 的 PowerPoint 所有权从 `DispatchEx` 前后进程快照建立：优先取 Application HWND 所属 PID，无法取得时只接受唯一新增的 `POWERPNT.EXE`，并保存进程创建时间。只有能定位到具体 Application 且 PID 不在启动前快照中时才允许退出；`Quit()` 失败后的强制清理还要重新核对 PID、创建时间、进程名以及无顶层窗口，任一条件无法确认就保留进程并告警。启动前已有的 PowerPoint Application 不修改全局 `DisplayAlerts`。

运行中的生产父链是 `PowerPoint SlideShowWindow → Broker 原生 host → Player 视频容器`。关闭会话前必须先隐藏并将 Broker host 从远端 Player 脱离，把 SlideShowWindow 恢复为顶层 popup 并销毁 host，再调用 `View.Exit()` 和关闭源 Presentation。最后一个公开会话也必须完整释放；Broker 只保留无窗口、无放映 HWND、无会话身份的空白 Application sentinel。并发物理冒烟会在全部公开会话关闭后重新打开四窗，验证同一 Application 在放映窗口数回到零后仍可继续 `Run()`；旧数值 HWND 被复用为普通 Application frame 不算放映残留。

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
| `db.sqlite3` | 当前状态库和 `ControlCommand` 持久化队列 | 迁移前备份，迁移时保留状态与终态确认语义 |
| `media/uploads/` | 上传文件 | 需要随数据库迁移 |
| `media/ppt_previews/` | PPT slide 预览 | 可重建，但迁移可保留减少首次加载 |
| `media/ppt_playback/` | `.ppsx/.pps` 播放缓存 | 可重建，建议按源 digest 校验 |
| `logs/` | app/runall/调试日志 | 不迁移为业务数据 |
| `staticfiles/` | collectstatic 输出 | 可重建 |

清空运行数据：

```powershell
uv run python manage.py clearall
```

该命令会删除 SQLite、media 和 logs 后重新迁移，只保留 `config.toml` 固定数据。它不暴露 REST API。

`ControlCommand` 的执行所有权不是单独一个可复用字符串：领取时同时保存随机 `consumer_id`、播放器 PID、进程创建时间和心跳。播放器每 5 秒续约，默认 30 秒租约；恢复流程只有在进程不存在、PID 创建时间不匹配或租约过期时才把旧 `executing` 记录置为失败，仍存活且心跳新鲜的其它播放器不会被新进程误清理。恢复后的指令不重放，正常退出则立即失败本进程未完成记录。

## 日志

| 日志 | 说明 |
| --- | --- |
| `logs/app/scp-cv.log` | Django 应用日志，RotatingFileHandler |
| `logs/runall/<timestamp>/django.log` | runall 启动的 Django 子进程输出 |
| `logs/runall/<timestamp>/frontend.log` | Vite 输出 |
| `logs/runall/<timestamp>/powerpoint-broker.log` | Broker 请求、COM 重试、PID/HWND 与最终结果 |
| `logs/runall/<timestamp>/pyside-播放器-<窗口号>.log` | 对应窗口的 PySide 播放器输出 |
| `logs/runall/<timestamp>/mediamtx.log` | MediaMTX 输出 |
| `logs/runall/service/` | `--service` 后台启动日志 |
| `logs/runall.shutdown` | 系统关机哨兵文件 |

迁移到目标运维平台时，应保留按子进程拆分日志的能力。Broker、播放器和 Django 日志必须分开，否则 COM、Qt 与 libVLC 的现场错误很难定位。认证密钥不得进入任何日志。

## 备份与恢复

最小备份集：

| 数据 | 原因 |
| --- | --- |
| `db.sqlite3` | 媒体源、会话、场景、背景音乐、流状态 |
| `media/uploads/` | 上传媒体文件 |
| `media/ppt_previews/` | 可选，PPT 预览缓存 |
| `media/ppt_playback/` | 可选，PPT 播放缓存 |
| `.env` 和 `frontend/.env` | 本机端口、PowerPoint 超时、MediaMTX、局域网访问配置 |
| `config.toml` | 固定管理员等启动数据 |

`%LOCALAPPDATA%/SCP-cv/runtime/ppt-broker.auth` 是当前主机和用户 Session 的运行时密钥，不属于业务备份集。恢复到另一台主机时应由 Broker 重新生成。

恢复顺序：

| 步骤 | 行为 |
| --- | --- |
| 1 | 停止 runall、Django、播放器、PowerPoint Broker、MediaMTX |
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
| `uv run pytest tests/test_command_queue.py -v` | 指令原子领取、确认、取消、消费者租约与崩溃恢复 |
| `uv run pytest tests/test_ppt_broker.py tests/test_ppt_broker_engine.py tests/test_ppt_broker_transport.py tests/test_ppt_broker_windows.py -v` | Broker 合同、STA、AF_PIPE、会话与 HWND |
| `uv run pytest tests/test_ppt_physical_smoke.py tests/test_ppt_smoke_command.py -v` | 四窗并发、不同页码、关闭隔离、重开与 CLI 校验 |
| `uv run pytest tests/test_mediamtx_service.py -v` | MediaMTX |
| `uv run pytest tests/test_ppt_broker_adapter.py tests/test_ppt_broker_export_services.py tests/test_preheat_pool.py tests/test_player_controller_open_recovery.py -v` | Broker adapter、导出、预热与切源恢复 |
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

Broker 四窗口并发诊断使用管理命令，不通过 REST 暴露：

```powershell
uv run python manage.py ppt_smoke --windows 1,2,3,4 --source-ids 42 --iterations 3 --timeout 120
```

`--source-ids` 可给一个四窗共用 ID，或按窗口顺序给四个 ID。每个源必须是可用的本地 PPT，且满足对应目标页（窗口 1-4 分别验证第 2/3/4/5 页）。命令自动创建四个临时 Player 宿主；每轮从四个客户端线程并发提交 OPEN，但 COM 仍由唯一 STA 串行执行。验证包括唯一 HWND、Broker 状态父 HWND、严格的 `SlideShow → Broker host → Player` 两级父链（兼容直接父链）、不同页码互不串页、关闭一窗不改变其余、重开被关闭窗口以及最终全部关闭。失败输出结构化 JSON 并返回非零。旧 `run_ppt_physical_smoke --ppt ...` 保留用于路径和显式父 HWND 的兼容诊断。

开发模式还需拖动调整窗口尺寸，确认 50 ms 防抖后的 `render_viewport_resized` 经 Adapter 转成 Broker `resize` 指令，并让 host 与 SlideShowWindow 同步到 Player 当前客户区；生产模式仍固定为目标显示器全尺寸。

## 故障定位

| 现象 | 优先检查 |
| --- | --- |
| 控制台 401 | 登录态、CSRF、`ApiAuthMiddleware`、cookie SameSite |
| SSE 不更新 | `/api/events/`、浏览器 EventSource、Django 日志、DB 是否被播放器写回 |
| 播放器不启动 | 是否活动桌面、PySide6、GPU 参数、对应 `pyside-播放器-<窗口号>.log` |
| 只启动后无窗口 | headless 显示器 ID 是否存在，launcher 是否选择窗口 |
| REST 发命令无反应 | `ControlCommand` 是否为 pending/executing/failed、consumer PID/创建时间/心跳租约是否有效；不要以兼容 `pending_command` 镜像作真值 |
| PPT 无法打开 | Broker health/PID/generation、PowerPoint 安装与 COM 注册、文件权限、桌面会话 |
| PPT 卡在加载 | `powerpoint-broker.log` 的 request/source/window/PID/HWND/parent、瞬时 HRESULT 重试和最终结果 |
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
| 运行 | runall 能复用健康 Broker；自有 Broker 优雅关闭且用户已有 PowerPoint 不受影响 |
| 媒体 | 图片、视频、Web、PPT、直播、背景音频均可播放 |
| PPT | PowerPoint 导入、预览、预热、四窗唯一 HWND/两级父链、关闭隔离、重开、起始页和多窗口切源验证 |
| 流 | MediaMTX 自动发现和 RTSP read 验证 |
| 设备 | 拼接屏和 TV TCP 指令现场验证 |
| 文档 | README、使用文档、维护文档和设计文档同步 |

## 运维迁移建议

| 主题 | 建议 |
| --- | --- |
| 进程管理 | 目标平台应能分别启动、停止、看护 Django、MediaMTX、Broker、Player、Frontend，并保留 Broker 单实例与关闭所有权 |
| 日志 | 保留子进程日志拆分，并把 runall 日志纳入统一采集 |
| 备份 | DB 和 media 必须同周期备份，避免源记录和文件脱节 |
| 配置 | 后端 `.env` 与前端 `frontend/.env` 分开管理 |
| 权限 | 运行用户必须能访问显示器、音频设备、Office COM 和本地文件 |
| 监控 | 至少监控端口、播放器进程、MediaMTX API、SSE 新鲜度 |
| 灰度 | 先在单窗口和 skip-mediamtx 模式验证，再接入全四屏和真实设备 |
