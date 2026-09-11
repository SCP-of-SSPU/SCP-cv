# 工作站实验手册

用途：在具备四屏、Office、VLC 素材、MediaMTX 与真实音频的工作站上，一次性收口 T050/T115/T116/T128/T129。

## 0.1 实际部署方式（2026-09-11，工作站 `d2` / 192.168.5.192）

工作站上**没有安装 .NET SDK 或运行时**（`HKLM:\SOFTWARE\dotnet\Setup\InstalledVersions` 缺失、`Program Files\dotnet` 不存在、PATH 无 `dotnet`），
因此不采用“在工作站构建”，而是从开发机做**自包含发布**再拷贝过去：

```powershell
# 开发机
dotnet publish runtime-dotnet/src/ScpCv.ControlHost/ScpCv.ControlHost.csproj  -c Release -r win-x64 --self-contained true -o .validation\ws-publish\ScpCv.ControlHost
# Supervisor / PlayerWorker / AudioWorker / PowerPointHost 同理
tar.exe -cf .validation\ws-publish.tar -C .validation\ws-publish .
scp .validation\ws-publish.tar d2:D:/SCP-cv/.validation/runtime-portable.tar
# 工作站
tar.exe -xf D:\SCP-cv\.validation\runtime-portable.tar -C D:\SCP-cv\.validation\runtime-portable
```

产物约 1.1 GB / 3469 文件，局域网传输约 12 秒。运行目录 `.validation/runtime-portable` 不在版本控制内。

若后续要直接在工作站构建，需要先安装 .NET 10 SDK；当前 `D:\SCP-cv` 只做了用户级发布产物部署。

## 0.2 工作站环境要点

- **PowerShell 5.1 + ANSI 代码页 936**：`*.ps1` 必须带 UTF-8 BOM，否则中文注释被按 GBK 解析、字符串未闭合导致 `ParserError`。仓库内 `runtime.ps1`、`run-headless.ps1`、`benchmark-commands.ps1` 已加 BOM。
- PowerShell 5.1 的 .NET Framework 没有 `String.Contains(string, StringComparison)` 重载，脚本内统一用 `IndexOf(..., StringComparison)`。
- `schtasks /tr` 上限 261 字符，所以无头启动先用 `-Detach` 生成 `headless-launch.ps1`，任务只指向该启动器。
- `CrossSiteCookies=true` 会下发 `Secure` 会话 Cookie，HTTP 下不会被回传；`run-headless.ps1` 现在按监听协议自动选择（https→true，http→false）。
- SSH 会话关闭会回收会话内的进程树，因此无头启动经一次性计划任务（`ScpCvHeadless-<hash>`）分离；重复触发由幂等守卫拦截。

## 0. 前置条件

- Windows x64 交互桌面，四个显示输出已接线并被系统识别；显示器名可在 `/api/displays/` 查看。
- 已构建运行时：`dotnet build runtime-dotnet/ScpCv.sln`。
- `tools/third_party/mediamtx/mediamtx.exe` 存在。
- 已准备真实素材：需要放映的 `.pptx`/`.pdf`、一段视频、一个 SRT/RTSP 流、一个网页源、一个音频文件。
- 客户端证书已信任（Web/Electron 直接访问 `https://<host>:18443` 不报证书错误）。

## 1. 启动 Hardware ControlHost

推荐用无头脚本启动（隐藏控制台窗口、日志落盘、可选一并编排 Worker）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File runtime-dotnet\scripts\run-headless.ps1 `
  -Detach `
  -SafetyMode Hardware `
  -DataRoot 'D:\SCP-cv\.validation\t129-workstation' `
  -ListenUrls 'https://localhost:18443' `
  -RuntimeRoot 'D:\SCP-cv\.validation\runtime-portable' `
  -SupervisorExecutable 'D:\SCP-cv\runtime-dotnet\src\ScpCv.Supervisor\bin\Debug\net10.0-windows10.0.19041.0\ScpCv.Supervisor.exe' `
  -MediaMtxPath 'D:\SCP-cv\tools\third_party\mediamtx\mediamtx.exe' `
  -DevelopmentPassword '<开发账号口令>' `
  -StartWorkers
```

说明：

- `-Detach` 经一次性计划任务启动，SSH 关闭后 `ControlHost` 继续运行；不加 `-Detach` 则前台运行。
- 停止（不需要口令）：`run-headless.ps1 -Stop -DataRoot 'D:\SCP-cv\.validation\t129-workstation'`，会结束 ControlHost 并清理计划任务。
- `-StartWorkers` 会通过 `/api/system/restart/` 拉起 4 个 PlayerWorker / AudioWorker / PowerPointHost / MediaMTX。
  4 个播放窗口是无边框全屏窗口，**会覆盖四块屏幕**，请在真正开始实验时再加。
- HTTPS 监听需要 Kestrel 证书；工作站上没有 .NET 开发证书，首次请先用 `-ListenUrls http://localhost:18443` 做冒烟，再配置正式证书。

## 1.1 2026-09-11 工作站实测结果

`d2` 上以 `-Detach -SafetyMode Hardware -ListenUrls http://localhost:18443` 启动后：

- `/health/ready` → 200；服务根返回 `{"service":"SCP-cv ControlHost","status":"ready","safety_mode":"hardware","database":"control.db"}`。
- `/api/displays/` → 4 块真实显示器，全部 `3840×2160`，坐标 `x=0 / 3840 / 7680 / 11520`，`DISPLAY1` 为主屏。
- `/api/volume/` → `level=51, muted=false, system_synced=true, backend=windows_core_audio`。
- `/api/runtime/` → `big_screen_mode=single, volume_level=100, muted_windows=[2,3,4]`。

注意：从 SSH 会话里用 `[System.Windows.Forms.Screen]::AllScreens` 只会看到 1 块 `WinDisc 1024x768`——SSH 会话在 session 0，
看不到交互桌面的真实显示拓扑。硬件探针必须在交互会话内运行的 ControlHost 上取（计划任务方式天然满足）。

本次只验证了 Hardware ControlHost 与硬件探针；四屏播放、Office、VLC、MediaMTX、音频的 60 分钟混合测试仍未执行。

等价的手动方式：

```powershell
$root = 'E:\Projects\SSPU\SCP-cv'
$data = "$root\.validation\t129-workstation-$(Get-Date -Format yyyyMMdd-HHmm)"
& "$root\runtime-dotnet\src\ScpCv.ControlHost\bin\Debug\net10.0\ScpCv.ControlHost.exe" `
  --SafetyMode=Hardware `
  --urls=https://localhost:18443 `
  --DataRoot=$data `
  --Authentication:AllowedOrigins:0=https://localhost `
  --Authentication:CrossSiteCookies=true `
  --Authentication:DevelopmentAccount:Username=qa-admin `
  --Authentication:DevelopmentAccount:Password=<开发账号口令> `
  --Authentication:DevelopmentAccount:IsStaff=true `
  --Authentication:DevelopmentAccount:IsSuperuser=true `
  --Supervisor:ExecutablePath=$root\runtime-dotnet\src\ScpCv.Supervisor\bin\Debug\net10.0-windows10.0.19041.0\ScpCv.Supervisor.exe `
  --Supervisor:RuntimeRoot=$root\runtime-dotnet\src `
  --Supervisor:StatePath=$data\runtime-processes.json `
  --Supervisor:MediaMtxPath=$root\tools\third_party\mediamtx\mediamtx.exe
```

期望日志：`ControlHost initialized with safety mode Hardware`、`Now listening on: https://localhost:18443`。

## 2. 拉起全部 Worker（T116 前置）

```powershell
# 登录并取 CSRF
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$h = @{ Origin = 'https://localhost' }
$csrf = (Invoke-RestMethod https://localhost:18443/api/auth/csrf/ -WebSession $s -Headers $h).csrfToken
Invoke-RestMethod -Method Post https://localhost:18443/api/auth/login/ -WebSession $s -Headers $h `
  -ContentType application/json -Body (@{ username = 'qa-admin'; password = '<开发账号口令>' } | ConvertTo-Json)
$h['X-CSRFToken'] = $csrf

Invoke-RestMethod -Method Post https://localhost:18443/api/system/restart/ -WebSession $s -Headers $h
```

期望：`detail` 为“Supervisor restart 的全部 Worker 已就绪。”，且状态文件含 7 个角色。

> 注意：4 个 PlayerWorker 是无边框全屏窗口。若在开发机上误关任意一个窗口，会按 FR-018 触发整组协作停止；工作站上请把这些窗口放到各自的输出上并避免误操作。

## 3. T115 普通命令基准

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File runtime-dotnet\scripts\benchmark-commands.ps1 `
  -BaseUrl https://localhost:18443 `
  -DatabasePath $data\control.db `
  -Password '<开发账号口令>' `
  -Samples 1000 -Targets 1,2,3,4 -DelayMilliseconds 50 `
  -HardwareNote '四屏 1920x1080 + 本地千兆；无外部流' `
  -OutputPath docs\qa\003-performance-commands.md
```

判读：脚本自身的 `verdict` 为 `通过` 才算 SC-006 的普通命令一半；`测量无效` 时必须先解决折叠或 Worker 离线问题再重跑。

## 4. T115 健康热切换基准

准备两个可预热（`keep_alive`）的网页源 A/B，交替执行“打开 A / 打开 B”，记录每次发起到画面可见的时间，共 100 次，
取 p95 与可见判定依据（截图或录屏帧时间）；把样本追加到 `docs/qa/003-performance.md`。

判读：p95 ≤ 300 ms。

## 5. T116 60 分钟混合运行

按下面顺序铺排并连续运行 60 分钟，每 5 分钟记录一次：

- 四屏各自播放不同内容（视频 / 图片 / PDF / 网页），确认互不串台。
- 打开一个真实 PPT：确认进入 PowerPoint 模式；随后打开第二个 PPT：确认按策略转为 PDF 回退。
- 播放 SRT 与 RTSP 各一次，确认自动发现可用。
- 后台音频播放、切歌、自动下一首，确认音量/静音/循环保持。
- 设备控制（开/关机、切换）走真实 `192.168.5.x` 端点或注明未接线。

记录项：每次异常的时间点、ControlHost/Worker 日志、内存与句柄、残留进程、最终 `runtime-processes.json`。

## 6. T128 客户端关闭与主机存活

在三个客户端各做一次：登录 → 触发一次状态同步 → 关闭客户端 → 立即请求主机 `/health/ready`，期望仍为 200。
Web 端另需确认受保护下载在浏览器会话内返回 200 且字节与源文件一致，见 `003-client-matrix.md`。

## 7. 收尾

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File runtime-dotnet\scripts\runtime.ps1 -Action stop
Get-Process -Name 'ScpCv.*','mediamtx' -ErrorAction SilentlyContinue
```

期望：无 SCP-cv/MediaMTX 残留；Office 若无法证明所有权则按设计保留，不按名称强杀。

## 8. 证据回填

- `docs/qa/003-windows-runtime.md`：60 分钟结果与硬件条件。
- `docs/qa/003-performance.md`：1000/100 样本 p95。
- `docs/qa/003-client-matrix.md`：三端关闭与文件结果。
- `specs/003-dotnet-runtime-refactor/verification.md` 与 `tasks.md`：勾选 T115/T116/T129，再评估 T118。
