---
description: "播放器 Runtime 可靠性、单 COM/PDF 放映与媒体热切换实现任务"
---

# Tasks: 播放器 Runtime 可靠性与热切换

**Input**: Design documents from `specs/002-player-runtime-reliability/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: 规范要求所有行为修复先增加自动化回归测试；Windows PowerPoint、VLC、MediaMTX、多屏和 QWebEngine 仍需按 `quickstart.md` 实机验证。

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 固定实现边界和验证入口。

- [X] T001 [P] 将 `specs/002-player-runtime-reliability/quickstart.md` 中的自动化与 Windows 实机命令校对到当前项目入口
- [X] T002 [P] 在 `tests/` 中建立 Runtime 可靠性测试模块分组并补齐文件头注释约定
- [X] T003 [P] 核对 `docs/openapi.yaml`、`docs/paths/` 和 `docs/components/schemas/` 的显示与播放合同变更清单

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立跨进程队列、租约和迁移基础；完成前不得开始播放器故事实现。

**⚠️ CRITICAL**: 所有用户故事依赖本阶段的数据库与命令消费语义。

- [X] T004 [P] 为窗口播放命令租约、背景音频命令租约和崩溃恢复编写失败优先测试，覆盖 `tests/test_playback_command_queue.py` 和 `tests/test_background_audio_command_queue.py`
- [X] T005 [P] 为播放队列与背景音频队列新增迁移回滚/旧字段投影测试，写入 `tests/test_migrations.py`
- [X] T006 在 `scp_cv/apps/playback/models/session.py` 增加播放命令状态、消费者、领取时间、尝试次数和最后错误字段，并在 `scp_cv/apps/playback/models/background_audio.py` 增加 `BackgroundAudioCommandRecord`
- [X] T007 在 `scp_cv/apps/playback/migrations/` 新增迁移，建立背景音频命令表、租约索引，并将旧记录初始化为 `pending`
- [X] T008 [P] 在 `scp_cv/services/playback_commands.py` 实现条件领取、租约过期恢复、按消费者确认和释放租约，保持 `pending_command` 兼容投影
- [X] T009 [P] 新建 `scp_cv/services/background_audio_commands.py`，实现背景音频有序入队、同类 pending 合并、条件领取、按记录确认和消费者租约释放
- [X] T010 在 `scp_cv/services/background_audio.py` 将所有直接写入 `pending_command` 的操作改为背景音频队列服务，并保留快照兼容字段
- [X] T011 [P] 为租约超时、重复消费者和确认身份不匹配补充单元测试，覆盖 `tests/test_playback_command_queue.py` 与 `tests/test_background_audio_command_queue.py`

**Checkpoint**: 队列记录可安全领取、确认、超时恢复；旧 REST/SSE 快照仍可读取。

---

## Phase 3: User Story 1 - 指令可靠执行与安全退出 (Priority: P1) 🎯 MVP

**Goal**: 指令只在真实执行完成后确认，背景音频不覆盖命令，多窗口和第三方资源采用协作式退出与可诊断清理。

**Independent Test**: 运行队列崩溃/竞态测试、控制器退出测试和清理异常注入测试；确认 processing 记录可恢复、子进程先协作退出。

### Tests for User Story 1

- [X] T012 [P] [US1] 编写 Qt 信号投递后主线程执行前退出的回归测试，覆盖 `tests/test_player_controller_command_ack.py`
- [X] T013 [P] [US1] 编写背景音频 OPEN→PAUSE 并发写入和旧确认误删回归测试，覆盖 `tests/test_background_audio_handlers.py`
- [X] T014 [P] [US1] 编写轮询线程停止超时、消费者租约释放和 COM worker 关闭超时测试，覆盖 `tests/test_player_controller_open_recovery.py` 与 `tests/test_ppt_com_worker.py`
- [X] T015 [P] [US1] 编写父进程协作终止、超时后 terminate/kill 和重复退出幂等测试，覆盖 `tests/test_run_player_command.py`
- [X] T016 [P] [US1] 编写 VLC stop/set-media/release 任一步骤异常仍继续后续释放的测试，覆盖 `tests/test_srt_stream_adapter.py`
- [X] T017 [P] [US1] 编写临时源删除失败必须记录窗口/源/阶段的测试，覆盖 `tests/test_player_controller_open_recovery.py`

### Implementation for User Story 1

- [X] T018 [US1] 在 `scp_cv/player/controller_polling.py` 让信号携带命令记录 ID 与消费者身份，并移除 emit 后立即 ack；同窗口存在未过期 processing 时不得领取下一条
- [X] T019 [US1] 在 `scp_cv/player/controller.py` 与 `scp_cv/player/controller_ppt_open.py` 实现同步 handler 完成后确认、异步 PPT 完成回调确认、退出前释放消费者租约
- [X] T020 [US1] 在 `scp_cv/player/background_audio_handlers.py` 让背景音频信号携带记录 ID，并在主线程 handler 完成后按 ID 确认，删除无条件 clear
- [X] T021 [US1] 在 `scp_cv/player/controller.py` 使用可唤醒停止事件，等待轮询线程确认退出后再关闭 adapter、预热池和 COM worker；超时写入明确失败日志
- [X] T022 [US1] 在 `scp_cv/apps/dashboard/management/commands/run_player.py` 实现父子播放器协作式退出、等待清理和超时强制终止，并记录每个 PID 与退出阶段
- [X] T023 [US1] 在 `scp_cv/player/adapters/ppt_com_worker.py` 处理 COM 初始化失败：拒绝/失败所有任务并停止 worker；处理 shutdown 返回值而不宣称已安全停止
- [X] T024 [US1] 在 `scp_cv/player/adapters/srt_stream.py` 将 stop、解绑媒体、释放 player/media/instance 拆为独立清理步骤，逐项记录异常
- [X] T025 [US1] 在 `scp_cv/player/controller_adapter_lifecycle.py` 将临时源删除失败改为结构化 warning 并保留可重试状态，不使用裸 `except: pass`

**Checkpoint**: `tests/test_playback_command_queue.py`、背景音频队列、控制器和退出清理测试全部通过。

---

## Phase 4: User Story 2 - 只暴露真实可用的播放能力与单屏显示 (Priority: P1)

**Goal**: 删除左右拼接全部新合同和界面残留，只保留单窗口→单显示器；不支持的媒体操作明确失败且不伪造状态。

**Independent Test**: 各媒体能力拒绝测试、REST/OpenAPI 合同测试、迁移后会话归一测试和前端构建通过；全仓搜索不再出现运行时拼接入口。

### Tests for User Story 2

- [X] T026 [P] [US2] 编写各 SourceAdapter 能力集合和不支持操作错误测试，覆盖 `tests/test_player_adapter_capabilities.py`
- [X] T027 [P] [US2] 更新显示服务/API 测试，验证只接受单屏目标且不再接受左右拼接，覆盖 `tests/test_playback_display_service.py` 与 `tests/test_rest_api.py`
- [X] T028 [P] [US2] 编写旧 `display_mode/is_spliced/spliced_display_label` 数据迁移为单屏的测试，覆盖 `tests/test_migrations.py`

### Implementation for User Story 2

- [X] T029 [US2] 在 `scp_cv/player/adapters/base.py` 定义能力集合与明确的不支持异常，并在所有具体适配器声明真实 capabilities
- [X] T030 [US2] 在 `scp_cv/services/playback.py`、`scp_cv/apps/dashboard/api_playback_views.py` 和相关服务中按能力拒绝 seek/翻页/暂停/循环/音量/静音等不支持操作，不更新乐观状态
- [X] T031 [US2] 在 `scp_cv/player/controller_handlers.py` 仅在适配器确认操作成功后写入状态，处理不支持异常并保留真实 adapter 状态
- [X] T032 [US2] 删除 `PlaybackMode.LEFT_RIGHT_SPLICE`、`is_spliced`、`spliced_display_label` 及相关模型字段/新迁移引用，新增 `scp_cv/apps/playback/migrations/` 数据迁移将历史活动会话归一为单屏
- [X] T033 [P] [US2] 删除 `scp_cv/services/display.py` 的拼接目标构造、`scp_cv/services/__init__.py` 导出、显示选择 API 及 `docs/paths/displays_select_.yaml` 中的拼接合同
- [X] T034 [P] [US2] 删除 `frontend/src/features/settings/tabs/DisplaySettingsTab.vue`、`frontend/src/stores/displays.ts`、`frontend/src/services/api.ts` 和播放组件中的拼接入口/字段，并同步中文文案
- [X] T035 [P] [US2] 更新 `docs/openapi.yaml`、`docs/_bundled.yaml`、`docs/components/schemas/DisplayMode.yaml`、`SessionSnapshot.yaml`、`docs/design/02-data-model.md` 中的单屏合同

**Checkpoint**: REST、SSE、前端和数据库只剩单屏显示语义，任何不支持操作均返回明确错误。

---

## Phase 5: User Story 3 - 单 PowerPoint COM 与 PDF 并发放映 (Priority: P1)

**Goal**: 主机范围同时最多一个 PowerPoint COM 放映；其它 PPT 自动使用匹配 PDF，PDF 窗口不因槽位释放自动升级。

**Independent Test**: 槽位竞争测试、PPT controller fallback 测试、PDF 缓存摘要校验测试，以及 Windows 四窗口实机验证。

### Tests for User Story 3

- [X] T036 [P] [US3] 编写 PowerPoint 槽位不可用时立即选择 PDF、槽位释放后不自动升级的测试，覆盖 `tests/test_powerpoint_slot.py` 与 `tests/test_player_controller_ppt_async_open.py`
- [X] T037 [P] [US3] 编写四窗口仅一 COM、其余 PDF、PDF 缺失安全失败的集成测试，覆盖 `tests/test_ppt_adapter.py` 与 `tests/test_player_controller_open_recovery.py`
- [X] T038 [P] [US3] 编写 PPT 源摘要与 PDF 缓存不匹配时拒绝回退的测试，覆盖 `tests/test_ppt_playback_cache.py` 与 `tests/test_ppt_file_preheat.py`

### Implementation for User Story 3

- [X] T039 [US3] 在 `scp_cv/services/slides_pdf.py` 和 `scp_cv/services/media.py` 使可回退的 PPT 源在进入系统时建立带源摘要的 PDF 缓存，并记录失败原因；保持历史缓存兼容
- [X] T040 [US3] 在 `scp_cv/player/adapters/ppt_opening.py` 与 `scp_cv/player/adapters/ppt.py` 对 PowerPoint 槽位采用不等待即时失败语义，区分槽位超时、COM 初始化失败和文件错误
- [X] T041 [US3] 在 `scp_cv/player/controller_handlers.py`、`scp_cv/player/controller_ppt_open.py` 增加槽位失败到 PDF adapter 的安全回退，校验 PDF 路径/摘要并保持 `adapter_kind=pdf`
- [X] T042 [US3] 在 `scp_cv/services/playback.py`、`scp_cv/services/playback_powerpoint.py` 停止打开新 PPT 前关闭其它 PPT 的旧协调逻辑，避免为第二个请求抢占/切换现有 COM；保留单槽事实来源
- [X] T043 [US3] 在 `scp_cv/player/powerpoint_slot.py` 增加持有者/崩溃恢复日志和仅清理本系统启动进程的边界，禁止误杀外部 PowerPoint

**Checkpoint**: 逻辑测试证明单槽和 PDF fallback；Windows 实机证明任务管理器中的本系统 PowerPoint 实例不超过一个。

---

## Phase 6: User Story 4 - 媒体资源热切换与持续预热 (Priority: P1)

**Goal**: 已预热网页切换只迁移实例和可见性，保留 DOM/登录/滚动状态；持续预热直播在 TTL 前续热或重建。

**Independent Test**: 网页实例身份/导航计数测试、同源替换清理测试、直播续热测试和 10 分钟 Windows 实机验证。

### Tests for User Story 4

- [X] T044 [P] [US4] 编写 QWebEngineView 预热认领、切离、再认领不 reload 且实例身份不变的测试，覆盖 `tests/test_web_adapter.py` 与 `tests/test_preheat_pool.py`
- [X] T045 [P] [US4] 编写同源预热替换先释放旧 WebView、重复归还不泄漏的测试，覆盖 `tests/test_preheat_pool.py`
- [X] T046 [P] [US4] 编写直播句柄过期前续热、过期后后台重建和前台认领测试，覆盖 `tests/test_preheat_stream.py` 与 `tests/test_srt_stream_adapter.py`

### Implementation for User Story 4

- [X] T047 [US4] 在 `scp_cv/player/adapters/web.py` 和 `scp_cv/player/web_preheat.py` 实现前后台容器迁移、可见性切换和实例状态保留，切换路径禁止 `setUrl/reload/about:blank`
- [X] T048 [US4] 在 `scp_cv/player/preheat_pool.py` 强化按源 ID/规范化 URI/源版本校验、同源替换清理和退出清理，避免不可达后台页面
- [X] T049 [US4] 在 `scp_cv/player/preheat_stream.py` 增加有效连接续热/后台重建接口，并在 `scp_cv/player/preheat_pool.py` 保持 `keep_alive` 资源长期可认领
- [X] T050 [US4] 在 `scp_cv/player/controller.py` 建立 Qt 定时预热维护 tick，在不阻塞前台 adapter 的前提下刷新过期直播资源
- [X] T051 [US4] 在 `scp_cv/player/controller_adapter_lifecycle.py` 调整切源流程，使网页等预热资源回收到后台而非立即导航到空白页，并记录归还/认领结果

**Checkpoint**: 页面状态切换测试通过；实机连续切换 50 次没有重复导航，直播运行 10 分钟仍可认领。

---

## Phase 7: User Story 5 - P3 拆分、文档同步与第三方集成可诊断性 (Priority: P2)

**Goal**: 修复全部 P3，拆分超大文件，文档引用与实现一致，并完成重点适配器/第三方集成 review。

**Independent Test**: 所有拆分后文件不超过项目阈值，导入兼容测试通过，Runtime 文档路径准确；输出适配器与第三方集成 review 结果。

- [X] T052 [P] [US5] 为 `scp_cv/player/adapters/ppt_window.py` 拆分窗口枚举、嵌入、定位和 Win32 清理模块，保留兼容导出并新增 `tests/test_ppt_window.py` 导入回归测试
- [X] T053 [P] [US5] 为 `scp_cv/player/window.py` 拆分光标跟踪、overlay、几何定位和窗口事件模块，保留 `PlayerWindow` 公共行为并更新 `tests/test_player_window.py`
- [X] T054 [P] [US5] 为 `scp_cv/player/adapters/srt_stream.py` 拆分 VLC runtime 配置、事件状态和生命周期模块，保留 `SrtStreamAdapter` 导出并更新 `tests/test_srt_stream_adapter.py`
- [X] T055 [US5] 更新 `docs/design/06-player-media-runtime.md`、`docs/design/02-data-model.md`、`docs/design/03-backend-services.md` 与 `docs/design/08-migration-guide.md`，删除左右拼接并改正 GPU/拆分后路径
- [X] T056 [US5] 对 `scp_cv/player/adapters/ppt.py`、`pdf.py`、`video.py`、`web.py`、`srt_stream.py`、`background_audio.py`、`ppt_com_worker.py` 及 MediaMTX/PowerPoint/VLC 集成执行只读 review，记录所有 P1/P2/P3 并将可执行修复补入本任务阶段

---

## Phase 8: Polish & Cross-Cutting Validation

**Purpose**: 完成全量验证、合同同步和实机交付记录。

- [X] T057 [P] 运行播放器专项测试并修复回归：`uv run pytest tests/test_playback_command_queue.py tests/test_background_audio_command_queue.py tests/test_player_controller*.py tests/test_ppt*.py tests/test_powerpoint_slot.py tests/test_preheat*.py tests/test_web_adapter.py tests/test_srt_stream_adapter.py tests/test_run_player_command.py tests/test_headless_launcher.py -q`
- [X] T058 [P] 运行后端完整测试与静态检查：`uv run pytest -q`、`uv run ruff check scp_cv tests`
- [X] T059 [P] 运行前端 `npm run typecheck`、`npm run build`，并执行 `redocly lint docs/openapi.yaml`
- [ ] T060 按 `specs/002-player-runtime-reliability/quickstart.md` 执行 Windows 实机验证，记录 PowerPoint 单槽/PDF、VLC/MediaMTX、网页热切换、直播续热、协作退出结果
- [X] T061 [P] 检查所有 `scp_cv/player/` Python 文件头、reST 函数注释、UTF-8/LF 和 500 行阈值，补齐遗漏
- [X] T062 运行 `$speckit-analyze` 对 `spec.md`、`plan.md`、`tasks.md` 做一致性分析，并在进入最终 review 前处理 CRITICAL/HIGH 结果

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 无依赖；先固定验证与合同清单。
- **Phase 2 (Foundational)**: 依赖 Phase 1；建立队列模型/迁移后才可执行用户故事。
- **Phase 3 (US1)**: 依赖 Phase 2；是 MVP，优先修复命令可靠性和安全退出。
- **Phase 4 (US2)**: 依赖 Phase 2，可与 US1 的播放器代码分文件并行；合同删除需在相关实现合并前完成。
- **Phase 5 (US3)**: 依赖 US1 的 ack/退出边界和 US2 的单屏合同。
- **Phase 6 (US4)**: 依赖 US1 的退出清理；与 US3 可并行开发但共享 `preheat_pool.py` 时需串行合并。
- **Phase 7 (US5)**: 依赖 US1-US4 行为稳定后进行，避免拆分掩盖功能回归。
- **Phase 8 (Polish)**: 依赖所有前置阶段；T060 实机结果是最终完成门槛。

### Parallel Opportunities

- Phase 2 的测试任务 T004/T005/T011 可并行；模型/服务实现仅在迁移接口确定后并行。
- US1 的测试 T012-T017 可并行；控制器、父进程、VLC 和临时清理实现可按文件并行。
- US2 的能力、合同、迁移测试和前端/文档删除可并行；共享模型/服务文件需串行。
- US3 的槽位、fallback、摘要测试可并行；PPT adapter 与服务策略变更需按依赖合并。
- US4 的 Web 与 stream 测试可并行；`preheat_pool.py` 只能由一个实现序列修改。
- US5 三个拆分任务分别触及不同文件，可并行；文档同步在拆分完成后执行。

### Implementation Strategy

1. 先完成 Phase 1-2，确保数据库命令队列具备可恢复语义。
2. 完成 US1 后独立验证“执行后确认、协作退出、资源清理”，形成可用 MVP。
3. 完成 US2 删除废弃拼接合同并阻止虚假成功。
4. 完成 US3/US4 后进行 PowerPoint、PDF、网页和直播实机验证。
5. 最后完成 P3 拆分、文档同步、全量检查和适配器/第三方集成 review。
