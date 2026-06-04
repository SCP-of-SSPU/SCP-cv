# 前端 Fluent Vue 设计

本文说明当前 Vue 控制台的结构、状态管理、接口边界和 Fluent 视觉体系，并给出迁移到目标 Django + Fluent + Vue 项目时应保留的前端契约。

最后更新：2026-06-04。

## 设计定位

当前前端是 SCP-cv 的播控控制台。它不直接访问 SQLite，不直接调用 Office、VLC 或 MediaMTX，也不直接控制播放器窗口。所有业务动作通过 Django REST 下发，所有运行态通过 REST 初始加载和 SSE 增量同步获得。

| 层级 | 当前路径 | 迁移重点 |
| --- | --- | --- |
| 接口合同 | `frontend/src/services/api.ts` | 优先迁移类型、请求封装、CSRF、SSE 地址构造规则 |
| 领域状态 | `frontend/src/stores/` | 保留 Pinia store 的状态结构和动作语义 |
| 页面呈现 | `frontend/src/features/`, `frontend/src/layouts/` | 可逐步替换为目标 Fluent 组件，但不要改变业务流 |

## 技术栈

| 项 | 当前实现 |
| --- | --- |
| 框架 | Vue 3 + Vite + TypeScript |
| 状态 | Pinia |
| 路由 | Vue Router |
| UI 组件 | Naive UI |
| Fluent 体系 | `@fluentui/tokens` 生成 CSS 变量，配合 Fluent 图标和 Naive theme overrides |
| 国际化 | `vue-i18n`，默认中文 |
| 构建脚本 | `npm --prefix frontend run build` |
| 类型检查 | `npm --prefix frontend run typecheck` |

当前项目的 Fluent 实现重点是 token、图标、间距、圆角、阴影、动效和信息架构，不是直接使用官方 Fluent Vue 组件库。目标项目如果已有 Fluent 组件，应优先保留现有 token 命名和领域状态，再替换呈现层。

## 入口与启动

| 文件 | 责任 |
| --- | --- |
| `frontend/src/main.ts` | 创建 Vue app、Pinia、i18n、router，注册全局未授权处理器，挂载 `App.vue` |
| `frontend/src/App.vue` | 安装 Naive providers、主题、全局 toast/dialog、认证初始化、store bootstrap、SSE 断开处理 |
| `frontend/src/stores/index.ts` | 暴露 stores，并通过 `bootstrapStores()` 并发加载首屏运行态 |
| `frontend/vite.config.ts` | Vite 构建和开发代理配置 |

启动链路：

```text
main.ts
  -> createPinia / router / i18n
  -> registerUnauthorizedHandler
  -> App.vue mounted
  -> auth.ensureInitialized()
  -> bootstrapStores()
  -> runtime.connectEvents()
```

迁移时不要把 `bootstrapStores()` 改成阻塞式串行加载。当前设计允许部分 store 加载失败并通过提示降级，避免单个辅助接口失败导致整个控制台不可用。

## 路由设计

路由定义在 `frontend/src/router/index.ts`。

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | 登录页 | `meta.public` 和 `meta.focus`，不显示 AppShell |
| `/` | 重定向 | 默认到 `/dashboard` |
| `/dashboard` | 总览 | 当前运行态、快捷入口、模式状态 |
| `/display/:target` | 显控页 | 大屏左/右、TV 左/右窗口控制 |
| `/ppt-focus/:windowId` | PPT 专注控制 | 只渲染当前窗口 PPT 控制，不显示外壳 |
| `/sources` | 媒体源 | 上传、网页源、源列表和筛选 |
| `/background-audio` | 背景音乐 | 音频播放列表和后台播放控制 |
| `/scenarios` | 场景 | 场景保存、激活、置顶、删除 |
| `/settings` | 设置 | 显示器、设备、系统相关控制 |
| `/about` | 兼容重定向 | 重定向到设置页 |

全局 guard 行为：

| 场景 | 行为 |
| --- | --- |
| 未初始化 | 调用 `auth.ensureInitialized()` |
| 未登录访问私有页 | 重定向 `/login?redirect=<原路径>` |
| 已登录访问 `/login` | 重定向 `/dashboard` |
| 每次跳转后 | 按 i18n 设置 `document.title` |

迁移到目标项目时，如果已有统一登录系统，可以替换 `auth` store 的认证来源，但应保留 401 全局拦截、跳转回原页面和 SSE 断连逻辑。

## API 客户端

核心文件：`frontend/src/services/api.ts`。

| 能力 | 当前实现 |
| --- | --- |
| 后端地址解析 | 开发模式优先相对路径，生产可用 `VITE_BACKEND_TARGET`，否则当前 host + 8000 |
| Cookie 会话 | 所有请求 `credentials: include` |
| CSRF | unsafe method 从 `csrftoken` cookie 读取并发送 `X-CSRFToken` |
| 超时 | JSON 请求默认 10 秒超时 |
| JSON 解析 | 仅按 JSON 解析，错误体也尽量解析 `detail/code` |
| 401 | 抛出 `UnauthorizedError` 并触发全局 handler |
| 上传 | 使用 XHR 支持进度回调，仍携带 cookie 和 CSRF |

关键类型集中在 `api.ts`，包括 `MediaSourceItem`、`SessionSnapshot`、`BackgroundAudioStateSnapshot`、`RuntimeSnapshot`、`ScenarioItem`、`DisplayTargetItem`、`DeviceItem`、`PptResourceItem`、`AuthUser`。

迁移时建议先复制类型和方法签名，再调整请求实现。这样页面和 store 不需要同时大改。

## 状态管理

Pinia stores 是前端领域边界，迁移时应优先保留。

| Store | 文件 | 责任 |
| --- | --- | --- |
| auth | `frontend/src/stores/auth.ts` | 当前用户、初始化、登录、登出、本地清理 |
| runtime | `frontend/src/stores/runtime.ts` | 大屏模式、系统音量、SSE 连接和重连 |
| sessions | `frontend/src/stores/sessions.ts` | 四窗口会话快照、打开/控制/导航/关闭动作 |
| sources | `frontend/src/stores/sources.ts` | 媒体源列表、分类、搜索、上传、删除 |
| displays | `frontend/src/stores/displays.ts` | 显示器列表和窗口显示目标选择 |
| devices | `frontend/src/stores/devices.ts` | 拼接屏和 TV TCP 指令状态 |
| backgroundAudio | `frontend/src/stores/backgroundAudio.ts` | 背景音乐状态、播放列表、音量、循环 |
| scenarios | `frontend/src/stores/scenarios.ts` | 场景列表、保存、激活、置顶、删除 |

`runtime.connectEvents()` 打开 `/api/events/`，接收 `playback_state` 后把 `sessions` 和 `background_audio` 分发到对应 store。

`sessions.applyRemoteSessions()` 使用 `last_updated_at` 比较，避免较旧的 REST/SSE 帧覆盖用户刚刚触发的本地更新。迁移时不要删除这个合并逻辑，否则高频播放状态回写会造成 UI 回跳。

`bootstrapStores()` 使用 `Promise.allSettled()` 并发加载 runtime、system volume、background audio、sessions、sources、scenarios、devices、displays。任一接口失败只提示，不阻断其他 store。迁移时如果目标项目有全局 loading，应仍然允许非核心模块失败降级，尤其是设备 TCP、MediaMTX 状态和系统音量。

## 页面模块

当前页面位于 `frontend/src/features/`。

| 模块 | 重点组件 | 迁移说明 |
| --- | --- | --- |
| dashboard | 总览页 | 汇总运行态，不应直接发复杂播控命令 |
| display | `DisplayControlView.vue`, `PlaybackControl.vue`, `SourcePicker.vue` | 四窗口播控核心，迁移风险最高 |
| sources | 媒体源管理 | 需保留上传进度、临时源、PPT 后端选择 |
| background-audio | 背景音乐 | 音频不进入四窗口，走独立后台播放器 |
| scenarios | 场景 | 需保留 tri-state 语义，不要把未设置误判为空 |
| settings | 显示器和设备 | 显示器选择当前不是实时 reposition，UI 文案需说明 |
| ppt-focus | PPT 专注控制 | 应继续使用 focus route，方便现场大按钮操作 |

`DisplayControlView.vue` 根据 `:target` 解析窗口目标。

| target | window_id | 业务含义 |
| --- | --- | --- |
| `big-left` | 1 | 大屏左 |
| `big-right` | 2 | 大屏右，仅 double 模式可用 |
| `tv-left` | 3 | TV 左 |
| `tv-right` | 4 | TV 右 |

`PlaybackControl.vue` 按源类型分支。

| 类型 | 控制能力 |
| --- | --- |
| PPT | 后端切换、上一页、下一页、跳页、当前页媒体控制、专注模式 |
| video | 播放、暂停、停止、循环、seek、音量、静音 |
| image | 展示和关闭，通常无音量和 seek |
| web | 展示 URL 和关闭，播放器端由 QWebEngine 处理页面 |
| stream | 直播状态、URL、关闭，通常无 seek |

PPT 后端切换需要确认，成功后会重开当前 PPT 并尽量回到原页。迁移时不能把后端切换做成纯前端状态，它必须调用后端 `switch_ppt_backend()`。

## Fluent 视觉体系

| 文件 | 责任 |
| --- | --- |
| `frontend/src/styles/tokens.css` | 生成的 Fluent 2 CSS custom properties |
| `frontend/scripts/generate-fluent-tokens.mjs` | token 生成脚本 |
| `frontend/src/design-system/theme/naiveTheme.ts` | Naive UI theme overrides |
| `frontend/src/design-system/theme/applyTheme.ts` | 将 `@fluentui/tokens` Theme 写入 CSS 变量的工具 |
| `frontend/src/composables/useTheme.ts` | light/dark/system 主题持久化和 `<html data-theme>` 切换 |
| `frontend/src/design-system/icons.ts` | Fluent 图标映射 |

`tokens.css` 不应手工编辑，应通过 `npm --prefix frontend run gen:fluent-tokens` 重新生成。业务组件样式应优先使用 token 变量。

迁移到标准 Fluent 组件的建议顺序：

| 顺序 | 动作 | 目的 |
| --- | --- | --- |
| 1 | 保留 `api.ts` 类型和 Pinia stores | 锁定业务契约 |
| 2 | 保留路由和页面信息架构 | 避免现场操作流变化 |
| 3 | 建立目标 Fluent 组件适配层 | 降低一次性替换风险 |
| 4 | 从 AppShell、按钮、表单、弹窗开始替换 | 优先替换低业务风险组件 |
| 5 | 最后替换 Display/PPT 控制组件 | 保留复杂交互稳定性 |

如果目标项目已有 Fluent Design System，建议把当前 `frontend/src/design-system/` 改造成桥接层，而不是让业务组件直接依赖两个组件库。

## 响应式和可访问性

`frontend/src/layouts/AppShell.vue` 已包含 compact 底部导航、medium/expanded rail、large+ drawer、skip link、`main` landmark、滚动顶栏状态和 focus route。`App.vue` 初始化 reduced motion。

迁移时应保留移动端现场操作体验。显控页常在手机、平板或触控屏上使用，不能只按桌面后台管理系统设计。

## 前端迁移风险

| 风险 | 影响 | 建议 |
| --- | --- | --- |
| 把播放器状态当成本地乐观状态 | SSE 回写后 UI 回跳或错误 | 以后端快照为准，保留 `last_updated_at` 合并 |
| 改变 source type 枚举 | 后端无法打开或 UI 分支错误 | 保留 `ppt/video/audio/image/web/srt_stream/rtsp_stream/custom_stream` |
| 把音频源放进四窗口 | 后端会拒绝或现场无声 | 音频只走背景音乐 store |
| 删除 CSRF/cookie 逻辑 | 登录态失效或 unsafe method 403 | 保留 `credentials` 和 `X-CSRFToken` |
| 把 `VITE_BACKEND_TARGET` 固化 | 局域网访问失败 | 继续支持相对路径和 env override |
| 将显示器选择包装成实时切换 | 用户误以为立即生效 | 后端/播放器未支持热 reposition 前需明确说明 |
| 用单一 PPT 后端替代选择 | 现场兼容性下降 | 保留源级和会话级 `ppt_backend` |

## 前端验收清单

| 项 | 验收标准 |
| --- | --- |
| 登录 | 未登录访问私有页跳登录，登录后回原路径 |
| 初始加载 | 任一非核心接口失败时控制台仍可进入 |
| SSE | 播放器状态变化 1 秒内反映到页面 |
| 播控 | 四个窗口均可打开、关闭、播放、暂停对应支持类型 |
| PPT | 后端切换、跳页、媒体控制、专注模式可用 |
| 背景音乐 | 音频源加入播放列表，不占用四窗口 |
| 主题 | light/dark/system 可切换并持久化 |
| 移动端 | 显控页可在窄屏完成源选择和控制 |
| 构建 | `npm --prefix frontend run typecheck` 和 `npm --prefix frontend run build` 通过 |
