# Tasks: 仅保留 REST 接口

**Input**: `specs/001-remove-grpc-rest-only/` 下的设计文档

**Organization**: 任务按用户故事组织；所有任务都包含准确路径并按依赖顺序排列。

## Phase 1: Setup

- [x] T001 记录当前 gRPC/protobuf/端口引用基线并核对删除清单，覆盖 `scp_cv/`、`tests/`、`docs/`、`frontend/`、`protos/`、`pyproject.toml` 与 `package.json`
- [x] T002 校验项目忽略文件和 Spec Kit 当前功能指针，确认 `.gitignore` 与 `.specify/.gitignore` 无需新增运行时例外

## Phase 2: Foundational

- [x] T003 删除 gRPC 专属源代码与合同目录 `scp_cv/grpc_generated/`、`scp_cv/grpc_servicers/`、`scp_cv/v1/`、`protos/`、`scp_cv/grpc_auth.py`、`scp_cv/grpc_handlers.py`
- [x] T004 删除 gRPC 专属测试和静态客户端资产 `tests/test_grpc_servicers.py`、`static/js/grpc-client.bundle.js.map`

## Phase 3: User Story 1 - 控制台继续正常播控 (P1)

**Goal**: REST/SSE 与前端控制链路保持不变。

**Independent Test**: REST、SSE 和播放器相关后端测试以及前端类型检查/构建全部通过。

- [x] T005 [US1] 更新 `scp_cv/settings.py` 与 `scp_cv/urls.py`，移除 gRPC 应用、认证、handler 和配置引用，同时保持 REST 路由不变
- [x] T006 [P] [US1] 更新 `frontend/src/locales/zh-CN/settings.ts`，移除当前 UI 中的 gRPC 端口展示
- [x] T007 [US1] 运行并修复 `tests/test_rest_api.py`、`tests/test_sse_service.py` 及受影响的 REST/播放器回归测试

## Phase 4: User Story 2 - 后端仅暴露 REST 入口 (P1)

**Goal**: 标准启动流程不再包含 gRPC 或 gRPC-Web。

**Independent Test**: runall 测试与命令帮助中不再出现 gRPC 参数、进程或端口。

- [x] T008 [US2] 从 `scp_cv/apps/dashboard/management/runall_arguments.py`、`runall_starters.py`、`runall_processes.py` 和 `commands/runall.py` 删除 gRPC-Web 参数、启动、监控和清理逻辑
- [x] T009 [US2] 更新 `tests/test_runall_command.py`、`tests/test_runall_service.py` 和 `tests/test_runall_residual_processes.py` 的启动编排断言
- [x] T010 [US2] 从 `.env.example` 和运行配置中删除 gRPC 主机、端口和 gRPC-Web 配置

## Phase 5: User Story 3 - 代码与文档边界清晰 (P2)

**Goal**: 依赖、构建、当前文档和 API 说明只描述 REST/SSE。

**Independent Test**: 依赖同步、文档校验和受控关键字扫描通过。

- [x] T011 [P] [US3] 从 `pyproject.toml` 删除 django-socio-grpc、grpcio、grpcio-tools、protobuf 依赖和生成代码排除项，并用 `uv lock` 更新 `uv.lock`
- [x] T012 [P] [US3] 从 `package.json` 删除 `@grpc-web/proxy` 并用 pnpm 更新 `pnpm-lock.yaml`
- [x] T013 [US3] 更新 `README.md`、`CONTRIBUTING.md`、`docs/使用文档.md`、`docs/维护文档.md` 和当前设计文档，明确仅支持 REST/SSE
- [x] T014 [US3] 更新 `docs/openapi.yaml`、`docs/_bundled.yaml` 与相关 API 文档描述，并运行 Redocly 校验
- [x] T015 [US3] 更新 `AGENTS.md`、`.specify/memory/constitution.md` 和 `docs/CHANGELOG.md` 中的当前集成描述与变更记录

## Phase 6: Polish & Cross-Cutting Validation

- [x] T016 运行 `uv run ruff check .`、Django check、迁移检查和后端全量 `uv run pytest tests/ -v`
- [x] T017 运行前端 typecheck/build、Spec Kit 校验、Prettier、ActionLint 和 Redocly 校验
- [x] T018 执行 gRPC/protobuf/50051/8081 静态扫描，确认当前源码、依赖、配置与使用文档无可执行遗留引用
- [x] T019 核对 `specs/001-remove-grpc-rest-only/quickstart.md` 的启动与回归步骤，并更新全部任务为完成状态

## Dependencies & Execution Order

- T001-T002 → T003-T004 → T005-T010 → T011-T015 → T016-T019。
- T006 可与 T005 并行；T011 与 T012 可并行，其余任务按共享文件和验证依赖顺序执行。
- US1 与 US2 均依赖 gRPC 专属代码删除；US3 可在核心删除完成后处理。

## Implementation Strategy

先删除独立边界资产，再逐层消除配置与启动引用，最后更新依赖和文档。任何 REST/SSE 回归失败
都必须在进入文档清理前修复，避免以删除测试掩盖行为退化。
