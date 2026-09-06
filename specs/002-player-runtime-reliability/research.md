# Research: 播放器 Runtime 可靠性与热切换

**Created**: 2026-08-30

本研究基于当前代码、现有测试和项目宪章完成。外部调研 agent 因服务限流不可用，未引入未经验证的第三方方案。

## 决策 1：命令采用“单消费者租约 + 主线程完成后确认”

- **Decision**: `PlaybackCommandRecord` 与背景音频命令记录均增加 `pending/processing` 状态、消费者标识、领取时间和尝试次数。领取使用数据库条件更新，只有最早记录且租约为空或过期时才可被一个消费者占用。Qt 信号携带记录 ID；同步 handler 返回后确认，异步 PPT 打开在完成回调中确认。控制器退出前释放本消费者仍持有的租约。
- **Rationale**: 保留现有 Django DB 跨进程边界，不新增 broker；避免 emit 后立即删除造成崩溃丢命令，同时限制同一窗口多条并发信号破坏顺序。
- **Alternatives considered**: 仅把 ack 移到槽函数后仍无法处理崩溃恢复和多进程竞争；内存队列无法跨进程恢复；Redis 会增加部署依赖。

## 决策 2：背景音频使用独立有序队列，保留兼容投影字段

- **Decision**: 新增 `BackgroundAudioCommandRecord`；服务层统一通过 enqueue 函数写记录并把最早记录投影到 `BackgroundAudioState.pending_command/command_args`。SET_VOLUME、SET_MUTE、SET_LOOP、SEEK 只合并尚未领取的同类记录；OPEN/STOP 清理尚未领取的旧记录但不删除 processing 记录。播放器按记录 ID ack。
- **Rationale**: 不破坏已有快照和管理界面读取，同时修复单槽覆盖与旧 clear 误删。
- **Alternatives considered**: CAS 单槽只能避免误删，不能保留 OPEN→PAUSE 等有序操作；删除兼容字段会扩大 REST/SSE 迁移范围。

## 决策 3：PowerPoint 采用“立即尝试唯一槽，失败直接 PDF”

- **Decision**: 主机级 `PowerPointSlot` 仍是 COM 唯一所有权；PPT 打开不等待其它持有者，槽位不可用时立即选择已生成且源摘要匹配的 PDF adapter。服务在源进入系统时为所有 PPT 建立 PDF 播放缓存；运行时不为回退临时拉起第二个 COM。当前已是 PDF 的窗口不会自动升级为 COM。
- **Rationale**: 跨 `run_player` 子进程的命名互斥体提供 OS 崩溃释放；不等待可避免第二窗口卡住并确保“其余作为 PDF”。现有 `slides_pdf` 已有摘要和缓存路径，可复用。
- **Alternatives considered**: 继续等待槽位会造成现场延迟和超时错误；用数据库锁无法覆盖非 Django PowerPoint 进程；自动升级会造成画面闪烁和页码状态变化。

## 决策 4：网页热切换保留 QWebEngineView 实例

- **Decision**: 预热池持有隐藏但可合成的宿主；切入时 reparent 到目标 web container、恢复几何和可见性，切离时 detach/reparent 回宿主，不调用 `setUrl`、`reload` 或 `about:blank`。按源 ID、规范化 URL 和源版本校验归属；同源替换先释放旧实例。预热池由 Qt 定时器周期检查并重建过期直播连接。
- **Rationale**: QWebEngineView 的 DOM、Cookie、登录、滚动和脚本状态存在于实例中；只迁移父组件才能实现类似桌面窗口切换。
- **Alternatives considered**: 每次打开 reload 会丢页面状态；直接 hide 宿主可能暂停 Chromium 合成；固定 TTL 后冷启动不能满足 keep_alive。

## 决策 5：退出与第三方清理采用分阶段、逐资源 best effort

- **Decision**: 父进程发送可捕获退出信号并等待子进程；仅超时后 terminate/kill。控制器停止使用可唤醒 Event、确认轮询线程结束后再拆资源；COM worker shutdown 返回 false 时保留失败状态并禁止继续假定已停止。VLC 的 stop、解绑、media release、instance release 分别执行并记录。临时文件删除失败记录窗口/源/阶段，并保留可重试标记。
- **Rationale**: 现场安全优先要求成功和失败路径都可清理、可诊断；单一 try 会让前置异常跳过后续 native release。
- **Alternatives considered**: 直接强杀最快但会留下 COM/VLC/临时资源；吞异常保持表面稳定但无法诊断和修复。

## 决策 6：P3 拆分与文档同步作为本次交付的一部分

- **Decision**: 将 `window.py` 的光标/overlay/几何辅助、`ppt_window.py` 的窗口枚举/嵌入/定位职责、`srt_stream.py` 的运行时配置/事件/生命周期按现有包结构拆成子模块，保留公共导入兼容层；更新 Runtime 设计文档中的真实路径，并删除左右拼接描述。
- **Rationale**: 满足项目 500 行拆分规则且降低第三方集成 review 的导航成本。
- **Alternatives considered**: 仅改文档会继续累积维护风险；一次性大规模重命名会破坏现有导入，因此使用小模块和兼容导出。

## 验证边界

- 自动化：pytest/pytest-django 覆盖队列竞争、崩溃租约恢复、PPT fallback、网页复用、逐资源清理和迁移。
- 工具检查：Ruff、后端完整测试、前端 typecheck/build、Redocly。
- 实机：Windows 10/11 登录桌面验证 4 窗口、一个 COM + 多 PDF、VLC/MediaMTX、网页登录状态热切换和协作退出；当前开发环境无法证明这些实机结果，必须在 quickstart 中标注执行人和日期。
