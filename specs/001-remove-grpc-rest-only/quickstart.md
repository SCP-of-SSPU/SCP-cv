# Quickstart: 验证仅保留 REST 接口

## 1. 安装与静态检查

```powershell
uv sync
pnpm install
pnpm install --prefix frontend
uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
```

预期：依赖同步成功，无 gRPC/protobuf 包要求，Django 检查和迁移检查通过。

## 2. 后端与前端回归

```powershell
uv run pytest tests/ -v
pnpm --prefix frontend run typecheck
pnpm --prefix frontend run build
npx @redocly/cli lint docs/openapi.yaml
```

预期：REST、SSE、播放器、媒体、场景、背景音频和设备相关测试全部通过；前端和 OpenAPI
校验通过。

## 3. 启动链路

```powershell
uv run python manage.py runall --headless
```

预期：启动日志和进程树中没有 gRPC/gRPC-Web 服务，50051 与 8081 不属于 SCP-cv 监听端口；
REST、SSE、前端、播放器与 MediaMTX 正常启动。

## 4. 遗留引用扫描

```powershell
git grep -n -i -E "grpc|grpcio|protobuf|50051|8081" -- \
  ':!specs/**' ':!docs/CHANGELOG.md'
```

预期：当前源码、依赖、启动配置和使用文档无命中；允许功能规范和历史变更记录说明本次移除。
