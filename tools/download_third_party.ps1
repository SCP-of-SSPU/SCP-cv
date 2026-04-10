[CmdletBinding()]
param(
    [switch]$DownloadMediaMTX = $true
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ThirdPartyRoot = Join-Path $PSScriptRoot 'third_party'
$MediaMTXRoot = Join-Path $ThirdPartyRoot 'mediamtx'

New-Item -ItemType Directory -Force -Path $ThirdPartyRoot | Out-Null
New-Item -ItemType Directory -Force -Path $MediaMTXRoot | Out-Null

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

Write-Host 'Third-party executables are ready.' -ForegroundColor Green
