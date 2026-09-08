# 行为基线与漂移登记

**Baseline commit**: `029a28577fa3d4b9224d45f229726c7bd26c9964`
**Inspection**: 2026-09-08；只读源码/规范/测试，未读取真实凭据或处理业务数据库。

本文件冻结要迁移的行为依据，不宣称已完成全覆盖测试。代码、现行规范与文档冲突时建立差异样例并评审；不把历史缺陷强行转成必须保留的业务合同。

最新范围：快速迭代，无现场维护；Git保存代码历史。行为基线用于重构测试，不要求搬迁历史数据。控制端改为共享Vue/Tailwind4的Web、Windows Electron、Android Capacitor，旧“前端原封不动”和长期兼容要求不再适用。

## 真源与范围

| 面 | 当前真源 | 迁移必须保留 |
| --- | --- | --- |
| 外部路由 | `scp_cv/apps/dashboard/api_urls.py`、`scp_cv/urls.py`、`dashboard/urls.py` | 核心 `/api/`包括folders、资源/备注、物理smoke、重启、兼容场景入口；不附加完整旧admin/页面兼容工程，真实API调用不得悄删 |
| HTTP合同 | `docs/openapi.yaml` 及其 `paths/`/`components/` 引用 | 参数/响应/错误/状态码、认证、下载预览及内容类型 |
| 账户 | `api_auth_views.py`、`auth_middleware.py`、`frontend/src/services/api.ts` | id/username/staff/superuser，匿名status/logout行为，改密后当前会话保留，cookie请求 |
| 媒体/安全 | `services/media*.py`、`models/media.py`、`test_media_local_path_security.py` | 所有源类型，允许目录真实路径检查，下载/预览重新验证，临时源及文件夹 |
| 窗口/模式 | `playback.py`、`playback_sessions.py`、`playback_window_controls.py` | 1–4、single/double、3/4强制静音与single的2静音、单窗单显示器 |
| 实际放映 | `models/session.py`、`playback_powerpoint.py`、前端 `playbackCapabilities.ts` | PDF仍是ppt类型；playback_mode实际上报；reset只影响powerpoint而非PDF |
| 队列 | `playback_commands.py`、`background_audio_commands.py` | 显示pending合并/取代与音频仅合并不同；ACK由实际处理结果驱动 |
| 场景 | `services/scenario.py`、`models/scenario_models.py` | 源unset保持/empty关闭/set打开；模式/音量仅set生效；resume同源活跃时保持 |
| 音频 | `services/background_audio.py`、`player/background_audio_handlers.py` | 独立列表、自然结束、循环、删除当前项停止；与四输出无占用关系 |
| SSE/竞态 | `services/sse.py`、`api_views.py`、前端runtime/sessions/backgroundAudio store | playback_state快照、credentials、断线补拉；sessions按last_updated_at拒旧帧 |
| Office/PDF | `slides_pdf.py`、`ppt_resources.py`、`player/powerpoint_slot.py`、`controller_ppt_open.py` | 摘要匹配、唯一动态放映、静态回退、不自动升级、备注/页内媒体 |
| 流与设备 | `mediamtx.py`、`device.py`、`video_wall.py`、`volume.py` | 自动发现、原端口/单位、物理模式阶段、Windows音量与失败策略 |
| 启停 | `management/commands/runall.py`、`run_player.py` 及runall辅助模块 | headless/service/显示器/GPU参数，整组协作退出，项目自有资源清理 |

## 易错语义

- 显示队列仅对 pending 的 `seek/set_loop/set_volume/set_mute` 合并；`open/close/reset_ppt` 取代旧 pending，不删除 processing。背景音频没有 OPEN 取代整队规则。
- ACK 后旧命令记录删除；现有实现没有持久完成凭据或 fencing epoch。本设计新增它们是内部可靠性机制，不宣称旧版已有。
- 能力矩阵：图片无播放控制；web 支持 play/stop；直播不 seek/loop；视频支持时间线/循环/音量；音频只走背景通道。PPT/PDF窗口音量不开放。
- 场景的“源empty”表示关闭，但“模式empty/音量empty”不表示恢复默认或清零；只有其state=set时执行。模式→系统音量→各窗口依次执行，不承诺硬件原子场景。
- 大屏模式调用真实视频墙协议，阶段为清屏→映射→提交→刷新；成功才保存逻辑模式。失败可能已有部分硬件副作用，数据库事务不能保证硬件回滚。
- `playback_mode` 在新open/close/reset清空，由实际适配器上报；预览请求用源ID+单调序号防A→B→A旧响应覆盖。
- `system/shutdown`/`restart` 指本项目栈的退出/重启，不是OS电源操作。

## 已发现漂移与显式设计差异

| 编号 | 现象 | 本计划处理 |
| --- | --- | --- |
| B01 | 旧架构/数据文档仍称单槽命令、发信号立即ACK | 以队列表/租约源码与主线程ACK测试冻结，实施时修文档，现阶段不修改旧文档 |
| B02 | README部分写PPT COM预热，与002唯一COM/PDF规则及运行时文档不一致 | 采用当前单槽/PDF基线，不恢复额外COM预热 |
| B03 | 文档背景命令枚举含next/prev，源码枚举没有 | 上一首/下一首属于服务列表决策，生成对应open，不擅增wire命令 |
| B04 | 旧SSE最新事件非持久replay；入口只读last_id查询参数，轮询消息无id | 新实现可改推送机制但保持快照外观；重连全量状态，不承诺全事件回放 |
| B05 | 部分写端点csrf_exempt；前端发token不证明后端校验 | 负向安全样例先冻结；补齐防伪单列评审，正常Vue请求不改 |
| B06 | sessions store有时间戳拒旧帧，backgroundAudio直接覆盖 | 内部revision排序不能自动解决跨HTTP/SSE竞争；验收覆盖，必要最小音频store保护单列评审 |
| B07 | 原生Office导出改为统一Host串行，活动放映时延后 | 保持源注册和失败metadata合同，准备时机差异须评审；不宣称无代价 |
| B08 | 独立进程可做单窗恢复，但002要求任一子进程退出后其余先协作停止 | 默认保持整组停止；自动单窗重启不在本次实现目标 |
| B09 | Django admin与legacy页面不是共享控制台主要接口 | 不做完整admin复制或长期维护代理；保留有真实调用者的API，删除旧实现时在正常提交中说明 |
| B10 | 早期计划假设已有现场并要求复杂迁移/回滚 | 用户明确否定该前提，改为Git小步迭代/新测试目录，不搬旧数据 |
| B11 | 原前端无Electron/Capacitor/Tailwind4 | 本轮用户指定三端共享前端，允许样式/平台适配但不改核心规则；Android封装已确认 |

## 旧验收边界

`specs/002-player-runtime-reliability/tasks.md` 中T060仍为未完成。不能把过去软件测试当真实PowerPoint/VLC/MediaMTX/多屏证据；新实现按开发环境验证，没有要求先做现场维护/生产切换的门槛。本轮不修改旧任务状态。

已存在的 `.agents/skills/mcp-builder`、`.agents/skills/mimo-v2-5-tts` 修改与本规划无关，不覆盖、不提交。
