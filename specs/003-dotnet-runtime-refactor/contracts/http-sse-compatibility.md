# External Contract: REST / SSE与三端会话

对外合同根仍为`docs/openapi.yaml`及引用文件；三端共享DTO，不复制第二份OpenAPI。当前是开发期重构，不要求历史数据、会话、Django admin或未使用旧页面的长期兼容。

## 行为验证

用基线commit的路由/view/测试与前端api.ts建立核心fixture，逐功能验证字段名、状态码、错误、权限、排序与下载/预览。新库使用测试数据，无需旧库导出；UI样式/Tailwind和平台壳可以调整，但不能掩盖业务差异。

允许归一化随机会话值、测试路径和观测时间；不归一化错误码、实际放映模式、页码、音量或相对动作顺序。真正改变业务规则时记录差异并确认，安全补强和必要平台适配写清测试。

## HTTP覆盖

| 面 | 保留 |
| --- | --- |
| Auth | csrf/login/logout/me/status/change-password，原请求响应外观、权限与改密流程 |
| Media | folders/sources、upload/local/web、move/download/preview/ppt-resources、临时源 |
| Playback | sessions/runtime、open/control/navigate/ppt-media/close/loop/volume/mute、show-ids/reset-all/reset-ppt |
| Audio | 状态、playlist与play-source/control/volume/mute/loop |
| Displays/Devices | 单显示器枚举/选择、TCP控制、视频墙模式、系统音量 |
| Scenarios | CRUD/create兼容API、capture/pin/activate及三态/排序 |
| System/Events | 显式停止/重启本栈、受控physical-smoke、REST/SSE实时状态 |

按实际API消费者保留兼容入口，不额外建设旧Django管理界面或长期旧页面代理。旧路由删除若影响真实调用者须明确列出；不返回假200占位。已有用户功能在共享Vue/受控开发命令中可用即可。

Web同源开发入口可保持5173、API8000；打包客户端选择受信HTTPS端点，具体绑定由配置给出。HTTP开发访问继续支持；不改8890/9997/8554流端口。保留尾斜杠、multipart参数和JSON401，不用登录HTML重定向代替API错误。

## 身份与CSRF

- 账户DTO保留id/username/is_staff/is_superuser，内部保留is_active及必要权限。新测试库按初始化规则建账户，不导入旧hash/session，不为Git回退维持Django密码格式。
- 使用ASP.NET标准password hasher与受保护Cookie，复用原密码校验/改密业务规则。已有账户启动时不被bootstrap覆盖。
- login缺字段400、无效凭据401、成功`{user}`；logout匿名可200且`{detail:"ok"}`；me匿名401；status匿名200且`{authenticated:false,user:null}`。以测试fixture校验。
- 改密后当前客户端登录保持，刷新请求防伪token；Cookie/票据格式是服务端实现，不要求继承Django签名session。
- 同源Web可继续读csrftoken；所有端都可从已有`auth/csrf` JSON取得`csrfToken`放内存，unsafe请求发送X-CSRFToken。跨源客户端不得读取服务器域的document.cookie。
- ASP.NET Antiforgery的RequestToken与内部HttpOnly验证cookie分离；session为HttpOnly。登录/登出/改密刷新token，keyring放用户受限目录。
- 打包客户端跨站HTTPS会话采用SameSite=None; Secure和精确Origin/CORS/credentials白名单；CSRF校验保留。常规包不通过关闭webSecurity、SSL校验或匿名SSE绕过限制。
- 已有HTTP开发Web使用匹配的非Secure/same-site开发配置，不把其与常规HTTPS包配置混淆。debug远程同源UI模式见[客户端合同](./frontend-clients.md)。
- 某些旧unsafe端点csrf_exempt是安全缺口；补校验须覆盖合法Vue和负向请求，不能假称旧版一直全面防伪。
- /media等受保护资源先鉴权，再提供文件；只匿名提供真正公开的前端构建资源，防静态文件绕过。

## 状态、文件与错误

- 保留各接口原有success/detail/code形状，不强制套新响应包装。
- HTTP接受命令不等于实际播放；playing、页码和powerpoint/pdf模式由有效执行结果确认。
- source_type仍8种，PDF仍属ppt。内部uncertain等状态经原错误字段和实际状态表达，不强加新前端枚举。
- 对外last_updated_at经Date.parse后的毫秒精度也要在实体新版本上严格递增，重启/回拨不倒退；同版本保持同值。
- 本机路径明确是播放主机允许目录的路径；Windows/Android客户端自己的文件须上传内容。注册/播放/下载/预览都验证真实路径，不能只信已有数据库记录。
- multipart/XHR、预览、下载需共享本端认证会话；不能由无Cookie的系统浏览器打开受保护下载后伪报成功。客户端保存/分享适配见客户端合同。
- 模式/设备控制失败如实报阶段与结果；数据库事务不能撤销已发生的硬件副作用。

## SSE与恢复

- 保留EventSource withCredentials及playback_state事件，payload保持`{sessions,background_audio}`等既有外观。
- text/event-stream、no-cache、禁代理缓冲，默认30秒注释心跳。服务端提交后推快照，约0.2s合并高频进度；不保证每帧状态必达。
- 保留last_id输入兼容，但旧SSE不是持久事件日志，新设计也不承诺完整历史replay。重连先恢复完整状态。
- sessions沿用时间戳门禁；音频store必要时补同类拒旧帧，不为三端复制不同状态合并逻辑。
- 新的connection_generation覆盖切主机/会话变化，旧请求/SSE必须丢弃；普通断线不创建第二个并存EventSource。
- Android退后台可能断流，回前台先me/快照再重连。离线命令不排队重放，SSE在线不能代替player_online。
- 三端均用浏览器/WebView的fetch/XHR+EventSource会话；不要只把HTTP换native而让SSE继续用另一Cookie jar。精确跨源策略见[frontend-clients.md](./frontend-clients.md)。

## 非目标

不新增JWT/SignalR、公网云接入、完整Django后台、会话跨版本迁移、历史事件日志或原生HTTP/SSE代理平台。共享Vue可更新样式与平台适配，但业务规则的改变必须显式提出。
