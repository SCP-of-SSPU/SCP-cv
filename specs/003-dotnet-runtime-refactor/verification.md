# 验收与验证记录

本文是 003 重构的证据索引。`通过` 只用于已经执行的自动化或人工检查；`待实机` 不等同于失败，也不得在交付说明中描述为已经通过。

## Q1–Q11 验收矩阵

| 范围 | 自动化证据 | 人工/实机证据 | 当前结论 |
| --- | --- | --- | --- |
| Q1 三端共享功能 | `frontend/scripts/platform-adapters.test.mjs`、`client-connection.test.mjs`、ControlHost 合同测试 | `docs/qa/003-client-matrix.md` | Web 通过；Electron/Android 实包已完成基础启动与页面验证，主机联调待补 |
| Q2 会话与 SSE | `AuthEndpointTests`、`SseEndpointTests`、`verify-packaged-session.test.mjs`、`client-connection.test.mjs` | 三端各 10 次恢复记录待补 | 自动化通过；实包恢复待验证 |
| Q3 业务规则 | Domain/ControlHost 全套测试、`OpenApiCoverageTests` | 浏览器业务状态见 `docs/qa/003-browser-ui.md` | 自动化通过；浏览器复核待执行 |
| Q4 可靠命令 | `CommandFencingTests`、`CommandRecoveryTests`、`ReliabilityAcceptanceTests`、`SecurityBoundaryTests` | 无 | 自动化通过 |
| Q5 Office/PDF | `PresentationPolicyTests`、`OfficeOperationTests`、`MediaPreparationTests` | `docs/qa/003-office-interop.md` | 软件边界通过；实际 Office/HWND 条件待验证 |
| Q6 网页预热 | `ResourceSwitchTests`、`WebViewPreheatTests` | `docs/qa/003-preheat-performance.md` | 状态机通过；真实 WebView2 性能待复核 |
| Q7 媒体/性能 | `VlcAdapterTests`、流发现实现与测试 | `docs/qa/003-performance.md` | 能力边界通过；1000/100 样本基准待执行 |
| Q8 启停/音频 | `BackgroundAudioTests`、`RuntimeLifecycleTests`、`ReliabilityAcceptanceTests` | `docs/qa/003-windows-runtime.md` | 自动化通过；完整实机循环待执行 |
| Q9 开发数据/Git | `DatabaseInitializerTests`、`DevelopmentDataTests`、`DataBoundaryTests` | `runtime-dotnet/README.md` | 通过；新库与旧库边界明确 |
| Q10 Windows 运行 | Windows/Integration 测试工程 | `docs/qa/003-windows-runtime.md` | 软件探针通过；四屏 60 分钟待实机 |
| Q11 原生壳/UI 安全 | `electron-security.test.mjs`、`capacitor-platform.test.mjs`、`security-boundary.test.mjs` | `docs/qa/003-electron.md`、`003-android.md`、`003-browser-ui.md` | 静态、自动化及 Electron/Android 基础实包边界通过；交互式文件/外链场景待补 |

## FR-001–FR-030 映射

| 需求 | 主要证据 | 状态 |
| --- | --- | --- |
| FR-001–003 | 前端共享构建测试、HTTP 合同测试、`DatabaseInitializerTests` | 自动化通过；三端实包待验证 |
| FR-004–006 | `PlaybackRulesTests`、ControlHost 兼容测试、`BackgroundAudioTests` | 通过 |
| FR-007–010 | 命令仓储、围栏、恢复、投影和前端 actual-state 测试 | 通过 |
| FR-011–014 | `PresentationPolicyTests`、`OfficeOperationTests`、`MediaPreparationTests` | 软件通过；Office 实机待验证 |
| FR-015–017 | `ResourceSwitchTests`、`WebViewPreheatTests`、`VlcAdapterTests`、流发现实现 | 软件通过；长时间预热待验证 |
| FR-018–021 | `RuntimeLifecycleTests`、Supervisor/Worker 测试与 QA 模板 | 软件通过；Windows 运行待验证 |
| FR-022–023 | 独立 DataRoot 测试、开发脚本、Git 范围说明 | 通过 |
| FR-024 | 平台适配测试、主机/客户端进程边界 | 软件通过；实包关闭行为待验证 |
| FR-025 | `LogRedaction` 与 `SecurityBoundaryTests` | 通过 |
| FR-026–027 | 本文件、Spec Kit 产物、锁文件和验证命令 | 进行中 |
| FR-028–030 | 响应式/平台/安全边界测试 | 自动化通过；浏览器、Electron、Android 实测待验证 |

## SC-001–SC-010 映射

| 成功标准 | 证据 | 当前结论 |
| --- | --- | --- |
| SC-001 | Q1、三端矩阵 | 待 Electron/Android 实包 |
| SC-002 | `ReliabilityAcceptanceTests`、`CommandRecoveryTests` | 通过 |
| SC-003 | `CommandRecoveryTests`、`OfficeOperationTests` | 通过 |
| SC-004 | `PresentationPolicyTests`、Office QA | 软件通过，实机待验证 |
| SC-005 | `WebViewPreheatTests`、预热 QA | 软件通过，真实 WebView2 待验证 |
| SC-006 | 性能 QA | 待 1000/100 样本 |
| SC-007 | `RuntimeLifecycleTests`、Windows 运行 QA | 软件通过，完整次数待实机 |
| SC-008 | `DevelopmentDataTests`、`DataBoundaryTests` | 通过 |
| SC-009 | Windows 60 分钟 QA | 待实机 |
| SC-010 | 本矩阵、三端恢复和 Android QA | 映射完成，实包项待执行 |

## 自动化执行记录

执行日期：2026-09-09；环境：Windows x64，.NET SDK 10.0.400。

- `dotnet restore runtime-dotnet/ScpCv.sln --force-evaluate`：通过。
- `dotnet build runtime-dotnet/ScpCv.sln --no-restore`：通过，0 警告、0 错误。
- `dotnet test runtime-dotnet/ScpCv.sln -c Release --no-build --no-restore --filter "Category!=Physical"`：通过，Domain 38、Contracts 18、Windows 5、Integration 32、Infrastructure 18、ControlHost 49，共 160 项。
- `pnpm --dir frontend test`：通过，36/36。
- `pnpm --dir frontend typecheck`：通过。
- `pnpm --dir frontend build:web`、`build:app`、`build:electron-main`：通过；Vite 提示主入口压缩前约 1.07 MB，记录为后续代码分割优化项。
- Playwright + Chrome（Vite preview + simulation ControlHost，1440×900/768×1024/390×844）：通过；截图见 `docs/qa/003-browser-*.png`，console/pageerror 为 0。
- `pnpm build:electron`：未完成；electron-builder 下载阶段遇到本机证书链错误（`unable to verify the first certificate`），未修改安全配置绕过。
- Electron unpacked 包实测：修复持久化 partition 协议注册和 sandbox preload 后，`app://scp-cv/#/connect` 正常渲染，CDP 页面标题和 `window.scpCvElectron` API 均可检查；完整 ControlHost 认证/SSE、文件对话框仍待联调。
- Android AVD 实测：Pixel_9_Pro / API 37 / WebView 145.0.7632.218 安装并启动 debug APK，连接页可见，HOME/重启生命周期可恢复；认证/SSE、文件和外链场景仍待联调。

## 尚未验证

- 打包 Electron 的真实认证、SSE、文件选择/保存和关闭行为。
- Android WebView>=111 设备上的 APK、前后台、返回键、文件与外链限制。
- 真实浏览器桌面/平板/手机视觉检查与控制台日志。
- 普通命令 1000 样本、健康热切换 100 样本的 p95。
- 四屏、Office、VLC、MediaMTX、音频的 60 分钟混合运行。

因此当前不得执行 T118，也不得删除 Django/Python 运行时。

## Convergence 实施记录（2026-09-09）

- T120：显示、音频、场景激活及 PPT 控制写操作已接入 `CommandCoordinator`；大屏模式产生的窗口静音也持久入队。完成结果和后续状态上报均重新投影最早剩余 pending 命令，避免清空尚未执行的意图。`RuntimeIntentQueueTests` 与 `CommandPendingProjectionTests` 通过。
- T121：Supervisor 的 `start/stop/restart/status` 入口、状态文件、四 Player/Audio/Office/MediaMTX 编排及成员退出整组停止已实现；一次开发构建故障退出证据见 `docs/qa/003-runtime-lifecycle.md`。
- T122：physical ControlHost 托管并发 Named Pipe broker，验证 OS PID/start-time/session/role/instance，支持 Worker 注册、heartbeat、Claim/Renew/Result/State、Wake 和 Supervisor 子进程登记。`RuntimePipeBrokerTests` 3 项通过。
- Worker 通用管道客户端已改为单 reader loop，按 `correlation_id` 分发最多 64 个在途响应，并将 Wake 等主动消息置于独立流；`RuntimePipeClientTests` 2 项通过。Supervisor 的首次可信启动入口仍属于 T127，不把预登记测试替代为完整启停控制通道。

## Spec Kit 一致性分析（T119）

2026-09-08 对 `spec.md`、`plan.md`、`tasks.md`、项目宪章和实现路径进行只读交叉检查：

- Spec Kit 校验：通过（`validate_specs.py --specs-dir specs`）。
- `git diff --check`：通过；仅报告现有 CRLF/LF 转换提示，无空白错误。
- FR-001–FR-030：均有计划和任务映射；SC-001–SC-010：均有自动或人工证据条目。
- 任务依赖顺序与快速迭代边界一致；T118 仍被明确阻塞于 T107–T116，且旧 Django/Python 未删除。
- 发现并保留的未完成项：T050、T113–T116 为真实封装客户端/硬件/性能门禁；它们已在 QA 文档标为待实机，不冒充通过。
- 无宪章 MUST 冲突、无未映射核心需求、无新增迁移/回滚工程。
