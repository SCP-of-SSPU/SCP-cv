# Internal Contract: Named Pipe 与执行恢复 v1

这是新增的内部协议设计，不是对外HTTP合同。用于同一Windows交互用户、同一受控安装和活动桌面；不支持远程客户端或任意进程执行。

网页、Electron与Capacitor控制客户端只访问REST/SSE，不连此Named Pipe，也不因与主机同为Windows就默认获得Supervisor权限。正常运行时的命令恢复仍保留，与已取消的生产版本回退工程无关。

## 拓扑与安全

- ControlHost为双工server，Supervisor/PlayerWorker/AudioWorker/PowerPointHost为持有长连接的client；控制面路由Office子操作，媒体字节不经管道。
- 名称形如 `scp-cv.<installation_id>.<logon_session>.runtime.v1`，不含secret；使用本地server `.`，服务端明确拒绝remote pipe clients。
- 限制DACL至配置用户/需要的SYSTEM管理访问；使用CurrentUserOnly并核验elevation、logon session、实际客户端PID/start time及Supervisor持有的子进程登记。相同用户的任意程序不因知道pipe名就自动获得role。
- 首个server实例使用FirstPipeInstance防占名；客户端也验证server PID/身份。启动登记用受ACL/继承句柄保护的启动上下文，不在命令行、日志或URI放令牌。
- 每角色有目标白名单：player只操作自身display；audio只操作audio:1；PowerPoint只处理关联Office请求；Supervisor可注册/停止自有进程，不能任意shell/路径启动。
- 管道连接不扩大HTTP授权：所有用户动作仍在ControlHost通过原权限与能力校验；Worker不能构造绕过API的用户命令。
- 不支持版本、身份或角色不匹配时fail closed，不自动降级为匿名/旧协议。

## 帧格式

4字节little-endian无符号长度 + UTF-8 JSON，长度1..1,048,576字节；读取需精确处理分段/半包/EOF。握手5秒截止，帧读取10秒截止；对长操作返回accepted后异步结果，不让一帧长期挂起。

```json
{
  "protocol_version": 1,
  "message_type": "ClaimRequest",
  "message_id": "e4f7b101-01cd-4b81-a818-b568b03555c1",
  "correlation_id": null,
  "instance_id": "9e1d0be3-017a-422d-953a-e97f4eb5b1fe",
  "owner_epoch": 12,
  "target": {"kind": "display", "id": 1},
  "payload": {}
}
```

UUID仅为示例，不是密钥。内部JSON字段固定snake_case；忽略已协商的可选新字段，未知message_type返回UnsupportedMessage，不能默默执行。major版本不匹配拒绝；不得将外部JSON原样映射为反射/COM方法调用。

## 消息目录

| 请求/消息 | 方向 | 语义/响应 |
| --- | --- | --- |
| Hello / Welcome | client↔ControlHost | 版本、真实实例/角色登记、capabilities、服务epoch；握手不代表player_ready |
| WorkerReady / HealthReport | Worker→ControlHost | 依赖、显示器、UI进展、实际资源；server持久投影并响应 |
| Wake | ControlHost→Worker | 某目标可能有命令；只含提示和最高sequence，丢失可补偿 |
| ClaimRequest / CommandLease | Worker↔ControlHost | 最早有效命令或NoWork；包含token/epoch/generation/deadline |
| LeaseRenew / RenewResult | Worker↔ControlHost | 指定执行token、当前阶段及UI健康证据；旧token/epoch拒绝 |
| CommandResult / ResultAccepted | Worker↔ControlHost | completed/failed/uncertain、真实证据、实际state；事务提交后才响应 |
| StateReport / StateAccepted | Worker↔ControlHost | source generation与report sequence；拒绝旧代次，不产生假playing |
| AudioFinished / EventAccepted | Audio↔ControlHost | generation+event_id幂等推进，由ControlHost确定下一首并入队 |
| OfficeRequest / OfficeResult | ControlHost↔PowerPointHost | 稳定office_operation_id、parent command/job/claim、group/host/slot epoch、deadline；Host真正出队前再验权并独立去重 |
| AttachSurface / SurfaceResult | ControlHost↔Player/PowerPointHost | 父/子HWND、PID/start time、dpi、几何；跨进程窗口验证，不直接递送COM对象 |
| PrepareSource / PreparationResult | ControlHost↔Worker/Office | 源版本、只读制品manifest、资源准备结果；不改当前可见源 |
| ShutdownRequest / ShutdownComplete | ControlHost或Supervisor协调→各宿主 | 幂等停止、清理阶段/结果；离线时Supervisor用独立受控退出信号/进程句柄兜底 |
| Error | 双向 | correlation、稳定错误code、阶段、可重试性、脱敏detail |

Office Host重启后必须重新握手、获得新epoch，旧HWND/slot失效；Player未收到有效SurfaceResult前不得报告原生PPT已显示。

## 整组停止闩锁

ControlHost是直接派发者，必须持久保存RuntimeGroupControl及group_epoch；不是只有Supervisor“不再启动进程”。只有armed状态可发CommandLease/执行类OfficeRequest；starting/draining/stopped/faulted拒绝新领取，已入队用户命令保留并给出非就绪诊断，不伪报已播放。

| 触发 | 默认处理 |
| --- | --- |
| 任一PlayerWorker退出，或用户请求系统shutdown/restart | ControlHost先draining/撤销派发授权，Supervisor整组协作停止 |
| ControlHost/Supervisor进程退出 | 剩余自有进程的监护路径进入组级安全停止；新ControlHost初始stopped，不因Worker重连armed |
| 本系统托管MediaMTX进程退出 | 沿用整体启动编排故障退出的组级停止；外部MediaMTX网络断开仅按流故障处理 |
| AudioWorker退出 | 音频目标faulted、无自动重播；默认整组协作停止以保持原音频随输出宿主退出的安全策略 |
| PowerPointHost退出/COM调用失控 | 对应Office目标/文稿faulted且冻结槽位；其他健康视频/PDF不自动换源。禁止自动再起Host，按明确reset/reopen或整组restart并确认旧Office释放后恢复 |
| 单资源加载失败、管道瞬时断线但宿主未退出 | 保留可安全维持的实际画面/音频，冻结无授权新操作；对账后仅在group仍armed时恢复，不把短断连等同误杀进程 |

显式启动Supervisor或已有system/restart是重新授权入口：先处置旧命令/副作用、完成清理和预检、提高group_epoch，再armed。故障后的重新连接仅恢复通信/诊断，不自动重放历史内容。成员故障分类作为G02运行可靠性评审项；如现场要求不同策略，先改规范再实现。

## 投递与背压

- 命令先durable commit再Wake。断线指数退避0.25→0.5→1→2→5秒并加抖动；连接成功先取组状态/实际状态，仅group仍armed且授权有效时请求命令。每1秒的补偿Claim同样受闩锁限制，Wake不改变顺序或解除停止。
- 每目标一条processing，每目标请求串行化；不同目标可并发，数据库写入仍有界串行。默认每连接最多64个在途控制消息。
- 状态report按目标只保留最新待发送值，不能合并丢掉CommandResult/AudioFinished；临界完成结果必须等ResultAccepted再清本地缓存。
- 队列拥塞必须返回明确可重试错误，不能已向HTTP宣称accepted后丢弃。保留旧HTTP响应格式，容量错误经现有code/detail表现并做合同测试。
- 运输心跳默认2秒，显示player_online兼容5秒TTL；UI卡死即便运输线程有心跳也不能报告ready。

## 租约、确认和fencing

- 默认租约30秒，processing每5秒带进展续期；每类操作阶段有独立截止时间，卡死不得无限续租。
- CommandLease精确绑定command_id、target、instance_id、owner_epoch、claim_token、source_generation、source_revision；ACK/renew/report都验证。
- 领取和状态变更在单次短事务CAS完成；凭据写入、会话实际状态和pending投影同事务提交，事务失败不发ResultAccepted。
- 同一token的重复CommandResult返回原结果，不二次推进列表或重复副作用。相同command_id不同结果hash拒绝并报警。
- 旧processing可在最新desired_generation变化后结束并保存历史结果，但不能覆盖新意图/状态。pending淘汰不删除processing或把它伪装成未执行。
- 租约过期只证明失联，不证明旧进程停止；转移执行权先冻结目标、由Supervisor证明旧进程已退出或完成显式停机握手，再增加epoch。若无法证明则uncertain/离线，禁止同时派发给两个物理执行端。
- ControlHost重启读取持久代次并提高服务epoch；重新认证活Worker，优先对账结果。不得直接将所有processing重置pending。

## Office子操作的独立去重

每个实际COM动作使用稳定office_operation_id，与父command/job、claim_token、source_generation、group/host/slot epoch及deadline绑定；传输重试不生成新operation_id。Host在入队时校验，并在STA实际取出准备调用COM前再次检查授权/闩锁/版本/deadline。

同一operation_id的queued/executing副本不再次入队，completed/failed副本只重传缓存结果；不同参数指纹的同ID拒绝。ControlHost持久登记子操作状态/结果，Host存本实例执行事实。若Host消失且COM动作是否完成未知，父动作继承uncertain；不能因父CommandResult尚未收到就重新NEXT/导出。

STA已进入的同步COM调用无法靠消息撤销；过期只撤销后续发布/派发资格，不能假称物理动作被回滚。调用未返回或未证明其自有Office已结束前保持inflight/Busy或Faulted，不释放槽、不安排重试。迟到导出结果进入隔离清理，未重新验证有效job/generation不得发布成功。

## 恢复判定

| 边界 | 行为 |
| --- | --- |
| 已入库、尚未Wake | 重连/补偿领取，保持顺序 |
| 已领取、已证明未执行且旧端停止 | 新token重新领取，保留attempt |
| 已执行、同一实例还持有完成结果 | 重传原结果，不执行第二遍 |
| 已执行、ACK已落库但响应丢失 | 依据完成凭据返回ResultAccepted |
| 旧实例消失，OPEN/SEEK等目标状态可安全恢复 | 仅在组授权已明确恢复后，检查资源版本/旧端退出并对账，再按确定目标重建；重连自身不触发恢复 |
| NEXT/PREV动画步、PPT媒体、设备toggle不可确认 | uncertain，冻结相关相对操作；经现有error/detail与诊断要求明确重置/处置 |
| 硬件模式中途失败 | 保留逻辑旧模式及分阶段失败证据，不能声称物理事务回滚 |
| 无交互桌面/旧Office仍存活 | 不换owner、不建第二COM，报告不可执行 |

设备TCP同步服务不必强行改成媒体Worker命令；它也必须有调用关联和不确定结果规则。epoch只阻止旧写入，不能撤销已发出的TCP/COM动作。

## 停止与清理

默认保留002的组级协作停止。ControlHost先将组置draining并撤销新派发→Supervisor通知各宿主停止领取→等待在途结果或明确uncertain→隐藏/解绑窗口→释放页面/VLC/Office/音频→上报清理结果→退出。默认协作等待5秒、terminate后再等3秒沿用旧行为，Office长任务如需更长超时须由专项验证后通过显式配置确定，不伪报已取消。

每步独立try/finally，失败不跳过后续清理。普通自有Worker用已登记process handle/PID+start time识别。Office还须在Quit/强退前重新核对Presentation清单及对象所有权：进程由本系统创建不保证后来没有用户文稿加入。无法证明持续独占时只关闭明确自有文稿，不Application.Quit、不强杀，保留Faulted/inflight并请求人工处置；COM卡死无法核验亦按此规则。旧Office未退出/未证明安全归还时不启动替代Host。

## 合同验收

半包/超大包/重复message_id、未知版本/角色、同用户未注册进程、不同桌面/权限级别、丢Wake、ACK丢失、旧epoch、数据库busy、UI挂死、ControlHost重启、长PPT打开、重复AudioFinished、队列合并和旧processing完成均需自动化测试。物理副作用不确定性必须在测试结论中显式保留。
