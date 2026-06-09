# SCP-cv

SCP-cv 是用于控制 **上海第二工业大学 28#108 多媒体显示系统** 的统一播放控制平台。系统在一台 Windows 主机上协同运行 Vue 控制台、Django 服务端、MediaMTX 流服务和 PySide6 播放器，用于管理 PPT、视频、图片、网页、音频和 SRT 直播流等媒体源，将内容投放到大屏与电视窗口，并通过独立背景音乐通道输出音频。

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
- **统一预热**：媒体源可开启后台预热，网页、图片、视频、背景音频、直播流和 PPT 按类型提前准备；直播流使用 URI 级可认领预热，PPT 按源文件级预打开，降低现场切换等待。
- **四窗口播控**：大屏左、大屏右、TV 左、TV 右分别独立控制，支持 single / double 大屏模式。
- **背景音乐**：音频源通过独立后台播放器输出，支持播放列表、立即播放、循环、音量和静音控制。
- **PPT 控制**：所有 PPT 导入、预览、播放缓存、预热和放映统一使用 Microsoft PowerPoint；导入后会尝试生成播放专用 `.ppsx`/`.pps` 缓存，显控页提供翻页、跳页和媒体控制。
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
        |
SQLite 播放会话状态
        |
PySide6 播放器 (PPT / 视频 / 图片 / 网页 / SRT / 背景音乐)
        |
MediaMTX (SRT publish/read + RTSP read)
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
- Microsoft PowerPoint 需要安装在当前 Windows 用户可自动化调用的环境中，播放器会尝试 PowerPoint COM ProgID。

## 环境变量

后端配置在仓库根目录 `.env`，前端 Vite 配置在 `frontend/.env`。两者分离：

- `.env`：Django、gRPC、MediaMTX、日志和后端运行配置。
- `frontend/.env`：`VITE_FRONTEND_PORT` 与 `VITE_BACKEND_TARGET`。

PPT 相关配置：

- PowerPoint 是唯一 PPT 播放器；导入、预览、播放缓存、预热和放映均不再提供后端选择。
- 支持 `.pptx/.ppt/.pps/.ppsx/.pptm/.ppsm/.pot/.potx/.potm/.odp` 等演示文件。导入后会尝试生成播放专用 `.ppsx`/`.pps` 缓存，宏格式默认导出为非宏 `.ppsx`；生成失败不阻断媒体源创建，播放时回退原始文件。
- PPT 媒体源启用预热时会按播放 URI 执行文件级预热：PowerPoint COM 会提前启动并无窗口预打开演示文稿，前台打开时按 `source_id + uri` 精确认领。
- PPT 放映时对应 PySide 播放窗口会先切到黑屏；PowerPoint 放映窗口成功后置顶，目标 PySide 窗口取消置顶；结束播放或切换到其它内容时先恢复 PySide 黑屏置顶，再关闭 PowerPoint 放映窗口。
- PPT 生命周期中播放器会最小化同一 Windows 桌面上除所有 PySide 播放窗口和当前 PowerPoint 放映窗口外的其它顶层可见窗口，避免残留窗口遮挡。
- 右上角“重置 PPT 放映”会关闭当前 PowerPoint 放映窗口与文档，再重启当前 PPT 放映并回到重置前页码。
- `PPT_PREVIEW_WORKER_TIMEOUT_SECONDS=180`：上传或导入 PPT 时，预览导出 worker 的最长等待时间；Office 预览导出失败或超时只会跳过预览，不会阻断媒体源创建。
- `PPT_PLAYBACK_EXPORT_TIMEOUT_SECONDS=180`：导入 PPT 时生成 `.ppsx`/`.pps` 播放缓存的最长等待时间；缓存生成失败只记录 metadata 并回退原始文件播放。

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

`--headless` 默认把窗口 1/2/3/4 分别映射到 Windows 显示器 ID 1/2/3/4；未传 `--gpu` 时使用系统默认 GPU。`--window3` 与兼容别名 `--windows3` 等价。
如果通过 SSH、OpenSSH 服务或其它非控制台会话远程启动，直接运行 `--headless` 无法访问物理显示器；请使用 `uv run python manage.py runall --headless --service`，系统会在当前登录用户的交互桌面中拉起真实 runall。

分进程调试：

```powershell
# Django REST + gRPC
uv run python manage.py runserver

# Vue 控制台
npm --prefix frontend run dev

# PySide6 播放器
uv run python manage.py run_player

# PySide6 播放器无 GUI 启动
uv run python manage.py run_player --headless --window1 1 --window2 2 --window3 3 --window4 4

# MediaMTX
.\tools\third_party\mediamtx\mediamtx.exe .\tools\third_party\mediamtx\mediamtx.yml
```

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

## 清除运行数据

如需把现场恢复到空数据库和空媒体状态，先停止 `runall`、Django、播放器等正在运行的进程，再执行：

```powershell
uv run manage.py clearall
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
