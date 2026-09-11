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
    [int]$ReadyTimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RuntimeRoot)) {
    $RuntimeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\src')).Path
}
if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    throw '必须显式传入 -DataRoot，避免无头进程误用其他运行时的数据目录。'
}
$dataPath = [System.IO.Path]::GetFullPath($DataRoot)

function Get-HeadlessControlHost {
    Get-CimInstance Win32_Process -Filter "Name='ScpCv.ControlHost.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($dataPath, [StringComparison]::OrdinalIgnoreCase) }
}

if ($Stop) {
    $targets = @(Get-HeadlessControlHost)
    if ($targets.Count -eq 0) {
        Write-Host "DataRoot 下没有运行中的 ControlHost：$dataPath"
        return
    }
    foreach ($target in $targets) {
        Stop-Process -Id $target.ProcessId -Force
        Write-Host "已停止 ControlHost pid=$($target.ProcessId)"
    }
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

New-Item -ItemType Directory -Force -Path $dataPath | Out-Null
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
Write-Host "ControlHost 已无头启动 pid=$($process.Id)"
Write-Host "日志：$outLog"

$ready = $false
$deadline = [DateTimeOffset]::UtcNow.AddSeconds($ReadyTimeoutSeconds)
while ([DateTimeOffset]::UtcNow -lt $deadline) {
    if ($process.HasExited) { throw "ControlHost 提前退出，退出码 $($process.ExitCode)；见 $errLog" }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -SkipCertificateCheck -TimeoutSec 5 -Uri ($ListenUrls.Split(';')[0].TrimEnd('/') + '/health/ready')
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ready) { throw "ControlHost 未在 $ReadyTimeoutSeconds 秒内就绪；见 $outLog" }
Write-Host 'ControlHost /health/ready = 200'

if (-not $StartWorkers) {
    Write-Host '未指定 -StartWorkers，跳过 Worker 编排。'
    return
}

$baseUrl = $ListenUrls.Split(';')[0].TrimEnd('/')
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$headers = @{ Origin = ([Uri]$baseUrl).GetLeftPart([System.UriPartial]::Authority) }
$csrf = (Invoke-RestMethod -SkipCertificateCheck -Uri "$baseUrl/api/auth/csrf/" -WebSession $session -Headers $headers).csrfToken
Invoke-RestMethod -SkipCertificateCheck -Method Post -Uri "$baseUrl/api/auth/login/" -WebSession $session -Headers $headers `
    -ContentType 'application/json' -Body (@{ username = $DevelopmentUsername; password = $DevelopmentPassword } | ConvertTo-Json) | Out-Null
$headers['X-CSRFToken'] = $csrf
$launch = Invoke-RestMethod -SkipCertificateCheck -Method Post -Uri "$baseUrl/api/system/restart/" -WebSession $session -Headers $headers
Write-Host ("Worker 编排：group_epoch={0} detail={1}" -f $launch.group_epoch, $launch.detail)
