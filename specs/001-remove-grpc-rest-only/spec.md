# Feature Specification: 仅保留 REST 接口

**Feature Branch**: `001-remove-grpc-rest-only`

**Created**: 2026-08-30

**Status**: Ready for planning

**Input**: User description: "删除项目中全部 gRPC 相关内容，只保留 REST"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - 控制台继续正常播控 (Priority: P1)

现场操作员使用现有 Web 控制台完成登录、媒体源管理、播放控制、背景音频、场景和设备控制，
所有功能均通过 REST 接口完成，用户不需要感知接口协议变化。

**Why this priority**: 现场核心工作不能因移除 gRPC 而中断。

**Independent Test**: 启动后端和前端，完成登录、创建媒体源、切换播放、调整音量和注销，
验证每个流程均成功且无 gRPC 连接或调用错误。

**Acceptance Scenarios**:

1. **Given** 后端和前端已启动，**When** 操作员登录并打开控制台，**Then** 页面加载成功，
   REST 请求返回预期结果，浏览器控制台没有 gRPC 相关错误。
2. **Given** 已登录且存在媒体源，**When** 操作员执行播放、停止、场景切换和背景音频控制，
   **Then** 播放状态通过 REST/SSE 正常更新，显示设备行为与现有功能一致。

### User Story 2 - 后端仅暴露 REST 入口 (Priority: P1)

系统维护者部署服务时只需维护现有 REST、SSE、媒体文件和管理入口，不再启动、配置或监控
独立的 gRPC 服务和端口。

**Why this priority**: 减少现场部署面和运行时故障来源是本次变更的直接目标。

**Independent Test**: 在干净环境执行标准启动流程，检查监听端口、启动日志和进程树，确认
不存在 gRPC 服务、protobuf 生成模块加载或 gRPC 依赖错误。

**Acceptance Scenarios**:

1. **Given** 使用项目默认配置，**When** 执行标准启动命令，**Then** 仅启动 REST、SSE、
   前端、播放器及其必要的媒体运行时。
2. **Given** 客户端请求任意 REST 接口，**When** 服务处理请求，**Then** 认证、错误格式、
   状态码和业务响应保持现有兼容性。

### User Story 3 - 代码与文档边界清晰 (Priority: P2)

开发者检索项目时，可以确认仓库中不存在需要维护的 gRPC 合同、生成代码、服务实现、依赖、
测试或启动说明；API 文档明确 REST 是唯一对外控制接口。

**Why this priority**: 清理遗留入口能降低后续维护和误用成本。

**Independent Test**: 对源代码、依赖清单、启动脚本、协议目录、测试和文档执行 gRPC 关键字
检索，并确认只剩迁移说明或历史变更记录中的必要文字。

**Acceptance Scenarios**:

1. **Given** 开发者安装项目依赖，**When** 查看依赖清单和锁文件，**Then** 不再需要 gRPC、
   grpcio、grpcio-tools 或 protobuf 运行时依赖。
2. **Given** 开发者查看 API 合同和维护文档，**When** 按文档启动或调用服务，**Then** 只
   能找到 REST/SSE 入口和对应验证方式。

### Edge Cases

- 旧客户端仍尝试连接 gRPC 端口时，连接应失败且不影响 REST 服务和播放器启动。
- 仓库中历史文档或变更记录可以保留 gRPC 的历史说明，但不得被当前启动脚本、API 文档或
  代码引用为可用入口。
- 移除 gRPC 依赖后，数据库迁移、媒体处理、播放器启动和前端构建不得因导入链变化失败。
- 删除生成代码时，不得误删 REST、SSE 或播放器仍使用的通用 protobuf/数据模型代码；若无
  任何剩余消费者，则应一并删除对应源文件和构建步骤。

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: 系统 MUST 保持现有 REST、SSE、媒体文件和管理入口的功能与认证兼容性。
- **FR-002**: 系统 MUST 删除 gRPC 服务注册、监听、认证适配、handler、servicer 和启动编排。
- **FR-003**: 系统 MUST 删除仅供 gRPC 使用的 protobuf 合同、生成代码、生成工具和构建步骤。
- **FR-004**: 系统 MUST 从 Python、Node 和前端相关依赖清单及锁文件中移除仅供 gRPC 使用的依赖。
- **FR-005**: 系统 MUST 删除或改写仅覆盖 gRPC 的测试，并为受影响的 REST 行为保留回归覆盖。
- **FR-006**: 系统 MUST 更新 README、维护文档、API 合同、启动说明和贡献指南，明确 REST 是
  唯一控制 API，并移除过时的 gRPC 操作指引。
- **FR-007**: 系统 MUST 让标准启动流程不再要求 gRPC 端口、进程或配置项。
- **FR-008**: 系统 MUST 在清理完成后通过静态检索确认不存在可执行的 gRPC 代码路径或未使用
  的 gRPC 配置；历史变更记录中的说明可保留。

### Key Entities

- **REST 控制接口**：现有认证、媒体、播放、场景、背景音频和设备控制 HTTP 接口集合。
- **gRPC 遗留入口**：待移除的 protobuf 合同、生成代码、服务实现、认证适配、启动配置和测试。
- **运行时启动编排**：负责 REST、SSE、前端、播放器和媒体运行时生命周期的现有命令集合。

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: 标准启动流程在 100% 的验证运行中不启动 gRPC 进程、不监听 gRPC 端口，且
  REST/SSE/播放器功能全部可用。
- **SC-002**: REST 回归测试覆盖的核心控制流程通过率保持 100%，包括认证、媒体源、播放、
  场景、背景音频、设备和 SSE 状态同步。
- **SC-003**: 依赖、源代码、协议目录和当前文档中不再存在可执行的 gRPC 引用；静态检索只
  允许命中明确标注为历史记录的内容。
- **SC-004**: 部署所需的服务端口数量减少至少 1 个，且 README 与维护文档中的端口表与实际
  启动监听结果一致。

## Assumptions

- REST 和 SSE 是当前 Web 控制台的实际生产链路，移除 gRPC 不改变业务语义。
- 不为旧 gRPC 客户端提供兼容代理、重定向或长期过渡服务；旧客户端需要迁移到 REST。
- `protos/` 与 `scp_cv/grpc_generated/` 若无其他消费者，将作为 gRPC 专属资产整体删除。
- 历史 CHANGELOG 可以保留过去版本的 gRPC 记录，但必须避免把历史入口描述为当前能力。
