$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$CollectorDir = Join-Path $Root "leaderboard-collector"
$Port = if ($env:COLLECTOR_PORT) { $env:COLLECTOR_PORT } else { "9000" }
$DataDir = Join-Path $Root "leaderboard-data"
New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
$env:TRADEVERSE_COLLECTOR_DATA = $DataDir

$Venv = Join-Path $CollectorDir ".venv"
if (-not (Test-Path $Venv)) {
    python -m venv $Venv
    & "$Venv\Scripts\pip.exe" install -q -r (Join-Path $CollectorDir "requirements.txt")
}

Write-Host "Leaderboard collector on http://0.0.0.0:$Port (data: $DataDir)"
& "$Venv\Scripts\python.exe" (Join-Path $CollectorDir "main.py")
