param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot),
    [string[]]$AllowedHost = @(),
    [ValidateRange(1024, 65535)]
    [int]$Port = 8790,
    [switch]$NoBrowser,
    [switch]$RunOnce
)

$ErrorActionPreference = "Stop"
$missionRoot = $PSScriptRoot
$python = Join-Path $missionRoot ".venv\Scripts\python.exe"
$webDist = Join-Path $missionRoot "web\dist\index.html"
$profileReceipt = Join-Path $missionRoot "web\dist\aegis-build-profile.txt"
$apiOrigin = "http://127.0.0.1:$Port"
$serverProcess = $null
$connectorId = $null

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "AEGIS dependencies are not installed. Run the setup commands in mission-control\README.md first."
}
if (-not (Test-Path -LiteralPath $RepositoryRoot -PathType Container)) {
    throw "RepositoryRoot must identify an existing authorized folder."
}

Push-Location $missionRoot
try {
    $needsBuild = -not (Test-Path -LiteralPath $webDist -PathType Leaf)
    if (-not $needsBuild) {
        $profile = if (Test-Path -LiteralPath $profileReceipt) { (Get-Content -Raw -LiteralPath $profileReceipt).Trim() } else { "" }
        $needsBuild = $profile -ne "operator"
    }
    if (-not $needsBuild) {
        $builtAt = (Get-Item -LiteralPath $webDist).LastWriteTimeUtc
        $needsBuild = $null -ne (Get-ChildItem -LiteralPath (Join-Path $missionRoot "web\src") -Recurse -File | Where-Object LastWriteTimeUtc -gt $builtAt | Select-Object -First 1)
    }
    if ($needsBuild) {
        Push-Location (Join-Path $missionRoot "web")
        try {
            & npm run build
            if ($LASTEXITCODE -ne 0) { throw "AEGIS interface build failed." }
        }
        finally { Pop-Location }
    }

    $serverReady = $false
    try {
        $health = Invoke-RestMethod -Uri "$apiOrigin/api/health" -TimeoutSec 2
        $serverReady = $health.status -eq "ok"
    }
    catch { $serverReady = $false }

    if (-not $serverReady) {
        $runtime = Join-Path $missionRoot "runtime"
        New-Item -ItemType Directory -Path $runtime -Force | Out-Null
        $serverProcess = Start-Process -FilePath $python -ArgumentList @("saas_server.py", "--port", $Port) -WorkingDirectory $missionRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime "product-server.log") -RedirectStandardError (Join-Path $runtime "product-server-error.log")
        foreach ($attempt in 1..30) {
            Start-Sleep -Milliseconds 500
            try {
                $health = Invoke-RestMethod -Uri "$apiOrigin/api/health" -TimeoutSec 2
                if ($health.status -eq "ok") { $serverReady = $true; break }
            }
            catch {
                if ($serverProcess.HasExited) { throw "AEGIS local server exited during startup. See runtime\product-server-error.log." }
            }
        }
    }
    if (-not $serverReady) { throw "AEGIS local server did not become healthy." }

    $connectorBody = @{
        name = "Local seven-team worker"
        capabilities = @("assessment.execute", "evidence.analyze", "gate.run")
    } | ConvertTo-Json
    $provisioned = Invoke-RestMethod -Method Post -Uri "$apiOrigin/api/v1/connectors" -ContentType "application/json" -Body $connectorBody
    $connectorId = $provisioned.connector.id

    $env:AEGIS_API_URL = $apiOrigin
    $env:AEGIS_CONNECTOR_TOKEN = $provisioned.token
    $env:AEGIS_PROGRAM_ROOT = (Resolve-Path -LiteralPath $RepositoryRoot).Path
    $env:AEGIS_ALLOWED_ROOTS = (Resolve-Path -LiteralPath $RepositoryRoot).Path
    $env:AEGIS_ALLOWED_HOSTS = ($AllowedHost -join ",")

    Write-Host "AEGIS product is running at $apiOrigin" -ForegroundColor Green
    Write-Host "Authorized folder: $($env:AEGIS_ALLOWED_ROOTS)"
    if ($AllowedHost.Count) { Write-Host "Authorized hosts: $($env:AEGIS_ALLOWED_HOSTS)" }
    Write-Host "Close this window or press Ctrl+C to stop the worker."
    if (-not $NoBrowser) { Start-Process "$apiOrigin/#/engagements" }
    $workerArguments = @("-m", "aegis_connector")
    if ($RunOnce) { $workerArguments += "--once" }
    & $python @workerArguments
}
finally {
    if ($connectorId) {
        try { Invoke-RestMethod -Method Delete -Uri "$apiOrigin/api/v1/connectors/$connectorId" | Out-Null } catch {}
    }
    Remove-Item Env:AEGIS_CONNECTOR_TOKEN -ErrorAction SilentlyContinue
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id
    }
    Pop-Location
}
