[CmdletBinding()]
param(
    [ValidateSet('start', 'stop', 'restart', 'status')]
    [string]$Action = 'status',
    [string]$RuntimeRoot = (Join-Path $PSScriptRoot '..\src'),
    [string]$MediaMtxPath = ''
)

$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot 'runtime-processes.json'
$supervisor = Join-Path $RuntimeRoot 'ScpCv.Supervisor\bin\Debug\net10.0-windows10.0.19041.0\ScpCv.Supervisor.exe'
$supervisorArgs = @('--action', $Action, '--runtime-root', $RuntimeRoot, '--state', $statePath)
if ($MediaMtxPath) { $supervisorArgs += @('--mediamtx', $MediaMtxPath) }

switch ($Action) {
    'start' { if (-not (Test-Path $supervisor)) { throw "请先构建 Supervisor: $supervisor" }; & $supervisor @supervisorArgs; if ($LASTEXITCODE -ne 0) { throw "Supervisor 启动失败，退出码 $LASTEXITCODE" } }
    'stop' { if (Test-Path $supervisor) { & $supervisor @supervisorArgs } else { Write-Host 'Supervisor 可执行文件不存在。' } }
    'restart' { if (-not (Test-Path $supervisor)) { throw "请先构建 Supervisor: $supervisor" }; & $supervisor @supervisorArgs; if ($LASTEXITCODE -ne 0) { throw "Supervisor 重启失败，退出码 $LASTEXITCODE" } }
    'status' { if (Test-Path $supervisor) { & $supervisor @supervisorArgs } else { Write-Host 'Supervisor 可执行文件不存在。' } }
}
