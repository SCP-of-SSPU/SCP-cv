<#
.SYNOPSIS
  普通控制命令的端到端“开始执行”基准（SC-006：1000 样本 p95 ≤ 1000 ms）。

.DESCRIPTION
  通过真实 ControlHost 提交 N 条窗口音量命令，默认在 4 个窗口之间轮询并留出提交间隔，
  避免同目标“后到意图覆盖先前意图”的折叠把样本吃掉。完成后从命令表读取
  CreatedAt → StartedAt 的真实间隔作为“开始执行”延迟。

  必须连接 SafetyMode=Hardware 且 Supervisor 已拉起真实 Worker 的主机；simulation 没有
  Worker 认领命令，本脚本会直接判定测量无效。
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://localhost:18444',
    [string]$DatabasePath = '',
    [string]$Username = 'qa-admin',
    [Parameter(Mandatory = $true)][string]$Password,
    [int]$Samples = 1000,
    [int[]]$Targets = @(1, 2, 3, 4),
    [int]$DelayMilliseconds = 50,
    [int]$DrainTimeoutSeconds = 180,
    [double]$MaxSupersededRatio = 0.2,
    [string]$HardwareNote = '',
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($DatabasePath)) {
    throw '必须显式传入 -DatabasePath，避免误读其他运行时的命令表。'
}
if (-not (Test-Path -LiteralPath $DatabasePath)) {
    throw "命令表不存在：$DatabasePath"
}

function Get-Percentile {
    param([double[]]$Values, [double]$Percentile)
    if ($Values.Count -eq 0) { return [double]::NaN }
    $sorted = $Values | Sort-Object
    $rank = [Math]::Ceiling($Percentile / 100 * $sorted.Count) - 1
    if ($rank -lt 0) { $rank = 0 }
    if ($rank -ge $sorted.Count) { $rank = $sorted.Count - 1 }
    return [double]$sorted[$rank]
}

function Invoke-Sqlite {
    param([string]$Sql)
    $result = & sqlite3 -readonly $DatabasePath $Sql
    if ($LASTEXITCODE -ne 0) { throw "sqlite3 查询失败：$Sql" }
    return $result
}

# --- 登录 ---
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$origin = ([Uri]$BaseUrl).GetLeftPart([System.UriPartial]::Authority)
$headers = @{ Origin = $origin }
$csrf = (Invoke-RestMethod -Uri "$BaseUrl/api/auth/csrf/" -WebSession $session -Headers $headers).csrfToken
Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/auth/login/" -WebSession $session -Headers $headers `
    -ContentType 'application/json' -Body (@{ username = $Username; password = $Password } | ConvertTo-Json) | Out-Null
$headers['X-CSRFToken'] = $csrf

$targetList = @($Targets | Select-Object -Unique | Sort-Object)
foreach ($target in $targetList) {
    if ($target -lt 1 -or $target -gt 4) { throw "窗口号必须在 1..4：$target" }
}

$startId = [long](Invoke-Sqlite 'SELECT COALESCE(MAX(Id), 0) FROM command_records;')
Write-Host ("基准起点 command id = {0}；样本 {1}；目标窗口 {2}；间隔 {3} ms" -f $startId, $Samples, ($targetList -join '/'), $DelayMilliseconds) -ForegroundColor Cyan

# --- 提交普通控制命令 ---
$httpSamples = [System.Collections.Generic.List[double]]::new()
$submitWatch = [Diagnostics.Stopwatch]::StartNew()
for ($i = 1; $i -le $Samples; $i++) {
    $windowId = $targetList[($i - 1) % $targetList.Count]
    $volume = if ($i % 2 -eq 0) { 40 } else { 60 }
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        Invoke-RestMethod -Method Patch -Uri "$BaseUrl/api/playback/$windowId/volume/" -WebSession $session `
            -Headers $headers -ContentType 'application/json' -Body (@{ volume = $volume } | ConvertTo-Json) | Out-Null
    }
    finally {
        $watch.Stop()
        $httpSamples.Add($watch.Elapsed.TotalMilliseconds)
    }
    if ($DelayMilliseconds -gt 0) { Start-Sleep -Milliseconds $DelayMilliseconds }
}
$submitWatch.Stop()
Write-Host ("提交完成：{0:N1}s，平均 HTTP {1:N1}ms" -f $submitWatch.Elapsed.TotalSeconds, ($httpSamples | Measure-Object -Average).Average) -ForegroundColor Cyan

# --- 等待队列排空 ---
$drainWatch = [Diagnostics.Stopwatch]::StartNew()
$open = 0
do {
    Start-Sleep -Milliseconds 250
    $open = [int](Invoke-Sqlite "SELECT COUNT(*) FROM command_records WHERE Id > $startId AND Status IN ('Pending','Processing');")
    if ($drainWatch.Elapsed.TotalSeconds -gt $DrainTimeoutSeconds) { break }
} while ($open -gt 0)
$drainWatch.Stop()

# --- 取样 ---
$raw = Invoke-Sqlite "SELECT Id, StartedAt - CreatedAt FROM command_records WHERE Id > $startId AND StartedAt IS NOT NULL ORDER BY Id;"
$startedMs = @($raw | Where-Object { $_ -match '^\d+\|' } | ForEach-Object { [double]($_ -split '\|')[1] / 10000.0 })
$enqueued = [int](Invoke-Sqlite "SELECT COUNT(*) FROM command_records WHERE Id > $startId;")
$superseded = [int](Invoke-Sqlite "SELECT COUNT(*) FROM command_records WHERE Id > $startId AND Status = 'Superseded';")
$completed = [int](Invoke-Sqlite "SELECT COUNT(*) FROM command_records WHERE Id > $startId AND Status = 'Completed';")
$supersededRatio = if ($enqueued -gt 0) { $superseded / $enqueued } else { 0 }

$verdict = '通过'
$verdictNote = ''
if ($startedMs.Count -lt $Samples * 0.9) {
    $verdict = '测量无效'
    $verdictNote = "仅 $($startedMs.Count)/$Samples 条命令真正开始执行；请确认 SafetyMode=Hardware 且 Worker 在线。"
}
elseif ($supersededRatio -gt $MaxSupersededRatio) {
    $verdict = '测量无效'
    $verdictNote = "折叠比例 $([Math]::Round($supersededRatio * 100, 1))% 超过阈值；请增大 -DelayMilliseconds 或增加目标窗口。"
}
elseif ((Get-Percentile $startedMs 95) -gt 1000) {
    $verdict = '未通过'
}

$result = [ordered]@{
    samples          = $Samples
    targets          = ($targetList -join ',')
    delay_ms         = $DelayMilliseconds
    enqueued         = $enqueued
    started          = $startedMs.Count
    completed        = $completed
    superseded       = $superseded
    superseded_ratio = [Math]::Round($supersededRatio, 3)
    leftover_open    = $open
    submit_seconds   = [Math]::Round($submitWatch.Elapsed.TotalSeconds, 2)
    drain_seconds    = [Math]::Round($drainWatch.Elapsed.TotalSeconds, 2)
    http_avg_ms      = [Math]::Round(($httpSamples | Measure-Object -Average).Average, 1)
    http_p95_ms      = [Math]::Round((Get-Percentile $httpSamples.ToArray() 95), 1)
    started_p50_ms   = [Math]::Round((Get-Percentile $startedMs 50), 1)
    started_p95_ms   = [Math]::Round((Get-Percentile $startedMs 95), 1)
    started_p99_ms   = [Math]::Round((Get-Percentile $startedMs 99), 1)
    started_max_ms   = [Math]::Round(($startedMs | Measure-Object -Maximum).Maximum, 1)
    verdict          = $verdict
}
$result | ConvertTo-Json | Write-Host
if ($verdictNote) { Write-Host $verdictNote -ForegroundColor Yellow }

if ($OutputPath) {
    $lines = @(
        '# 普通命令基准原始样本'
        ''
        "采集时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')"
        "ControlHost：$BaseUrl"
        "命令表：$DatabasePath"
        "样本：$Samples 次 PATCH /api/playback/{窗口}/volume/（40/60 交替）"
        "目标窗口：$($targetList -join '/')；提交间隔：$DelayMilliseconds ms"
        "硬件/媒体条件：$HardwareNote"
        ''
        '| 指标 | 值 |'
        '| --- | --- |'
        "| 入队命令数 | $($result.enqueued) |"
        "| 已开始执行 | $($result.started) |"
        "| 已完成 | $($result.completed) |"
        "| 被折叠 | $($result.superseded)（$([Math]::Round($supersededRatio * 100, 1))%） |"
        "| 排空后仍未完成 | $($result.leftover_open) |"
        "| HTTP 提交平均 | $($result.http_avg_ms) ms |"
        "| HTTP 提交 p95 | $($result.http_p95_ms) ms |"
        "| 开始执行 p50 | $($result.started_p50_ms) ms |"
        "| 开始执行 p95 | $($result.started_p95_ms) ms |"
        "| 开始执行 p99 | $($result.started_p99_ms) ms |"
        "| 开始执行最大 | $($result.started_max_ms) ms |"
        ''
        "判定（SC-006：p95 ≤ 1000 ms）：$verdict"
    )
    if ($verdictNote) { $lines += $verdictNote }
    $lines | Set-Content -LiteralPath $OutputPath -Encoding utf8
    Write-Host "原始样本已写入 $OutputPath" -ForegroundColor Green
}
