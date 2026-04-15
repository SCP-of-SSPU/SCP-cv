<#
.SYNOPSIS
    下载 SCP-cv 项目所需的第三方依赖（mpv/libmpv）。

.DESCRIPTION
    从 shinchiro/mpv-winbuild-cmake GitHub Releases 下载
    mpv-dev-x86_64 压缩包，解压到 tools/third_party/mpv/。
    需要 7-Zip 或系统自带 tar 解压 .7z / .tar.gz。

.PARAMETER Force
    若已存在 libmpv-2.dll 则跳过下载，指定 -Force 强制重新下载。

.EXAMPLE
    .\tools\download_third_party.ps1
    .\tools\download_third_party.ps1 -Force
#>
[CmdletBinding()]
param(
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
$MpvDir = Join-Path $ScriptDir "third_party\mpv"

# ═══════════════ 配置 ═══════════════
# shinchiro/mpv-winbuild-cmake 仓库 API
$GithubApiUrl = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"

# 目标文件名模式：mpv-dev-x86_64-*.7z 或 .tar.gz
$AssetPattern = "mpv-dev-x86_64"

# 必须存在的关键文件
$RequiredDll = "libmpv-2.dll"


function Find-7Zip {
    <#
    .SYNOPSIS 查找 7-Zip 可执行文件路径。
    #>
    $candidates = @(
        "7z",
        "${env:ProgramFiles}\7-Zip\7z.exe",
        "${env:ProgramFiles(x86)}\7-Zip\7z.exe"
    )
    foreach ($path in $candidates) {
        if (Get-Command $path -ErrorAction SilentlyContinue) {
            return $path
        }
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}


function Get-LatestMpvDevAsset {
    <#
    .SYNOPSIS 从 GitHub API 获取最新 mpv-dev-x86_64 资产下载链接。
    .OUTPUTS [PSCustomObject] 包含 name 和 browser_download_url。
    #>
    Write-Host "[INFO] 查询最新版本..." -ForegroundColor Cyan
    $headers = @{ "User-Agent" = "SCP-cv-downloader" }
    $release = Invoke-RestMethod -Uri $GithubApiUrl -Headers $headers -TimeoutSec 30

    $asset = $release.assets | Where-Object { $_.name -like "$AssetPattern*" } | Select-Object -First 1
    if (-not $asset) {
        throw "未找到匹配 '$AssetPattern' 的资产文件（版本：$($release.tag_name)）"
    }

    Write-Host "[INFO] 找到：$($asset.name)（$($release.tag_name)）" -ForegroundColor Green
    return $asset
}


function Expand-7zArchive {
    <#
    .SYNOPSIS 使用 7-Zip 解压 .7z 文件。
    .PARAMETER ArchivePath 压缩包路径。
    .PARAMETER DestinationPath 解压目标目录。
    #>
    param(
        [string]$ArchivePath,
        [string]$DestinationPath
    )
    $sevenZip = Find-7Zip
    if (-not $sevenZip) {
        throw "需要 7-Zip 解压 .7z 文件。请安装 7-Zip（https://www.7-zip.org/）或使用 winget install 7zip.7zip"
    }
    Write-Host "[INFO] 使用 7-Zip 解压..." -ForegroundColor Cyan
    & $sevenZip x $ArchivePath "-o$DestinationPath" -y | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "7-Zip 解压失败（exit code: $LASTEXITCODE）"
    }
}


function Expand-TarGzArchive {
    <#
    .SYNOPSIS 使用 tar 解压 .tar.gz 文件。
    .PARAMETER ArchivePath 压缩包路径。
    .PARAMETER DestinationPath 解压目标目录。
    #>
    param(
        [string]$ArchivePath,
        [string]$DestinationPath
    )
    Write-Host "[INFO] 使用 tar 解压..." -ForegroundColor Cyan
    tar -xzf $ArchivePath -C $DestinationPath
    if ($LASTEXITCODE -ne 0) {
        throw "tar 解压失败（exit code: $LASTEXITCODE）"
    }
}


# ═══════════════ 主流程 ═══════════════

Write-Host "========================================" -ForegroundColor Yellow
Write-Host " SCP-cv 第三方依赖下载" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

# 检查是否已存在
$dllPath = Join-Path $MpvDir $RequiredDll
if ((Test-Path $dllPath) -and (-not $Force)) {
    Write-Host "[OK] $RequiredDll 已存在，跳过下载。使用 -Force 参数重新下载。" -ForegroundColor Green
    exit 0
}

# 确保目标目录存在
if (-not (Test-Path $MpvDir)) {
    New-Item -ItemType Directory -Path $MpvDir -Force | Out-Null
}

# 获取下载链接
$asset = Get-LatestMpvDevAsset
$downloadUrl = $asset.browser_download_url
$fileName = $asset.name
$tempFile = Join-Path $env:TEMP $fileName

# 下载
Write-Host "[INFO] 下载中：$downloadUrl" -ForegroundColor Cyan
Write-Host "[INFO] 保存到：$tempFile" -ForegroundColor Cyan
Invoke-WebRequest -Uri $downloadUrl -OutFile $tempFile -TimeoutSec 300

if (-not (Test-Path $tempFile)) {
    throw "下载失败：$tempFile 不存在"
}

# 解压到临时目录
$tempExtract = Join-Path $env:TEMP "mpv-dev-extract"
if (Test-Path $tempExtract) {
    Remove-Item -Path $tempExtract -Recurse -Force
}
New-Item -ItemType Directory -Path $tempExtract -Force | Out-Null

if ($fileName -match "\.7z$") {
    Expand-7zArchive -ArchivePath $tempFile -DestinationPath $tempExtract
} elseif ($fileName -match "\.(tar\.gz|tgz)$") {
    Expand-TarGzArchive -ArchivePath $tempFile -DestinationPath $tempExtract
} else {
    throw "不支持的压缩格式：$fileName"
}

# 查找 libmpv-2.dll（可能在子目录中）
$foundDll = Get-ChildItem -Path $tempExtract -Recurse -Filter $RequiredDll | Select-Object -First 1
if (-not $foundDll) {
    throw "解压后未找到 $RequiredDll"
}

# 复制 libmpv-2.dll 到目标目录
$dllSource = $foundDll.FullName
Copy-Item -Path $dllSource -Destination $MpvDir -Force
Write-Host "[OK] 已复制 $RequiredDll → $MpvDir" -ForegroundColor Green

# 验证
if (Test-Path $dllPath) {
    $dllInfo = Get-Item $dllPath
    Write-Host "[OK] libmpv-2.dll 大小：$([math]::Round($dllInfo.Length / 1MB, 1)) MB" -ForegroundColor Green
} else {
    throw "$RequiredDll 复制失败"
}

# 清理临时文件
Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "[OK] 临时文件已清理" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host " 下载完成！" -ForegroundColor Green
Write-Host " 路径：$dllPath" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
