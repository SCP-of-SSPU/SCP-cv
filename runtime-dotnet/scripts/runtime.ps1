[CmdletBinding()]
param(
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string]$Action = 'status',
    [string]$RuntimeRoot = (Join-Path $PSScriptRoot '..\src')
)

$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot 'runtime-processes.json'
$supervisor = Join-Path $RuntimeRoot 'ScpCv.Supervisor\bin\Debug\net10.0-windows10.0.19041.0\ScpCv.Supervisor.exe'

switch ($Action) {
    'start' { if (-not (Test-Path $supervisor)) { throw "请先构建 Supervisor: $supervisor" }; & $supervisor start; }
    'stop' { if (Test-Path $statePath) { Write-Host "请由 Supervisor 根据 PID/start-time 证据执行停止；不会按名称强杀进程。" } else { Write-Host '没有已登记的运行时。' } }
    'restart' { & $PSCommandPath -Action stop -RuntimeRoot $RuntimeRoot; & $PSCommandPath -Action start -RuntimeRoot $RuntimeRoot }
    'status' { if (Test-Path $statePath) { Get-Content $statePath } else { Write-Host 'Supervisor 状态文件不存在。' } }
}
