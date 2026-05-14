# SCP-cv

SCP-cv 是用于控制 **上海第二工业大学 28#108 多媒体显示系统** 的统一播放控制平台。系统在一台 Windows 主机上协同运行 Vue 控制台、Django 服务端、MediaMTX 流服务和 PySide6 播放器，用于管理 PPT、视频、图片、网页和 SRT 直播流等媒体源，并将内容投放到大屏与电视窗口。

## 项目信息

| 项目 | 内容 |
|------|------|
| 开发者 | Qintsg（饶弘玮，上海第二工业大学 25网工A2） |
| 单位 | 上海第二工业大学 / 计算机与信息工程学院 / SSPU AI-Lab / 超级棒棒糖 |
| 应用地点 | 上海第二工业大学 28#108 |
| 许可证 | Artistic-2.0 |
| 镜像仓库 | `http://git.bbt.sspu.edu.cn/Qintsg/scp-cv`（仅作为同步镜像，不作为主开发入口） |

## 核心能力

- **统一媒体源管理**：上传文件、添加本机路径、添加网页源、自动发现 MediaMTX SRT 流。
- **四窗口播控**：大屏左、大屏右、TV 左、TV 右分别独立控制，支持 single / double 大屏模式。
- **PPT 控制**：PowerPoint COM 自动化驱动，支持翻页、跳转、提词器、预览图和页面媒体控制。
- **SRT 直播播放**：MediaMTX 接收 OBS / 外部设备推流，播放器通过 libVLC 低延迟拉流。
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
PySide6 播放器 (PPT / 视频 / 图片 / 网页 / SRT)
        |
MediaMTX (SRT publish/read)
```

## 环境要求

- Windows 10/11
- Python 3.12 或更高版本（推荐使用 `uv` 管理）
- Node.js 20 或更高版本
- Microsoft PowerPoint（PPT 播放必需）
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

# 初始化数据库
uv run python manage.py migrate
```

第三方运行时按以下约定放置：

- `tools/third_party/mediamtx/mediamtx.exe`：MediaMTX 主程序，配置文件同目录放置。
- `tools/third_party/vlc/runtime/`：项目内置 VLC/libVLC runtime；也可以使用系统安装的 `C:\Program Files\VideoLAN\VLC`。

## 环境变量

后端配置在仓库根目录 `.env`，前端 Vite 配置在 `frontend/.env`。两者分离：

- `.env`：Django、gRPC、MediaMTX、日志和后端运行配置。
- `frontend/.env`：`VITE_FRONTEND_PORT` 与 `VITE_BACKEND_TARGET`。

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

# 后台启动，不绑定当前终端生命周期；输出写入 logs/runall-service.log
uv run python manage.py runall --headless --service

# 指定窗口到 Windows 显示器 ID，并指定 GPU ID
uv run python manage.py runall --headless --window1 1 --window2 2 --window3 3 --window4 4 --gpu 0
```

`--headless` 默认把窗口 1/2/3/4 分别映射到 Windows 显示器 ID 1/2/3/4；未传 `--gpu` 时使用系统默认 GPU。`--window3` 与兼容别名 `--windows3` 等价。

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

## 文档

- [使用文档](docs/使用文档.md)：现场部署、环境变量、启动、播控流程和常见问题。
- [维护文档](docs/维护文档.md)：目录职责、运行时资产、依赖升级、备份、故障定位和发布维护流程。
- [OpenAPI YAML](docs/openapi.yaml)：REST API 机器可读接口合同。
- [贡献指南](CONTRIBUTING.md)：开发流程、提交规范和验证要求。
- [代码风格](STYLE.md)：Python、TypeScript、Vue、CSS 和文档风格约定。
- [变更记录](docs/CHANGELOG.md)：历史变更说明。

## 仓库整理约定

以下内容不进入版本库：本地 agent 配置、Playwright/Codex 运行缓存、pytest/ruff 缓存、`node_modules/`、上传媒体、日志和历史 `requirements*.txt`。Python 依赖以 `pyproject.toml` + `uv.lock` 为准，前端依赖以 `frontend/package.json` + `frontend/package-lock.json` 为准。

## 许可证

本项目主代码使用 Artistic License 2.0，详见 [LICENSE](LICENSE)。第三方运行时与依赖遵循其各自许可证。
