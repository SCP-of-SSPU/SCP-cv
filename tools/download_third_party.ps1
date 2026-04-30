<#
.SYNOPSIS
    Download third-party VLC/libVLC runtime for SCP-cv.

.DESCRIPTION
    Downloads the official Windows x64 VLC zip package from VideoLAN and
    extracts runtime files into tools/third_party/vlc/runtime/.
    python-vlc is only the Python binding; SRT playback still requires
    libvlc.dll, libvlccore.dll, and the plugins directory.

.PARAMETER Force
    Re-download even when libvlc.dll already exists.

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
$VlcDir = Join-Path $ScriptDir "third_party\vlc"
$VlcRuntimeDir = Join-Path $VlcDir "runtime"

$VlcWin64DirectoryUrl = "https://get.videolan.org/vlc/last/win64/"
$VlcDownloadBaseUrl = "https://download.videolan.org/pub/videolan/vlc"
$RequiredDll = "libvlc.dll"
$RequiredCoreDll = "libvlccore.dll"
$RequiredPluginsDir = "plugins"


function Get-LatestVlcZipAsset {
    <#
    .SYNOPSIS Resolve latest Windows x64 VLC zip asset from VideoLAN.
    .OUTPUTS PSCustomObject with name and url.
    #>
    Write-Host "[INFO] Querying latest VLC Windows x64 zip..." -ForegroundColor Cyan
    $response = Invoke-WebRequest -Uri $VlcWin64DirectoryUrl -UseBasicParsing -TimeoutSec 30
    $baseUri = $response.BaseResponse.ResponseUri.AbsoluteUri
    $matches = [regex]::Matches($response.Content, 'href="(?<name>vlc-(?<version>[^"/]+)-win64\.zip)"')

    if ($matches.Count -eq 0) {
        throw "No VLC win64 zip asset found at $baseUri"
    }

    $fileName = $matches[0].Groups["name"].Value
    $version = $matches[0].Groups["version"].Value
    $downloadUri = "$VlcDownloadBaseUrl/$version/win64/$fileName"
    Write-Host "[INFO] Found: $fileName" -ForegroundColor Green

    return [PSCustomObject]@{
        name = $fileName
        url = $downloadUri
    }
}


function Assert-VlcRuntime {
    <#
    .SYNOPSIS Validate required VLC runtime files.
    .PARAMETER RuntimeDir VLC runtime directory.
    #>
    param(
        [string]$RuntimeDir
    )

    $libvlcPath = Join-Path $RuntimeDir $RequiredDll
    $corePath = Join-Path $RuntimeDir $RequiredCoreDll
    $pluginsPath = Join-Path $RuntimeDir $RequiredPluginsDir

    if (-not (Test-Path $libvlcPath)) {
        throw "Missing $RequiredDll at $libvlcPath"
    }
    if (-not (Test-Path $corePath)) {
        throw "Missing $RequiredCoreDll at $corePath"
    }
    if (-not (Test-Path $pluginsPath)) {
        throw "Missing $RequiredPluginsDir directory at $pluginsPath"
    }
}


Write-Host "========================================" -ForegroundColor Yellow
Write-Host " SCP-cv third-party dependency download" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow

$dllPath = Join-Path $VlcRuntimeDir $RequiredDll
if ((Test-Path $dllPath) -and (-not $Force)) {
    Assert-VlcRuntime -RuntimeDir $VlcRuntimeDir
    Write-Host "[OK] $RequiredDll already exists. Use -Force to re-download." -ForegroundColor Green
    exit 0
}

if (Test-Path $VlcRuntimeDir) {
    Remove-Item -Path $VlcRuntimeDir -Recurse -Force
}
New-Item -ItemType Directory -Path $VlcRuntimeDir -Force | Out-Null

$asset = Get-LatestVlcZipAsset
$tempFile = Join-Path $env:TEMP $asset.name
$tempExtract = Join-Path $env:TEMP "scp-cv-vlc-extract"

try {
    Write-Host "[INFO] Downloading: $($asset.url)" -ForegroundColor Cyan
    Write-Host "[INFO] Saving to: $tempFile" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $asset.url -OutFile $tempFile -UseBasicParsing -TimeoutSec 300

    if (Test-Path $tempExtract) {
        Remove-Item -Path $tempExtract -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempExtract -Force | Out-Null

    Write-Host "[INFO] Extracting VLC zip..." -ForegroundColor Cyan
    Expand-Archive -Path $tempFile -DestinationPath $tempExtract -Force

    $foundDll = Get-ChildItem -Path $tempExtract -Recurse -Filter $RequiredDll | Select-Object -First 1
    if (-not $foundDll) {
        throw "Extracted package does not contain $RequiredDll"
    }

    $sourceDir = Split-Path -Parent $foundDll.FullName
    Copy-Item -Path (Join-Path $sourceDir "*") -Destination $VlcRuntimeDir -Recurse -Force
    Assert-VlcRuntime -RuntimeDir $VlcRuntimeDir

    $dllInfo = Get-Item $dllPath
    Write-Host "[OK] VLC runtime prepared: $VlcRuntimeDir" -ForegroundColor Green
    Write-Host "[OK] libvlc.dll size: $([math]::Round($dllInfo.Length / 1MB, 1)) MB" -ForegroundColor Green
}
finally {
    Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Temporary files removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host " Download complete" -ForegroundColor Green
Write-Host " Path: $dllPath" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Yellow
