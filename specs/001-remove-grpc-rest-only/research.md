# Research: 仅保留 REST 接口

## Decision 1: 直接终止 gRPC 兼容

**Decision**: 删除 gRPC/gRPC-Web 服务和客户端资产，不提供 REST 转发代理。

**Rationale**: 用户明确要求“全部删掉，只保留 REST”；兼容层会继续保留依赖、端口和维护成本。

**Alternatives considered**: 保留只读 gRPC、提供弃用期、增加 gRPC 到 REST 代理。均与目标冲突。

## Decision 2: 保留 REST 与 SSE

**Decision**: HTTP REST 负责命令和查询，SSE 继续负责播放状态推送。

**Rationale**: 当前 Vue 控制台已经使用此链路，业务服务和数据库状态不依赖 gRPC。

**Alternatives considered**: 用轮询替代 SSE。没有需求收益，且会增加延迟与负载。

## Decision 3: 删除 protobuf 资产和依赖

**Decision**: 删除 proto 源文件、生成 Python 代码、生成工具、protobuf 和 gRPC Python/Node 依赖。

**Rationale**: 仓库检索显示这些资产仅被 gRPC 服务和测试消费；REST 使用 JSON，不需要 protobuf。

**Alternatives considered**: 保留 proto 作为文档。OpenAPI 已是 REST 的机器可读合同，保留会造成误导。

## Decision 4: 锁文件由包管理器更新

**Decision**: 修改 `pyproject.toml` 和 `package.json` 后分别使用 `uv lock` 与 `pnpm install --lockfile-only`。

**Rationale**: 可可靠清理传递依赖并保持锁文件内部一致性。

**Alternatives considered**: 手工删除锁文件段落。容易遗漏依赖边并破坏可重复安装。
