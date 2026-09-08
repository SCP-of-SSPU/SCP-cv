# Data Model: 兼容领域数据与可靠执行

**Status**: Phase 1 设计；新实体尚未实现。以 [baseline.md](./baseline.md) 为当前字段真源，禁止从过时设计文档推断 EF 字段。

## 持久化约定

- 新库由ControlHost独占业务写入，开发初始化/schema升级在尚未启动Worker时执行；所有Worker和控制客户端不访问业务库。不建设跨栈数据搬迁工具。
- 保留整数标识（C# long）、snake_case外部字段、空串/NULL、布尔与JSON语义；EF内部命名可变化，DTO不受影响。新库独立分配ID，不要求历史记录ID迁移不变。
- 时刻统一 UTC，数据库使用 UTC ticks 或明确 UTC DateTime 映射，不依赖SQLite对DateTimeOffset排序；HTTP仍输出旧客户端可比较的ISO时间格式。
- 应用维护 `revision`/CAS；SQLite不提供SQL Server rowversion。单写入调度仍需短事务、busy timeout、重试上限，DbContext不得跨线程共享。
- 对外更新时间在相同实体上须经Vue的Date.parse解析后仍以毫秒严格递增，使用持久化的max(now_ms,last_ms+1)投影，不能仅增加一个.NET tick；重启/墙钟回拨也不倒退。真实观测时刻另记observed_at，不把逻辑时间用于租约测时。JSON未知键原样保留，不透传为不受约束的执行命令。
- 临时源清理遵循业务可见删除与物理引用释放分离；只处理已授权应用资源，不为代码版本回退建设额外文件隔离区。

## 兼容实体映射

| 领域参考 | 新实体/关键字段 | 关系、约束及初始化规则 |
| --- | --- | --- |
| 账户/组/权限 | UserAccount：id、username、password_hash、is_active/is_staff/is_superuser、组/权限 | 新库初始化测试账号，使用ASP.NET标准密码验证/存储；保留权限和外部字段，不迁移旧hash/session；不推定staff等于superuser |
| MediaFolder | MediaFolder：id/name/parent_id/created_at/updated_at | parent自引用、删除规则保持，创建/调整时校验无环 |
| MediaSource | MediaSource：旧字段全映射，附内部source_revision/content_digest | 类型仍8种，PDF仍属ppt；folder删除SET NULL；uri、uploaded_file、未知metadata保留；下载时重新验证路径 |
| PptResource | PptResource：source_id/page_index/slide_image/speaker_notes/media_items | 唯一(source_id,page_index)，页码>=1；源删除cascade；notes、media项结构和shape_id原样 |
| PlaybackSession | PlaybackSession：window_id、source、状态/模式/错误、页码/进度、音量/循环、显示目标、兼容pending字段 | window_id唯一且1–4；display_mode仅single；playback_mode仅空/powerpoint/pdf；source删除SET NULL |
| RuntimeState | RuntimeState：id=1、big_screen_mode、volume_level/volume_muted、updated_at | 显式单例约束；single/double与单窗显示模式不可混用 |
| Scenario | Scenario：name/description/sort_order、模式/音量state、targets、时间 | 只沿用真实模型，无文档虚构字段；targets JSON三态、resume/autoplay，排序-sort_order,-updated_at |
| BackgroundAudioState | BackgroundAudioState：id=1、current_source、state/error、position/duration、volume/mute/loop、兼容pending | 独立于窗口；source删除SET NULL；初始volume=70、loop=true等默认来自旧模型，不能套窗口默认值 |
| BackgroundAudioPlaylistItem | PlaylistItem：id/source_id/sort_order/created_at | 按sort_order,id；服务层去重、仅audio；不擅加会拒旧数据的数据库唯一约束 |
| StreamSource | StreamSource：id/name/identifier/url、online/active/state/last_seen/error | stream_identifier唯一；自动发现更新媒体映射；启动后online由实际探测确认 |
| PlaybackCommandRecord / BackgroundAudioCommandRecord | CommandRecord（内部统一存储，策略仍分目标类型） | 保留目标、命令、参数、顺序、合并区别；新库没有旧队列导入，不无条件重放运行中不确定动作 |
| DeviceEndpoint旧占位 | 不创建新的可配置设备表 | 保留现有配置/设备协议；历史unmanaged占位不等于当前可编辑业务实体 |

实体按现行源码行为设计，以测试fixture验证约束和DTO，不要求逐列复制历史数据库。新库可独立初始化，遇到已有不兼容库明确退出/另选目录，绝不自动清空。新栈EF schema演进继续保留。

## 指令和执行身份

### CommandRecord

| 字段 | 说明 |
| --- | --- |
| command_id | UUID，跨重试不变；不建立历史queue ID迁移映射 |
| target_kind/target_id | display:1–4 或 audio:1；Office子操作使用关联请求，不另建第二条用户指令 |
| target_sequence | 目标内单调整数，唯一(target_kind,target_id,target_sequence) |
| command/args/schema_version | 保留旧动作字符串/参数语义；内部版本化DTO；白名单验证 |
| source_generation/source_revision | 关联哪次内容请求、哪个源版本；A→B→A必须不同generation |
| status | pending/processing/completed/failed/superseded/uncertain |
| consumer_instance_id/owner_epoch | 真实执行实例身份和目标所有权代次 |
| claim_token/lease_expires_at | 每次领取的新随机token与ControlHost计算的租约截止 |
| attempt_count/deadline | 重试次数/操作阶段截止，与租约续期分离 |
| created_at/started_at/completed_at | 排队、执行与确认时间 |
| result_code/result_evidence/last_error | 实际证据与失败分类；不存截图/大媒体/凭据到队列 |

索引：目标+status+sequence、status+lease_expires_at、command_id唯一；每目标最多一条processing，由写入协调和事务约束共同保证。

```text
pending → processing → completed / failed
   │          │
   │          ├─ 旧端已停止且证明未执行或可幂等 → pending
   │          └─ 执行事实不可判定 → uncertain → 明确对账/人工处置
   └─ 被合法合并/取代 → superseded
```

- 显示OPEN/CLOSE/RESET_PPT仅替代pending；显示与音频仅合并pending的SEEK/SET_LOOP/SET_VOLUME/SET_MUTE；音频OPEN不清队列。
- NEXT/PREV保持原语义，PPT可能是动画步骤；不得一律变下一页GOTO。
- failed是明确失败的最终结果，不无限自动重试；uncertain不能伪装completed或自动跳过后续相对动作。
- 完成证据有界保留默认7天，未完成/uncertain不按时龄删除；审计到期仅在无关联未决请求、离线旧消费者无法重新获权时清理，配置改变须测试去重窗口。
- 兼容pending字段为外部投影：旧显示enqueue时投影新命令、ACK后投影最早剩余；音频始终最早剩余。先fixture冻结，不能擅自统一投影时序。内部账本不暴露为新HTTP枚举。

### WorkerOwnership

target、worker_instance_id、pid、process_start_time、logon_session、owner_epoch、last_transport_heartbeat、last_ui_progress、capabilities、status。可持久记录诊断，但进程事实启动时重建，不把旧pid自动视为新实例。

连接身份由OS管道客户端信息及Supervisor子进程登记校验，payload的pid不是证据。epoch是ControlHost原子递增的整数，旧epoch不能写新状态；它只能限制数据写入，不能撤销已发出的物理副作用。

### RuntimeGroupControl

id=1、group_epoch、state（stopped/starting/armed/draining/faulted）、stop_reason、explicit_start_request_id。由ControlHost保存；Supervisor通过受认证控制通道请求变更。所有Claim/Office执行授权须检查armed及匹配group_epoch。重新连接不解除停止闩锁；显式启动Supervisor或现有系统restart动作完成清理、重置、预检后才可重新armed。故障后的历史指令须对账/处置，不随armed自动重放不确定物理动作。

OfficeOperation包含稳定operation_id、parent command/job和claim、group/host/slot epoch、deadline、queued/executing/completed/failed/uncertain状态与结果指纹；Host在STA出队真正调用COM前再次校验。准备请求业务超时与inflight实体分离；COM未返回/未证实退出前不释放执行槽或重试。

### Desired/Observed 内部分离

- `desired_generation`随有效open/close/reset递增，volume等仍定位当前代次；`observed_generation`对应最后确认可见源。
- 兼容PlaybackSession可以立即投影旧合同规定的loading/idle，但不据此宣称adapter已打开/释放。另保留actual_source_id/actual_adapter_kind/cleanup_pending用于协调。
- 旧processing完成晚于新意图时可登记旧命令凭据，不更新新会话源/实际模式；执行完后依序处理新命令。
- 新源失败且旧画面仍有效时，按原恢复规则回写旧实际源和状态，同时保存失败诊断；不能只回滚DB而把新窗留在前台。
- AudioFinished事件携带audio_instance_id/source_generation/event_id；同事件只能推进列表一次。

## 资源模型

### MediaPreparationJob（持久）

job_id、source_id、source_revision/digest、kind（metadata/preview/show-format/pdf）、status（queued/running/succeeded/failed/cancelled）、priority、deadline、artifact_manifest、error、Office执行身份。

唯一(source_id,digest,kind,recipe_version)防重复导出；派生资源先写临时文件，完整验证后原子发布manifest，再更新source metadata。源版本已变则只清理半成品，不覆盖新缓存。Office作业所有权只在PowerPointHost；控制面可以做不需要COM的ZIP元数据解析。

### ArtifactManifest（持久）

source_id、source_digest、recipe_version、相对路径、SHA-256、文件大小、页数、状态/错误。路径须在允许缓存根内；仅文件存在不足以表示匹配。复用旧摘要算法/metadata格式由适配层显式映射，不能把不同算法字符串直接比对。

### WarmResource（Worker内存）

resource_id、window/audio_target、source_id、source_revision、uri、security_context、adapter_kind、instance_generation、state、is_muted、引用集合/健康度。

活WebView/LibVLC/COM对象不持久化、不跨进程传递；共享的只能是只读制品。Ready资源保持到显式取消、版本变化、退出或故障；资源预算不足时拒绝/延后新的预热并可诊断，不能静默驱逐仍承诺保活的网页。

### PowerPointOwnership（OS锁 + Host内存 + 持久诊断）

machine_mutex、host_instance/epoch、owned_office_pid/start_time、active_window_id/source_generation、presentation_identity、slideshow_hwnd、slot_state、inflight_job。

命名互斥锁按主机唯一自有放映域设计，实例/安装ID用于排错而不允许多个安装各占一槽。锁释放或abandoned不代表PowerPoint已经退出；重建前Supervisor必须核验旧Office是否还活着。HWND通过PID/线程/窗口样式验证；无法确认自有Office时不接管、不强杀。

## 控制客户端状态（非服务端业务表）

**ServerProfile**：选定服务器的scheme/host/port、显示名与本地模式；验证为允许的HTTPS origin或明确debug开发服务器。不含密码/session/CSRF，不支持带凭据URL。客户端保存非敏感连接偏好，不在服务器为每台手机建一套业务库。

**ClientConnection**：disconnected/connecting/unauthenticated/connected/stale/error、connection_generation、当前内存CSRF请求token、SSE连接身份/最后同步时刻；三端共享状态机，平台提供前后台/网络事件。

切换主机增加generation并清旧store/会话；旧响应或事件不得写入新主机状态。普通重连只恢复读状态，不重放离线控制。Cookie由本端浏览器/WebView会话存储，前端不自行保存HttpOnly会话票据。

## 开发数据边界

新后端可在独立目录运行EF schema初始化和样例seed，不需要历史业务导入/逆向导出实体。Git版本不携带数据库/媒体；代码变旧导致schema不兼容时另选新测试目录，而不是自动还原或删除用户数据。
