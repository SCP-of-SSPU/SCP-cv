# SCP-cv

> 面向 **单机大屏** 场景的统一播放控制系统——通过 Web 控制台、gRPC 接口远程操控本地大屏，支持 PPT、视频、音频、图片、WebRTC 实时流等多种媒体源。

---

## 功能特性

- **统一媒体源管理**：本地文件上传、路径添加、WebRTC 流注册，全部媒体在同一界面管理
- **PPT 全功能控制**：通过 COM 自动化驱动 PowerPoint，支持翻页、跳转、播放/暂停
- **GStreamer + WebRTC 播放**：基于 GStreamer 管线和 MediaMTX WHEP 实现低延迟流播放
- **多显示器拼接**：单屏 / 左右双屏拼接模式，启动时通过 GUI 选择目标屏幕
- **双协议控制面**：HTTP REST API + gRPC 双通道，适配 Web 前端、中控系统、自动化脚本
- **SSE 实时推送**：播放状态和媒体源变更通过 Server-Sent Events 实时同步到浏览器
- **一键启动**：`python manage.py runall` 单终端同时启动 MediaMTX、Django、PySide6 播放器

## 架构概览

```
┌──────────────────────────────────┐
│         Web 控制台 (浏览器)        │
│   Fluent 2 风格 · 三 Tab 布局    │
│   媒体源 │ 播放控制 │ 设置         │
└──────────┬───────────────────────┘
           │ HTTP / SSE
┌──────────▼───────────────────────┐
│        Django 服务端               │
│  HTTP Views + gRPC (端口 50051)   │
│  SQLite 播放会话 (单例)            │
└──────────┬───────────────────────┘
           │ 数据库轮询
┌──────────▼───────────────────────┐
│      PySide6 本地播放器             │
│  PlayerController → 适配器分发     │
│  ┌─────────┬──────────┬────────┐ │
│  │ PPT适配  │ 视频适配  │ 流适配 │ │
│  │ (COM)   │(GStreamer)│(WebRTC)│ │
│  └─────────┴──────────┴────────┘ │
└──────────────────────────────────┘
           │ 拉流
┌──────────▼───────────────────────┐
│       MediaMTX 流服务器             │
│  WebRTC (WHIP/WHEP) · 端口 8889  │
└──────────────────────────────────┘
```

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Django | 6.0.3 |
| gRPC 集成 | django-socio-grpc | 0.25.0 |
| 播放器 GUI | PySide6 (Qt 6) | 6.11.0 |
| 流媒体管线 | PyGObject / GStreamer | ≥ 3.50.0 |
| 流媒体服务器 | MediaMTX | — |
| 数据库 | SQLite | 内置 |
| 代码检查 | Ruff | 0.15.9 |
| 测试框架 | pytest + pytest-django | 9.0.2 / 4.12.0 |

## 快速开始

### 环境要求

- **Python** 3.12+
- **GStreamer MinGW x86_64**（[下载页](https://gstreamer.freedesktop.org/download/)，安装时选择 **Complete** 选项以包含开发文件）
- **Visual Studio**（含 C++ 桌面开发组件，构建 PyGObject 时需要 MSVC link.exe）
- **Microsoft PowerPoint**（PPT 播放功能需要，通过 COM 自动化调用）

### 安装

```powershell
# 克隆仓库
git clone <repo-url> SCP-cv
cd SCP-cv

# 创建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# 复制环境变量配置
copy .env.example .env

# 初始化数据库
python manage.py migrate

# 安装 PyGObject（GStreamer Python 绑定）
python tools/install_pygobject.py
```

### 启动

```powershell
# 一键启动（推荐）：MediaMTX + Django + 播放器
python manage.py runall

# 自定义参数
python manage.py runall --host 0.0.0.0 --port 8080 --skip-mediamtx
```

启动后：

1. 浏览器打开 `http://127.0.0.1:8000/` 访问 Web 控制台
2. 播放器启动器 GUI 弹出，选择显示模式和目标屏幕
3. 通过控制台上传/添加媒体源，点击播放即可在大屏显示

> **提示**：`DJANGO_DEBUG=True` 时播放器窗口带标题栏（可拖拽缩放），`False` 时全屏无边框置顶。

### 分进程启动（调试用）

```powershell
# 终端 1：Django 服务端（HTTP + gRPC）
python manage.py runserver

# 终端 2：PySide6 播放器
python manage.py run_player

# 终端 3：MediaMTX（可选）
.\tools\third_party\mediamtx\mediamtx.exe
```

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
│   │   └── streams/            # WebRTC 流注册模型（StreamSource）
│   ├── player/                 # PySide6 播放器（窗口 + 控制器 + GStreamer 初始化）
│   ├── services/               # 业务服务层（显示、播放、MediaMTX、SSE）
│   └── grpc_generated/         # protoc 生成的 Python 代码
├── protos/                     # gRPC Proto 定义
│   └── scp_cv/v1/control.proto # 统一播放控制服务合约
├── static/                     # CSS + JavaScript
├── templates/                  # Django 模板
├── tests/                      # pytest 测试套件（65 项）
├── tools/                      # 第三方可执行文件（MediaMTX、mpv）
└── docs/                       # 项目文档
    ├── API.md                  # HTTP + gRPC 接口参考
    ├── 使用文档.md              # 安装与使用指南
    ├── CHANGELOG.md            # 变更记录
    └── 需求I.md                # 原始需求文档
```

## 端口汇总

| 端口 | 服务 | 说明 |
|------|------|------|
| 8000 | Django HTTP | Web 控制台 + REST API + SSE |
| 50051 | gRPC | 播放控制 gRPC 服务 |
| 8889 | MediaMTX WebRTC | WHIP 推流 / WHEP 拉流 |
| 9997 | MediaMTX API | 流管理 REST API |

## 测试

```powershell
# 运行全部测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_media_source.py -v
```

## 文档

- [API 接口参考](docs/API.md) — HTTP 端点 + gRPC 方法 + SSE 事件
- [使用文档](docs/使用文档.md) — 安装部署 + 操作指南
- [变更记录](docs/CHANGELOG.md) — 版本变更明细

## 许可

私有项目，未授权不得分发。
