# Quickstart: 开发验证与三端联调

**Status**: 仅规划；没有新.NET/Electron/Capacitor工程或包。当前可运行检查与未来命令分开列出，不自动授权启动真实设备/Office。

## 当前文档检查

在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe .specify\scripts\python\validate_specs.py --specs-dir specs
git diff --check
```

本地feature指向003、Git分支main；新未跟踪文档另查链接、代码围栏、空白和需求编号。

## 已有代码的参考测试

仅在隔离测试数据下执行，与后续实际改动相关时选择；本轮不重复运行无关完整构建：

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest tests/ -q --tb=short
pnpm --prefix frontend test
pnpm --prefix frontend run typecheck
pnpm --prefix frontend run build
```

旧规范002的未完成实机项是风险参考，不是本次必须先做现场维护的前提，也不能当作已验证事实。

## 实施后开发入口

以下项目/scripts目前不存在，是后续tasks需要交付的命令约定：

```powershell
dotnet restore runtime-dotnet/ScpCv.sln --locked-mode
dotnet build runtime-dotnet/ScpCv.sln -c Release --no-restore
dotnet test runtime-dotnet/ScpCv.sln -c Release --no-build --filter "Category!=Physical"
dotnet run --project runtime-dotnet/src/ScpCv.ControlHost -- --SafetyMode=Simulation --urls=http://127.0.0.1:18000 --DataRoot=.validation/dotnet
```

预期：单独测试目录、假Worker/Office/设备，无真实输出/电源动作；新数据初始化不依赖旧库。已有目录不兼容时明确报错，不自动清空。

前端构建入口（未来脚本）：

```powershell
pnpm --prefix frontend run build:web
pnpm --prefix frontend run build:app
pnpm --prefix frontend run build:electron
pnpm --prefix frontend exec cap sync android
```

Android工程在cap sync后用匹配SDK/Gradle构建开发APK，安装到测试设备；Windows运行实际打包Electron应用，不能只启动Vite网页算通过。精确打包工具版本随锁文件确定，不要求商店签发/自动更新服务。

常规本地资源包连接受设备信任证书的HTTPS测试后端，配置精确CORS/CSRF客户端origin与受控Cookie策略；网页HTTP/Android调试HTTP见[客户端合同](./contracts/frontend-clients.md)。不能把HTTP模拟后端命令直接当成常规原生包的完整认证验证。

## 测试范围 Q1–Q11

| 编号 | 内容 | 判据 |
| --- | --- | --- |
| Q1 三端共享功能 | Web、Windows Electron、Android Capacitor连接同一测试主机，登录/媒体/显控/场景/音频 | 同一页面源码/DTO，核心业务结果一致；不止空壳启动 |
| Q2 会话与SSE | 三端csrf/login/me/SSE/改密/登出；401、跨源、同毫秒逆序、A→B→A、切主机、10次断连/前后台 | Cookie会话一致；CSRF有效；过期帧丢弃；单连接恢复全量状态，无离线重放 |
| Q3 业务规则 | 四窗、single/double静音、全部媒体能力、三态/resume/capture、设备失败 | 保持既有语义；不假报成功，不将Android文件路径当主机路径 |
| Q4 可靠命令 | 100次执行前崩溃、1000次音频并发、100次ACK丢失；旧token/epoch、假身份、组停止后重连 | 保留有效命令、不误删、相对动作不盲重放、停止闩锁有效 |
| Q5 Office/PDF | 单槽竞争/摘要过期/缺PDF/reset；重复NEXT、过期子操作、超时inflight、用户Office共存 | 动态<=1、PDF不误升级/重置，未释放不建新Host，不误杀 |
| Q6 网页预热 | 两健康页面50次切换、脚本/滚动/登录，跨Worker与renderer故障 | 健康实例复用/无新增导航；故障如实失效；不跨进程搬DOM |
| Q7 媒体/性能 | 视频音频格式/seek/loop、SRT/RTSP自动发现、10分钟预热；普通指令/热切换计时 | 单位正确；1000指令p95开始<=1s，100热切换p95可见<=300ms，冷打开单列 |
| Q8 启停/音频 | 20次正常启停、10次故障退出；旧/重复Finished；关闭客户端 | 音频不跳项/漏音，自有资源可清理；客户端关闭不停止播放主机 |
| Q9 开发数据/Git | 全新测试目录初始化、密码/模型fixture、不兼容旧数据路径 | 不依赖旧库，不自动删除现有数据；代码恢复说明不承诺数据恢复 |
| Q10 Windows运行 | 开发多屏/DPI/负坐标/窗口焦点、Office/VLC、60分钟混合播放 | 实际画面正确，无未处置崩溃/静默停播/不可达资源持续增长 |
| Q11 原生壳/UI安全 | 实际APK/Electron包，路由刷新/返回、主题/Tailwind、文件上传/下载、旧WebView、外链/权限、debug配置隔离 | 三端无资源404/错误页面；返回和文件功能正确；不暴露任意系统能力；本地常规包不误带远程server.url/cleartext |

需在最早开发切片完成Q2的真实包Cookie/SSE实验和Q5的Office互操作风险实验。若本地包因设备第三方Cookie策略失败，明确不兼容原因；debug同源远程UI通过不能抵扣本地包验收。不通过时改对应设计，不用关闭安全配置伪造成功。

## 数据、设备与结果记录

- Git只恢复已跟踪源码/规范/锁文件，未跟踪数据库/媒体独立保存。不需要数据逆迁移/生产切流演练，也不因“Git回退”自动清空数据库。
- 触及显示器/音响/设备的测试仅在用户同意的开发环境运行；模拟单元测试不默认连接真实设备。
- 记录commit、平台/运行时版本、测试素材摘要、Q编号、样本数、日志和未执行原因。Win32/Office实际结果不能只靠mock确认。
- 60分钟固定预热集合下观察对象/句柄释放与内存趋势；不把GC单点波动当泄漏，也不掩盖持续不可达对象增长。
- 文档检查、软件测试、真实客户端包测试、Windows播放测试分别报告；没有现场维护阶段或15分钟回退SLA。

## 本轮修订记录

确认Android技术选择1项；更新spec的澄清、用户场景、需求、成功标准与假设；同步计划、研究、数据模型、HTTP/SSE及客户端合同，删除不需要的生产迁移设计要求。

规范质量清单按新范围重新自查（由speckit-specify更新陈旧迁移条目）结果16/16；本轮全仓Spec Kit、13份文档的本地链接/代码围栏/空白/需求引用检查、git diff --check全部通过；30项FR、10项SC、1条已确认问答，无残留旧迁移阶段或工具实体。

本次澄清覆盖结论：客户端平台、开发范围、版本恢复边界已解决；核心领域、交互、可靠性、安全、外部接口与验收边界明确。未执行依赖安装、代码实现、打包、软件完整测试或任何数据库/设备操作；未生成tasks、未创建Git提交。
