# Runtime Contract: 媒体、预热与Office生命周期

关联 [spec.md](../spec.md) FR-004/006/010–021；这是目标行为设计，不是库API调用清单或实现代码。

这里的web适配器是Windows大屏输出中的WebView2，不是控制台Electron或Android WebView。新控制客户端不改变本运行时的播放/预热所有权，关闭客户端也不释放主机媒体。

## 适配器边界

每类适配器具有Prepare、Open、Control、Observe、Hide/Retain、Close/Dispose的概念边界。能力由Domain声明且与旧测试一致；技术库支持某操作不等于对用户自动开放该操作。

| 源/通道 | 新实现 | 兼容边界 |
| --- | --- | --- |
| image | WPF Bitmap/Image | 保持缩放/定位；不伪造播放/暂停能力 |
| video | LibVLCSharp | 原Qt视频的autoplay、seek、loop、音量/静音和结束行为逐项对照 |
| audio | AudioWorker + LibVLCSharp | 不占1–4窗口，列表业务由ControlHost决定 |
| web | WebView2 | 原play/stop语义；保留页面和登录，不增加窗口音量接口 |
| srt/rtsp/custom_stream | LibVLCSharp | 不新开放seek/loop；SRT默认read、RTSP手动兼容；延迟单位原样 |
| ppt实际pdf | Windows.Data.Pdf + WPF位图 | source_type仍ppt，页码1-based；不宣称支持动画/页内媒体 |
| ppt实际powerpoint | PowerPointHost STA + 放映窗口 | 唯一动态放映、页/动画导航与媒体控制、重置恢复页码 |

## 输出身份、声音与显示

- 始终4个逻辑输出；single是大屏工作模式而非只启动1个Worker。窗口3/4固定静音，single额外约束窗口2；具体设置顺序与支持媒体检查取旧服务fixture。
- 实际显示器用Windows设备路径/适配器信息内部定位，外部保留既有label/ID契约。枚举、负坐标、缩放、热插拔失败可诊断；禁止自动搬到用户主屏伪装成功。
- 每种媒体固定父容器和原生矩形区域。WebView/LibVLC/Office间不依赖透明WPF叠层；置顶、焦点和播放器ID覆盖单独验证airspace。
- 后台视频/直播预热须静音，web隐藏保活时限制声音但不暂停必要脚本；前台按已有策略恢复。AudioWorker只在收到有效播放指令后发声。
- 四进程隔离自有对象故障，但不能隔离GPU/驱动/音频设备/Office全局资源故障。

## 资源状态

```text
Cold → Preparing → ReadyHidden → Visible
           │             ↑          │
           │             └──────────┘
           └→ Failed       Hide/Retain
ReadyHidden/Visible/Failed → Draining → Disposed
```

- 资源key为`target + source_id + source_revision/digest + uri + security_context + adapter_kind`。
- ReadyHidden要求实际对象准备完成且健康，不只是DB keep_alive=true；Visible要求切换协议完成，不仅调用Open返回。
- `keep_alive/preheat`是用户预热意图，保留既有别名/metadata外观；Preparing/失败进度为内部诊断，不凭空新增外部必填字段。
- 每Worker内认领/归还活资源；跨Worker只共享不可变文件制品。同一网页在两个窗口打开必定是两个实例，不能经Named Pipe转移DOM/COM/VLC对象。
- 健康且已接受预热页面保持到显式取消、版本/上下文变化、退出或实际故障。不得为省内存静默驱逐并假报保活成功；预算不足时延后/拒绝新预热并记录原因。
- 配置的源/内存预算由开发机负载测试给出；不隐式引入比既有业务更低的数量限制。测试记录实际并发素材/预算及超预算行为，无需现场上线演练。
- 预热直播定期健康检测/续热，TTL只是检查依据，不到点无条件销毁健康连接；沿用SRT/VLC握手宽限和配置单位。
- 活对象绝不持久化。进程崩溃后重建资源且报告冷启动，不宣称DOM状态仍在；WebView2 ProcessFailed明确标记受影响资源。

## 切源事务（UI意义，不是数据库原子事务）

1. 取得新内容generation，保留旧adapter/实际源和可恢复显示状态。
2. 校验源版本/权限/能力，认领健康预热或进入Preparing。已提交新open并不等于新画面已经出现。
3. 非PPT切换尽可能在新资源Ready后显示；旧PPT嵌入窗口可先隐藏以交还容器，失败再恢复旧窗口。不能承诺所有媒体无黑帧。
4. 显示新资源、上报实际状态与模式，再将旧资源归还ReadyHidden或Draining。清理失败与显示成功分别记录。
5. 新资源失败且旧资源有效时恢复旧画面/实际source；无法恢复则明确黑屏安全态。不能DB已回旧源但画面仍是失败的新容器。
6. 迟到的A或B结果只能完成其历史命令，不影响最新A的generation、预览、模式或错误。

Ready判据按媒体定义：图像/PDF已完成有效页面渲染；web导航完成且宿主可显示（真实页面可按允许配置检测就绪）；视频/直播有有效播放状态/输出与错误宽限；PPT拥有验证过的放映窗且页码有效。软件结果不能代替物理屏幕可见性的实机测量。

## PowerPointHost

### 槽位与操作

- 主机唯一自有动态放映所有权；槽位包含host/epoch、目标window/generation、presentation身份、HWND及Office进程证据。
- Host内唯一STA+消息泵创建/访问/释放所有COM对象；其他进程只交换DTO/句柄，不传RCW/COM接口对象。
- COM激活可能关联既有Office实例；必须验证本系统是否真正拥有，无法证明时拒绝接管/强杀并提示用户处理。
- 首个允许动态放映的open取槽；占用时直接按匹配源digest的PDF回退，不等待/关闭别的放映、不建第二COM。
- PDF缺失/过期明确失败；已PDF不因槽释放升级；reset-ppt只处理实际powerpoint窗口并保留页码，PDF窗口保持。
- 同一窗口换另一动态PPT需要串行关闭/打开，不能假设两个COM放映重叠热切换；旧画面恢复只在原资源仍可恢复时提供。

### 准备作业

- OpenXML元数据/备注/媒体关系解析可由控制面执行，但保真PNG/PDF/show-format导出全部走唯一Host。
- `Idle/Preparing/Showing/Closing/Faulted`为Host状态。长导出只在无Showing时开始；Showing期间作业排队，未进入COM的作业等待超时后可安全取消并记录可重试准备失败。已进入COM的导出超过deadline，仅结束业务等待并标记失控/inflight；不能视为执行已结束、槽已释放或立即可重试。
- 放映优先只表示未开始作业的调度优先级，不代表可抢占已进入的同步COM调用。导出中打开新动态源可用现有有效PDF回退，否则受控等待/失败，绝不再起第二Host绕过。
- COM未返回或未确认自有Office安全退出前保持Busy/Faulted与inflight，不派发新COM调用/重试；迟到制品先隔离，取消/超时/旧generation不得回写新缓存。每个子操作按IPC合同独立去重，并在STA真实出队前再次验证组/槽授权。
- 上传/注册仍保留“预览/缓存失败不阻断媒体源创建”；不能未经合同评审变成新job-only响应。后台补齐结果沿现有metadata、预览资源与事件外观刷新。
- 输出先写半成品，摘要/页数/格式验证后发布；版本已变丢弃半成品，不替换新source缓存。
- 文稿密码、受保护视图、宏/外链/模态弹窗不能自动降低安全设置绕过；超时可诊断，不全局关闭Office安全策略。

### HWND与恢复

- AttachSurface须验证父/子HWND对应PID/start time、有效窗口、owner/generation、DPI上下文和样式。
- 顺序为创建宿主容器→启动窗口化放映→验证句柄/样式→嵌入/调整大小→确认目标可显示。失败归还槽/进入Faulted，绝不报告playing。
- Hide/Detach先于宿主销毁；停止导航并等待在途COM操作完成或明确超时。仅释放/关闭明确自有Presentation；Application.Quit或强退前重新核对当前文稿与持续独占，不能仅凭启动时PID/start time判定。用户后来加入文稿、无法枚举或COM卡死时，不Quit/强杀，进入人工处置并保留槽位失控证据。
- 锁abandoned不证明Office死亡，重建Host前确认旧端终止；不按POWERPNT进程名全杀。
- SetParent/DPI/airspace失败应在开发原型中暴露；顶层放映窗方案仅经评审后替代，不能偷偷改成全部静态PDF。

## 音频与结束事件

AudioWorker保持单独实例，列表顺序/next/previous/loop/deletion由ControlHost决定；Worker只有执行与状态。自然结束事件必须携带event_id、当前source generation、播放实例身份。新源已播放后收到旧Finished只登记过期，不推进列表；重复同事件只ACK一次。

默认音量、循环、删除当前列表项停止/清源、列表末尾非循环stopped且position=duration沿用原服务。显示音量/系统主音量/背景音量是三个层次，不能合并为一个全局slider。

## 销毁与安全态

先停止新操作/回调重入，再隐藏/解绑、停止媒体、释放player/media/instance、页面/进程、文件引用。各步独立finally；一个VLC释放失败不跳过其余步骤。临时源只有所有前台/预热/在途引用都解除才允许物理删除；失败保留重试与审计。

退出/崩溃/桌面失效不自动重播历史内容；默认兼容整组停止，成员故障分类与ControlHost停止闩锁见[runtime-ipc.md](./runtime-ipc.md)。重连仅恢复通信，不重新授权播放；源错误可局部回旧画面时不等同Worker退出，不扩大为任意杀进程。
