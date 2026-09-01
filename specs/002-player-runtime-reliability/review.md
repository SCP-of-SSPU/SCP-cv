# 播放适配器与第三方集成复审

**日期**：2026-08-30  
**范围**：PowerPoint/PDF/视频/网页/libVLC 适配器、MediaMTX、背景音频、预热、命令队列与退出清理。

## Standards 轴

- 已按 AGENTS.md 与项目宪章检查 UTF-8/LF、文件头、结构化日志、500 行阈值、失败可诊断与资源逐步清理。
- `ppt_window.py`、`window.py`、`srt_stream.py` 已拆分；新增 `controller_display.py` 后 `scp_cv/player/` 无超过 500 行文件。
- Ruff、Django system check、迁移一致性和 `git diff --check` 均通过。

## Spec 轴

复审中发现并已处置：

| 严重度 | 发现 | 处置 |
| --- | --- | --- |
| P1 | PowerPoint 导航经 COM worker 异步投递后，控制器会提前确认命令 | 导航/暂停/媒体控制改为等待真实 COM 结果，错误传播到会话状态 |
| P1 | Windows `SIGTERM` 不能保证 Python/Qt 清理路径执行 | 多窗口子进程增加 shutdown-file IPC；runall/父播放器先协作退出，超时后 terminate/kill |
| P1 | 长时间 PPT 打开可能超过命令租约并被重复领取 | 活跃消费者轮询时续租；进程退出后租约仍可被其它消费者恢复 |
| P1 | COM worker 初始化失败与任务入队存在竞态，任务可能永远不回调 | 入队后再次检查初始化/关闭状态并即时失败所有任务 |
| P1 | COM 槽位冲突后的 PDF fallback 未释放切换前旧适配器；PDF 打开失败路径不完整 | fallback 成功后关闭旧适配器；失败时恢复旧画面或黑屏并写错误 |
| P2 | `runall` 的进程树清理仍可能绕过 run_player 的协作退出 | 可识别 run_player shutdown-file 时先请求清理；其他进程保持原终止策略 |
| P2 | PowerPoint/临时源/VLC 预热清理存在静默异常 | 改为逐资源释放和包含 window/source/stage 的诊断日志 |
| P3 | Runtime 文档仍有旧 PowerPoint-only/拼接/拆分路径描述 | 同步单 COM/PDF fallback、单屏与新模块路径 |

## 第三方边界结论

- **PowerPoint**：系统级命名互斥体是唯一 COM 槽位事实来源；其它窗口使用源摘要匹配 PDF，不抢占持有者、不自动升级、不终止外部 PowerPoint。
- **VLC/MediaMTX**：libVLC stop、解绑、player/media/instance release 相互独立；MediaMTX 由 runall 进程树管理，直播 URL 与低延迟参数保持既有合同。
- **WebEngine**：预热 `QWebEngineView` 在前后台容器间迁移；切换路径不调用 reload/setUrl/about:blank，只有显式刷新或最终销毁允许导航。
- **剩余验证边界**：自动化和静态检查已通过；PowerPoint/VLC/多屏/WebEngine 的真实 Windows 现场步骤仍需按 quickstart 执行并记录。

当前自动化范围内没有未处置的 P1/P2/P3 finding。
