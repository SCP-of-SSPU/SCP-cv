# Tasks: 共享多端控制台与 .NET 播控运行时

**Input**: `specs/003-dotnet-runtime-refactor/` 下的 `spec.md`、`plan.md`、
`research.md`、`data-model.md`、`contracts/` 与 `quickstart.md`

**Prerequisites**: requirements checklist 16/16 通过；项目宪章已更新到 2.0.0；
实现分支为 `refactor/003-dotnet-runtime`

**Tests**: 本规范明确要求自动化、真实浏览器/封装客户端和 Windows 开发机验证，
因此每个用户故事均包含先行测试或风险探针任务。

**Scope Guard**: 当前处于快速迭代期。不创建旧 Django 数据迁移、逆迁移、长期双栈、
生产切流、现场回退演练、商店发布或自动更新系统。Git 只恢复受跟踪源码、规范和锁文件，
不得自动删除或覆盖现有数据库与媒体。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可在不修改同一文件且不依赖未完成任务时并行执行
- **[Story]**: 对应 `spec.md` 的用户故事
- 每项任务均给出目标文件路径；完成后必须将 `[ ]` 改为 `[X]`

## Phase 1: Setup（工程骨架）

**Purpose**: 建立可还原、可构建的 .NET 多进程工程和三端共享前端构建入口。

- [X] T001 更新实施分支、状态和宪章检查记录到 `specs/003-dotnet-runtime-refactor/spec.md`、`specs/003-dotnet-runtime-refactor/plan.md`、`specs/003-dotnet-runtime-refactor/governance.md` 与 `specs/003-dotnet-runtime-refactor/quickstart.md`
- [X] T002 创建锁定 .NET 10 SDK 的 `runtime-dotnet/global.json` 和解决方案 `runtime-dotnet/ScpCv.sln`
- [X] T003 [P] 建立统一编译、分析器与集中包版本配置 `runtime-dotnet/Directory.Build.props`、`runtime-dotnet/Directory.Packages.props` 和 `runtime-dotnet/NuGet.Config`
- [X] T004 创建 Domain、Contracts、Infrastructure、ControlHost、Supervisor、PlayerWorker、AudioWorker、PowerPointHost 工程及引用关系到 `runtime-dotnet/src/*/*.csproj`
- [X] T005 [P] 创建 Domain、Contracts、Infrastructure、ControlHost、Integration、Windows 测试工程及分类约定到 `runtime-dotnet/tests/*/*.csproj` 和 `runtime-dotnet/tests/README.md`
- [X] T006 扩充 .NET、Electron、Capacitor、Android 与验证数据忽略规则到 `.gitignore`
- [X] T007 为 Tailwind 4、Electron、Capacitor 和多目标构建添加锁定依赖及脚本到 `frontend/package.json` 和 `pnpm-lock.yaml`
- [X] T008 接入 `@tailwindcss/vite` 并映射现有 Fluent tokens、保持无 Preflight 策略到 `frontend/vite.config.ts`、`frontend/src/styles/tailwind.css` 和 `frontend/src/main.ts`
- [X] T009 建立 web/app 构建模式、共享路由工厂与平台适配接口到 `frontend/src/platform/index.ts`、`frontend/src/router/index.ts`、`frontend/vite.config.ts` 和 `frontend/tsconfig.json`

**Checkpoint**: `dotnet restore`、空解决方案构建、现有前端测试/类型检查/构建均可运行。

---

## Phase 2: Foundational（阻塞性基础设施）

**Purpose**: 建立所有用户故事共享的领域、持久化、合同、进程通信和模拟验证基础。

**⚠️ CRITICAL**: 本阶段完成前不进入业务用户故事。

- [X] T010 [P] 定义窗口、媒体、场景、播放模式、命令状态与运行组值对象到 `runtime-dotnet/src/ScpCv.Domain/Model/DomainPrimitives.cs`
- [X] T011 [P] 定义账户、媒体、会话、场景、音频、流与派生资源实体到 `runtime-dotnet/src/ScpCv.Domain/Model/Entities.cs`
- [X] T012 实现四窗静音、媒体能力、场景三态和 PowerPoint/PDF 模式规则到 `runtime-dotnet/src/ScpCv.Domain/Rules/PlaybackRules.cs` 和 `runtime-dotnet/tests/ScpCv.Domain.Tests/PlaybackRulesTests.cs`
- [X] T013 [P] 定义保持 snake_case 外观的认证、媒体、显控、场景、设备和音频 HTTP DTO 到 `runtime-dotnet/src/ScpCv.Contracts/Http/*.cs`
- [X] T014 [P] 定义版本化 IPC 帧、握手、领取、续租、结果、状态、Office 与关闭消息到 `runtime-dotnet/src/ScpCv.Contracts/Ipc/*.cs`
- [X] T015 编写 DTO 序列化与 `docs/openapi.yaml` 样例兼容测试到 `runtime-dotnet/tests/ScpCv.Contracts.Tests/HttpContractTests.cs` 和 `runtime-dotnet/tests/ScpCv.Contracts.Tests/IpcContractTests.cs`
- [X] T016 创建仅供 ControlHost 使用的 EF Core 上下文与实体配置到 `runtime-dotnet/src/ScpCv.Infrastructure/Persistence/ControlDbContext.cs` 和 `runtime-dotnet/src/ScpCv.Infrastructure/Persistence/Configurations/*.cs`
- [X] T017 创建新库初始 EF Core schema 到 `runtime-dotnet/src/ScpCv.Infrastructure/Persistence/Migrations/*_InitialControlSchema.cs` 和 `runtime-dotnet/src/ScpCv.Infrastructure/Persistence/Migrations/ControlDbContextModelSnapshot.cs`
- [X] T018 实现独立 DataRoot、SQLite WAL/busy timeout、已有不兼容库拒绝和非破坏性初始化到 `runtime-dotnet/src/ScpCv.Infrastructure/Configuration/DataRootOptions.cs`、`runtime-dotnet/src/ScpCv.Infrastructure/Persistence/DatabaseInitializer.cs` 和 `runtime-dotnet/tests/ScpCv.Infrastructure.Tests/DatabaseInitializerTests.cs`
- [X] T019 [P] 实现短事务单写入调度与逐操作 DbContext 工厂到 `runtime-dotnet/src/ScpCv.Infrastructure/Persistence/WriteCoordinator.cs`
- [X] T020 实现持久命令、租约、完成证据与目标序列存储到 `runtime-dotnet/src/ScpCv.Infrastructure/Commands/CommandRepository.cs` 和 `runtime-dotnet/src/ScpCv.Infrastructure/Persistence/Configurations/CommandRecordConfiguration.cs`
- [X] T021 [P] 实现运行组停止闩锁、Worker 所有权和 Office 操作持久化到 `runtime-dotnet/src/ScpCv.Infrastructure/Runtime/RuntimeAuthorityRepository.cs`
- [X] T022 [P] 建立稳定错误码、敏感字段脱敏和结构化关联日志到 `runtime-dotnet/src/ScpCv.Contracts/Errors/ErrorCodes.cs` 和 `runtime-dotnet/src/ScpCv.Infrastructure/Diagnostics/LogRedaction.cs`
- [X] T023 组装 ControlHost 配置、DI、健康检查和 simulation 安全模式到 `runtime-dotnet/src/ScpCv.ControlHost/Program.cs`、`runtime-dotnet/src/ScpCv.ControlHost/appsettings.json` 和 `runtime-dotnet/src/ScpCv.ControlHost/appsettings.Development.json`
- [X] T024 实现 4 字节长度帧、大小/超时限制、Windows 管道 ACL 和已登记进程身份校验到 `runtime-dotnet/src/ScpCv.ControlHost/Ipc/NamedPipeServer.cs` 和 `runtime-dotnet/tests/ScpCv.Integration.Tests/IpcFramingTests.cs`
- [X] T025 [P] 建立假 Worker、Office、设备和确定性时钟测试宿主到 `runtime-dotnet/tests/ScpCv.Integration.Tests/Fakes/RuntimeFakes.cs` 和 `runtime-dotnet/tests/ScpCv.Integration.Tests/Fixtures/ControlHostFixture.cs`
- [X] T026 [P] 创建 Electron/Capacitor Cookie、CSRF 与 EventSource 共享会话风险探针到 `frontend/scripts/verify-packaged-session.mjs` 和 `frontend/scripts/verify-packaged-session.test.mjs`
- [X] T027 [P] 创建 Office HWND、STA 消息泵、SetParent 与 DPI 诊断探针到 `runtime-dotnet/tools/ScpCv.InteropProbe/ScpCv.InteropProbe.csproj` 和 `runtime-dotnet/tools/ScpCv.InteropProbe/Program.cs`

**Checkpoint**: simulation ControlHost 能用全新目录启动；合同、SQLite、管道半包/超大包及两项风险探针具备可重复入口。

---

## Phase 3: User Story 1 - 三端共享同一套控制台（Priority: P1）🎯 MVP

**Goal**: Web、Windows Electron 与 Android Capacitor 使用同一套页面、路由、store、DTO 和业务规则连接同一 ControlHost。

**Independent Test**: 三端在 simulation 主机完成登录、媒体、四窗、模式、预案、设备和实时状态流程，未批准业务差异为 0。

### Tests for User Story 1

- [X] T028 [P] [US1] 先编写认证、CSRF、改密、权限和登出合同测试到 `runtime-dotnet/tests/ScpCv.ControlHost.Tests/AuthEndpointTests.cs`
- [X] T029 [P] [US1] 先编写媒体、会话、场景、设备和音频旧 HTTP 外观合同测试到 `runtime-dotnet/tests/ScpCv.ControlHost.Tests/LegacyHttpContractTests.cs`
- [X] T030 [P] [US1] 先编写切主机 generation、迟到响应、SSE 重连和无离线重放前端测试到 `frontend/scripts/client-connection.test.mjs`
- [X] T031 [P] [US1] 先编写 history/hash 路由、返回键和文件传输平台适配测试到 `frontend/scripts/platform-adapters.test.mjs`

### Implementation for User Story 1

- [X] T032 [US1] 实现 ASP.NET Core Identity/会话 Cookie、权限、CSRF token 与精确 Origin 策略到 `runtime-dotnet/src/ScpCv.Infrastructure/Auth/AuthServiceCollectionExtensions.cs` 和 `runtime-dotnet/src/ScpCv.ControlHost/Auth/AuthEndpoints.cs`
- [X] T033 [US1] 实现账户 seed、登录、状态、me、改密和登出端点到 `runtime-dotnet/src/ScpCv.ControlHost/Auth/AuthEndpoints.cs` 和 `runtime-dotnet/src/ScpCv.Infrastructure/Auth/DevelopmentAccountSeeder.cs`
- [X] T034 [P] [US1] 实现文件夹、媒体源、上传、播放主机路径、下载与预览服务到 `runtime-dotnet/src/ScpCv.Infrastructure/Media/MediaSourceService.cs`
- [X] T035 [US1] 映射既有媒体与文件夹路由和响应外观到 `runtime-dotnet/src/ScpCv.ControlHost/Endpoints/MediaEndpoints.cs`
- [X] T036 [P] [US1] 实现运行状态、四窗口、显示器选择和系统音量领域服务到 `runtime-dotnet/src/ScpCv.Infrastructure/Playback/RuntimeStateService.cs`
- [X] T037 [US1] 映射 sessions、runtime、displays、playback 与 volume 路由到 `runtime-dotnet/src/ScpCv.ControlHost/Endpoints/PlaybackEndpoints.cs`
- [X] T038 [P] [US1] 实现场景排序、捕获、更新与三态激活服务到 `runtime-dotnet/src/ScpCv.Infrastructure/Scenarios/ScenarioService.cs`
- [X] T039 [US1] 映射 scenarios 路由和兼容响应到 `runtime-dotnet/src/ScpCv.ControlHost/Endpoints/ScenarioEndpoints.cs`
- [X] T040 [P] [US1] 实现配置驱动的设备查询/控制与 simulation 适配器到 `runtime-dotnet/src/ScpCv.Infrastructure/Devices/DeviceService.cs`
- [X] T041 [US1] 映射 devices、system/restart 与 system/shutdown 路由到 `runtime-dotnet/src/ScpCv.ControlHost/Endpoints/SystemEndpoints.cs`
- [X] T042 [US1] 实现初始快照、最新事件、心跳和重连全量同步 SSE 到 `runtime-dotnet/src/ScpCv.ControlHost/Events/SseEventStream.cs`
- [X] T043 [US1] 实现服务器配置、cookie fetch/EventSource、connection_generation 和切主机清理到 `frontend/src/services/api.ts`、`frontend/src/platform/connection.ts` 和 `frontend/src/stores/runtime.ts`
- [X] T044 [US1] 新增播放主机连接页和断线/播放器离线分层状态到 `frontend/src/features/settings/ServerConnectionView.vue` 和 `frontend/src/router/index.ts`
- [X] T045 [US1] 用 Tailwind utilities 重整共享响应式壳层并保持 Fluent tokens/Naive UI 行为到 `frontend/src/layouts/AppShell.vue`、`frontend/src/layouts/AppNavigation.vue` 和 `frontend/src/styles/tailwind.css`
- [X] T046 [US1] 实现安全 `app://scp-cv` 协议、CSP、导航/权限限制和窗口生命周期到 `frontend/electron/main.ts`
- [X] T047 [US1] 实现 contextIsolation preload 的受限文件选择/保存与主机配置 API 到 `frontend/electron/preload.ts` 和 `frontend/src/platform/electron.ts`
- [X] T048 [US1] 配置 Capacitor 本地资源、受限 HTTPS origin 和必要插件到 `frontend/capacitor.config.ts`、`frontend/src/platform/capacitor.ts` 和 `frontend/android/app/src/main/AndroidManifest.xml`
- [X] T049 [US1] 实现 Android 前后台/SSE 重建、返回键、安全区域和文件上传下载到 `frontend/src/platform/capacitor.ts` 和 `frontend/src/platform/lifecycle.ts`
- [ ] T050 [US1] 在真实 Web、打包 Electron 与 Android 测试设备记录共享用例和会话/SSE 结果到 `docs/qa/003-client-matrix.md`

**Checkpoint**: US1 可在 simulation 主机独立演示；关闭任一客户端不停止主机，三端均不复制业务页面。

---

## Phase 4: User Story 2 - 可靠命令与故障恢复（Priority: P1）

**Goal**: 保留显示/音频队列差异，并以 token、epoch、generation 和完成证据避免丢命令、旧写入和危险重放。

**Independent Test**: 在领取、执行、确认各边界注入退出/断连，完成 100 次执行前恢复、100 次 ACK 丢失与 1000 次音频并发测试。

### Tests for User Story 2

- [X] T051 [P] [US2] 先编写显示 OPEN/CLOSE/RESET 与音频 OPEN 的合并/取代差异测试到 `runtime-dotnet/tests/ScpCv.Domain.Tests/CommandPolicyTests.cs`
- [X] T052 [P] [US2] 先编写 claim token、owner/group epoch、租约和迟到 generation 拒绝测试到 `runtime-dotnet/tests/ScpCv.Integration.Tests/CommandFencingTests.cs`
- [X] T053 [P] [US2] 先编写执行前崩溃、ACK 丢失、重复结果与 uncertain 非幂等动作测试到 `runtime-dotnet/tests/ScpCv.Integration.Tests/CommandRecoveryTests.cs`

### Implementation for User Story 2

- [X] T054 [US2] 实现事务内入队、目标序列、兼容 pending 投影和提交后 Wake 到 `runtime-dotnet/src/ScpCv.Infrastructure/Commands/CommandCoordinator.cs`
- [X] T055 [P] [US2] 实现显示命令验证、合并和 pending-only 取代策略到 `runtime-dotnet/src/ScpCv.Domain/Commands/DisplayCommandPolicy.cs`
- [X] T056 [P] [US2] 实现背景音频有序合并且 OPEN 不清队列的策略到 `runtime-dotnet/src/ScpCv.Domain/Commands/AudioCommandPolicy.cs`
- [X] T057 [US2] 实现 armed 闸门、最早命令领取、租约续期和安全重新领取到 `runtime-dotnet/src/ScpCv.Infrastructure/Commands/CommandLeaseService.cs`
- [X] T058 [US2] 实现幂等结果确认、结果指纹、实际/意图区分和 uncertain 处置到 `runtime-dotnet/src/ScpCv.Infrastructure/Commands/CommandResultService.cs`
- [X] T059 [US2] 接线 Claim、Renew、Result、StateReport 与 Wake IPC 到 `runtime-dotnet/src/ScpCv.ControlHost/Ipc/RuntimeMessageDispatcher.cs`
- [X] T060 [US2] 创建 Worker 通用管道客户端、重连退避、结果缓存和停止闩锁处理到 `runtime-dotnet/src/ScpCv.Contracts/Runtime/RuntimePipeClient.cs`
- [X] T061 [US2] 将有效完成状态和错误发布到兼容 SSE 投影到 `runtime-dotnet/src/ScpCv.ControlHost/Events/RuntimeProjectionPublisher.cs`
- [X] T062 [US2] 调整前端 accepted/online/actual state 展示，禁止请求返回即伪报 playing 到 `frontend/src/stores/sessions.ts` 和 `frontend/src/features/display/DisplayView.vue`
- [X] T063 [US2] 实现 SC-002/003 样本化故障注入测试与结果输出到 `runtime-dotnet/tests/ScpCv.Integration.Tests/ReliabilityAcceptanceTests.cs`

**Checkpoint**: 命令恢复和不确定副作用判定可仅凭 simulation 独立验证，不宣称 exactly-once。

---

## Phase 5: User Story 3 - PowerPoint 动态放映与 PDF 回退（Priority: P1）

**Goal**: 全主机唯一动态放映，静态回退严格匹配源版本，Office 操作由独立 STA/COM 进程串行拥有。

**Independent Test**: 四窗口并发打开文稿并穿插导入/超时/重复 NEXT，验证动态放映不超过一路、回退不误升级且不误杀用户 Office。

### Tests for User Story 3

- [X] T064 [P] [US3] 先编写单槽、摘要匹配 PDF、缺失失败、不自动升级和 reset 模式测试到 `runtime-dotnet/tests/ScpCv.Domain.Tests/PresentationPolicyTests.cs`
- [X] T065 [P] [US3] 先编写 Office operation 去重、STA 出队再验权、超时 inflight 与迟到结果测试到 `runtime-dotnet/tests/ScpCv.Integration.Tests/OfficeOperationTests.cs`
- [X] T066 [P] [US3] 先编写准备作业优先级、原子发布和旧 source digest 清理测试到 `runtime-dotnet/tests/ScpCv.Infrastructure.Tests/MediaPreparationTests.cs`

### Implementation for User Story 3

- [X] T067 [US3] 实现主机唯一命名互斥锁、Office PID/start-time 与持续所有权诊断到 `runtime-dotnet/src/ScpCv.PowerPointHost/Ownership/PowerPointOwnershipGuard.cs`
- [X] T068 [US3] 实现独立 STA 线程、消息泵、operation 去重和取消边界到 `runtime-dotnet/src/ScpCv.PowerPointHost/Sta/OfficeStaDispatcher.cs`
- [X] T069 [US3] 实现明确自有 Presentation 的打开、放映、导航、媒体控制、导出和关闭到 `runtime-dotnet/src/ScpCv.PowerPointHost/Interop/PowerPointComAdapter.cs`
- [X] T070 [US3] 实现 HWND/PID/start-time/DPI/样式验证与 AttachSurface 到 `runtime-dotnet/src/ScpCv.PowerPointHost/Windows/SlideShowWindowAttacher.cs`
- [X] T071 [US3] 实现 PowerPoint 槽位、PDF 回退、实际 playback_mode 和 reset 协调到 `runtime-dotnet/src/ScpCv.Infrastructure/Presentations/PresentationCoordinator.cs`
- [X] T072 [US3] 实现持久准备作业、无 Showing 时 Office 调度和制品 manifest 原子发布到 `runtime-dotnet/src/ScpCv.Infrastructure/Media/MediaPreparationService.cs`
- [X] T073 [P] [US3] 实现 Windows.Data.Pdf 页渲染、邻页预取和 1-based 页码到 `runtime-dotnet/src/ScpCv.PlayerWorker/Adapters/PdfPlaybackAdapter.cs`
- [X] T074 [US3] 映射 ppt-resources、navigate、ppt-media 与 reset-ppt 兼容路由到 `runtime-dotnet/src/ScpCv.ControlHost/Endpoints/PresentationEndpoints.cs`
- [X] T075 [US3] 保持实际 PowerPoint/PDF 模式和快速切源请求序列 UI 防护到 `frontend/src/features/display/pptResourceRequest.ts` 和 `frontend/src/features/display/playbackCapabilities.ts`
- [X] T076 [US3] 在开发 Windows/Office 环境记录 HWND、混合 DPI、模态、用户 Office 共存与长导出探针结果到 `docs/qa/003-office-interop.md`

**Checkpoint**: 软件测试证明仲裁和回退语义；实机项未执行时明确保留为未验证，不降级安全策略。

---

## Phase 6: User Story 4 - 网页状态保活与低等待切换（Priority: P1）

**Goal**: Worker 内保留健康网页和 VLC 资源，切换可见性而不重新导航，不跨进程搬运原生活对象。

**Independent Test**: 同一输出的两个健康网页切换 50 次新增导航为 0；直播预热 10 分钟后仍可认领。

### Tests for User Story 4

- [X] T077 [P] [US4] 先编写资源 key、source generation、旧结果和切换失败恢复测试到 `runtime-dotnet/tests/ScpCv.Domain.Tests/ResourceSwitchTests.cs`
- [X] T078 [P] [US4] 先编写 WebView 导航计数、隐藏保活、renderer 故障和预算拒绝测试到 `runtime-dotnet/tests/ScpCv.Windows.Tests/WebViewPreheatTests.cs`
- [X] T079 [P] [US4] 先编写 VLC seek/loop/音量/结束回调与 SRT/RTSP 能力测试到 `runtime-dotnet/tests/ScpCv.Windows.Tests/VlcAdapterTests.cs`

### Implementation for User Story 4

- [X] T080 [US4] 实现每实例一个显示器的 WPF Worker 宿主、几何和生命周期到 `runtime-dotnet/src/ScpCv.PlayerWorker/App.xaml.cs` 和 `runtime-dotnet/src/ScpCv.PlayerWorker/PlayerWindow.xaml.cs`
- [X] T081 [US4] 定义 Prepare/Open/Control/Observe/Hide/Close 适配器合同和资源状态机到 `runtime-dotnet/src/ScpCv.PlayerWorker/Adapters/IPlaybackAdapter.cs` 和 `runtime-dotnet/src/ScpCv.PlayerWorker/Resources/WarmResource.cs`
- [X] T082 [US4] 实现 Worker 独立 UDF 的 WebView2 实例池、ProcessFailed 与健康检查到 `runtime-dotnet/src/ScpCv.PlayerWorker/Adapters/WebViewPlaybackAdapter.cs`
- [X] T083 [US4] 实现 Worker 生命周期 LibVLC、媒体池、回调调度和安全释放到 `runtime-dotnet/src/ScpCv.PlayerWorker/Adapters/VlcPlaybackAdapter.cs`
- [X] T084 [P] [US4] 实现 WPF 图片适配器和文件版本校验到 `runtime-dotnet/src/ScpCv.PlayerWorker/Adapters/ImagePlaybackAdapter.cs`
- [X] T085 [US4] 实现新资源 Ready 后显隐切换、旧画面恢复和迟到 generation 隔离到 `runtime-dotnet/src/ScpCv.PlayerWorker/Playback/SourceSwitchCoordinator.cs`
- [X] T086 [US4] 接入 MediaMTX 流发现、在线探测和 10 分钟预热健康续检到 `runtime-dotnet/src/ScpCv.Infrastructure/Streams/StreamDiscoveryService.cs`
- [X] T087 [US4] 记录 50 次网页切换和流预热的导航、延迟与资源趋势到 `docs/qa/003-preheat-performance.md`

**Checkpoint**: 同一 Worker 健康资源可复用，崩溃后如实冷重建，未承诺跨进程保存 DOM。

---

## Phase 7: User Story 5 - 独立音频与可诊断运行（Priority: P2）

**Goal**: AudioWorker 独立播放列表；Supervisor 在正确交互桌面编排四显示、一音频、一个 Office 与 MediaMTX，并安全启停。

**Independent Test**: simulation 完成音频全流程和 20 次正常启停/10 次故障退出；开发 Windows 验证交互桌面、显示器与真实依赖边界。

### Tests for User Story 5

- [X] T088 [P] [US5] 先编写列表顺序、自然结束、重复/旧 Finished、循环和删除当前项测试到 `runtime-dotnet/tests/ScpCv.Domain.Tests/BackgroundAudioTests.cs`
- [X] T089 [P] [US5] 先编写成员退出、停止闩锁、协作超时、PID 复用和不误杀测试到 `runtime-dotnet/tests/ScpCv.Integration.Tests/RuntimeLifecycleTests.cs`

### Implementation for User Story 5

- [X] T090 [US5] 创建 AudioWorker 管道宿主和单播放实例生命周期到 `runtime-dotnet/src/ScpCv.AudioWorker/Program.cs`
- [X] T091 [US5] 实现背景音频 LibVLC 播放、进度、音量、循环与 generation 结束事件到 `runtime-dotnet/src/ScpCv.AudioWorker/Audio/VlcAudioAdapter.cs`
- [X] T092 [US5] 实现列表、立即播放、上一首/下一首、删除源与自然推进服务到 `runtime-dotnet/src/ScpCv.Infrastructure/Audio/BackgroundAudioService.cs`
- [X] T093 [US5] 映射 background-audio 全部兼容路由和响应到 `runtime-dotnet/src/ScpCv.ControlHost/Endpoints/BackgroundAudioEndpoints.cs`
- [X] T094 [US5] 实现 AudioFinished event_id/source_generation 幂等推进到 `runtime-dotnet/src/ScpCv.ControlHost/Ipc/AudioEventHandler.cs`
- [X] T095 [US5] 实现 Supervisor 子进程登记、PID/start-time/会话校验和日志汇聚到 `runtime-dotnet/src/ScpCv.Supervisor/Processes/ProcessRegistry.cs`
- [X] T096 [US5] 实现四 PlayerWorker、一 AudioWorker、一 PowerPointHost 和 MediaMTX 的交互桌面启动编排到 `runtime-dotnet/src/ScpCv.Supervisor/Runtime/RuntimeLauncher.cs`
- [X] T097 [P] [US5] 实现显示器枚举、设备路径、负坐标、混合 DPI 与目标分配到 `runtime-dotnet/src/ScpCv.Supervisor/Windows/DisplayTopologyService.cs`
- [X] T098 [US5] 实现 draining、5 秒协作等待、3 秒自有进程终止和 Office 特殊保护到 `runtime-dotnet/src/ScpCv.Supervisor/Runtime/ShutdownCoordinator.cs`
- [X] T099 [US5] 实现项目自有 MediaMTX 启停、健康和外部实例边界到 `runtime-dotnet/src/ScpCv.Supervisor/Runtime/MediaMtxProcess.cs`
- [X] T100 [US5] 提供 start/stop/restart/status 开发入口到 `runtime-dotnet/scripts/runtime.ps1` 和 `runtime-dotnet/README.md`
- [X] T101 [US5] 执行 20 次正常启停、10 次故障退出与客户端关闭测试并记录到 `docs/qa/003-runtime-lifecycle.md`

**Checkpoint**: 控制客户端和播放主机生命周期解耦；无交互桌面时如实 unavailable。

---

## Phase 8: User Story 6 - Git 驱动的非破坏性快速迭代（Priority: P2）

**Goal**: 全新测试目录可初始化，代码回退边界清楚，任何版本操作都不隐式覆盖旧数据库或媒体。

**Independent Test**: 在三个全新目录初始化并运行认证/模型用例；向已有/不兼容目录注入标记文件后确认初始化拒绝且文件未改变。

### Tests for User Story 6

- [X] T102 [P] [US6] 先编写全新目录 seed、重复初始化和不兼容 schema 拒绝测试到 `runtime-dotnet/tests/ScpCv.Integration.Tests/DevelopmentDataTests.cs`
- [X] T103 [P] [US6] 先编写 DataRoot 越界、旧 `db.sqlite3` 与媒体不被触碰测试到 `runtime-dotnet/tests/ScpCv.Infrastructure.Tests/DataBoundaryTests.cs`

### Implementation for User Story 6

- [X] T104 [US6] 实现显式 `db init`、`db seed-development` 和 schema 状态命令到 `runtime-dotnet/src/ScpCv.ControlHost/Commands/DatabaseCommands.cs`
- [X] T105 [US6] 将独立验证目录、Git 恢复范围和禁止自动清空规则写入 `runtime-dotnet/README.md` 和 `docs/维护文档.md`
- [X] T106 [US6] 更新规范状态并移除已完成的旧“仅规划”声明到 `specs/003-dotnet-runtime-refactor/spec.md`、`specs/003-dotnet-runtime-refactor/plan.md`、`specs/003-dotnet-runtime-refactor/governance.md` 和 `specs/003-dotnet-runtime-refactor/quickstart.md`

**Checkpoint**: 数据初始化不依赖旧库；Git 操作不被描述为数据库/媒体恢复方案。

---

## Phase 9: Polish & Cross-Cutting Validation

**Purpose**: 收敛合同、文档、性能、真实平台验证和旧实现清理。

- [X] T107 [P] 建立全部 `docs/openapi.yaml` 路由、方法、状态码与 .NET endpoint 的自动对照测试到 `runtime-dotnet/tests/ScpCv.Contracts.Tests/OpenApiCoverageTests.cs`
- [X] T108 [P] 补齐日志脱敏、路径越界、CSRF/CORS、外链与 IPC 假身份安全测试到 `runtime-dotnet/tests/ScpCv.Integration.Tests/SecurityBoundaryTests.cs` 和 `frontend/scripts/security-boundary.test.mjs`
- [X] T109 建立 Q1–Q11、FR-001–030、SC-001–010 到自动/人工证据的验收矩阵到 `specs/003-dotnet-runtime-refactor/verification.md`
- [X] T110 运行并修复全部非实机 .NET 测试，记录命令和结果到 `specs/003-dotnet-runtime-refactor/verification.md`
- [X] T111 运行并修复共享前端测试、typecheck、web/app/Electron 构建，记录结果到 `specs/003-dotnet-runtime-refactor/verification.md`
- [X] T112 在真实浏览器检查桌面/平板/手机布局、活动/错误/媒体状态和控制台日志，记录到 `docs/qa/003-browser-ui.md`
- [ ] T113 在实际打包 Electron 中验证安全协议、认证/SSE、路由、文件和关闭行为，记录到 `docs/qa/003-electron.md`
- [ ] T114 在实际 Android APK 与 WebView>=111 设备验证认证/SSE、前后台、返回键、文件和外链限制，记录到 `docs/qa/003-android.md`
- [ ] T115 执行普通命令 1000 样本与健康热切换 100 样本基准，记录 p95 和测试条件到 `docs/qa/003-performance.md`
- [ ] T116 执行开发 Windows 四屏/Office/VLC/MediaMTX/音频 60 分钟混合测试，记录硬件条件和未通过项到 `docs/qa/003-windows-runtime.md`
- [X] T117 更新目标架构、开发运行、客户端连接和故障诊断文档到 `README.md`、`docs/使用文档.md`、`docs/维护文档.md` 和 `docs/CHANGELOG.md`
- [ ] T118 在 T107–T116 所需门禁通过后删除被完整替代的 Django/Python 运行时代码与依赖，并同步 `pyproject.toml`、`uv.lock`、`manage.py`、`scp_cv/` 和 `tests/`
- [X] T119 运行 Spec Kit 校验、`git diff --check` 与跨产物一致性分析，并记录最终结论到 `specs/003-dotnet-runtime-refactor/verification.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: 无依赖，立即开始。
- **Phase 2 Foundational**: 依赖 Phase 1，阻塞全部用户故事。
- **US1**: 依赖 Phase 2；以 simulation ControlHost 形成首个可演示 MVP。
- **US2**: 依赖 Phase 2，并为 US1 的写操作提供可靠执行语义。
- **US3**: 依赖 US2 的命令凭据/IPC；不依赖 US4/US5。
- **US4**: 依赖 US2 的 generation/结果机制；可与 US3 的非共享文件工作并行。
- **US5**: 依赖 US2，并集成 US3/US4 的进程生命周期。
- **US6**: 依赖 Phase 2；可在不修改同一文件时与 US3/US4 并行，最终状态更新在各故事后完成。
- **Polish**: 依赖选定的全部用户故事；T118 还严格依赖 T107–T116 门禁通过。

### User Story Dependencies

```text
Setup → Foundation → US1（共享控制台 MVP）
                   ├→ US2（可靠命令）→ US3（Office/PDF）
                   │                 └→ US4（预热/切换）
                   ├→ US6（开发数据/Git）
                   └→ US5（音频/启停，集成 US2–US4）
                                      ↓
                                 Polish / 旧栈清理
```

### Within Each User Story

- 测试和风险探针先写并确认能捕获缺失行为，再实现对应代码。
- Domain/合同先于 Infrastructure，Infrastructure 先于 endpoint/worker，最后做客户端与集成。
- 同一目标命令串行；不同目标、不同工程且无未完成依赖的 `[P]` 任务可并行。
- 每个 checkpoint 通过后再提交该逻辑块并进入下一阶段。

### Parallel Opportunities

- T003/T005、T010/T011/T013/T014、T019/T021/T022/T025/T026/T027 可在各自前置完成后并行。
- 各用户故事的先行测试可并行编写；US3 与 US4 在 US2 完成后可并行。
- 前端平台壳文件与 .NET 领域/基础设施文件可并行，但共享 `frontend/vite.config.ts`、
  `frontend/src/router/index.ts` 和集中包配置必须串行修改。
- 真实 Electron、Android、浏览器、Windows 运行验证可在构建产物稳定后由不同测试环境并行执行。

---

## Parallel Examples

### US1

```text
T028 AuthEndpointTests.cs
T029 LegacyHttpContractTests.cs
T030 client-connection.test.mjs
T031 platform-adapters.test.mjs
```

### US2

```text
T051 CommandPolicyTests.cs
T052 CommandFencingTests.cs
T053 CommandRecoveryTests.cs
```

### US3 + US4

```text
T064–T066 Presentation/Office/Preparation tests
T077–T079 Resource/WebView/VLC tests
```

### US5 + US6

```text
T088–T089 Audio/Lifecycle tests
T102–T103 Development data boundary tests
```

---

## Implementation Strategy

### MVP First

1. 完成 Phase 1 和 Phase 2。
2. 完成 US1，让三端通过同一共享页面连接 simulation ControlHost。
3. 停止并验证认证/SSE、路由、文件与业务合同，再进入真实播放副作用。

### Incremental Delivery

1. 每个任务或紧密逻辑块使用 `type(scope): 中文摘要` 小提交。
2. US2 先建立可靠命令，再接入 Office、WebView2、VLC 和音频等外部副作用。
3. US3/US4 完成后由 US5 统一进程生命周期；US6 始终验证数据不被破坏。
4. 只有 T107–T116 门禁通过后才执行 T118 删除旧实现；历史由 Git 保留，不维持长期双栈。

## Notes

- 不把 HTTP 接受响应当作物理播放成功；实际模式和状态只由有效执行结果确认。
- 不通过关闭证书校验、Electron `webSecurity` 或 Android 安全限制来伪造封装客户端成功。
- 不因缺少实机环境勾选真实 Office、显示器、Electron 包或 Android APK 验证任务。
- 不创建旧业务数据迁移、回滚 SLA、生产切换或现场维护任务。

## Phase 10: Convergence

- [X] T120 CRITICAL 将显示、音频与 Office 相关写操作通过 `CommandCoordinator` 事务入队，并确保兼容 pending 投影仅由队列/执行结果推进 per FR-007–010
- [X] T121 CRITICAL 实现 Supervisor 可运行入口、持久子进程登记、四 PlayerWorker/AudioWorker/PowerPointHost/MediaMTX 启动及任一输出故障后的整组协作退出 per FR-018–020
- [X] T122 CRITICAL 在 ControlHost 托管并发 Named Pipe broker，接入受认证 Supervisor 子进程登记、OS PID/start-time/session/role 校验、命令 dispatch、wake 与停止闩锁 per FR-007, FR-019
- [ ] T123 CRITICAL 实现 PlayerWorker 启动参数、管道领取/续租/结果/状态循环，以及 WPF 中真实 LibVLCSharp、WebView2、Windows.Data.Pdf、图片表面和健康预热切换 per FR-015–017 (missing)
- [ ] T124 CRITICAL 为 AudioWorker 接入管道命令循环、LibVLC 执行、状态上报和带 event_id/source_generation 的自然结束通知 per FR-018 (missing)
- [ ] T125 CRITICAL 将 PowerPointHost 接入独立 STA/COM IPC 宿主，并把唯一槽位、HWND 附着、导航、媒体、导出与安全关闭接入 PlayerWorker/ControlHost 流程 per FR-011–014 (partial: 已完成参数解析、Named Pipe 握手、WorkerReady 和 STA 长连接；OfficeRequest/操作闭环仍缺)
- [ ] T126 将真实 Windows 显示拓扑和 Core Audio 接入非 simulation ControlHost，保留 simulation 的明确虚拟实现和 unavailable 诊断 per FR-004, FR-019–020 (partial)
- [X] T127 受认证本机 runtime start/stop/restart/status 控制通道已接入 bootstrap、`/api/system/restart/` 与 `/api/system/shutdown/`；Supervisor 回执驱动 Worker ready→armed，启动超时/早退/登记失败会清理自有进程并持久化 faulted per FR-018, FR-020
- [ ] T128 修复并回归验证 Web 初始导航挂载竞态，完成 Web/Electron/Android 对 HTTPS simulation ControlHost 的认证、SSE 重连、路由、文件与客户端关闭矩阵 per FR-028–030 (partial)
- [ ] T129 在可运行的真实 Worker 上执行普通命令 1000 样本、健康预热切换 100 样本及具备四屏/Office/VLC/MediaMTX/音频条件时的 60 分钟混合测试，并记录原始证据 per SC-006, SC-009 (partial)
