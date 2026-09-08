# Client Contract: Web / Electron Windows / Capacitor Android

**Scope**: 用户已确认Android采用Capacitor。三端复用Vue 3 + Tailwind CSS 4 + Vue Router + Pinia + Vite；没有Linux/macOS原生客户端、iOS、离线控制、商店上架或自动更新平台要求。

## 角色与共享代码

| 平台 | 资源/宿主 | 边界 |
| --- | --- | --- |
| Web | Vite生成网页，由开发服务器或ControlHost提供 | 控制主机，不能直接读主机文件/调用COM |
| Windows客户端 | Electron本地打包同一Vue构建 | 只控制台，不代替WPF，不默认启动/停止后端 |
| Android客户端 | Capacitor本地打包同一Vue构建 | 只控制台，不包含.NET/Office/多屏播放器 |
| Windows播放主机 | ControlHost/Supervisor/Worker/Office/MediaMTX | 保持原实际播放/设备业务规则 |

三端同一份pages、routes、stores、API DTO、状态比较与能力判断；platform层只包连接配置、返回/生命周期、文件选择/保存等差异。不得复制三套业务流程，也不得把Electron preload当成任意Node入口。

## Tailwind与组件

- 安装Tailwind4与`@tailwindcss/vite`，与Vue Vite插件并用。业务工具类映射现有CSS变量/token，避免另建硬编码色板。
- 使用`@theme inline`引用Fluent语义token；保留Naive UI等已有交互组件。Tailwind不是弹窗/表格/选择器的行为实现，不要求本次重写它们。
- 初次接入仅引入theme/utilities层，不引入preflight.css；评估后的局部基础样式放受控层。验证既有Naive样式优先级、焦点、主题、抽屉与移动尺寸。
- 不用动态拼接完整类名导致Vite/Tailwind扫描遗漏；共享源码目录需被三个构建目标一致扫描。

## 构建、路由与平台基线

- Web保留history路由和服务器fallback；本地资源包用hash路由，路由表、权限守卫及页面不变。Vite base/资源URL按目标配置，禁止硬编码开发机绝对路径。
- Electron以受限`app://scp-cv`标准/安全自定义协议服务本地资源，app ready前注册必要standard/secure/supportFetchAPI/corsEnabled权限；路径规范化后只读打包目录，不允许任意磁盘路径或绕过CSP。
- Capacitor `webDir`指向app构建输出，执行cap sync android；常规包本地origin使用`https://localhost`，不使用file://。本地服务和路由正确处理刷新/Android返回。
- Node选择受支持LTS且>=22；Capacitor8采用minSdk24、compileSdk/targetSdk36和对应Android构建链。锁文件记录确切版本。
- Tailwind4最低Chrome/WebView111、Firefox128、Safari16.4；Android显式`minWebViewVersion=111`并在启动时检测/显示更新提示。Android API24可运行Capacitor不代表其WebView足够新；其他WebView实现也需特性测试。

## 主机连接与会话：常规包采用HTTPS

1. Web默认同源相对`/api`与`/api/events/`；Vite开发代理保持。打包客户端先显示共享连接页，用户输入播放主机HTTPS origin，校验scheme/host/port，拒绝内嵌凭据、任意路径/脚本协议。
2. 后端需设备信任的有效TLS证书；不忽略证书错误。开发机可使用已被该测试设备信任的开发证书。原8000 HTTP开发入口保留，HTTPS是可配置额外绑定，不擅改MediaMTX端口。
3. Electron渲染器、Android WebView均使用标准fetch/XHR和EventSource：请求`credentials: include`，事件`withCredentials:true`。同一目标上的REST/SSE用同一个会话存储，三端之间不共享Cookie文件。
4. ControlHost对白名单客户端origin返回精确`Access-Control-Allow-Origin`及credentials，预检允许`X-CSRFToken`等必要头，`Vary: Origin`；绝不以`*`搭配credentials。启用跨站客户端时session及防伪验证cookie配置`SameSite=None; Secure`，仍执行Origin与token校验。
5. 登录前/后、改密后请求已有`auth/csrf`，将JSON中的`csrfToken`保存在内存并发`X-CSRFToken`；跨源不能读取后端域的document.cookie。session是HttpOnly，框架内部防伪cookie独立，JS不能伪造它们。Web同源保留原csrftoken兼容。
6. Android仅对本应用受限WebView启用第三方cookie接收（CookieManager的per-WebView策略），因为现代targetSdk默认可能拒绝。导航和网络目标限定为应用本地origin及用户确认的服务器；这不是全系统浏览器放宽。Electron选定session需实测允许该受控跨站会话。
7. 关闭CapacitorHttp的fetch/XHR原生补丁，也不混用另一套native Cookie jar。该补丁不保证EventSource同时接入，不能以“登录接口200”推定SSE已认证。
8. 先验证csrf→login→me→一条受保护SSE→改密/登出；若设备/企业策略拒绝必要Cookie，显示明确不兼容原因，不降级匿名、不禁webSecurity、不悄换JWT。此测试先于大规模壳层开发。

服务端CSRF、防跨源和TLS配置属于三端连接的正常必要条件，不引入原生HTTP/SSE转发服务或自制双栈认证桥。跨站Cookie仍受设备策略约束，不承诺所有WebView/企业策略都可用。

## HTTP局域网调试例外

常规本地origin包不能仅开启cleartext就可靠访问HTTP后端：混合内容、Secure/SameSite cookie与第三方策略仍可能失败。

开发联调可显式选择debug远程UI模式：Electron loadURL和Capacitor server.url指向用户确认的同源开发Vue入口，API/SSE经该入口代理至ControlHost。Android debug包单独允许该开发服务器HTTP；只连接可信测试网络/测试账号，无TLS保密保证，导航/原生权限仍受限。

server.url、cleartext、allowMixedContent/allowNavigation是开发配置，不自动进入本地资源常规构建；常规包构建测试检查它们没有被误启用。该调试模式不是额外独立前端，仍运行同一源码。主机配置变更导致需要重建debug APK时如实说明，不能把仅开发热加载当成本地包功能已完成。

## 原生权限与导航

- Electron `nodeIntegration=false`、`contextIsolation=true`、`sandbox=true`、`webSecurity=true`；CSP script/style/connect来源明确，开发HMR例外只进debug配置。
- preload仅暴露少量命名操作并验证调用方origin/参数；禁止暴露ipcRenderer、任意shell、任意文件读写、Named Pipe或Office对象。主窗口权限默认拒绝，文件/下载按用户手势与明确目标授权。
- Capacitor只注册需要的插件，网络/文件权限按功能请求；不给远程媒体网页原生bridge。远程网页源由Windows播放器WebView2加载，不进入控制客户端受信视图。
- 拦截窗口打开/重定向，UI只允许本地资源或明确debug服务器；外链经确认交系统浏览器。受保护媒体预览使用已有资源接口，不能无限放开应用导航。
- 客户端启动/退出不触发system/restart或shutdown；显式主机停止按钮才发送受保护命令。

## 生命周期、文件和错误状态

- 连接配置存非敏感host/scheme/port；更换服务器先关闭SSE、清Pinia/CSRF/本端会话并提高connection_generation，旧响应必须丢弃，再登录新服务器。
- 本端会话清理由受限平台适配仅清本应用会话Cookie；在线时尽力调用旧服务器logout。离线时只能清本端凭据，不能宣称服务端旧session已撤销。服务器凭据不跟随主机切换，不将Cookie/CSRF值存连接配置。
- Android退后台或断网不保证SSE长连存活；回前台先验证会话、拉完整状态、重建单一SSE。网页/Electron亦复用同一连接状态机，防重连订阅倍增。
- 离线显示状态过期并禁用控制；不积攒翻页/播放指令待联网自动重放。
- 上传默认共享HTML file input/Blob/FormData与XHR进度；Android接document provider并覆盖取消/大文件错误。不要把客户端路径当作主机允许的本地路径。
- 下载在当前会话内取受保护资源，再经受限平台保存/分享适配处理；大文件选择可流式实现，不能把所有视频无上限转base64穿bridge。预览/下载的401/取消/空间不足不得误报成功。
- Android返回先关抽屉/弹层、再router.back，根页面按明确交互退出客户端；退出不能中断主机播放。覆盖安全区域、软键盘、44px触控、横竖屏和权限拒绝。

## 验收

Q1/Q2/Q11验证真实Web、Electron打包程序和Capacitor APK，不以Vite浏览器通过替代原生包。必须覆盖本地资源路径/路由、Cookie/SSE共同认证、跨源CSRF、主机切换、10次网络/生命周期恢复、文件选择/上传/保存、旧WebView提示、外链和原生权限拒绝，以及客户端关闭不影响主机。
