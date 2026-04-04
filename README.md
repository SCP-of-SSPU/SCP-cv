# SCP-cv

SCP-cv 是一个面向单机大屏播放场景的 Django + gRPC 初始化工程，目标是先把 **HTTP 控制台、gRPC 接口、本地播放器、显示器拼接和资源管理** 的骨架搭好，再逐步填充业务逻辑。

## 当前初始化结果

- Django 服务端渲染的控制台首页已经可访问
- Fluent 2 风格的基础样式已经接入
- 显示器枚举、MediaMTX / LibreOffice 路径探测和统一播放会话模型已经预留
- gRPC 接入点与 proto 合同已经预留
- SQLite 作为默认本地数据库

## 技术栈

- Python 3.12
- Django 6
- django-socio-grpc
- PySide6
- python-pptx
- LibreOffice CLI
- MediaMTX
- SQLite

## 目录概览

- `scp_cv/`：Django 项目配置与共享服务
- `scp_cv/apps/`：按业务域拆分的 Django apps
- `templates/`：共享模板
- `static/`：共享静态资源
- `protos/`：gRPC 合同
- `tools/`：第三方可执行文件下载脚本与说明
- `docs/`：需求、接口和变更记录

## 本地启动

1. 安装依赖

   `python -m pip install -r requirements-dev.txt`

2. 初始化数据库

   `python manage.py migrate`

3. 启动 Django 开发服务器

   `python manage.py runserver`

4. 打开浏览器访问首页

   `http://127.0.0.1:8000/`

## 第三方可执行文件

项目需要本地可执行文件来支撑阶段一的媒体与流接入：

- MediaMTX：用于 SRT 接入
- LibreOffice CLI：用于 PPT 转换与导出

推荐使用 `tools/download_third_party.ps1` 进行 MediaMTX 下载，并通过 `winget` 或现有安装补齐 LibreOffice。

## 参考文档

- `docs/需求I.md`
- `docs/API.md`
- `docs/CHANGELOG.md`
