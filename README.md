# SCP-cv

> 面向 **单机大屏** 场景的统一播放控制系统——通过 Vue Web 控制台、REST API 与保留 gRPC 接口远程操控本地大屏，支持 PPT、视频、音频、图片、网页与 SRT 实时流等多种媒体源。

---

## 功能特性

- **统一媒体源管理**：本地文件上传、路径添加、网页与流媒体源注册，全部媒体在同一界面管理
- **PPT 全功能控制**：通过 COM 自动化驱动 PowerPoint，支持翻页、跳转、播放/暂停、备注提词和当前页媒体控制
- **libVLC 低延迟播放**：基于 python-vlc + libVLC 和 MediaMTX 实现低延迟 SRT 直连播放，启动时可选择 SRT 渲染显卡
- **多显示器拼接**：单屏 / 左右双屏拼接模式，启动时通过 GUI 选择目标屏幕
- **前后端分离**：`frontend/` Vue 3 控制台通过 REST + SSE 调用 Django 后端
- **保留 gRPC 集成**：核心播放控制 gRPC 接口继续服务中控系统和自动化脚本
- **SSE 实时推送**：播放状态和媒体源变更通过 Server-Sent Events 实时同步到浏览器
- **系统与设备控制**：支持 Windows 系统音量/静音同步，并通过 TCP 指令控制拼接屏和电视电源
- **一键启动**：`uv run python manage.py runall` 单终端同时启动 MediaMTX、Django、PySide6 播放器

## 架构概览

```
┌──────────────────────────────────┐
│       Vue Web 控制台 (frontend/) │
│ REST + SSE · 四路窗口控制          │
└──────────┬───────────────────────┘
           │ REST / SSE
┌──────────▼───────────────────────┐
│        Django 服务端               │
│  REST API + gRPC (端口 50051)     │
│  SQLite 播放会话 (单例)            │
└──────────┬───────────────────────┘
           │ 数据库轮询
┌──────────▼───────────────────────┐
│      PySide6 本地播放器             │
│  PlayerController → 适配器分发     │
│  ┌─────────┬──────────┬────────┐ │
│  │ PPT适配  │ 视频适配  │ 流适配 │ │
│  │ (COM)   │(QMedia)  │(libVLC)│ │
│  └─────────┴──────────┴────────┘ │
└──────────────────────────────────┘
           │ 拉流 (SRT)
┌──────────▼───────────────────────┐
│       MediaMTX 流服务器             │
│ SRT 推流 / 读取 (8890)           │
└──────────────────────────────────┘
```

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Django | 6.0.3 |
| 前端框架 | Vue + Vite + TypeScript | 3.x / latest |
| gRPC 集成 | django-socio-grpc | 0.25.0 |
| 播放器 GUI | PySide6 (Qt 6) | 6.11.0 |
| 流媒体服务器 | MediaMTX | — |
| 数据库 | SQLite | 内置 |
| 代码检查 | Ruff | 0.15.9 |
| 测试框架 | pytest + pytest-django | 9.0.2 / 4.12.0 |

## 快速开始

### 环境要求

- **Python** 3.12+
- **Microsoft PowerPoint**（PPT 播放功能需要，通过 COM 自动化调用）

### 安装

```powershell
# 克隆仓库
git clone <repo-url> SCP-cv
cd SCP-cv

# 如未安装 uv（Windows PowerShell）
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 安装项目 Python（遵循 .python-version）并同步依赖
uv python install
uv sync

# 准备 VLC/libVLC 播放运行时
powershell -ExecutionPolicy Bypass -File .\tools\download_third_party.ps1

# 复制环境变量配置
copy .env.example .env

# 初始化数据库
uv run python manage.py migrate

# 安装 Vue 前端依赖
npm install --prefix frontend
```

> 项目已切换到 `uv` 工作流；根目录的 `requirements*.txt` 仅作为历史兼容清单保留，不再作为推荐安装入口。仅需运行时依赖时，可将 `uv sync` 改为 `uv sync --no-dev`。

### 启动

```powershell
# 一键启动（推荐）：MediaMTX + Django + Vue + 播放器
uv run python manage.py runall

# 自定义监听地址，便于局域网控制台访问
uv run python manage.py runall --backend-host 0.0.0.0 --frontend-host 0.0.0.0 --skip-mediamtx
```

启动后：

1. 本机浏览器打开 `http://127.0.0.1:5173/` 访问 Vue Web 控制台，手机访问时使用 `http://<本机局域网IP>:5173/`
2. 播放器启动器 GUI 弹出，多显卡主机可先选择 SRT 渲染显卡，再选择播放窗口对应的目标屏幕
3. 通过浏览器 Web 控制台上传/添加媒体源，点击播放即可在大屏显示

> **提示**：`DJANGO_DEBUG=True` 时播放器窗口带标题栏（可拖拽缩放），`False` 时全屏无边框置顶。
> 手机访问 Web 控制台时会优先进入播放控制页，并提供 PPT 遥控器用于大按钮翻页和左右滑动翻页。

### 分进程启动（调试用）

```powershell
# 终端 1：Django 服务端（REST + gRPC）
uv run python manage.py runserver

# 终端 2：Vue 前端
npm --prefix frontend run dev

# 终端 3：PySide6 播放器
uv run python manage.py run_player

# 终端 4：MediaMTX（可选）
.\tools\third_party\mediamtx\mediamtx.exe
```

Vue 前端默认监听 `0.0.0.0:5173`，便于手机和同一局域网设备访问；如仅允许本机访问，可运行 `npm --prefix frontend run dev -- --host 127.0.0.1`。

## 目录结构

```
SCP-cv/
├── manage.py                   # Django 入口
├── scp_cv/                     # Django 项目配置
│   ├── settings.py             # 配置（django-environ 读取 .env）
│   ├── urls.py                 # URL 路由
│   ├── grpc_handlers.py        # gRPC 处理器注册
│   ├── grpc_servicers.py       # gRPC 服务实现
│   ├── apps/
│   │   ├── dashboard/          # Web 控制台（视图 + 模板 + 管理命令）
│   │   ├── playback/           # 播放会话模型（PlaybackSession + MediaSource）
│   │   └── streams/            # 外部流注册模型（StreamSource）
│   ├── player/                 # PySide6 播放器（窗口 + 控制器 + libVLC 适配）
│   ├── services/               # 业务服务层（显示、播放、MediaMTX、SSE）
│   └── grpc_generated/         # protoc 生成的 Python 代码
├── protos/                     # gRPC Proto 定义
│   └── scp_cv/v1/control.proto # 统一播放控制服务合约
├── frontend/                   # Vue 3 + Vite 前端控制台
├── tests/                      # pytest 测试套件
├── tools/                      # 第三方可执行文件（MediaMTX、VLC）
└── docs/                       # 项目文档
    ├── API.md                  # HTTP + gRPC 接口参考
    ├── 使用文档.md              # 安装与使用指南
    ├── CHANGELOG.md            # 变更记录
    └── 需求I.md                # 原始需求文档
```

## 端口汇总

| 端口 | 服务 | 说明 |
|------|------|------|
| 5173 | Vue 前端 | Web 控制台开发服务器 |
| 8000 | Django HTTP | REST API + admin + 媒体文件 |
| 50051 | gRPC | 播放控制 gRPC 服务 |
| 8890 | MediaMTX SRT Publish/Read | OBS / 外部设备推流入口与播放器读取入口 |
| 9997 | MediaMTX API | 流管理 REST API |

## 测试

```powershell
# 运行全部测试
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build

# 运行特定测试文件
uv run pytest tests/test_media_service.py -v
```

## 文档

- [API 接口参考](docs/API.md) — HTTP 端点 + gRPC 方法 + SSE 事件
- [使用文档](docs/使用文档.md) — 安装部署 + 操作指南
- [变更记录](docs/CHANGELOG.md) — 版本变更明细

## 许可

私有项目，未授权不得分发。
