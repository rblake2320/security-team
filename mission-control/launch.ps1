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
    if ($needsBuild) {
        Push-Location $webRoot
        try { npm run build } finally { Pop-Location }
    }
}

if (-not (Test-Path -LiteralPath $distIndex)) {
    throw 'The web build is missing. Run launch.ps1 without -SkipBuild first.'
}

Write-Host "Opening AEGIS Mission Control at http://127.0.0.1:$Port ($Mode mode)" -ForegroundColor Green
$serverArgs = @((Join-Path $missionRoot 'server.py'), '--port', $Port, '--mode', $Mode)
if ($RequireAccessHeader) { $serverArgs += '--require-access-header' }
python @serverArgs
