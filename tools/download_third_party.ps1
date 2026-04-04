[CmdletBinding()]
param(
    [switch]$DownloadMediaMTX = $true,
    [switch]$InstallLibreOffice = $false
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ThirdPartyRoot = Join-Path $PSScriptRoot 'third_party'
$MediaMTXRoot = Join-Path $ThirdPartyRoot 'mediamtx'
$LibreOfficeRoot = Join-Path $ThirdPartyRoot 'libreoffice'

New-Item -ItemType Directory -Force -Path $ThirdPartyRoot | Out-Null
New-Item -ItemType Directory -Force -Path $MediaMTXRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LibreOfficeRoot | Out-Null

function Get-LatestGithubAsset {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Repository,

        [Parameter(Mandatory = $true)]
        [string]$AssetPattern
    )

    $release = Invoke-RestMethod -Headers @{ 'User-Agent' = 'SCP-cv' } -Uri "https://api.github.com/repos/$Repository/releases/latest"
    $asset = $release.assets | Where-Object { $_.name -match $AssetPattern } | Select-Object -First 1

    if (-not $asset) {
        throw "Unable to find a release asset matching $AssetPattern in $Repository."
    }

    return $asset
}

if ($DownloadMediaMTX) {
    Write-Host 'Downloading MediaMTX...' -ForegroundColor Cyan
    $mediaMtxAsset = Get-LatestGithubAsset -Repository 'bluenviron/mediamtx' -AssetPattern 'windows_amd64\.zip$'
    $archivePath = Join-Path $ThirdPartyRoot $mediaMtxAsset.name

    Invoke-WebRequest -Headers @{ 'User-Agent' = 'SCP-cv' } -Uri $mediaMtxAsset.browser_download_url -OutFile $archivePath

    if (Test-Path $MediaMTXRoot) {
        Remove-Item -Path $MediaMTXRoot -Recurse -Force
    }

    New-Item -ItemType Directory -Force -Path $MediaMTXRoot | Out-Null
    Expand-Archive -Path $archivePath -DestinationPath $MediaMTXRoot -Force
    Write-Host "MediaMTX extracted to $MediaMTXRoot" -ForegroundColor Green
}

if ($InstallLibreOffice) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host 'Installing LibreOffice through winget...' -ForegroundColor Cyan
        winget install --id TheDocumentFoundation.LibreOffice -e --silent --accept-package-agreements --accept-source-agreements
        Write-Host 'LibreOffice install command completed. Confirm that soffice.exe is available on PATH.' -ForegroundColor Green
    }
    else {
        Write-Warning 'winget is not available, so LibreOffice cannot be installed automatically.'
    }
}

Write-Host 'Third-party executables are ready.' -ForegroundColor Green
