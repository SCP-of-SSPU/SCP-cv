# Phase 0 Research: .NET Windows 播控运行时

**Date**: 2026-09-08
**Input**: [spec.md](./spec.md) / 用户指定架构；基线 `029a28577fa3d4b9224d45f229726c7bd26c9964`。

以下Decision是设计选择；Rationale区分代码事实与公开依据。前期Windows互操作依据保留适用部分，本轮新增共享前端与客户端调研；主规划核验了引用资料，不把文档访问或调研建议当作实机验证。

## R01 - .NET 10 与 Windows 支持

- **Decision**: .NET/ASP.NET Core/EF Core 10 同一大版本，x64；Windows UI 使用显式 Windows TFM；实施时锁定验证过的 SDK/NuGet 补丁。
- **Rationale**: 官方表列 .NET 10 为 LTS，支持至 2028-11-14。Windows 安装文档对 Windows 10 支持限于列出的 LTSC/Enterprise 版本，不能泛称所有 Windows 10/11 均受支持。
- **Alternatives considered**: .NET 8 剩余支持期短；.NET Framework 不适合新后端；NativeAOT/trimming 对 WPF/COM/反射包装风险不值得本次引入。
- **Gate**: 记录真实 Windows SKU/build、Office 位数/版本、VLC、WebView2、GPU；不支持的 OS 须升级或另审兼容风险，不能把“可运行”等同厂商支持。
- **Sources**: [生命周期](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core)、[Windows 支持](https://learn.microsoft.com/en-us/dotnet/core/install/windows)。

## R02 - WPF 不自动解决无缝合成

- **Decision**: 固定原生矩形显示区域 + 显隐；PowerPoint 跨进程 SetParent 为先验证路线，检查 DPI、样式和 HWND 所有权。
- **Rationale**: SetParent 不自动修改 WS_CHILD/WS_POPUP；跨进程 DPI awareness 不同可能强制重置子进程 DPI。LibVLCSharp.WPF 明确存在 airspace，叠层实际使用分离窗口。
- **Alternatives considered**: Host 自管顶层放映窗并统一几何/Z-order 为失败后的评审候选；捕获成纹理引入延迟/交互限制，本次不选；全部 PPT 转 PDF 改变动态能力，拒绝。
- **Gate**: 100/125/150% 混合 DPI、负坐标、跨屏/拔插、50 次切源、焦点/置顶、用户 Office 共存。不通过先改计划，不静默降级。
- **Sources**: [SetParent](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setparent)、[LibVLCSharp.WPF](https://raw.githubusercontent.com/videolan/libvlcsharp/3.x/src/LibVLCSharp.WPF/README.md)。

## R03 - Office 唯一 STA 仲裁

- **Decision**: PowerPointHost 在交互桌面 STA 消息泵中拥有 COM；放映、隐藏打开、预览和导出全经此宿主；活动放映优先，阻塞导出只在无活动放映时串行执行。
- **Rationale**: Office 非可重入、STA，不支持 ASP.NET/NT Services 等非交互自动化。同步 Export 可能堵住翻页；超时不能安全取消 COM。单 Host 不保证独占新 PowerPoint.exe，归属无法证明时禁止强杀。
- **Alternatives considered**: 额外 COM 导出进程引入争抢；无条件边放映边导出没有时延保证；OpenXML 可解析部分元数据但不能保真渲染，不代替 Office。
- **Gate**: 放映时上传/准备的时机差异需评审；请求保持现有容错外观，准备失败不阻断源注册。验证模态对话框、长导出、卡死、用户 Office 不受干扰。
- **Sources**: [Office 非交互限制](https://learn.microsoft.com/en-us/office/client-developer/integration/considerations-unattended-automation-office-microsoft-365-for-unattended-rpa)、[隐藏打开](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.presentations.open)、[静态导出](https://learn.microsoft.com/en-us/office/vba/api/powerpoint.presentation.exportasfixedformat)。

## R04 - WebView2 线程与故障域

- **Decision**: 每 Worker 独立 UDF/environment，UI/STA 创建操作，保持消息泵；仅本 Worker 内复用页面，监听 ProcessFailed；需持续脚本/网络的预热页面不 TrySuspendAsync。
- **Rationale**: WebView2 要求 UI STA；Task.Result 阻塞消息泵会阻断回调。同 UDF 可共享 browser/renderer。IsVisible=false 只表示不渲染；Suspend 会暂停计时器/动画且为 best effort。
- **Alternatives considered**: 跨进程搬迁 WebView/DOM 不可行；共享 UDF 扩大故障域；每次 Navigate 破坏核心保活。
- **Gate**: 登录、滚动、JS计数、WebSocket、隐藏静音、崩溃恢复；不承诺重启保留 DOM 或隔离全机 GPU 故障。
- **Sources**: [线程](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/threading-model)、[进程](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/process-model)、[挂起](https://learn.microsoft.com/en-us/dotnet/api/microsoft.web.webview2.core.corewebview2.trysuspendasync)、[可见性](https://learn.microsoft.com/en-us/dotnet/api/microsoft.web.webview2.core.corewebview2controller.isvisible)。

## R05 - LibVLC 与 PDF

- **Decision**: 每 Worker 生命周期一个 LibVLC 实例，按媒体管理 Media/MediaPlayer；回调先调度，不原回调重入；Windows.Data.Pdf 渲染图片、限额预取邻页。
- **Rationale**: LibVLCSharp 最佳实践要求 Dispose，提示回调重入可能死锁。Windows.Data.Pdf 是渲染 API，不是现成放映器；PDF 静态视图不保留 PPT 动画/页内媒体。
- **Alternatives considered**: 长期保留 Qt 本地视频造成多栈；自制 FFmpeg/D3D 播放超出需求；浏览器视频不能替代 native SRT。
- **Gate**: Qt→VLC 的格式、seek/loop/autoplay/音量/结束事件逐项测试；实际四路 GPU 能力需同机验证。
- **Sources**: [最佳实践](https://raw.githubusercontent.com/videolan/libvlcsharp/3.x/docs/best_practices.md)、[安装与许可](https://raw.githubusercontent.com/videolan/libvlcsharp/3.x/README.md)、[PdfPage](https://learn.microsoft.com/en-us/uwp/api/windows.data.pdf.pdfpage)。

## R06 - SQLite 与 Named Pipe

- **Decision**: ControlHost 有界单写入调度、短事务、逐操作 DbContext；WAL 位于本地磁盘。应用生成 claim token/epoch，不依赖 SQLite 行锁或数据库 rowversion。管道双工传输、持久提交先于唤醒。
- **Rationale**: WAL 仍只有一个 writer、不适用于网络文件系统；单进程不等于自动串行写入。EF SQLite 不支持数据库生成并发 token，DateTimeOffset 排序受限。管道权限需显式限制用户、会话、角色，不信任自报 PID。
- **Alternatives considered**: Worker 直接写库保留 ORM 耦合；内存管道不可恢复；Redis/RabbitMQ 为单机增添服务。
- **Gate**: lost wake、busy timeout、失败提交、旧 epoch 回写、身份伪造、版本不匹配；新 owner 先证明旧物理执行端停止。
- **Sources**: [WAL](https://www.sqlite.org/wal.html)、[EF SQLite 限制](https://learn.microsoft.com/en-us/ef/core/providers/sqlite/limitations)、[Named Pipes](https://learn.microsoft.com/en-us/dotnet/standard/io/how-to-use-named-pipes-for-network-interprocess-communication)、[PipeOptions](https://learn.microsoft.com/en-us/dotnet/api/system.io.pipes.pipeoptions?view=net-10.0)。

## R07 - 至少一次交付与不确定副作用

- **Decision**: 保留队列顺序/合并，新增内部 token/epoch/generation 和完成凭据；同结果幂等接收。非幂等动作不确定时先对账，无法证明则 uncertain。
- **Rationale**: 旧队列有租约，ACK 后删记录，无完成台账。Office/硬件/UI 与数据库不能原子提交。NEXT 可能是动画步，不总能变成 GOTO 下一页。
- **Alternatives considered**: 租约过期直接换 Worker 不能阻止旧物理动作；全部动作变绝对值改变语义；exactly-once 宣称不成立。
- **Gate**: 同实例结果重传与旧实例消失分开；UI 健康与后台线程心跳分开；默认30秒租约不是实际执行超时，长任务需续租与阶段截止时间。
- **Sources**: 仓库 `services/playback_commands.py`、`background_audio_commands.py`、`player/controller_polling.py`、`adapters/ppt_navigation.py`。

## R08 - 新数据认证与共享会话

- **Decision**: 新后端独立初始化，使用ASP.NET标准密码hasher/受保护Cookie，不编写Django历史密码/session导入器。保持既有认证HTTP响应与CSRF字段；同一控制端REST/SSE均走浏览器/WebView会话。
- **Rationale**: 用户取消旧数据迁移要求，原密码格式往返没有必要。原SSE不是持久事件日志，继续全量快照恢复。CapacitorHttp只patch fetch/XHR，不能假定EventSource跟随其native cookie jar。
- **Alternatives considered**: 原生HTTP/SSE桥增加额外实现与会话同步；JWT/SignalR改变既有外部合同；Django兼容密码存储属于已取消范围。
- **Validation**: 三端实际包完成csrf/login/me/SSE/改密/登出；同毫秒旧帧、切服务器和前后台重连。未通过Cookie策略的设备不得假报可控制。
- **Sources**: [ASP.NET防伪](https://learn.microsoft.com/en-us/aspnet/core/security/anti-request-forgery?view=aspnetcore-10.0)、[CapacitorHttp](https://capacitorjs.com/docs/apis/http)、源码api_auth_views.py、sse.py及共享frontend服务。

## R09 - 快速迭代替代生产迁移

- **Decision**: Git小提交/revert管理代码；新数据目录和fixture初始化，不建跨栈导入导出、切流或逆迁移工具。不删除当前用户数据。
- **Rationale**: 用户明确项目无现场维护、处于快速迭代；长期双轨与生产回退不产生当前价值。Git不恢复被忽略的数据库/媒体，恢复代码可能需要另一个兼容数据目录。
- **Alternatives considered**: 早期方案的数据搬迁、旧密码格式保留、文件隔离及15分钟回退指标全部取消；运行时命令崩溃恢复继续保留。
- **Validation**: 新空目录能启动测试，旧目录不兼容时报错，不自动清空；历史由Git保留，无要求新旧同时控制设备。
- **Sources**: 用户本轮范围修订；仓库.gitignore与现有初始化/测试约定。

## R10 - 开发运行与最小治理

- **Decision**: 自有Windows运行时同一普通交互用户，保留协作退出；明确Office/VLC/WebView2/MediaMTX外部依赖。同步宪章目标栈，不建设生产上线审批链。
- **Rationale**: 框架更换不能消除Office STA/桌面和原生资源限制；但这些验证可在开发机完成，没有现场维护演练前提。
- **Alternatives considered**: 服务内Office、不验证就假成功都不可取；完整使用周期/8h上线门槛不再作为当前开发要求。
- **Validation**: 核心回归、三端实际运行、Windows播放、60分钟固定资源集合测试。更长生产耐久验收留给以后真实部署需求。
- **Sources**: [WebView2部署](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)、前述Office文档、用户范围修订。

## R11 - Tailwind4与共享Vue

- **Decision**: 使用官方@tailwindcss/vite；Tailwind4布局/工具类复用既有Fluent token与Naive UI组件，@theme inline映射变量，初期不导入Preflight。
- **Rationale**: 当前frontend已有Vue/Router/Pinia/Vite和Naive/token桥；Tailwind是CSS工具而非业务组件库。全局Preflight会改变元素默认样式，先复用可避免无意改变现有交互。
- **Alternatives considered**: 为三端写三份页面、用纯Tailwind重写所有组件均无需求依据；不再坚持前端完全不能改样式。
- **Validation**: 明暗主题、弹层/表单/表格、utility优先级、移动安全区域/触控、构建类扫描。浏览器最低Chrome111、Firefox128、Safari16.4；Android实际WebView需>=111。
- **Sources**: [Vite插件](https://tailwindcss.com/docs/installation/using-vite)、[浏览器兼容](https://tailwindcss.com/docs/compatibility)、[主题变量](https://tailwindcss.com/docs/theme)、[Preflight](https://tailwindcss.com/docs/preflight)、本仓库frontend/package.json和vite.config.ts。

## R12 - Electron与Capacitor分工及安全

- **Decision**: Windows用Electron、Android用用户确认的Capacitor8；同一Vite源码构建网页/app，网页history、本地包hash。Electron安全自定义app协议、Capacitor本地https://localhost。
- **Rationale**: Electron是桌面宿主，不运行Android。Capacitor支持Android/Web原生壳；8.0要求Node22+、minSdk24及SDK36，但其默认WebView最低60低于Tailwind4，需要显式提升minWebViewVersion。
- **Alternatives considered**: Electron同时覆盖Android不可行；不同前端框架/原生UI重写不符合共享页面目标；iOS/Linux/macOS客户端不自动纳入。
- **Validation**: Electron nodeIntegration=false、contextIsolation/sandbox/webSecurity=true；插件/导航/文件权限受限；APK实际路由/返回/生命周期/文件验证；包内不含凭据/服务器.env。
- **Sources**: [Electron安全指南源码](https://raw.githubusercontent.com/electron/electron/main/docs/tutorial/security.md)、[Electron协议](https://www.electronjs.org/docs/latest/api/protocol)、[Capacitor配置](https://capacitorjs.com/docs/config)、[Capacitor8升级要求](https://capacitorjs.com/docs/updating/8-0)。

## R13 - 本地资源包跨源Cookie与HTTP调试

- **Decision**: 常规本地包连接受信HTTPS后端，Cookie SameSite=None; Secure、精确origin/CORS/CSRF与credentials；Android仅对受限本应用WebView允许必要第三方Cookie。保留browser fetch/XHR+EventSource同会话，CSRF token从既有JSON取。HTTP LAN通过明确debug同源远程UI联调，不作为常规包默认能力。
- **Rationale**: CORS允许credentials不代表浏览器会接受第三方Cookie；Android较新target默认可能拒绝。Capacitor本地HTTPS访问HTTP后端还受mixed-content、Secure Cookie限制，单改cleartext不够。server.url/allowNavigation等官方标为开发用途，不应误带常规包。
- **Alternatives considered**: 关闭webSecurity/忽略证书会破坏安全；只patch native HTTP造成SSE会话分裂；一开始自制HTTP/SSE代理平台不符合快速开发目标；只实现debug远程UI不足以证明本地包可用。
- **Validation**: 三端真实常规包Cookie/SSE专项先行；可信开发证书在设备上安装信任后测试；遇设备政策拒Cookie明确不兼容，不暗中换匿名/JWT。常规包检查无server.url/cleartext，debug模式只用可信测试服务器/账户。
- **Sources**: [MDN CORS/第三方Cookie限制](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)、[Android CookieManager官方实现说明](https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/master/core/java/android/webkit/CookieManager.java)、[Capacitor配置](https://capacitorjs.com/docs/config)、[CapacitorHttp补丁范围](https://capacitorjs.com/docs/apis/http)。

## 调研范围与未执行项

R01–R07保留前一轮已核验的Windows运行时依据；本轮重新检查前端源码，并访问Tailwind、Capacitor、Electron、CORS与Android CookieManager资料形成R08–R13。没有安装/打包/实测客户端；文档限制和设计选择不能作为Cookie、DPI或实际播放已通过的证据。后续按开发用例验证，不要求现场迁移或逆迁移。
