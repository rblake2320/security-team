[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8765,
    [ValidateSet('operator', 'demo')]
    [string]$Mode = 'operator',
    [switch]$RequireAccessHeader,
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$missionRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$webRoot = Join-Path $missionRoot 'web'
$distIndex = Join-Path $webRoot 'dist\index.html'
$profileReceipt = Join-Path $webRoot 'dist\aegis-build-profile.txt'
$expectedProfile = if ($Mode -eq 'demo') { 'showcase' } else { 'operator' }

if (-not $SkipBuild) {
    if (-not (Test-Path -LiteralPath (Join-Path $webRoot 'node_modules'))) {
        Push-Location $webRoot
        try { npm ci } finally { Pop-Location }
    }

    $sourceFiles = Get-ChildItem -LiteralPath (Join-Path $webRoot 'src') -Recurse -File
    $needsBuild = -not (Test-Path -LiteralPath $distIndex)
    if (-not $needsBuild) {
        $builtAt = (Get-Item -LiteralPath $distIndex).LastWriteTimeUtc
        $needsBuild = $null -ne ($sourceFiles | Where-Object LastWriteTimeUtc -gt $builtAt | Select-Object -First 1)
    }
    if (-not $needsBuild) {
        $actualProfile = if (Test-Path -LiteralPath $profileReceipt) { (Get-Content -Raw -LiteralPath $profileReceipt).Trim() } else { '' }
        $needsBuild = $actualProfile -ne $expectedProfile
    }
    if ($needsBuild) {
        Push-Location $webRoot
        try {
            if ($expectedProfile -eq 'showcase') { npm run build:showcase } else { npm run build }
        } finally {
            Pop-Location
        }
    }
}

if (-not (Test-Path -LiteralPath $distIndex)) {
    throw 'The web build is missing. Run launch.ps1 without -SkipBuild first.'
}
if (-not $SkipBuild -and (Get-Content -Raw -LiteralPath $profileReceipt).Trim() -ne $expectedProfile) {
    throw "The web build profile does not match requested mode $Mode."
}

Write-Host "Opening AEGIS Mission Control at http://127.0.0.1:$Port ($Mode mode)" -ForegroundColor Green
$serverArgs = @((Join-Path $missionRoot 'server.py'), '--port', $Port, '--mode', $Mode)
if ($RequireAccessHeader) { $serverArgs += '--require-access-header' }
python @serverArgs
