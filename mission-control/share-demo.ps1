[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8766
)

$ErrorActionPreference = 'Stop'
$missionRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$webRoot = Join-Path $missionRoot 'web'
$runtimeRoot = Join-Path $missionRoot 'runtime'
$distIndex = Join-Path $webRoot 'dist\index.html'
$serverPath = Join-Path $missionRoot 'server.py'

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw 'cloudflared is not installed or is not on PATH.'
}

Push-Location $webRoot
try {
    if (-not (Test-Path -LiteralPath (Join-Path $webRoot 'node_modules'))) { npm ci }
    npm run build:showcase
} finally {
    Pop-Location
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
$stdout = Join-Path $runtimeRoot 'demo-server.out.log'
$stderr = Join-Path $runtimeRoot 'demo-server.err.log'
$server = Start-Process -FilePath 'python' `
    -ArgumentList @($serverPath, '--port', $Port, '--mode', 'demo') `
    -WorkingDirectory (Split-Path -Parent $missionRoot) `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 24; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
            if ($health.status -eq 'ok' -and $health.mode -eq 'demo') { $ready = $true; break }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) { throw "Demo server did not become healthy. Inspect $stderr" }

    Write-Host 'Public demo safety boundary: READ-ONLY + REDACTED + SYNTHETIC AGENT FEED' -ForegroundColor Yellow
    Write-Host 'Cloudflare will print a temporary trycloudflare.com URL below. Press Ctrl+C to stop sharing.' -ForegroundColor Green
    cloudflared tunnel --url "http://127.0.0.1:$Port" --no-autoupdate
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force
    }
}
