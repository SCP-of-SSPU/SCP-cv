# SCP-cv

SCP-cv 是用于控制 **上海第二工业大学 28#108 多媒体显示系统** 的统一播放控制平台。系统在一台 Windows 主机上协同运行 Vue 控制台、Django 服务端、MediaMTX 流服务、PySide6 播放器和唯一 PowerPoint Broker，用于管理 PPT、视频、图片、网页、音频和 SRT 直播流等媒体源，将内容投放到大屏与电视窗口，并通过独立背景音乐通道输出音频。

## 项目信息

| 项目 | 内容 |
|------|------|
| 开发者 | Qintsg（饶弘玮，上海第二工业大学 25网工A2） |
| 单位 | 上海第二工业大学 / 计算机与信息工程学院 / SSPU AI-Lab / 超级棒棒糖 |
| 应用地点 | 上海第二工业大学 28#108 |
| 许可证 | Artistic-2.0 |
| 镜像仓库 | `http://git.bbt.sspu.edu.cn/Qintsg/scp-cv`（仅作为同步镜像，不作为主开发入口） |

## 核心能力

- **统一媒体源管理**：上传文件、添加本机路径、添加网页源、自动发现 MediaMTX SRT 入流并默认创建 SRT 直拉源。
- **统一预热**：媒体源可开启后台预热，网页、图片、视频、背景音频、直播流和 PPT 按类型提前准备；直播流使用 URI 级可认领预热，PPT 由 Broker 按源文件级预打开，降低现场切换等待。
- **四窗口播控**：大屏左、大屏右、TV 左、TV 右分别独立控制，支持 single / double 大屏模式。
- **背景音乐**：音频源通过独立后台播放器输出，支持播放列表、立即播放、循环、音量和静音控制。
- **PPT 控制**：所有 PPT 导入、PNG 预览、播放缓存导出、预热和放映统一使用 Microsoft PowerPoint，并集中到单一 Broker 进程、单一 COM STA 和单一 PowerPoint Application；显控页提供翻页、跳页和媒体控制。
- **持久化指令确认**：窗口 1-4 和背景音频各自使用有序命令通道，指令从待领取、执行中到成功、失败或取消均持久化记录，播放器重启不会静默覆盖或盲目重放旧指令。
- **SRT / RTSP 直播播放**：MediaMTX 接收 OBS / 外部设备 SRT 推流，自动发现源默认通过 SRT read 地址交给 libVLC 播放；RTSP 保留为手动兼容路径。
- **REST + SSE 控制台**：Vue 前端通过 REST 下发指令，通过 SSE 同步播放状态。
- **保留 gRPC 接口**：用于兼容中控系统和自动化脚本。
- **设备控制**：支持拼接屏、电视电源 TCP 指令和 Windows 系统音量同步。

## 架构概览

```text
Vue 控制台 (frontend/)
  REST / SSE
        |
Django 服务端 (REST + gRPC)
        | SQLite 播放会话状态 + ControlCommand 持久化队列
        v
PySide6 播放器 (视频 / 图片 / 网页 / SRT / 背景音乐)
        | SRT / RTSP                      | AF_PIPE（PPT 放映）
        v                                 |
MediaMTX                                 |
(publish/read)                            |
                                          v
Django PPT 导出服务 -------- AF_PIPE --> 唯一 PowerPoint Broker
                                          (单一 STA + 单一 PowerPoint Application)
                                                   |
                                 窗口化 PPT 放映 HWND 嵌入播放器窗口 1-4
```

## 环境要求

- Windows 10/11
- Python 3.12 或更高版本（推荐使用 `uv` 管理）
- Node.js 20 或更高版本
- Microsoft PowerPoint（唯一支持的 PPT 播放、预览和 show-format 导出组件）
- VLC/libVLC Windows x64 运行时（SRT 播放必需）
- MediaMTX Windows x64 可执行文件

## 快速开始

```powershell
git clone <repo-url> SCP-cv
cd SCP-cv

# 安装 uv（如本机尚未安装）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 同步 Python 依赖；本项目不再维护 requirements*.txt
uv python install
uv sync

# 安装前端依赖
npm ci --prefix frontend

# 准备本地环境变量
copy .env.example .env
copy frontend\.env.example frontend\.env

# 确认固定启动数据配置；默认管理员来自 config.toml
type config.toml

# 初始化数据库
uv run python manage.py migrate
```

第三方运行时按以下约定放置：

- `tools/third_party/mediamtx/mediamtx.exe`：MediaMTX 主程序，配置文件同目录放置。
- `tools/third_party/vlc/runtime/`：项目内置 VLC/libVLC runtime；也可以使用系统安装的 `C:\Program Files\VideoLAN\VLC`。
- Microsoft PowerPoint 需要安装在当前 Windows 用户可自动化调用的环境中，PowerPoint Broker 会尝试 PowerPoint COM ProgID。

## 环境变量

后端配置在仓库根目录 `.env`，前端 Vite 配置在 `frontend/.env`。两者分离：

- `.env`：Django、gRPC、MediaMTX、日志和后端运行配置。
- `frontend/.env`：`VITE_FRONTEND_PORT` 与 `VITE_BACKEND_TARGET`。

PPT 相关配置：

- PowerPoint 是唯一 PPT 播放器；导入、预览、播放缓存、预热和放映均不再提供后端选择。
- 支持 `.pptx/.ppt/.pps/.ppsx/.pptm/.ppsm/.pot/.potx/.potm/.odp` 等演示文件。导入后会尝试生成播放专用 `.ppsx`/`.pps` 缓存，宏格式默认导出为非宏 `.ppsx`；生成失败不阻断媒体源创建，播放时回退原始文件。
- 当前 Windows 用户和 Session 只运行一个 PowerPoint Broker。Broker 内部只有一个 COM STA，并懒加载一个供 PNG 预览导出、`.ppsx`/`.pps` 缓存导出、预热和窗口 1-4 放映共同使用的 PowerPoint Application；PySide 播放器和 Django 不再创建、复用或清理 PowerPoint COM 实例。
- PPT 媒体源启用预热时，由 Broker 以低优先级按 `source_id + uri` 执行文件级预热；前台打开、关闭和翻页等高优先级操作会先执行，命中后直接认领预打开的 Presentation。
- PPT 放映时目标 PySide 播放窗口会立即切到黑色视频容器并保持可见、置顶。Broker 保留完整放映范围，调用 `SlideShowSettings.Run()` 后对非首页目标显式执行 `GotoSlide()`；校验 `SlideShowWindow.HWND` 后，生产环境按“放映窗口 → Broker 原生 host → Player 视频容器”的两级父链嵌入。
- PPT 切换采用事务式替换：Broker 先隐藏旧放映，验证新放映和嵌入成功后才释放旧 Presentation；失败时恢复旧画面。
- 关闭放映前，Broker 会先隐藏窗口、把 host 从 Player 父链脱离、将 SlideShowWindow 恢复为隐藏顶层窗口并销毁 host，再退出 COM View、释放放映 HWND 并关闭对应源 Presentation。最后一个公开会话关闭前会创建一个无窗口、无放映、无会话身份的空白 Application sentinel，避免 PowerPoint 在 `SlideShowWindows.Count` 回到零后拒绝下一次 `Run()`；sentinel 在 Broker shutdown 时关闭。
- 开发模式窗口可调整尺寸；Player 会在 resize 稳定后通知 Adapter，PPT Adapter 通过 AF_PIPE `resize` 指令让 Broker 同步 host 与放映子窗口的客户区。
- 右上角“重置 PPT 放映”通过持久化命令批次按窗口执行关闭和重开，并恢复到重置前页码。
- PNG 预览和 `.ppsx`/`.pps` 缓存导出也通过同一 Broker/STA/Application 执行；Broker 在任务结束后关闭临时 Presentation，不影响活动放映会话。
- `PPT_PREVIEW_WORKER_TIMEOUT_SECONDS=180`：保留旧配置名，现用于限制 Broker PNG 预览导出调用的等待时间；失败或超时只会跳过预览，不阻断媒体源创建。
- `PPT_PLAYBACK_EXPORT_TIMEOUT_SECONDS=180`：限制 Broker 生成 `.ppsx`/`.pps` 播放缓存的等待时间；失败或超时只记录 metadata 并回退原始文件播放。

播放器与 Broker 通过当前用户 Session 专属的 Windows `AF_PIPE` 通信。管道地址、PID 和 Broker 代次等诊断信息写入 `%LOCALAPPDATA%\SCP-cv\runtime\ppt-broker.json`，认证密钥写入同目录的 `ppt-broker.auth`；元数据不包含密钥，不要提交或复制认证文件到仓库。

Broker 在创建 Application 前后记录 `POWERPNT.EXE` 的 PID 与创建时间，优先使用 Application HWND 对应 PID，无法读取时只接受唯一新增 PID。只有能定位到具体 Application 且未出现在启动前快照中的进程才属于 Broker；退出时先确认没有外部 Presentation，`Quit()` 失败后的强制清理还必须同时满足 PID、创建时间、进程名和无顶层窗口，无法证明归属时保留进程。

直播与低延迟相关配置：

- `MEDIAMTX_SRT_PUBLISH_LATENCY_US=30000`：SRT 推流端 URL 中的 latency，按微秒理解，默认保留现场已验证的 30ms；OBS / 编码器推流地址形如 `srt://<主机IP>:8890?streamid=publish:<流标识>&latency=30000&pkt_size=1316`。
- `MEDIAMTX_SRT_READ_LATENCY_MS=50`：播放器 SRT 拉流 URL 中的 latency，按毫秒理解，可按现场网络质量增减。
- `MEDIAMTX_RTSP_READ_TRANSPORT=tcp`：RTSP 拉流传输策略，播放器会转换为 libVLC `:rtsp-tcp` 或 `:rtsp-udp`。
- `STREAM_VLC_NETWORK_CACHING_MS=50`、`STREAM_VLC_LIVE_CACHING_MS=50`、`STREAM_VLC_FILE_CACHING_MS=0`：前台 libVLC 播放缓存参数。
- `STREAM_VLC_CLOCK_JITTER=0`、`STREAM_VLC_CLOCK_SYNCHRO=0`、`STREAM_VLC_DROP_LATE_FRAMES=True`、`STREAM_VLC_SKIP_FRAMES=True`：前台 libVLC 追实时画面的时钟与丢帧策略。
- `STREAM_PREHEAT_NETWORK_CACHING_MS=100`、`STREAM_PREHEAT_LIVE_CACHING_MS=100`：直播 URI 级预热连接使用的缓存参数。
- `STREAM_PREHEAT_TTL_SECONDS=60`：直播预热连接可被前台认领的最长保留时间。

预热行为说明：

- 图片和本地视频按 `source_id + uri` 进行文件级预热；命中后前台直接认领已加载资源。
- 背景音频按 `source_id + uri` 预设本地 `QMediaPlayer + QAudioOutput`，背景音乐打开时优先认领，音频源仍不占用四个显示窗口。
- 自动发现的 MediaMTX 在线流默认保存为 `srt://<read-host>:8890?streamid=read:<stream_identifier>&latency=<ms>`；如需 RTSP 拉流，可手动添加 RTSP / 自定义直播源。
- SRT / RTSP / 自定义直播按 `source_id + uri` 建立可认领 libVLC 预热连接；前台 `SrtStreamAdapter` 命中后复用预热的 `instance/player/media`，不再把直播预热称为文件级。

控制指令写入 SQLite `ControlCommand` 队列，窗口 1-4 与背景音频分别顺序消费。播放器原子领取最早的 `pending` 指令，执行后确认成 `succeeded`、`failed` 或 `cancelled`；终止批次可以取消尚未领取的旧指令，并给正在执行的旧指令标记取消。消费者身份由随机 `consumer_id`、PID 和进程创建时间共同确定，并周期续约心跳；恢复流程只终结进程已消失、身份不匹配或租约过期的 `executing` 记录，不会误伤仍存活并持续续约的播放器。被恢复的指令标记失败且不盲目重放，仍未领取的指令继续保留。`PlaybackSession.pending_command` 和背景音频同名字段仅作为兼容只读镜像，不再是指令真值来源。

`runall` 启动前端时会移除父进程继承的 `VITE_*` 变量，让 `frontend/.env` 成为前端开发服务的实际配置来源。若 `frontend/.env` 未配置 `VITE_BACKEND_TARGET`，`runall` 才会按当前后端监听地址提供兜底值。

局域网手机或其它控制端访问时，请把 `frontend/.env` 中的 `VITE_BACKEND_TARGET` 设置为浏览器可访问的后端地址，例如：

```env
VITE_FRONTEND_PORT=5173
VITE_BACKEND_TARGET=http://192.168.1.100:8000
```

## 启动

推荐一键启动：

```powershell
uv run python manage.py runall
```

常用参数：

```powershell
# 允许局域网访问前后端
uv run python manage.py runall --backend-host 0.0.0.0 --frontend-host 0.0.0.0

# 已手动启动 MediaMTX 时跳过
uv run python manage.py runall --skip-mediamtx

# 调试时跳过播放器或前端
uv run python manage.py runall --skip-player
uv run python manage.py runall --skip-frontend

# 无启动器 GUI 启动全部服务和 4 个播放窗口
uv run python manage.py runall --headless

# 后台启动，不绑定当前终端生命周期；输出写入 logs/runall/service/
uv run python manage.py runall --headless --service

# 指定窗口到 Windows 显示器 ID，并指定 GPU ID
uv run python manage.py runall --headless --window1 1 --window2 2 --window3 3 --window4 4 --gpu 0
```

`--headless` 默认把窗口 1/2/3/4 分别映射到 Windows 显示器 ID 1/2/3/4；`runall --headless` 会为每个窗口启动独立 PySide 播放器进程以隔离 Qt 和渲染生命周期，但所有 PPT 操作仍集中到同一个 Broker。启用播放器时，`runall` 会复用当前 Windows Session 中健康的 Broker，否则启动自有实例；两种情况都记录 PID + generation、等待 AF_PIPE readiness，并把身份变化或断开视为关键依赖退出。退出时先停止播放器；只有自有 Broker 才发送 `shutdown` 并等待，复用 Broker 不取得关闭所有权，Broker 也绝不走递归 PowerPoint 进程树终止。`--skip-player` 会同时跳过 Broker；该调试模式若仍需导入 PPT 并生成 PNG/播放缓存，应另行启动 `run_ppt_broker`。未传 `--gpu` 时使用系统默认 GPU。`--window3` 与兼容别名 `--windows3` 等价。
如果通过 SSH、OpenSSH 服务或其它非控制台会话远程启动，直接运行 `--headless` 无法访问物理显示器；请使用 `uv run python manage.py runall --headless --service`，系统会在当前登录用户的交互桌面中拉起真实 runall。

分进程调试：

```powershell
# Django REST + gRPC
uv run python manage.py runserver

# Vue 控制台
npm --prefix frontend run dev

# PowerPoint Broker（显式分进程调试时先启动）
uv run python manage.py run_ppt_broker

# PySide6 播放器
uv run python manage.py run_player

# PySide6 播放器无 GUI 启动
uv run python manage.py run_player --headless --window1 1 --window2 2 --window3 3 --window4 4

# 单窗口调试，常用于验证某一路 PPT/显示器
uv run python manage.py run_player --headless --only-window 2 --window2 2

# MediaMTX
.\tools\third_party\mediamtx\mediamtx.exe .\tools\third_party\mediamtx\mediamtx.yml
```

独立运行 `run_player` 时，它会先连接当前用户 Session 中健康的 Broker；若不存在，则自行启动 `manage.py run_ppt_broker`，并只在自己拥有该子进程时于退出阶段关闭它。`--only-window` 是由 `runall` 或父 `run_player` 管理的子进程模式，不会自行启动 Broker；单独使用该参数前必须先运行 `run_ppt_broker`，否则命令会明确报错。

默认端口：

| 端口 | 服务 |
|------|------|
| 5173 | Vue 控制台 |
| 8000 | Django REST / admin / 媒体文件 |
| 50051 | gRPC |
| 8890 | MediaMTX SRT publish/read |
| 9997 | MediaMTX API |

## 常用验证

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

### 四窗口 PPT 并发物理冒烟

该命令会侵入式替换 Broker 中窗口 1-4 的现有 PPT 会话，只能在维护窗口执行。先启动 `runall` 或单独启动 `run_ppt_broker`，再从媒体源列表取得 PPT source ID。四窗复用同一源时，该 PPT 至少需要 5 页：

```powershell
uv run python manage.py ppt_smoke --windows 1,2,3,4 --source-ids 42 --iterations 3 --timeout 120
```

也可以按窗口顺序提供四个 PPT source ID：`--source-ids 42,43,44,45`。命令会拒绝不存在、非 PPT、不可用或本地文件已丢失的源，并自动创建四个临时 PySide 原生宿主窗口；不会猜测或认领未知的 PowerPoint 顶层窗口。

旧的路径型命令继续兼容，也可显式提供四个现有容器 HWND；四项必须全部提供或全部省略，支持十进制和 `0x` 十六进制：

```powershell
uv run python manage.py run_ppt_physical_smoke `
  --ppt "D:\Slides\smoke.pptx" `
  --window1-hwnd 0x10101 --window2-hwnd 0x10102 `
  --window3-hwnd 0x10103 --window4-hwnd 0x10104 `
  --iterations 3 --broker-timeout 120
```

每轮从四个调用线程同时提交 OPEN，随后验证四个非零且唯一的放映 HWND、Broker 状态，以及“放映窗口 → Broker host → Player 容器”的严格两级父链（兼容无中间 host 的直接父链）；窗口 1-4 分别跳到第 2/3/4/5 页，每一步都确认其它窗口页码、HWND 和父链不变；再轮换关闭一个窗口、继续验证其余三个、重开被关闭窗口并重新验证四窗不变量，最后幂等关闭本轮全部 owner 会话。命令输出包含 source ID、PPT 路径、Broker PID/代次和逐轮诊断的 JSON；任一不变量或清理失败都会返回非零退出码。现有 `POST /api/playback/physical-smoke/` 用于数据库播放器链路的逐类媒体回归，不替代此 Broker 并发诊断。

## 清除运行数据

如需把现场恢复到空数据库和空媒体状态，先停止 `runall`、Django、所有播放器和 PowerPoint Broker 等正在运行的进程，再执行：

```powershell
uv run python manage.py clearall
```

该命令只作为 Django 管理命令提供，不暴露 API 或前端入口。它会删除 `db.sqlite3` 及 SQLite 附属文件，清空 `media/` 和 `logs/`，重新执行迁移，并仅按 `config.toml` 写入固定数据；当前固定数据只有默认管理员。

## 文档

- [使用文档](docs/使用文档.md)：现场部署、环境变量、启动、播控流程和常见问题。
- [维护文档](docs/维护文档.md)：目录职责、运行时资产、依赖升级、备份、故障定位和发布维护流程。
- [设计文档](docs/design/README.md)：面向迁移合并到 Django + Fluent + Vue 项目的系统架构、数据模型、接口、前端、播放器、运维和迁移指南。
- [OpenAPI YAML](docs/openapi.yaml)：REST API 机器可读接口合同。
- [贡献指南](CONTRIBUTING.md)：开发流程、提交规范和验证要求。
- [代码风格](STYLE.md)：Python、TypeScript、Vue、CSS 和文档风格约定。
- [变更记录](docs/CHANGELOG.md)：历史变更说明。

## 仓库整理约定

以下内容不进入版本库：本地 agent 配置、Playwright/Codex 运行缓存、pytest/ruff 缓存、`node_modules/`、上传媒体、日志和历史 `requirements*.txt`。Python 依赖以 `pyproject.toml` + `uv.lock` 为准，前端依赖以 `frontend/package.json` + `frontend/package-lock.json` 为准。

## 许可证

本项目主代码使用 Artistic License 2.0，详见 [LICENSE](LICENSE)。第三方运行时与依赖遵循其各自许可证。
