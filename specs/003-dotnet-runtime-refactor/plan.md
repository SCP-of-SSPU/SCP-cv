# Implementation Plan: 共享多端控制台与.NET播控运行时

**Branch**: `main` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)
**Status**: 依据用户澄清修订的Phase 0/1设计；只改规划，不实施、不打包、不操作设备。

## Summary

项目处于快速迭代期，没有现场维护要求。用Git管理代码演进与恢复，不建设生产数据转换、双栈长期兼容、逆迁移或现场切流流程。保留播控核心行为与REST/SSE合同，允许重整前端样式与平台适配。

共享前端：Vue 3 + Tailwind CSS 4 + Vue Router + Pinia + Vite。网页直接使用；Windows客户端由Electron承载；Android客户端由用户确认的Capacitor承载。三端只有一套业务页面、store和服务接口。客户端与Windows播放执行端是不同角色，Electron不替代WPF播放器，Android不运行Office/多屏运行时。

后端保持用户选定方案：ASP.NET Core ControlHost、SQLite/EF Core、持久命令队列、Named Pipe，以及交互桌面Supervisor管理的PlayerWorker ×4、AudioWorker ×1、PowerPointHost ×1和MediaMTX。

## Technical Context

**Language/Version**: C#/.NET 10 LTS；Vue 3/TypeScript、Tailwind CSS 4、现有Router/Pinia/Vite；Electron稳定版、Capacitor 8。实施时以锁文件固定验证过的版本，本次不安装或升级。

**Primary Dependencies**: ASP.NET Core/EF Core SQLite 10、WPF、LibVLCSharp/libVLC、WebView2、Windows.Data.Pdf、PowerPoint COM、MediaMTX；前端加`@tailwindcss/vite`及Electron/Capacitor构建依赖。保留可复用Naive UI交互组件及Fluent tokens，Tailwind不替代有状态组件或业务逻辑。

**Storage**: 新后端在独立`data/dotnet/control.db`初始化，开发测试使用独立目录/fixture；原`db.sqlite3`和媒体不被自动删除或原地接管。仅ControlHost写业务状态；EF schema migrations属于新栈内部建表/演进，不是旧业务数据迁移工程。

**Testing**: xUnit/合同与SQLite测试、已有Python行为样例、共享Vue测试、浏览器/Electron/Android实际运行测试、Windows播放测试。测试缺硬件时报告未执行，不要求先完成现场维护演练。

**Target Platform**: 控制端=Web + Windows Electron + Android Capacitor；Linux/macOS原生客户端、iOS和商店发布不在范围。播放端=受支持Windows x64交互桌面；Windows 10按实际SKU/build核验。Tailwind4要求Chrome/WebView>=111、Firefox>=128、Safari>=16.4；Android不能只看OS版本。

**Project Type**: 单Windows播放主机 + 可在其他设备运行的控制端。多控制端不是多播放节点/分布式调度。

**Performance Goals**: 开发机普通控制1000样本p95开始<=1s、健康热切换100样本p95可见<=300ms；60分钟混合播放稳定性测试；三端各10次断连/恢复。均为待验证目标。

**Constraints**: 不改变四窗/音频/场景/单COM-PDF回退语义；不丢有效命令、不假报播放；不跨线程/进程迁移原生活对象；安全隔离与资源清理保留。外部HTTP合同唯一根仍为`docs/openapi.yaml`。

**Scale/Scope**: 四输出、一背景音频、一自有动态放映；不引入云服务、消息代理、版本数据同步、自动更新平台或完整Django admin复制品。

## Constitution Check

现行宪章1.0.0仍限定Python/Django，本次不擅自改写。用户已明确选择目标技术栈和开发期范围；后续实现前通过speckit-constitution将治理文字同步为目标栈，不额外制造生产审批/切流阶段。见[governance.md](./governance.md)。

| 原则 | Phase 0 / Phase 1复核 |
| --- | --- |
| 现场安全优先 | 当前没有现场维护；保留操作设备时的安全行为、授权、日志、清理测试，不安排停播窗口或生产回滚 |
| 规范可追溯 | 同一003功能，澄清已入spec；需求→设计→验证映射，后续tasks另生成 |
| 可验证交付 | 按功能小步测试，三端与真实Windows播放各有用例；无测试结论冒充实现完成 |
| 集成边界 | 共享前端与原生壳分开，HTTP/SSE与本机Named Pipe分开，DTO保持兼容 |
| 简单可维护 | 删除不需要的数据搬迁/双轨/逆迁移模块，保留必要命令与媒体所有权 |
| 固定旧技术栈 | 设计变更理由明确；正式实现需同步宪章，不把此规划说成现行宪章已经修改 |

## Project Structure

### Documentation (this feature)

`spec.md`、`plan.md`、`baseline.md`、`research.md`、`data-model.md`、`governance.md`、`quickstart.md`、`checklists/requirements.md`及`contracts/`。原[migration.md](./migration.md)文件保留链接，但已改为简短的开发迭代/Git说明，不再定义复杂迁移。

### Source Code (repository root)

以下为目标目录，不代表已经创建：

```text
frontend/
├── src/                      # 三端共享pages/router/stores/services/styles
│   └── platform/             # 连接配置、文件/返回/生命周期薄适配
├── electron/                 # Windows main/preload，受限原生能力
├── capacitor.config.ts
├── android/                  # Capacitor生成/维护的Android工程
└── vite.config.ts            # Web/app构建模式，同一份源码
runtime-dotnet/
├── ScpCv.sln
├── global.json
├── Directory.Build.props
├── Directory.Packages.props
├── src/
│   ├── ScpCv.Domain/
│   ├── ScpCv.Contracts/
│   ├── ScpCv.Infrastructure/  # EF/媒体/配置/日志；无迁移专用工具
│   ├── ScpCv.ControlHost/
│   ├── ScpCv.Supervisor/
│   ├── ScpCv.PlayerWorker/    # 一个二进制启动4实例
│   ├── ScpCv.AudioWorker/
│   └── ScpCv.PowerPointHost/
└── tests/                    # Domain/Contract/Integration/Windows
scp_cv/ + tests/              # 现有实现，完成替换后按正常提交清理
tools/third_party/
docs/openapi.yaml
```

**Structure Decision**: Domain无UI/ORM/COM；Worker不引用EF、不写库。共享Vue不直接引用Node/AndroidAPI；平台差异封装在薄适配层。无需维护web/windows/android三份业务页面；旧代码由Git保留历史，不要求长期同目录双栈可运行。

## Target Architecture

```text
共享 Vue 3 + Tailwind 4 + Vue Router + Pinia + Vite
                 ├── Web浏览器
                 ├── Electron → Windows控制客户端
                 └── Capacitor → Android控制客户端
                           │ REST + SSE
                           ▼
Windows播放主机：ASP.NET Core ControlHost
                 ├── 认证/媒体/场景/设备服务
                 ├── EF Core + SQLite + 持久命令队列
                 └── Named Pipe（本机，不给客户端直接访问）
                           │
交互桌面 Supervisor
    ├── PlayerWorker ×4：WPF / LibVLCSharp / WebView2 / Windows.Data.Pdf
    ├── AudioWorker ×1
    ├── PowerPointHost ×1：独立STA/COM
    └── MediaMTX
```

Electron/Capacitor只是控制台。客户端可以与主机同机或远程，不默认携带/启动ControlHost或Office；关闭客户端仅关闭自己的连接，不关闭主机。需要停止主机时走已有显式系统命令及权限。

## Shared Frontend Design

- Vite接入Tailwind4官方插件；现有CSS变量/Fluent tokens仍为颜色等设计值真源，通过`@theme inline`映射。初期不全局开启Preflight，避免重置Naive UI；保留必要组件，不同时改业务规则。
- Web保持history路由并配置服务端fallback；打包本地资源使用hash路由，路由记录/守卫/页面完全共享。
- Web使用相对API与开发Vite代理；Electron/Capacitor打包同一Vue资源，提供连接主机页。端口8000仍为兼容HTTP开发入口，打包客户端常规连接使用受信HTTPS端点，具体见客户端合同。
- Cookie登录与SSE必须由同一浏览器/WebView会话完成；跨源CSRF token从现有JSON响应取得，不读取另一个域的document.cookie。不同时启用原生HTTP补丁和浏览器EventSource造成两套Cookie。
- Electron开启contextIsolation/sandbox/webSecurity、关闭nodeIntegration；Capacitor仅开放必要插件。网页源在PlayerWorker WebView2播放，不在有原生权限的控制壳内当受信UI加载。
- Android至少API24且实际WebView>=111；返回键、安全区域、键盘、文件选择、退出/回前台SSE重连都有测试。更旧设备明确提示，不假称支持。
- 局域网HTTP调试使用明确的debug同源远程UI模式，不把Capacitor的server.url/cleartext/allowNavigation开发选项默认带入常规本地资源包；不关闭webSecurity或忽略证书错误解决登录。
- 不承诺离线控制、跨客户端共享登录或后台永久SSE。断线禁用命令，恢复拉全量状态，不自动重放离线操作。

完整约束：[frontend-clients.md](./contracts/frontend-clients.md)。

## Runtime Design Kept

1. ControlHost校验权限/能力，事务内入队与更新兼容意图，提交后Wake。
2. Worker仅在armed组状态领取，持command/token/epoch/source_generation执行；重连不解除停止闩锁。
3. 实际结果经ControlHost落库并推SSE；新内容A→B→A、迟到状态与毫秒时间戳竞争有防护。
4. ACK丢失可重传同结果；不确定NEXT/动画/设备toggle不得盲重试，不承诺exactly-once。
5. Office唯一STA/放映所有权，子操作独立去重；同步导出超时不释放inflight槽。持续独占无法证明时不Quit/强杀用户Office。
6. 健康网页预热只在所属Worker内保活；跨Worker共享文件而非DOM/COM/VLC对象。PDF摘要匹配、回退不自动升级、音频独立。
7. 默认保留组级协作停止及正常运行的故障恢复；这属于产品可靠性，不是被用户取消的版本迁移/回滚工程。

细节保持在[IPC](./contracts/runtime-ipc.md)与[媒体生命周期](./contracts/media-lifecycle.md)，无需为增加客户端重新设计播放内核。

## Phase 0: Research Outcomes

新增客户端相关调研收敛为Tailwind/Vite接入、Windows Electron/Android Capacitor分工、资源与路由复用、浏览器会话统一及HTTPS/debug边界。旧数据转换方案已取消；原生媒体调研保留适用部分，见[research.md](./research.md)。

## Phase 1: Deliverables

- [data-model.md](./data-model.md)：领域/可靠命令/资源模型和控制端连接配置，不含旧数据迁移模型。
- [HTTP/SSE合同](./contracts/http-sse-compatibility.md)：业务API与会话语义。
- [三端客户端合同](./contracts/frontend-clients.md)：共享资源、权限、跨源会话、打包与恢复。
- [migration.md](./migration.md)：少量开发/Git约定。
- [quickstart.md](./quickstart.md)：当前可运行检查、未来构建命令、开发验证。
- [governance.md](./governance.md)：将现行栈约束同步为新方案的最小事项。

## Lightweight Development Order

1. **骨架与风险验证**：规范/宪章同步；.NET最小服务与三端共享前端；先跑通三端登录/SSE、Office HWND/DPI关键实验。
2. **逐功能完成**：媒体/场景/队列/播放适配按纵向切片实现，Tailwind样式与壳层接入共享功能，每片带回归。
3. **联调与收尾**：Windows/Android包和网页实测、开发机播放验证；清理已替代旧代码并提交Git。

只是一张开发顺序表，不安排停播、生产切换、逆迁移、双轨保持周期或回退SLA。详细tasks由后续speckit-tasks生成。本次没有提交/切分支/打包。

## Requirement Traceability

| 需求 | 设计 | 验证 |
| --- | --- | --- |
| FR-001–003 | 共享前端/HTTP/新数据初始化 | SC-001/008；Q1/Q2/Q9 |
| FR-004–006 | 领域模式/场景/音频 | SC-001/009；Q3/Q8 |
| FR-007–010 | IPC/执行凭据/状态 | SC-002/003/006；Q4 |
| FR-011–014 | 能力/Office/PDF | SC-004；Q5 |
| FR-015–017 | Worker预热/流 | SC-005/006；Q6/Q7 |
| FR-018–021 | 开发启停/运行时 | SC-007/009；Q8/Q10 |
| FR-022–023 | Git与非破坏性开发目录 | SC-008；Q9 |
| FR-024、FR-028–030 | 三端壳/权限/连接恢复/文件 | SC-001/010；Q1/Q2/Q11 |
| FR-025–027 | 日志/规范/验证 | SC-007/010；Q4/Q10 |

## Complexity Tracking

| 需要说明的差异 | 理由 | 简化边界 |
| --- | --- | --- |
| 固定Python/Django栈改.NET与多端前端 | 用户明确指定 | 实现前同步宪章；不新增生产审批链 |
| Windows/Android两种原生壳 | Electron不能运行Android，用户已同意Capacitor | 只共享一套Vue，薄平台适配，不复制业务 |
| 原生多宿主与可靠命令 | 保留播放核心语义和线程/进程安全 | 不扩展到分布式运行时或外部消息代理 |

## Completion Record

澄清问答1项已接受；沿用003目录和main分支。已执行项目路径前置检查与setup_plan.py；没有注册clarify/specify/plan前后hook。规范质量检查和最终静态验证见quickstart。没有生成tasks、修改业务代码、安装依赖或操作数据库/设备。
