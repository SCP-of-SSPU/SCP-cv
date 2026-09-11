<#
.SYNOPSIS
  以无头方式运行 ControlHost（隐藏窗口 + 日志落盘），可选一并拉起受管 Worker。

.DESCRIPTION
  “无头”指不在交互桌面上弹出控制台窗口：ControlHost 以隐藏窗口启动，
  stdout/stderr 分别写入 DataRoot 下的 control-host.out.log / control-host.err.log。
  注意：PlayerWorker 的四块播放窗口本身就是播放输出，属于产品功能，不会被隐藏。
#>
[CmdletBinding(DefaultParameterSetName = 'Start')]
param(
    [Parameter(ParameterSetName = 'Stop')][switch]$Stop,
    [string]$RuntimeRoot = '',
    [string]$DataRoot = '',
    [string]$ListenUrls = 'https://localhost:18443',
    [string]$AllowedOrigins = 'https://localhost',
    [string]$ControlHostPath = '',
    [string]$MediaMtxPath = '',
    [string]$SupervisorExecutable = '',
    [string]$DevelopmentUsername = 'qa-admin',
    [string]$DevelopmentPassword = '',
    [switch]$StartWorkers,
    [switch]$Detach,
    [int]$ReadyTimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 没有 Invoke-WebRequest -SkipCertificateCheck；
# 仅当目标是本机 https（自签证书）时放宽校验回调，避免脚本在旧版 PowerShell 上直接失败。
$isHttps = $ListenUrls.TrimStart().StartsWith('https://', [StringComparison]::OrdinalIgnoreCase)
$supportsSkip = (Get-Command Invoke-WebRequest).Parameters.ContainsKey('SkipCertificateCheck')
if ($isHttps -and -not $supportsSkip) {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
}

function Invoke-ScpCvWeb {
    param([string]$Uri, [string]$Method = 'GET', $WebSession = $null, [hashtable]$Headers = $null, [string]$ContentType = '', [string]$Body = '')
    $splat = @{ Uri = $Uri; Method = $Method; UseBasicParsing = $true; TimeoutSec = 15 }
    if ($supportsSkip) { $splat['SkipCertificateCheck'] = $true }
    if ($WebSession) { $splat['WebSession'] = $WebSession }
    if ($Headers) { $splat['Headers'] = $Headers }
    if ($ContentType) { $splat['ContentType'] = $ContentType }
    if ($Body) { $splat['Body'] = $Body }
    return Invoke-WebRequest @splat
}

if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
    $RuntimeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\src')).Path
}
if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    throw '必须显式传入 -DataRoot，避免无头进程误用其他运行时的数据目录。'
}
$dataPath = [System.IO.Path]::GetFullPath($DataRoot)
New-Item -ItemType Directory -Force -Path $dataPath | Out-Null
$scriptLog = Join-Path $dataPath 'run-headless.log'

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $Message
    Write-Host $line
    # 分离启动时本进程没有控制台，日志必须同时落盘才能回看。
    Add-Content -LiteralPath $scriptLog -Value $line -Encoding UTF8
}

function Get-HeadlessControlHost {
    Get-CimInstance Win32_Process -Filter "Name='ScpCv.ControlHost.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($dataPath, [StringComparison]::OrdinalIgnoreCase) }
}

function Get-HeadlessTaskName {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($dataPath.ToLowerInvariant()))
    }
    finally { $sha.Dispose() }
    return 'ScpCvHeadless-' + (($hash[0..3] | ForEach-Object { $_.ToString('x2') }) -join '')
}

if ($Stop) {
    $targets = @(Get-HeadlessControlHost)
    if ($targets.Count -eq 0) {
        Write-Log "DataRoot 下没有运行中的 ControlHost：$dataPath"
    }
    foreach ($target in $targets) {
        Stop-Process -Id $target.ProcessId -Force
        Write-Log "已停止 ControlHost pid=$($target.ProcessId)"
    }
    $taskName = Get-HeadlessTaskName
    schtasks /delete /tn $taskName /f 2>$null | Out-Null
    Write-Log "已清理计划任务 $taskName"
    return
}

# -Detach：用一次性计划任务重新拉起自身。SSH 会话关闭会回收会话内的进程树，
# 计划任务实例不属于该进程树，因此 SSH 可以立刻返回而 ControlHost 继续运行。
# 任务保留用于后续手动运行；-Stop 会连同任务一起清理。
if ($Detach) {
    $parts = @(
        '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"'),
        '-RuntimeRoot', ('"' + $RuntimeRoot + '"'),
        '-DataRoot', ('"' + $dataPath + '"'),
        '-ListenUrls', ('"' + $ListenUrls + '"'),
        '-AllowedOrigins', ('"' + $AllowedOrigins + '"'),
        '-DevelopmentUsername', ('"' + $DevelopmentUsername + '"'),
        '-DevelopmentPassword', ('"' + $DevelopmentPassword + '"')
    )
    if (-not [string]::IsNullOrWhiteSpace($ControlHostPath)) { $parts += @('-ControlHostPath', ('"' + $ControlHostPath + '"')) }
    if (-not [string]::IsNullOrWhiteSpace($SupervisorExecutable)) { $parts += @('-SupervisorExecutable', ('"' + $SupervisorExecutable + '"')) }
    if (-not [string]::IsNullOrWhiteSpace($MediaMtxPath)) { $parts += @('-MediaMtxPath', ('"' + $MediaMtxPath + '"')) }
    if ($StartWorkers) { $parts += '-StartWorkers' }
    $parts += @('-ReadyTimeoutSeconds', $ReadyTimeoutSeconds)
    $action = 'powershell.exe -NoProfile ' + ($parts -join ' ')
    $taskName = Get-HeadlessTaskName
    schtasks /create /tn $taskName /tr $action /sc once /st 23:59 /f | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "创建计划任务 $taskName 失败。" }
    schtasks /run /tn $taskName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "运行计划任务 $taskName 失败。" }
    Write-Log "已通过计划任务分离启动：$taskName，日志：$scriptLog"
    return
}

# 幂等守卫：同一 DataRoot 已有 ControlHost 时不再重复启动（计划任务可能被再次触发）。
$running = @(Get-HeadlessControlHost)
if ($running.Count -gt 0) {
    Write-Log "DataRoot 下已有 ControlHost 运行（pid=$($running[0].ProcessId)），跳过启动。"
    return
}

if ([string]::IsNullOrWhiteSpace($ControlHostPath)) {
    $candidates = @(
        (Join-Path $RuntimeRoot 'ScpCv.ControlHost\bin\Debug\net10.0\ScpCv.ControlHost.exe')
        (Join-Path $RuntimeRoot 'ScpCv.ControlHost\bin\Release\net10.0\ScpCv.ControlHost.exe')
    )
    $exe = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $exe) {
        # 兼容自包含发布布局：任意深度的 ScpCv.ControlHost 目录下的可执行文件。
        $exe = Get-ChildItem -LiteralPath $RuntimeRoot -Filter 'ScpCv.ControlHost.exe' -Recurse -File -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName
    }
}
else {
    $exe = [System.IO.Path]::GetFullPath($ControlHostPath)
}
if ([string]::IsNullOrWhiteSpace($exe) -or -not (Test-Path -LiteralPath $exe)) {
    throw "未找到 ControlHost（RuntimeRoot=$RuntimeRoot）。先 dotnet build/publish，或用 -ControlHostPath 指定。"
}
$exe = [System.IO.Path]::GetFullPath($exe)
if ([string]::IsNullOrWhiteSpace($DevelopmentPassword)) {
    throw '必须传入 -DevelopmentPassword（或先在本机配置正式账号）。'
}

$outLog = Join-Path $dataPath 'control-host.out.log'
$errLog = Join-Path $dataPath 'control-host.err.log'

$arguments = @(
    '--urls=' + $ListenUrls
    '--DataRoot=' + $dataPath
    '--Authentication:AllowedOrigins:0=' + $AllowedOrigins
    '--Authentication:CrossSiteCookies=true'
    '--Authentication:DevelopmentAccount:Username=' + $DevelopmentUsername
    '--Authentication:DevelopmentAccount:Password=' + $DevelopmentPassword
    '--Authentication:DevelopmentAccount:IsStaff=true'
    '--Authentication:DevelopmentAccount:IsSuperuser=true'
)

if (-not [string]::IsNullOrWhiteSpace($SupervisorExecutable)) {
    $arguments += '--Supervisor:ExecutablePath=' + ([System.IO.Path]::GetFullPath($SupervisorExecutable))
    $arguments += '--Supervisor:RuntimeRoot=' + $RuntimeRoot
    $arguments += '--Supervisor:StatePath=' + (Join-Path $dataPath 'runtime-processes.json')
}
if (-not [string]::IsNullOrWhiteSpace($MediaMtxPath)) {
    $arguments += '--Supervisor:MediaMtxPath=' + ([System.IO.Path]::GetFullPath($MediaMtxPath))
}

$process = Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $outLog -RedirectStandardError $errLog
Write-Log "ControlHost 已无头启动 pid=$($process.Id)"
Write-Log "日志：$outLog"

$ready = $false
$deadline = [DateTimeOffset]::UtcNow.AddSeconds($ReadyTimeoutSeconds)
while ([DateTimeOffset]::UtcNow -lt $deadline) {
    if ($process.HasExited) { throw "ControlHost 提前退出，退出码 $($process.ExitCode)；见 $errLog" }
    try {
        $response = Invoke-ScpCvWeb -Uri ($ListenUrls.Split(';')[0].TrimEnd('/') + '/health/ready')
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ready) { throw "ControlHost 未在 $ReadyTimeoutSeconds 秒内就绪；见 $outLog" }
Write-Log 'ControlHost /health/ready = 200'

if (-not $StartWorkers) {
    Write-Log '未指定 -StartWorkers，跳过 Worker 编排。'
    return
}

$baseUrl = $ListenUrls.Split(';')[0].TrimEnd('/')
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$headers = @{ Origin = ([Uri]$baseUrl).GetLeftPart([System.UriPartial]::Authority) }
$csrf = (Invoke-ScpCvWeb -Uri "$baseUrl/api/auth/csrf/" -WebSession $session -Headers $headers).Content | ConvertFrom-Json | Select-Object -ExpandProperty csrfToken
Invoke-ScpCvWeb -Method Post -Uri "$baseUrl/api/auth/login/" -WebSession $session -Headers $headers `
    -ContentType 'application/json' -Body (@{ username = $DevelopmentUsername; password = $DevelopmentPassword } | ConvertTo-Json) | Out-Null
$headers['X-CSRFToken'] = $csrf
$launch = (Invoke-ScpCvWeb -Method Post -Uri "$baseUrl/api/system/restart/" -WebSession $session -Headers $headers).Content | ConvertFrom-Json
Write-Log ("Worker 编排：group_epoch={0} detail={1}" -f $launch.group_epoch, $launch.detail)
